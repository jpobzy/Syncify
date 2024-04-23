from flask import Flask, render_template, request
import requests, json, base64, jwt, datetime, glob
from dateutil.relativedelta import relativedelta
from flask_socketio import SocketIO
from urllib.parse import urlencode, urlparse, parse_qs


app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

p8_files = glob.glob('*.p8')
if p8_files:
    for file in p8_files:
        p8_file = file

else:
    raise Exception("No .p8 files found in the current working directory.")




apple_music_developer_token =  {}
apple_music_authentication_headers = {}
apple_music_access_token = {}
apple_music_user_id = ''


spotify_access_token = {}
spotify_user_id = ''
spotify_authentication_headers = {}
spotify_beginning_url ='https://api.spotify.com/v1/'




with open('Spotify_config.json') as spotify_config_file:
    config = json.load(spotify_config_file)
    client_id = config['client_id']
    redirect_uri = config['redirect_uri']
    client_secret = config['client_secret']


with open('AM_config.json') as am_config_file:
    config = json.load(am_config_file)
    kid = config['key_id']
    iss =  config['iss']



@app.route("/")
def root():
    return render_template('index.html')


##################### apple music login process ##################
@socketio.on('login_apple_music_user')
def button_clicked():
    print('login-button was clicked')
    if 'developer_Token' not in apple_music_developer_token:
        create_Apple_Music_Developer_Tokens()
        print('generated Apple Music Developer Token')
    else:
        print('Apple Music Developer Token is already generated')
    print()
    socketio.emit('generate_music_user_token', apple_music_developer_token['developer_token'])

def create_Apple_Music_Developer_Tokens():
    issuedAt, expirationTime = get_IssuedAt_And_ExpTime()
    with open(p8_file, 'r') as file:
        secret = file.read()
    headers = {
        "alg": 'ES256',
        "kid": kid 
    }
    payload = {
        "iss": iss,  
        "exp": expirationTime,
        "iat": issuedAt
    }
    developer_token = jwt.encode(payload, secret, algorithm='ES256', headers=headers)       
    apple_music_developer_token['developer_token'] = developer_token
    apple_music_authentication_headers['Authorization'] = 'Bearer ' + developer_token
    apple_music_access_token['developer_token'] = developer_token
    return 

def get_IssuedAt_And_ExpTime():
    present_date = datetime.datetime.now()
    future_date = present_date + relativedelta(months=+5)
    apple_music_access_token['expires_in'] = future_date   
    future_unix_timestamp = int(future_date.timestamp())
    current_unix_timestamp = int(present_date.timestamp())
    return (current_unix_timestamp, future_unix_timestamp )


############# generating apple music token ###############
@socketio.on('set_music_user_token')
def set_Full_Auth(music_user_token):
    apple_music_developer_token['music-user-token'] = music_user_token
    apple_music_authentication_headers['Music-User-Token'] = music_user_token
    req = requests.get(headers=apple_music_authentication_headers, 
                 url='https://api.music.apple.com/v1/me/recent/played',
                 params={'limit': '1'})
    req_content = json.loads(req.content)['data'][0]['attributes']             
    username = req_content['curatorName']
    socketio.emit('apple_music_user_login_success', {'username': username})

    global apple_music_user_id
    apple_music_user_id = req_content['id']




########## generating spotify tokens
@socketio.on('login_spotify_user')
def authorize_spotify():
    with open('scopes/dev_scopes.json') as scopes_file:
        scopes = json.load(scopes_file)['scope']
        scope_string = ' '.join(scopes)

    authorization_base_url = 'https://accounts.spotify.com/authorize'
    spotify_params = {
        'client_id': client_id,
        'response_type': 'code',
        'redirect_uri': redirect_uri,
        'scope': scope_string,
    }
    authorization_url = authorization_base_url + '?' + urlencode(spotify_params)
    print(authorization_url)
    socketio.emit('spotify_authorization_url', {'url': authorization_url, 'rediredctUri': redirect_uri })
    

