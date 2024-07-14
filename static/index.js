var socket = io();
socket.on('connect', function() {
    socket.emit('my event', {data: 'I\'m connected!'});
});

let apple_music_auth_bool = false;

window.addEventListener('beforeunload', window_refresh_event);
function window_refresh_event(){
    // if (apple_music_auth_bool === true){
    //   window.music.unauthorize();  
    // }
    socket.close();
};

document.addEventListener('musickitloaded', () =>{
    console.log('musickitloaded');
    // unauthorize();
    socket.on('generate_music_user_token', function(token){
        console.log("token is: ",token);

        MusicKit.configure({
            developerToken: String(token),
            app: {
                name:'My Cool Web App',
                build: '1978.4.1'
            }
        });

        let music = MusicKit.getInstance();
        apple_music_auth_bool = true;
        window.music = music;
        window.music.authorize().then(musicUserToken => {
            console.log(`Authorized, music-user-token: ${musicUserToken}`);
            socket.emit('set_music_user_token', musicUserToken);
          }).catch(error => {
            console.error('Error authorizing:', error);
        });
        
    });
});





let spotify_account_authorized = false
let apple_music_account_authorized = false

// Spotify login 
document.getElementById('login_spotify_button').addEventListener('click', login_to_spotify)

function login_to_spotify(){
    socket.emit('login_spotify_user');
};

socket.on('spotify_authorization_url', function (data) {
    const new_window = window.open(data.url, '_blank');
});


socket.on('spotify_user_login_success', function spotifyUserLoginSuccessHandler(spotify_username){
    window.spotify_username = spotify_username.username;
    spotify_account_authorized = true
    login_button = document.getElementById('login_spotify_button')
    login_button.remove();
    both_accounts_authorized()
});





// login to apple music
document.getElementById('login_apple_music_button').addEventListener('click', login_to_apple_music);

function login_to_apple_music(){
    socket.emit('login_apple_music_user');
};

socket.on('apple_music_user_login_success', function(apple_music_username) {  
    login_button = document.getElementById('login_apple_music_button')
    login_button.remove();
    cookies_button = document.getElementById('deleteCookiesBtn')
    cookies_button.remove();
    window.apple_music_username = apple_music_username.username;
    apple_music_account_authorized = true
    both_accounts_authorized()
});

function both_accounts_authorized(){
    if (apple_music_account_authorized === true && spotify_account_authorized === true){
        console.log('login successful')
        root_page_templating();  
    }else if (apple_music_account_authorized === false && spotify_account_authorized === true){
        console.log('apple music account is not authorized');
    }else if (apple_music_account_authorized === true && spotify_account_authorized === false){
        console.log('spotify account is not authorized');
    };
    console.log();
};


var counter = 0
function root_page_templating(){ 
    counter += 1
    console.log(`conter is: ${counter}`)
    var playlist_container = document.getElementById('playlist_container');
    playlist_container.innerHTML =  '<p>Welcome Apple Music user ' + window.apple_music_username + '!</p>' 
    playlist_container.innerHTML += '<p>Welcome Spotify user ' + window.spotify_username + '!</p>'; 
    playlist_container.innerHTML += '<button onclick="transfer_spotify()" ">Transfer Spotify Playlist to Apple Music</button>';
    playlist_container.innerHTML += '<br>';
    playlist_container.innerHTML += '<button onclick="transfer_apple_music_to_spotify()">Transfer Apple Music Playlist to Spotify</button>';
    playlist_container.innerHTML += '<br>';
    playlist_container.innerHTML += '<br>';
    // playlist_container.innerHTML += '<button onclick="sync()">Sync a playlist</button>';
    playlist_container.innerHTML += '<button onclick="get_link()">Transfer a playlist from a link</button>';
};



button_counter = 0;
function transfer_spotify(){
    var playlist_container = document.getElementById('playlist_container');
    playlist_container.innerHTML = 'Please wait'

    button_counter += 1;
    console.log(button_counter);
    socket.emit('get_spotify_users_playlist_names');
    socket.on('spotify_playlist_data', function (data) {
        let i = 0;
        playlist_container.innerHTML = '<p>Choose a playlist to transfer!</p>';
        while (i < data.length) {
            playlist_container.innerHTML += `<button onclick="transfer_spotify_playlist_chosen(${'\'' + data[i]['id'] + '\''}, ${'\'' + data[i]['name'] + '\''})" ">${data[i]['name']}</button>`;
            i++;
        }
        playlist_container.innerHTML += '<br>';
        playlist_container.innerHTML += '<button onclick="root_page_templating()">Main menu</button>';
    });



};



