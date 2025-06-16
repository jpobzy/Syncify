from flask import Flask, render_template, request
import requests, json, base64, jwt, datetime, glob
from dateutil.relativedelta import relativedelta
from flask_socketio import SocketIO
from urllib.parse import urlencode, urlparse, parse_qs
from thefuzz import fuzz

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

@app.route("/callback", strict_slashes=False)
def reroute():
    # Get the current URL path and query string
    current_path = request.full_path
    
    # Construct the new URL with 'www' subdomain
    # new_url = f"http://www.127.0.0.1:8000{current_path}"
    
    print(f"curr path is {current_path}")
    spotify_authorization_code = current_path.split('code=')[1]
    print(f'auth code is {spotify_authorization_code}')
    check_spotify_token_expiration()
    print(f'spotify auth token is: {spotify_access_token}')
    authorize_spotify(spotify_authorization_code)
    
    # Redirect to the new URL
    return  """
            <script>
                // Close the popup window
                window.close();
            </script>
            """


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

    # global apple_music_user_id
    # apple_music_user_id = req_content['id']



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
    # print(f"again user id is {spotify_user_id}")
    check_spotify_token_expiration()
    req = requests.get(url=f"https://api.spotify.com/v1/users/{spotify_user_id}/playlists",
                params={'limit': 50}, 
                headers=spotify_authentication_headers)
    content = json.loads(req.content)
    # print(f"socket.on server get_spotify_users_playlist_names ")


    
    socketio.emit('spotify_playlist_data', content['items'])


@socketio.on('transfer_this_spotify_playlist_to_apple_music')
def transfer_spotify_playlist_to_apple_music(playlist_id, playlist_name):
    transfer_playlist('spotify', 'apple_music', playlist_id)
    return


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
    transfer_playlist('apple_music', 'spotify', playlist_id)
    return



