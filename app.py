import os
import random
from pathlib import Path
from typing import Optional
import json

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from flask import Flask, render_template, redirect, request, url_for, jsonify, g, session

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.urandom(24)  # Set a secret key for session management
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './.flask_session/'

# Spotify's credentials - replace with your own or load from environment variables
SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REDIRECT_URI = os.environ.get('SPOTIFY_REDIRECT_URI', 'http://localhost:5000/callback')
SPOTIFY_SCOPE = "user-library-read streaming user-read-email user-read-private streaming"
CACHE_PATH = Path('.spotify_caches/')

# Ensure cache directory exists
os.makedirs(CACHE_PATH, exist_ok=True)
os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)


class SaveManager:
    def __init__(self, username):
        self.username = username
        self.save_folder = Path('saves')
        self.save_path = self.save_folder.joinpath(f'{self.username}.save')
        self.save_content: dict = {}

        self.save_folder.mkdir(parents=True, exist_ok=True)
        if not self.save_path.exists():
            self.create_save_file()
        self.read_save()

    def create_save_file(self):
        default_content = {
            'login_token': {},
            'playlists': {},
            'tracks': {}
        }

        with self.save_path.open(mode='w+', encoding='utf-8') as file:
            json.dump(default_content, file, indent=4)
        print(f'[SAVE] Save has been created for {self.username}')

    def read_save(self):
        with self.save_path.open(mode='r', encoding='utf-8') as file:
            try:
                save_content = json.load(file)
            except json.decoder.JSONDecodeError:
                save_content = {}
            self.save_content = save_content
        print(f'[SAVE] Loaded {self.username}')

    def write_save(self, cat, content, sub_cat=None):
        self.read_save()
        new_save = self.save_content.copy()
        if sub_cat:
            new_save[cat][sub_cat] = content
        else:
            new_save[cat] = content

        # write
        with self.save_path.open(mode='w', encoding='utf-8') as file:
            json.dump(new_save, file, indent=4)
            file.truncate()

        # update
        self.save_content = new_save
        print(f'[SAVE] has been updated for {self.username} ({cat} / {sub_cat})')


# global variable????
saveHandler: Optional[SaveManager] = None


# set up pages
@app.before_request
def before_request():
    global saveHandler
    if username := session.get('username'):
        saveHandler = SaveManager(username)
        if (user_token := saveHandler.save_content['login_token']) != {}:
            refresh_token()
            session['login_token'] = user_token


# first page
@app.route('/')
def index():
    return redirect(url_for('home'))


# home page
@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/start_game', methods=['POST'])
def start_game():
    username = request.form.get('username')
    if username:
        session['username'] = username
        return redirect(url_for('authorize'))
    return redirect(url_for('index'))



# spotify auth functions
def generate_spotify_client():
    if 'login_token' not in session:
        return None  # redirect user to login if no token
    access_token = session['login_token']['access_token']
    return spotipy.Spotify(auth=access_token)


def generate_auth_manager():
    return SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope=SPOTIFY_SCOPE,
        show_dialog=True,
        cache_path=Path.joinpath(CACHE_PATH, 'thunninoi')
    )


def refresh_token():
    global saveHandler
    if 'login_token' not in session:
        return redirect(url_for('spotify_login'))  # redirect user to login if no token
    auth_manager = generate_auth_manager()
    auth_manager.cache_handler.save_token_to_cache(session['login_token'])

    # check token validity
    user_token = auth_manager.get_cached_token()

    auth_manager.refresh_access_token(user_token['refresh_token'])
    new_token = auth_manager.get_cached_token()
    saveHandler.write_save('login_token', new_token)  # write new token
    print('[TOKEN] has been refreshed')


# authorization page
@app.route('/authorize')
def authorize():
    if generate_spotify_client():  # try to create client, if has no login information will auto
        return redirect(url_for('playlist_selection'))
    else:
        return redirect(url_for('spotify_login'))


# Redirect to log in from spotify to generate token
@app.route('/spotify_login')
def spotify_login():
    auth_manager = generate_auth_manager()
    auth_url = auth_manager.get_authorize_url()
    return redirect(auth_url)


