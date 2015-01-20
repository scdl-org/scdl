#!/usr/bin/python3
"""scdl allow you to download music from soundcloud

Usage:
    scdl -l <track_url> [-a | -f | -t | -p][-c][-o <offset>]\
[--hidewarnings][--debug | --error][--path <path>][--addtofile][--onlymp3]
    scdl me (-s | -a | -f | -t | -p)[-c][-o <offset>]\
[--hidewarnings][--debug | --error][--path <path>][--addtofile][--onlymp3]
    scdl -h | --help
    scdl --version


Options:
    -h --help          Show this screen
    --version          Show version
    me                 Use the user profile from the auth_token
    -l [url]           URL can be track/playlist/user
    -s                 Download the stream of an user (token needed)
    -a                 Download all track of an user (including repost)
    -t                 Download all upload of an user
    -f                 Download all favorite of an user
    -p                 Download all playlist of an user
    -c                 Continue if a music already exist
    -o [offset]        Begin with a custom offset
    --path [path]      Use a custom path for this time
    --hidewarnings     Hide Warnings. (use with precaution)
    --addtofile        Add the artist name to the filename if it isn't in the filename already
    --onlymp3          Download only the mp3 file even if the track is Downloadable
    --error            Only print debug information (Error/Warning)
    --debug            Print every information and
"""
from docopt import docopt
from termcolor import colored
import configparser
from scdl import __version__

import warnings
import os
import signal
import sys
import time

import soundcloud
import wget
import urllib.request
import json

import mutagen

log_verbosity = 1  # (0 = Error ; 1 = Error && Info ; 2 = Debug && Error && Info)
arguments = None
token = ''
path = ''
offset = 0
scdl_client_id = '9dbef61eb005cb526480279a0cc868c4'
client = soundcloud.Client(client_id=scdl_client_id)


def log(str, strverbosity=1):  # strverbosity (0 = Error ; 1 = Info ; 2 = Debug)
    global log_verbosity
    if log_verbosity >= strverbosity:
        if strverbosity == 0:
            print(colored(str, 'red'))
        elif strverbosity == 1:
            print(colored(str, 'white'))
        elif strverbosity == 2:
            print(colored(str, 'yellow'))


def main():
    """
    Main function, call parse_url
    """
    signal.signal(signal.SIGINT, signal_handler)
    global offset
    global log_verbosity
    global arguments

    # import conf file
    get_config()

    # Parse argument
    arguments = docopt(__doc__, version=__version__)

    if arguments["--debug"]:
        log_verbosity = 2
    elif arguments["--error"]:
        log_verbosity = 0

    log("Soundcloud Downloader", strverbosity=1)
    log(arguments, strverbosity=2)

    if arguments["-o"] is not None:
        try:
            offset = int(arguments["-o"])
        except:
            log('Offset should be an Integer...', strverbosity=0)
            sys.exit()

    if arguments["--hidewarnings"]:
        warnings.filterwarnings("ignore")

    if arguments["--path"] is not None:
        if os.path.exists(arguments["--path"]):
            os.chdir(arguments["--path"])
        else:
            log('Invalid path in arguments...', strverbosity=0)
            sys.exit()
    log('Downloading to '+os.getcwd()+'...', strverbosity=2)

    log('', strverbosity=1)
    if arguments["-l"]:
        parse_url(arguments["-l"])
    elif arguments["me"]:
        if arguments["-a"]:
            download_all_user_tracks(who_am_i())
        elif arguments["-f"]:
            download_user_favorites(who_am_i())
        elif arguments["-t"]:
            download_user_tracks(who_am_i())
        elif arguments["-p"]:
            download_user_playlists(who_am_i())


def get_config():
    """
    read the path where to store music
    """
    global token
    config = configparser.ConfigParser()
    config.read(os.path.join(os.path.expanduser('~'), '.config/scdl/scdl.cfg'))
    try:
        token = config['scdl']['auth_token']
        path = config['scdl']['path']
    except:
        log('Are you sure scdl.cfg is in $HOME/.config/scdl/ ?', strverbosity=0)
        sys.exit()
    if os.path.exists(path):
        os.chdir(path)
    else:
        log('Invalid path in scdl.cfg...', strverbosity=0)
        sys.exit()


