# Syncify

In order to use this you need both a Apple apple which has the Apple Developer Program ($99/yr fee) and a Spotify Developer account (free) 

You will also need to have [Docker desktop installed](https://www.docker.com/products/docker-desktop/)




# Apple account setup:
(requries an Apple developer account for $99 a year)

You can either follow [this guide](https://developer.apple.com/help/account/configure-app-capabilities/create-a-media-identifier-and-private-key/#:~:text=Register%20a%20media%20identifier,requesting%20access%20to%20Apple%20Music.)

or follow the steps below:

1. Go to the [Apple developer page](https://developer.apple.com/) 
2. Hit account (right side next to the magnifier glass) > sign in
3. Scroll down to `Membership details` and look for `Team ID` and copy that 10 character value 
4. Scroll up and locate `Certificates, IDs & Profiles` in `Program resources` or scroll down and click on `Certificates, IDs & Profiles`
5. Click on `Identifiers` and then create a new Identifier (blue plus button)
6. Choose `Media ID's` then continue
7. Enter a description and identifier
8. Enable MusicKit
9. Hit `Continue` then `Register`
10. Click on `Keys` then add a key
11. Choose a key name and enable `Media Services (MusicKit, ShazamKit)
12. Click on `Configure` and select the Media ID you created and save it
13. Hit `Continue` then `Register`

# Setting up Apple account secret values:
1. Once the key is created, download the .p8 file and move it into the folder structure 
2. Copy and paste the key id value into the `AM_config.json` file
3. Copy and paste your 10 character Team ID which can be found in your account settings, into the `iss` value in the `AM_config.json` file 

 

# Spotify Developer account setup:

1. Go to the [spotify developer page](https://developer.spotify.com/) and sign in
2. Click on your account and go to the dashboard
3. Create an app and make sure the Redirect URI is `[http://localhost:8080/callback/](http://127.0.0.1:8000/callback)`
4. Once the app is created go into and click on `Settings`
5. Copy and paste the `Client ID` and `Client Secret` values into the `Spotify_config.json` file


# Running the app:

1. open a terminal and go to the folder location and run `Docker Compose up`
2. Open a browser and go to `localhost:8080`
3. Sign into both accounts and choose which platform to transfer a playlist to