@socketio.on('spotify_auth_code')
def authorize_spotify(authcode):
    body_params = {
        'grant_type': 'authorization_code',
        'code': authcode,
        'redirect_uri': redirect_uri
    }
    
    credentials = f"{client_id}:{client_secret}"
    
    credentials_base64 = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        'content-type': 'application/x-www-form-urlencoded',
        'Authorization': 'Basic ' + credentials_base64
    }

    req = requests.post('https://accounts.spotify.com/api/token', headers=headers, data=body_params)
    
    set_cached_spotify_token_info(req)
    spotify_authentication_headers['Authorization'] = f"Bearer {spotify_access_token['access_token']}"
    username_req = requests.get(url='https://api.spotify.com/v1/me', 
                                # headers={'Authorization' : f"Bearer {spotify_access_token['access_token']}"})
                                headers= spotify_authentication_headers)

    user = json.loads(username_req.content)
    global spotify_user_id
    spotify_user_id = str(user['id'])
    print(f"users id is {user['id']}")
    
    socketio.emit('spotify_user_login_success', {'username': user['display_name']})


def set_cached_spotify_token_info(req):
    content = json.loads(req.content)
    spotify_access_token['access_token'] = content['access_token']
    
    present_date = datetime.datetime.now()
    future_date = present_date + datetime.timedelta(seconds=content['expires_in'])
    print(f"present time is: {present_date}, token exp time is: {content['expires_in']}, futrure time is: {future_date}")
    
    spotify_access_token['expires_in'] = future_date
    spotify_access_token['refresh_token'] = content['refresh_token']
    return

############### both user accounts authorized ############
@socketio.on('both_accounts_authorized')
def test():
    print(f"spotify token is: {spotify_access_token}")
    
    check_spotify_token_expiration()
    socketio.emit('both_accounts_authorized')


def check_spotify_token_expiration():
    if spotify_access_token:
        present_date = datetime.datetime.now()
        if present_date > spotify_access_token['expires_in']:
            print('spotify token is expired')
            token_url = 'https://accounts.spotify.com/api/token'
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': spotify_access_token['refresh_token'],
                'client_id': client_id,
                'client_secret': client_secret
            }
            req = requests.post(token_url, data=data)
            set_cached_spotify_token_info(req)
        return


@socketio.on('get_spotify_users_playlist_names')
def get_playlist_names():
    print(f"again user id is {spotify_user_id}")
    check_spotify_token_expiration()
    req = requests.get(url=f"https://api.spotify.com/v1/users/{spotify_user_id}/playlists",
                params={'limit': 50}, 
                headers=spotify_authentication_headers)
                # headers={'Authorization' : f"Bearer {spotify_access_token['access_token']}"})
    content = json.loads(req.content)
    print(f"socket.on server get_spotify_users_playlist_names ")


    # print(content['items'])
    socketio.emit('spotify_playlist_data', content['items'])