# Callback after log in from spotify
@app.route('/callback')
def callback():
    access_token_code = request.args.get('code')
    auth_manager = generate_auth_manager()
    access_token = auth_manager.get_access_token(access_token_code)
    session['login_token'] = access_token  # update to webapp
    saveHandler.write_save('login_token', access_token)  # write to save file
    return redirect(url_for('authorize'))


# End of authorization stuff

# Playlist select
@app.route('/playlist_selection')
def playlist_selection():
    if session.get('playlist_uri'):
        session['playlist_uri'] = None
    return render_template('playlist_select.html')


# Request user playlist from Spotify
def request_playlist_api():
    if 'login_token' not in session:
        return None
    print(session['login_token'])
    spotify_client = generate_spotify_client()
    # Default
    playlist_list = [
        {
            'id': 1,
            'title': 'Liked Tracks',
            'cover_image': 'https://cdn.discordapp.com/avatars/451356106862886914/c9f9506efbf1d08c9995701434170b0c?size=1024',
            'uri': 'liked',
            'total_tracks': spotify_client.current_user_saved_tracks()['total']
        }
    ]

    # Get custom playlists
    id = 2
    playlist_sp = spotify_client.current_user_playlists()

    # Iterate until the last
    while playlist_sp:
        for pl in playlist_sp['items']:
            playlist_list.append({
                'id': id,
                'title': pl['name'],
                'cover_image': pl['images'][0]['url'],
                'uri': pl['uri'],
                'total_tracks': pl['tracks']['total']
            })
            id += 1
        playlist_sp = spotify_client.next(playlist_sp) if playlist_sp['next'] else None

    return playlist_list


# endpoint for flask to get playlist list
@app.route('/get_playlist_list')
def get_playlist_list():
    # check if already has playlist save locally or not
    if saveHandler.save_content['playlists'] == {}:
        playlists = request_playlist_api()
        saveHandler.write_save('playlists', playlists)  # save to local
    all_playlists = saveHandler.save_content['playlists']

    search = request.args.get('search', '').lower()
    page = int(request.args.get('page', 1))
    page_size = 10

    if search:
        filtered_pl = [
            pl for pl in all_playlists if search in pl['title'].lower()
        ]
    else:
        filtered_pl = all_playlists.copy()

    start = (page - 1) * page_size
    end = start + page_size
    paginated_pl = filtered_pl[start:end]
    return jsonify({
        'playlists': paginated_pl,
        'has_more': len(filtered_pl) > end
    })


# endpoint for refresh playlist list by recall to spotify
@app.route('/refresh_playlist_list', methods=['POST'])
def refresh_playlist_list():
    request_playlist_api()
    return 'Success'


# endpoint to submit selected playlist
@app.route('/submit_selected_playlist', methods=['POST'])
def submit_selected_playlist():
    # get value from form
    selected_id = request.form.get('playlist')
    print(selected_id)
    all_playlist = saveHandler.save_content['playlists']

    if selected_id:
        selected_playlist = next((pl for pl in all_playlist if pl['id'] == int(selected_id)), 0)
        session['playlist_uri'] = selected_playlist['uri']
        return redirect(url_for('songle'))
    else:
        return "NAH"


# End of playlist selection

# Tracks
def request_track_api(uri):
    if 'playlist_uri' not in session:
        return None
    client = generate_spotify_client()

    if uri == 'liked':
        pl = client.current_user_saved_tracks()
    else:
        pl = client.playlist_items(playlist_id=uri)

    track_list = []
    this_id = 1
    while pl:
        for item in pl['items']:
            track = item['track']
            track_info = {
                "id": this_id,
                "title": track['name'],
                'artist': ', '.join([artist['name'] for artist in track['artists']]),
                'cover_img': track['album']['images'][0]['url'],
                'durations_ms': track['duration_ms'],
                'uri': track['uri']
            }
            track_list.append(track_info)
            this_id += 1
        pl = client.next(pl) if pl['next'] else None
    return track_list