def transfer_playlist(originating_platform, target_platform, playlist_id, playlist_link=None):
    
    print(playlist_id)
    if originating_platform == 'spotify':
        check_spotify_token_expiration()
    req = ((requests.get(url=f"https://api.spotify.com/v1/playlists/{playlist_id}", headers=spotify_authentication_headers)) if originating_platform == 'spotify' else (requests.get(headers=apple_music_authentication_headers, url=f'https://api.music.apple.com/v1/me/library/playlists/{playlist_id}/tracks'))) if playlist_link == None else ((requests.get(url=f"https://api.spotify.com/v1/playlists/{playlist_id}", headers=spotify_authentication_headers)) if not playlist_id.startswith('p') else (requests.get(url=f'https://api.music.apple.com/v1/catalog/us/playlists/{playlist_id}',headers=apple_music_authentication_headers)))
    # print(req.url)
    # return

    content = json.loads(req.content)
    if originating_platform == 'apple_music' and 'data' not in content:
        socketio.emit('playlist_missing_tracks')
        return
  
    playlist_name = (content['name'] if originating_platform == 'spotify' else content['data'][0]['attributes']['name']) if playlist_link==None else (content['name'] if originating_platform == 'spotify' else (content['data'][0]['attributes']['name']))
    tracks = (content['tracks']['items'] if originating_platform == 'spotify' else content['data']) if playlist_link==None else (content['tracks']['items'] if originating_platform == 'spotify' else (content['data'][0]['relationships']['tracks']['data']))

    
    
    
    playlist_next_url = (content['tracks']['next'] if originating_platform == 'spotify' else (content['next'].split('playlists')[1] if 'next' in content else None))
    buffer_count = 0
    while playlist_next_url is not None:
        buffer_count += 1
        if originating_platform == 'spotify':
            check_spotify_token_expiration()
        buffer_req = requests.get(url=playlist_next_url, headers=spotify_authentication_headers) if originating_platform == 'spotify' else requests.get(headers=apple_music_authentication_headers,
                        url=f'https://api.music.apple.com/v1/me/library/playlists{playlist_next_url}')
        buffer_content = json.loads(buffer_req.content)
        tracks += buffer_content['items'] if originating_platform == 'spotify' else buffer_content['data']
        playlist_next_url = buffer_content['next'] if originating_platform == 'spotify' else (buffer_content['next'].split('playlists')[1] if 'next' in buffer_content else None)



    aws_data = [] # stuff being sent to aws lambda
    
    missed_tracks = []
    track_duration_not_equal_arr = []
    explicit_tracks_missed = []

    track_id_or_uri_arr = []
    count = 0
    for track in tracks:
        
        if originating_platform == 'applemusic':
            if 'name' and 'artistName' and 'albumName' not in track['attributes']: # supports when a user adds a track to their playlist thats not in the apple 
                continue
        
        track_name = track['track']['name'].replace("'", "").split('(feat.')[0].replace(":", "") if originating_platform == 'spotify' else track['attributes']['name'].replace(")", "").replace("'", "") 
        track_artists = ', '.join(artist['name'] for artist in track['track']['artists']).replace("'", "").replace('(feat.)', '').replace(')', '') if originating_platform == 'spotify' else track['attributes']['artistName'].replace("(feat.", "").replace(")", "").replace("'", "") + (track_name.split('(feat.')[-1] if "(feat." in track_name else "") 
        search_query = f'{track_name} {track_artists}'
        track_explicit_content_rating_bool = (True if track['track']['explicit'] == True else False) if originating_platform == 'spotify' else (False if 'contentRating' not in track['attributes'] else True if track['attributes']['contentRating'] == 'explicit' else False)
        limit = 5 
        track_duration_in_millis = track['track']['duration_ms'] if originating_platform == 'spotify' else track['attributes']['durationInMillis']
        if originating_platform == 'spotify':
            check_spotify_token_expiration()
        track_search_req = requests.get(url='https://api.spotify.com/v1/search',
                                        headers=spotify_authentication_headers,  
                                        params= {"q": search_query,
                                                "type": "track",
                                                "limit": limit,
                                                'market': "US",
                                                'offset': 0
                                            }) if target_platform == 'spotify' else requests.get(headers=apple_music_authentication_headers,
                                        url='https://api.music.apple.com/v1/catalog/us/search',
                                        params={'types': 'songs', 'term': search_query,'limit': limit})

        content = json.loads(track_search_req.content)   
        # print(search_query)
        # print(content)
        # print()
        if (originating_platform == 'spotify' and len(content['results']) < 1) if playlist_link == None else False: # when searching with given playlist link content return value is diff because of diff url
            missed_tracks.append({'query': search_query, 'origin_platform': originating_platform, 'target_platform': target_platform})
            continue # edge case for when the search query does not find anything when searching for an apple music track that is in spotify

        track_counter = 0
        for item in (content['tracks']['items']) if target_platform == 'spotify' else (content['results']['songs']['data']):
            epsilon = 10000  # 10 seconds in milliseconds

            track1 = search_query 

            search_track_track_name = (item['name']) if target_platform == 'spotify' else (item['attributes']['name']).split('(feat.)')[0]
            search_track_artist_name = ((', '.join(artist['name'] for artist in item['artists'])).replace("'", "").replace('(feat.)', '').replace(')', '')) if target_platform == 'spotify' else (item['attributes']['artistName'])
            
            track2 = f'{search_track_track_name} + {search_track_artist_name}' 
            

            
            token_sort_ratio = fuzz.token_sort_ratio(track1, track2)
            token_set_ratio = fuzz.token_set_ratio(track1, track2)
            partial_token_sort_ratio = fuzz.partial_token_sort_ratio(track1, track2)

            if ((item['explicit'] == True and track_explicit_content_rating_bool == True) if target_platform == 'spotify' else (track['contentRating'] == 'explicit' and track_explicit_content_rating_bool == True) if 'contentRating' in track else False):
                if (abs(int(item['duration_ms']) - int(track_duration_in_millis)) <= epsilon) if target_platform == 'spotify' else (abs(int(item['attributes']['durationInMillis']) - int(track_duration_in_millis)) <= epsilon): # if spotify track duration is within 10 seconds of apple music song duration then keep it
                    data = item['uri'] if target_platform == 'spotify' else {"id": str(item['id']), "type": "library-songs"}
                    
                    track_id_or_uri_arr.append(data) 
                    track_counter +=1

                    (aws_data.append(create_aws_item(item, ('spotify' if target_platform == 'spotify' else 'apple_music'), (track['id'] if target_platform == 'spotify' else None) ))) if playlist_link == None else ''

                    break
                track_counter += 1
                if track_counter == 5:
                    missed_tracks.append({'query': search_query, 'origin_platform': originating_platform, 'target_platform': target_platform})
                    
            else:
                if (abs(int(item['duration_ms']) - int(track_duration_in_millis)) <= epsilon) if target_platform == 'spotify' else (abs(int(item['attributes']['durationInMillis']) - int(track_duration_in_millis)) <= epsilon): # if spotify track duration is within 10 seconds of apple music song duration then keep it
                    data = item['uri'] if target_platform == 'spotify' else {"id": str(item['id']), "type": "library-songs"}
                    track_id_or_uri_arr.append(data) 
                    track_counter +=1


                    (aws_data.append(create_aws_item(item, ('spotify' if target_platform == 'spotify' else 'apple_music'), (track['id'] if target_platform == 'spotify' else None) ))) if playlist_link == None else ''

                    break 
                track_counter += 1
                if track_counter == 5:
                    missed_tracks.append({'query': search_query, 'origin_platform': originating_platform, 'target_platform': target_platform})
                   
    print(len(tracks))
    print(len(track_id_or_uri_arr))
    print(missed_tracks)

    headers=spotify_authentication_headers if target_platform == 'spotify' else apple_music_authentication_headers
    headers['Content-Type'] = 'application/json'
    if target_platform == 'spotify':
        check_spotify_token_expiration()
    create_playlist_req = requests.post(headers=headers,
                                            url=f'https://api.spotify.com/v1/users/{spotify_user_id}/playlists',
                                            json ={'name': f"{playlist_name}",
                                            'description': "Transferred via SAM",
                                            'public' : True
                                            }) if target_platform == 'spotify' else requests.post(headers=headers, 
                            url='https://api.music.apple.com/v1/me/library/playlists',
                            json={'attributes': {'description': 'Transferred via SAM', 'name':f"{playlist_name}"}
                                }) 

    new_playlist_content = json.loads(create_playlist_req.content) if target_platform == 'spotify' else json.loads(create_playlist_req.content)['data'][0]
    new_playlist_id = new_playlist_content['id']

    chunk_size = 100
    for i in range(0, len(track_id_or_uri_arr), chunk_size):
        chunk = track_id_or_uri_arr[i:i + chunk_size]
        if target_platform == 'spotify':
            check_spotify_token_expiration()
        add_tracks_to_playlist_req = requests.post(headers=headers,
                                                       url=f'https://api.spotify.com/v1/playlists/{new_playlist_id}/tracks',
                                                       json={"uris": chunk}) if target_platform == 'spotify' else requests.post(headers=headers, 
                            url=f'https://api.music.apple.com/v1/me/library/playlists/{new_playlist_id}/tracks',
                            json={"data": chunk
                                }) 


    upload_aws_data(aws_data, new_playlist_content, playlist_name, playlist_id, platform=target_platform)
    transfer_completion_data = {'playlist_transferred_name': playlist_name}
    socketio.emit("transfer_completed", transfer_completion_data)
    return