@socketio.on('transfer_this_spotify_playlist_to_apple_music')
def transfer_spotify_playlist_to_apple_music(playlist_id, playlist_name):
    print(f"beginning the transfer of playlist: {playlist_name}")
    check_spotify_token_expiration()
    req = requests.get(url=f"https://api.spotify.com/v1/playlists/{playlist_id}", headers=spotify_authentication_headers)
    
    content = json.loads(req.content)
    # print(content)
    playlist_next_url = content['tracks']['next']
    
    playlist_tracks = content['tracks']['items']
    while playlist_next_url is not None:
        check_spotify_token_expiration()
        buffer_req = requests.get(url=playlist_next_url, headers=spotify_authentication_headers)
        buffer_content = json.loads(buffer_req.content)
        playlist_tracks += buffer_content['items']
        playlist_next_url = buffer_content['next']
    track_id_arr = []
    
    missed_tracks = []
    track_duration_not_equal_arr = []
    explicit_tracks_missed = []
    
    
    
    for track in playlist_tracks: 
        track_name = track['track']['name'].replace("'", "")
        # feat_artist = track_name.split('(feat.')[-1] if "(feat." in track_name else ""
        track_name = track_name.split('(feat.')[0].replace(":", "")
        track_artists = ', '.join(artist['name'] for artist in track['track']['artists']).replace("'", "").replace('(feat.)', '').replace(')', '') 
        search_query = f'{track_name} {track_artists}'
        track_explicit_content_rating_bool = True if track['track']['explicit'] == True else False
        limit = 5 
        spotify_track_duration_in_millis = track['track']['duration_ms']
        
        
        track_search_req = requests.get(headers=apple_music_authentication_headers,
                                        url='https://api.music.apple.com/v1/catalog/us/search',
                                        params={'types': 'songs', 'term': search_query,'limit': limit})
        content = json.loads(track_search_req.content)
        
        track_counter = 0
        if len(content['results']['songs']['data']) == 0:
            missed_tracks.append(search_query)
        else:
            track_counter = 0 # if tracks == 5 then all tracks found werent equal to search queue
            # print(f"query: {search_query}")
            for item in content['results']['songs']['data']:
                track = item['attributes']
                print(track['name'])
                if 'contentRating' in track:
                    if track['contentRating'] == 'explicit' and track_explicit_content_rating_bool == True:
                        
                        epsilon = 10000  # 10 seconds in milliseconds
                        apple_music_track_duration_in_millis = track['durationInMillis']
                        if abs(int(apple_music_track_duration_in_millis) - int(spotify_track_duration_in_millis)) <= epsilon:
                            print(f"query: {search_query}, result: {track['name']} {track['contentRating']}")
                            song_id = item['id']
                            data = {"id": str(song_id), "type": "library-songs"}
                            track_id_arr.append(data)
                            break
                            
                        track_counter += 1
                        if track_counter == 5:
                            explicit_tracks_missed.append({'spotify_track_result':search_query,
                                                        'apple_music_tracks_result': content
                                                        })
                            print(f'results did could not find right track for {search_query}')
                else:    
                    if track_explicit_content_rating_bool == False:
                        
                        # print("track is non explicit")
                        epsilon = 10000  # 10 seconds in milliseconds
                        apple_music_track_duration_in_millis = track['durationInMillis']
                        if abs(int(apple_music_track_duration_in_millis) - int(spotify_track_duration_in_millis)) <= epsilon:
                            print(f"query: {search_query}, result: {track['name']}")
                            song_id = item['id']
                            data = {"id": str(song_id), "type": "library-songs"}
                            track_id_arr.append(data)
                            break
                            
                        track_counter += 1
                        if track_counter == 5:
                            explicit_tracks_missed.append({'spotify_track_result':search_query,
                                                        'apple_music_tracks_result': content
                                                        })
                            print(f'results did could not find right track for {search_query}')
 
    headers=apple_music_authentication_headers 
    headers['Content-Type'] = 'application/json'
    create_apple_music_playlist_req = requests.post(headers=headers, 
                            url='https://api.music.apple.com/v1/me/library/playlists',
                            json={'attributes': {'description': 'created in SAM', 'name':f"Copy of {playlist_name}"}
                                  }) 
    
    new_playlist_content = json.loads(create_apple_music_playlist_req.content)['data']


    playlist = json.loads(create_apple_music_playlist_req.content)['data'][0]
    playlist_id = playlist['id']
    playlist_link = f"https://music.apple.com/us/playlist/{playlist_id}"


    # get users id and name
    user_req = requests.get(headers = apple_music_authentication_headers, 
        url='https://api.music.apple.com/v1/me/recent/played',
        params={'limit': '1'})

    user_req_data = json.loads(user_req.content)['data']
    print(f"user req is {user_req_data}")
    user_id = user_req_data[0]['id']




    
    
    chunk_size = 100
    for i in range(0, len(track_id_arr), chunk_size):
        chunk = track_id_arr[i:i + chunk_size]
        new_req = requests.post(headers=headers, 
                            url=f'https://api.music.apple.com/v1/me/library/playlists/{playlist_id}/tracks',
                            json={"data": chunk
                                  }) 
        
    print(f"status code {new_req.status_code}")
    transfer_status_code = new_req.status_code #200


    transfer_completion_data = {
        'transfer_status_code': transfer_status_code,
        'missed_tracks' : missed_tracks, # songs that werent found given the search query
        'matched_tracks_but_unequal_duration_time': track_duration_not_equal_arr,
        'playlist_transferred_name': playlist_name
    }
        
    print(f"amount missed: {len(missed_tracks)}")
    print(f"missed tracks for playlist {playlist_name}: {missed_tracks}")
    print(f"tracks that had unequal duration time is: {track_duration_not_equal_arr}")
    print(f"amount of missed tracks with unequal duration time is: {len(track_duration_not_equal_arr)}")
    print(f"missed explicit tracks playlist {playlist_name}: {explicit_tracks_missed}")
    print(f"amount of missed tracks with explicit is: {len(explicit_tracks_missed)}")
    socketio.emit("transfer_completed", transfer_completion_data)