def get_item(track_url):
    """
    Fetches metadata for an track or playlist
    """

    try:
        item = client.get('/resolve', url=track_url)
    except Exception:
        log('Error resolving url, retrying...', strverbosity=0)
        time.sleep(5)
        try:
            item = client.get('/resolve', url=track_url)
        except Exception as e:
            log("Could not resolve url " + track_url, strverbosity=0)
            log(e, strverbosity=0)
            sys.exit(0)
    return item


def parse_url(track_url):
    """
    Detects if the URL is a track or playlists, and parses the track(s) to the track downloader
    """
    global arguments
    item = get_item(track_url)

    if not item:
        return
    elif isinstance(item, soundcloud.resource.ResourceList):
        download_all(item)
    elif item.kind == 'track':
        log("Found a track", strverbosity=1)
        download_track(item)
    elif item.kind == "playlist":
        log("Found a playlist", strverbosity=1)
        download_playlist(item)
    elif item.kind == 'user':
        log("Found an user profile", strverbosity=1)
        if arguments["-f"]:
            download_user_favorites(item)
        elif arguments["-t"]:
            download_user_tracks(item)
        elif arguments["-a"]:
            download_all_user_tracks(item)
        elif arguments["-p"]:
            download_user_playlists(item)
        else:
            log('Please provide a download type...', strverbosity=0)
    else:
        log("Unknown item type", strverbosity=0)


def who_am_i():
    """
    display to who the current token correspond, check if the token is valid
    """
    global client
    client = soundcloud.Client(access_token=token, client_id=scdl_client_id)

    try:
        current_user = client.get('/me')
    except:
        log('Invalid token...', strverbosity=0)
        sys.exit(0)
    log('Hello' + current_user.username + '!', strverbosity=1)
    log('', strverbosity=1)
    return current_user


def download_all_user_tracks(user):
    """
    Find track & repost of the user
    """
    global offset
    user_id = user.id

    url = "https://api.sndcdn.com/e1/users/%s/sounds.json?limit=1&offset=%d&client_id=9dbef61eb005cb526480279a0cc868c4" % (user_id, offset)
    response = urllib.request.urlopen(url)
    data = response.read()
    text = data.decode('utf-8')
    json_data = json.loads(text)
    while str(json_data) != '[]':
        offset += 1
        try:
            this_url = json_data[0]['track']['uri']
        except:
            this_url = json_data[0]['playlist']['uri']
        log('Track n°%d' % (offset))
        parse_url(this_url)

        url = "https://api.sndcdn.com/e1/users/%s/sounds.json?limit=1&offset=%d&client_id=9dbef61eb005cb526480279a0cc868c4" % (user_id, offset)
        response = urllib.request.urlopen(url)
        data = response.read()
        text = data.decode('utf-8')
        json_data = json.loads(text)


def download_user_tracks(user):
    """
    Find track in user upload --> no repost
    """
    global offset
    count = 0
    tracks = client.get('/users/' + str(user.id) + '/tracks', limit=10, offset=offset)
    for track in tracks:
        for track in tracks:
            count += 1
            log("", strverbosity=1)
            log('Track n°%d' % (count), strverbosity=1)
            download_track(track)
        offset += 10
        tracks = client.get('/users/' + str(user.id) + '/tracks', limit=10, offset=offset)
    log('All users track downloaded!', strverbosity=1)


def download_user_playlists(user):
    """
    Find playlists of the user
    """
    global offset
    count = 0
    playlists = client.get('/users/' + str(user.id) + '/playlists', limit=10, offset=offset)
    for playlist in playlists:
        for playlist in playlists:
            count += 1
            log("", strverbosity=1)
            log('Playlist n°%d' % (count), strverbosity=1)
            download_playlist(playlist)
        offset += 10
        playlists = client.get('/users/' + str(user.id) + '/playlists', limit=10, offset=offset)
    log('All users playlists downloaded!', strverbosity=1)


def download_user_favorites(user):
    """
    Find tracks in user favorites
    """
    global offset
    count = 0
    favorites = client.get('/users/' + str(user.id) + '/favorites', limit=10, offset=offset)
    for track in favorites:
        for track in favorites:
            count += 1
            log("", strverbosity=1)
            log('Favorite n°%d' % (count), strverbosity=1)
            download_track(track)
        offset += 10
        favorites = client.get('/users/' + str(user.id) + '/favorites', limit=10, offset=offset)
    log('All users favorites downloaded!', strverbosity=1)


def download_my_stream():
    """
    DONT WORK FOR NOW
    Download the stream of the current user
    """
    client = soundcloud.Client(access_token=token, client_id=scdl_client_id)
    activities = client.get('/me/activities')
    log(activities, strverbosity=3)