function transfer_spotify_playlist_chosen(playlist_id, playlist_name){
    console.log(`playlist_info is ${playlist_id}`);
    console.log(`playlist_name is ${playlist_name}`);
    var playlist_container = document.getElementById('playlist_container');
    playlist_container.innerHTML = "<p>" + "Please wait while " + playlist_name + " is being transferred" + "</p>"
    socket.emit('transfer_this_spotify_playlist_to_apple_music', playlist_id, playlist_name)
    socket.on("transfer_completed", function(transfer_completion_data){

        playlist_container.innerHTML = '<p>Transfer was successful for playlist ' + transfer_completion_data['playlist_transferred_name'] + '</p>'
        playlist_container.innerHTML += '<button onclick="root_page_templating()">Main menu</button>';
        playlist_container.innerHTML += '<br>';
        playlist_container.innerHTML += '<button onclick="transfer_spotify()">Transfer another Apple Music playlist to Spotify</button>';
        
    });

};




function transfer_apple_music_to_spotify(){
    var playlist_container = document.getElementById('playlist_container');
    playlist_container.innerHTML = 'Please wait'

    button_counter += 1;
    console.log(button_counter);
    socket.emit('get_users_apple_music_playlist_names');
    socket.on('users_apple_music_playlist_data', function (data) {
        let i = 0;
        playlist_container.innerHTML = '<p>Choose a playlist to transfer!</p>';
        while (i < data.length) {
            playlist_container.innerHTML += `<button onclick="transfer_apple_muisic_playlist_chosen(${'\'' + data[i]['id'] + '\''}, ${'\'' + data[i]['attributes']['name'] + '\''})" ">${data[i]['attributes']['name']}</button>`;
            i++;
        }
        playlist_container.innerHTML += '<br>';
        playlist_container.innerHTML += '<button onclick="root_page_templating()">Main menu</button>';
    });
};



function transfer_apple_muisic_playlist_chosen(playlist_id, playlist_name){
    console.log(`playlist_info is ${playlist_id}`);
    console.log(`playlist_name is ${playlist_name}`);
    var playlist_container = document.getElementById('playlist_container');
    playlist_container.innerHTML = "<p>" + "Please wait while " + playlist_name + " is being transferred" + "</p>"
    socket.emit('transfer_this_apple_music_playlist_to_spotify', playlist_id, playlist_name)
    socket.on("transfer_completed", function(transfer_completion_data){
        
        playlist_container.innerHTML = '<p>Transfer was successful for playlist ' + transfer_completion_data['playlist_transferred_name'] + '</p>'
        playlist_container.innerHTML += '<button onclick="root_page_templating()">Main menu</button>';
        playlist_container.innerHTML += '<br>';
        playlist_container.innerHTML += '<button onclick="transfer_apple_music_to_spotify()">Transfer another Apple Music playlist to Spotify</button>';
    
    });

};



socket.on("playlist_missing_tracks", function(){
    playlist_container.innerHTML = '<p>Transfer failed due to playlist not having any tracks added to it</p>'
    playlist_container.innerHTML += '<button onclick="root_page_templating()">Main menu</button>';
    playlist_container.innerHTML += '<br>';
    
});




const formContent = `
            <form id="playlist_form" autocomplete="OFF">
                <label for="link">Playlist link:</label>
                <input type="text" name="link" id="link"><br><br>
                <label for="platform">Choose a platform:</label>
                <select name="platform" id="platform">
                    <option value="spotify">Spotify</option>
                    <option value="apple_music">Apple Music</option>
                </select><br><br>
                <input type="button" value="Submit" onclick="submit_link()">
                
            </form>
        `;


function get_link(){
//     console.log('link clicked')
    var playlist_container = document.getElementById('playlist_container');
    playlist_container.innerHTML = formContent;
    playlist_container.innerHTML += '<button onclick="root_page_templating()">Main menu</button>';
};


function submit_link() {
    link = document.getElementById('link').value;
    platform = document.getElementById('platform').value
    let spotify_beginning_link = 'https://open.spotify.com/playlist/';
    let apple_music_beginning_link = 'https://music.apple.com/us/playlist/';
    if (link.startsWith(spotify_beginning_link) || link.startsWith(apple_music_beginning_link)){
        socket.emit('playlist_link', link, platform);
        var playlist_container = document.getElementById('playlist_container');
        playlist_container.innerHTML = 'Please wait';

        socket.on("transfer_completed", function(transfer_completion_data){
            // if (transfer_completion_data['transfer_status_code'] == 200){
            playlist_container.innerHTML = '<p>Transfer was successful for playlist ' + transfer_completion_data['playlist_transferred_name'] + '</p>'
            playlist_container.innerHTML += '<button onclick="root_page_templating()">Main menu</button>';
            playlist_container.innerHTML += '<br>';
            
            // };
        });
    
    };

};