################# transfering apple music playlist to spotify ################

@socketio.on('get_users_apple_music_playlist_names')
def get_users_apple_music_playlists():
    req = requests.get(headers=apple_music_authentication_headers,
                       url='https://api.music.apple.com/v1/me/library/playlists',
                       )
    content = json.loads(req.content)
    playlists_arr = content['data']
    
    
    if 'next' in content:
        next_url = content['next'].split('playlists')[1]
    
        while next_url:
            new_req = requests.get(headers=apple_music_authentication_headers,
                        url=f'https://api.music.apple.com/v1/me/library/playlists{next_url}',
                        )
            content = json.loads(new_req.content)
            playlists_arr += content['data']
            if 'next' not in content:
                break
            next_url = content['next'].split('playlists')[1]
        
    socketio.emit('users_apple_music_playlist_data', playlists_arr)



@socketio.on('transfer_this_apple_music_playlist_to_spotify')
def transfer_apple_music_to_spotify(playlist_id, playlist_name):
    print(f"beginning the transfer of playlist: {playlist_name}")
    req = requests.get(headers=apple_music_authentication_headers,
                       url=f'https://api.music.apple.com/v1/me/library/playlists/{playlist_id}/tracks')
    content = json.loads(req.content)
    tracks_arr = content['data']

    if 'next' in content:
        next_url = content['next'].split('playlists')[1]
        while next_url:
            new_req = requests.get(headers=apple_music_authentication_headers,
                        url=f'https://api.music.apple.com/v1/me/library/playlists{next_url}',
                        )
            content = json.loads(new_req.content)
            tracks_arr += content['data']
            if 'next' not in content:
                break
            next_url = content['next'].split('playlists')[1]
    
    
   
    spotify_track_uri_arr = []
    missed_songs = []
    
    track_duration_not_equal_arr = []
    
    for track in tracks_arr:
        print(track)
        track_name = track['attributes']['name'].replace(")", "").replace("'", "") #8
        feat_artist = track_name.split('(feat.')[-1] if "(feat." in track_name else "" #8
        track_name = track_name.split('(feat.')[0]#8
        track_artist = track['attributes']['artistName'].replace("(feat.", "").replace(")", "").replace("'", "") + feat_artist #8
        track_explicit_content_rating_bool = False if 'contentRating' not in track['attributes'] else True if track['attributes']['contentRating'] == 'explicit' else False# 'contentRating': 'explicit'
        limit = 5
        apple_music_track_duration_in_millis = track['attributes']['durationInMillis']
        search_query = f'{track_name} {track_artist}'     
          
        check_spotify_token_expiration()
        track_search_req = requests.get(url='https://api.spotify.com/v1/search',
                                        headers=spotify_authentication_headers,  
                                        params= {"q": search_query,
                                                "type": "track",
                                                "limit": limit,
                                                'market': "US",
                                                'offset': 0
                                            })

        
        content = json.loads(track_search_req.content)       
        
        track_counter = 0
        if len(content['tracks']['items']) == 0:
            missed_songs.append(search_query) # keep track of songs that weren't searched properly
        else:
            for item in content['tracks']['items']:
                if 'explicit' in item:
                    if item['explicit'] == True and track_explicit_content_rating_bool == True:
                    # if item['explicit'] == True: # old conditional need to check later
                        
                        epsilon = 10000  # 10 seconds in milliseconds
                        if abs(int(item['duration_ms']) - int(apple_music_track_duration_in_millis)) <= epsilon: # if spotify track duration is within 10 seconds of apple music song duration then keep it
                            spotify_track_uri_arr.append(item['uri'])
                            break
                        
                        track_counter += 1
                        if track_counter == 5:
                            track_duration_not_equal_arr.append({'apple_music_track': search_query,  # keep track of songs that got matched but have different track lengths
                                                                'spotify_track_result': 
                                                                    f"{item['name']} {item['artists'][0]['name']}"}) 
                            print(f"AM track {search_query} duration {apple_music_track_duration_in_millis} did not equal spotify track {item['name']} duration: {item['duration_ms']}")
                    else:
                        if track_explicit_content_rating_bool == False:        
                            epsilon = 10000  # 10 seconds in milliseconds
                            if abs(int(item['duration_ms']) - int(apple_music_track_duration_in_millis)) <= epsilon: # if spotify track duration is within 10 seconds of apple music song duration then keep it
                                spotify_track_uri_arr.append(item['uri'])
                                break
                            track_counter += 1
                            if track_counter == 5:
                                track_duration_not_equal_arr.append({'apple_music_track': search_query,  # keep track of songs that got matched but have different track lengths
                                                                    'spotify_track_result': 
                                                                        f"{item['name']} {item['artists'][0]['name']}"}) 
                                print(f"AM track {search_query} duration {apple_music_track_duration_in_millis} did not equal spotify track {item['name']} duration: {item['duration_ms']}")
                    
            

    
            
    
    headers=spotify_authentication_headers
    headers['Content-Type'] = 'application/json'
    check_spotify_token_expiration()
    create_spotify_playlist_req = requests.post(headers=headers,
                                            url=f'https://api.spotify.com/v1/users/{spotify_user_id}/playlists',
                                            json ={'name': f"Copy of {playlist_name}",
                                            'description': "Transfer test",
                                            'public' : True
                                            })
    
    playlist = json.loads(create_spotify_playlist_req.content)

    playlist_id = playlist['id']
    playlist_link = playlist['external_urls']['spotify']

    chunk_size = 100
    for i in range(0, len(spotify_track_uri_arr), chunk_size):
        chunk = spotify_track_uri_arr[i:i + chunk_size]
        check_spotify_token_expiration()
        add_tracks_to_spotify_playlist_req = requests.post(headers=headers,
                                                       url=f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks',
                                                       json={"uris": chunk})
    print(add_tracks_to_spotify_playlist_req.status_code)
    

    transfer_status_code = 200
    transfer_completion_data = {
        'transfer_status_code': add_tracks_to_spotify_playlist_req.status_code,
        'missed_tracks' : missed_songs, # songs that werent found given the search query
        'matched_tracks_but_unequal_duration_time': track_duration_not_equal_arr,
        'playlist_transferred_name': playlist_name
    }

    
    print(f"amount missed: {len(missed_songs)}")
    print(f"missed tracks for playlist {playlist_name}: {missed_songs}")
    print(f"tracks that had unequal duration time is: {track_duration_not_equal_arr}")
    print(f"amount of missed tracks with unequal duration time is: {len(track_duration_not_equal_arr)}")
    socketio.emit("transfer_completed", transfer_completion_data)
    return
    
    
if __name__ == '__main__':
    
    

    host = "0.0.0.0"
    port = 8000

    app.run(debug=False, host=host, port=port)