def download_playlist(playlist):
    """
    Download a playlist
    """
    count = 0
    invalid_chars = '\/:*?|<>"'

    playlist_name = playlist.title.encode('utf-8', 'ignore').decode('utf-8')
    playlist_name = ''.join(c for c in playlist_name if c not in invalid_chars)

    if not os.path.exists(playlist_name):
        os.makedirs(playlist_name)
    os.chdir(playlist_name)

    for track_raw in playlist.tracks:
        count += 1
        mp3_url = get_item(track_raw["permalink_url"])
        log('Track n°%d' % (count), strverbosity=1)
        download_track(mp3_url, playlist.title)

    os.chdir('..')


def download_all(tracks):
    """
    Download all song of a page
    Not recommended
    """
    log("NOTE: This will only download the songs of the page.(49 max)", strverbosity=0)
    log("I recommend you to provide an user link and a download type.", strverbosity=0)
    count = 0
    for track in tracks:
        count += 1
        log("", strverbosity=1)
        log('Track n°%d' % (count), strverbosity=1)
        download_track(track)


def download_track(track, playlist_name=None):
    """
    Downloads a track
    """
    global arguments

    if track.streamable:
        stream_url = client.get(track.stream_url, allow_redirects=False)
    else:
        log('%s is not streamable...' % (track.title), strverbosity=0)
        log('', strverbosity=1)
        return
    title = track.title
    title = title.encode('utf-8', 'ignore').decode('utf-8')
    log("Downloading " + title, strverbosity=1)

    #filename
    if track.downloadable and not arguments["--onlymp3"]:
        log('Downloading the orginal file.', strverbosity=1)
        url = track.download_url + '?client_id=' + scdl_client_id

        filename = urllib.request.urlopen(url).info()['Content-Disposition'].split('filename=')[1]
        if filename[0] == '"' or filename[0] == "'":
            filename = filename[1:-1]
    else:
        url = stream_url.location
        invalid_chars = '\/:*?|<>"'
        if track.user['username'] not in title and arguments["--addtofile"]:
            title = track.user['username'] + ' - ' + title
        title = ''.join(c for c in title if c not in invalid_chars)
        filename = title + '.mp3'

    # Download
    if not os.path.isfile(filename):
        wget.download(url, filename)
        log('', strverbosity=1)
        if '.mp3' in filename:
            try:
                if playlist_name is None:
                    settags(track, filename)
                else:
                    settags(track, filename, playlist_name)
            except:
                log('Error trying to set the tags...', strverbosity=0)
        else:
            log('This type of audio don\'t support tag...', strverbosity=0)
    else:
        if arguments["-c"]:
            log(title + " already Downloaded", strverbosity=1)
            log('', strverbosity=1)
            return
        else:
            log('', strverbosity=1)
            log("Music already exists ! (exiting)", strverbosity=0)
            sys.exit(0)

    log('', strverbosity=1)
    log(filename + ' Downloaded.', strverbosity=1)
    log('', strverbosity=1)


def settags(track, filename, album='Soundcloud'):
    """
    Set the tags to the mp3
    """
    log("Settings tags...", strverbosity=1)
    user = client.get('/users/' + str(track.user_id), allow_redirects=False)

    artwork_url = track.artwork_url
    if artwork_url is None:
        artwork_url = user.avatar_url
    artwork_url = artwork_url.replace('large', 't500x500')
    urllib.request.urlretrieve(artwork_url, '/tmp/scdl.jpg')

    audio = mutagen.File(filename)
    audio["TIT2"] = mutagen.id3.TIT2(encoding=3, text=track.title)
    audio["TALB"] = mutagen.id3.TALB(encoding=3, text=album)
    audio["TPE1"] = mutagen.id3.TPE1(encoding=3, text=user.username)
    audio["TCON"] = mutagen.id3.TCON(encoding=3, text=track.genre)
    if artwork_url is not None:
        audio["APIC"] = mutagen.id3.APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=open('/tmp/scdl.jpg', 'rb').read())
    else:
        log("Artwork can not be set.", strverbosity=0)
    audio.save()


def signal_handler(signal, frame):
    """
    handle keyboardinterrupt
    """
    time.sleep(1)
    files = os.listdir()
    for f in files:
        if not os.path.isdir(f) and ".tmp" in f:
            os.remove(f)

    log('')
    log('Good bye!')
    sys.exit(0)

if __name__ == "__main__":
    main()