@app.route('/get_playlist_tracks')
def get_playlist_tracks():
    #print(session['playlist_uri'])
    if 'playlist_uri' not in session:
        return redirect('/')
    pl_uri = session['playlist_uri']

    # check if have saved or not
    if pl_uri not in saveHandler.save_content['tracks']:
        track_list = request_track_api(pl_uri)
        saveHandler.write_save(cat='tracks', sub_cat=pl_uri, content=track_list)
    all_tracks = saveHandler.save_content['tracks'][pl_uri]

    #sort
    all_tracks = sorted(all_tracks, key=lambda x: x['title'].lower())
    search = request.args.get('search', '').lower()
    page = int(request.args.get('page', 1))
    page_size = 10

    filtered_tracks = [
        track for track in all_tracks
        if search in track['title'].lower() or search in track['artist'].lower()
    ] if search else all_tracks.copy()

    start = (page - 1) * page_size
    end = start + page_size
    paginated_track = filtered_tracks[start:end]
    print(
        ({
            'tracks': paginated_track,
            'has_more': len(filtered_tracks) > end
        })
    )
    return jsonify({
        'tracks': paginated_track,
        'has_more': len(filtered_tracks) > end
    })


@app.route('/songle')
def songle():
    session['track_target'] = get_random_track()
    session['attempts'] = 1
    session['play_duration'] = [0, 1, 3, 5, 10, 30][session['attempts']] * 1000
    context = {
        'attempt' : session['attempts']
    }
    return render_template('track_player.html', **context)


def get_random_track():
    if 'playlist_uri' not in session:
        return None
    if (pl_uri := session['playlist_uri']) not in saveHandler.save_content['tracks']:
        to_save = request_track_api(pl_uri)
        saveHandler.write_save(cat='tracks', sub_cat=pl_uri, content=to_save)
    print(pl_uri)
    all_tracks = saveHandler.save_content['tracks'][pl_uri]
    return random.choice(all_tracks)


@app.route('/get_track_to_play')
def get_track_to_play():
    if 'track_target' not in session or 'play_duration' not in session:
        return jsonify({
            'error'
        })
    return jsonify({
        'uri': session['track_target']['uri'],
        'duration': int(session['play_duration'])
    })


@app.route('/play_track', methods=['POST'])
def play_track():
    data = request.json
    device_id = data['device_id']
    uri = data['uri']
    print(f'playing {uri}')

    client = generate_spotify_client()
    client.start_playback(device_id=device_id, uris=[uri], position_ms=0)
    return jsonify({'success': True})


@app.route('/get_spotify_token')
def get_spotify_token():
    token = saveHandler.save_content['login_token']
    auth_manager = generate_auth_manager()
    auth_manager.cache_handler.save_token_to_cache(token)

    # check token validity
    user_token = auth_manager.get_cached_token()

    auth_manager.refresh_access_token(user_token['refresh_token'])
    new_token = auth_manager.get_cached_token()
    saveHandler.write_save('login_token', new_token)  # write new token
    print('[TOKEN] has been refreshed')

    return jsonify({'token': new_token['access_token']})


@app.route('/songle_check_answer', methods=['POST'])
def songle_check_answer():
    # get value from form
    if 'playlist_uri' not in session:
        return redirect('/')
    correct_track = session.get('track_target')

    print(request.form)
    if request.form.get('skip'):
        return jsonify({
            'success': False,
            'attempts': 99,
            'track': correct_track
        })
    answered_track = request.form.get('track')
    if not answered_track:
        answered_track = 0

    print(answered_track)
    print(correct_track)

    if str(answered_track).strip() == str(correct_track['id']).strip():
        result = True
    else:
        session['attempts'] = session.get('attempts') + 1
        session['play_duration'] = [0, 1, 3, 5, 10, 30][session['attempts']] * 1000  # seconds based on number of tries
        result = False

    print(correct_track)
    return jsonify({
        'success': result,
        'attempts': session.get('attempts'),
        'track': correct_track
    })


@app.route('/get_another_song')
def get_another_song():
    print('get_another_song')
    session['track_target'] = get_random_track()
    session['attempts'] = 1
    session['play_duration'] = [0, 1, 3, 5, 10, 30][session['attempts']] * 1000
    return jsonify({
        'success': True
    })


@app.route('/success_page')
def success_page():
    return "Nice!"


@app.route('/failure_page')
def failure_page():
    return "Nah!"


# Debug stuff?
@app.route('/placeholder', methods=['POST', 'GET'])
def placeholder():
    return None


if __name__ == "__main__":
    app.run(debug=True)