def create_aws_item(item, platform, origin_track_catalogId=None):
    if platform == 'spotify':
        return {'album_name': item['album']['name'], 
                                'artist_name': ', '.join(name['name'] for name in item['artists']), 
                                'track_id': item['id'],
                                'track_link': item['external_urls']['spotify'],
                                'track_name': item['name'],
                                'origin_track_catalogId': origin_track_catalogId}
                       
    else:
        return {"album_name": item['attributes']['albumName'], 
                                "artist_name": item['attributes']['artistName'],
                                'track_id': item['id'], 
                                "track_link": item['attributes']['url'], 
                                "track_name": item['attributes']['name'],
                                'origin_track_catalogId': item['id']
                                }



def upload_aws_data(aws_data, new_playlist_content, playlist_name, origin_playlist_id, platform):
    user_id = spotify_user_id if platform == 'spotify' else (json.loads((requests.get(headers = apple_music_authentication_headers, url='https://api.music.apple.com/v1/me/recent/played', params={'limit': '1'})).content)['data'][0]['id'])
    new_playlist_id = new_playlist_content['id']
    playlist_link = new_playlist_content['external_urls']['spotify'] if platform == 'spotify' else f"https://music.apple.com/us/playlist/{new_playlist_id}"
    

    aws_chunk_size = 50
    for i in range(0, len(aws_data), aws_chunk_size):
        aws_chunk = aws_data[i: i + aws_chunk_size]
        sample_data = {'playlist_type': 'Apple_Music', 
        'user_id': user_id, 
        'playlist_id': new_playlist_id,
        'playlist_link': playlist_link, 
        'playlist_name': playlist_name,
        'origin_playlist_id': origin_playlist_id,
        'track_list_data': aws_chunk}
        aws_req = requests.post(url='https://l4nwln3vvvjvbsg3to6bvmzseq0oyikw.lambda-url.us-east-2.on.aws/',
        json = sample_data 
        )
    return









@socketio.on('playlist_link')
def parse_link(link, platform):
    print(f'link is {link}')
    originating_platform='spotify' if link.startswith('https://open.spotify.com/playlist/') else 'apple_music'
    playlist_id = (link.replace('https://open.spotify.com/playlist/', '').split('?')[0]) if link.startswith('https://open.spotify.com/playlist/') else ('pl.'+ link.split('/pl.')[-1])
    return transfer_playlist(originating_platform=originating_platform, target_platform=platform, playlist_id=playlist_id, playlist_link=link)


    
if __name__ == '__main__':
    
    

    host = "0.0.0.0"
    port = 8000

    app.run(debug=False, host=host, port=port)