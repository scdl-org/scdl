#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

"""scdl allow you to download music from soundcloud

Usage:
    scdl -l <track_url> [-a | -f | -t | -p][-c][-o <offset>]\
[--hidewarnings][--debug | --error][--path <path>][--addtofile][--onlymp3][--hide-progress]
    scdl me (-s | -a | -f | -t | -p)[-c][-o <offset>]\
[--hidewarnings][--debug | --error][--path <path>][--addtofile][--onlymp3][--hide-progress]
    scdl -h | --help
    scdl --version


Options:
    -h --help          Show this screen
    --version          Show version
    me                 Use the user profile from the auth_token
    -l [url]           URL can be track/playlist/user
    -s                 Download the stream of a user (token needed)
    -a                 Download all tracks of a user (including repost)
    -t                 Download all uploads of a user
    -f                 Download all favorites of a user
    -p                 Download all playlists of a user
    -c                 Continue if a music already exist
    -o [offset]        Begin with a custom offset
    --path [path]      Use a custom path for this time
    --hidewarnings     Hide Warnings. (use with precaution)
    --addtofile        Add the artist name to the filename if it isn't in the filename already
    --onlymp3          Download only the mp3 file even if the track is Downloadable
    --error            Only print debug information (Error/Warning)
    --debug            Print every information and
    --hide-progress    Hide the wget progress bar
"""

import json
import logging
import os
import signal
import sys
import time
import warnings
import math
import shutil
import requests

import configparser
import mutagen
from docopt import docopt
from clint.textui import progress

from scdl import __version__
from scdl import soundcloud, utils

logging.basicConfig(level=logging.INFO, format='%(message)s')
logging.getLogger('requests').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addFilter(utils.ColorizeFilter())
logger.newline = print

arguments = None
token = ''
path = ''
offset = 0
scdl_client_id = '95a4c0ef214f2a4a0852142807b54b35'

client = soundcloud.Client(client_id=scdl_client_id)


def main():
    """
    Main function, call parse_url
    """
    signal.signal(signal.SIGINT, signal_handler)
    global offset
    global arguments

    # import conf file
    get_config()

    # Parse argument
    arguments = docopt(__doc__, version=__version__)

    if arguments['--debug']:
        logger.level = logging.DEBUG
    elif arguments['--error']:
        logger.level = logging.ERROR

    logger.info('Soundcloud Downloader')
    logger.debug(arguments)

    if arguments['-o'] is not None:
        try:
            offset = int(arguments['-o']) - 1
        except:
            logger.error('Offset should be an integer...')
            sys.exit()
        logger.debug('offset: %d', offset)

    if arguments['--hidewarnings']:
        warnings.filterwarnings('ignore')

    if arguments['--path'] is not None:
        if os.path.exists(arguments['--path']):
            os.chdir(arguments['--path'])
        else:
            logger.error('Invalid path in arguments...')
            sys.exit()
    logger.debug('Downloading to '+os.getcwd()+'...')

    logger.newline()
    if arguments['-l']:
        parse_url(arguments['-l'])
    elif arguments['me']:
        if arguments['-a']:
            download_all_user_tracks(who_am_i())
        elif arguments['-f']:
            download_all_of_user(who_am_i(), 'favorite', download_track)
        elif arguments['-t']:
            download_all_of_user(who_am_i(), 'track', download_track)
        elif arguments['-p']:
            download_all_of_user(who_am_i(), 'playlist', download_playlist)


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
        logger.error('Are you sure scdl.cfg is in $HOME/.config/scdl/ ?')
        sys.exit()
    if os.path.exists(path):
        os.chdir(path)
    else:
        logger.error('Invalid path in scdl.cfg...')
        sys.exit()


def get_item(track_url):
    """
    Fetches metadata for an track or playlist
    """
    try:
        item = client.get('/resolve', url=track_url)
    except Exception:
        logger.error('Error resolving url, retrying...')
        time.sleep(5)
        try:
            item = client.get('/resolve', url=track_url)
        except Exception as e:
            logger.error('Could not resolve url {0}'.format(track_url))
            logger.exception(e)
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
        logger.info('Found a track')
        track = json.loads(item.raw_data)
        logger.debug(track)
        download_track(track)
    elif item.kind == 'playlist':
        logger.info('Found a playlist')
        download_playlist(item)
    elif item.kind == 'user':
        logger.info('Found a user profile')
        if arguments['-f']:
            download_all_of_user(item, 'favorite', download_track)
        elif arguments['-t']:
            download_all_of_user(item, 'track', download_track)
        elif arguments['-a']:
            download_all_user_tracks(item)
        elif arguments['-p']:
            download_all_of_user(item, 'playlist', download_playlist)
        else:
            logger.error('Please provide a download type...')
    else:
        logger.error('Unknown item type')


def who_am_i():
    """
    display to who the current token correspond, check if the token is valid
    """
    global client
    client = soundcloud.Client(access_token=token, client_id=scdl_client_id)

    try:
        current_user = client.get('/me')
    except:
        logger.error('Invalid token...')
        sys.exit(0)
    logger.info('Hello {0.username}!'.format(current_user))
    logger.newline()
    return current_user


def download_all_user_tracks(user):
    """
    Find track & repost of the user
    """
    global offset
    resources = list()
    start_offset = offset

    logger.info('Retrieving all the track of user {0.username}...'.format(user))
    url = 'https://api-v2.soundcloud.com/profile/soundcloud:users:{0.id}?limit=200&offset={1}'.format(
        user, offset
    )
    while url:
        url = '{0}&client_id={1}'.format(url, scdl_client_id)
        logger.debug('url: ' + url)

        response = requests.get(url)
        json_data = response.json()

        resources.extend(json_data['collection'])
        url = json_data['next_href']

    total = len(resources)
    s = '' if total == 1 else 's'
    logger.info('Retrieved {0} track{1}'.format(total, s))
    for counter, item in enumerate(resources, 1):
        try:
            name = 'track' if item['type'] == 'track-repost' else item['type']
            logger.info('n°{1} of {2} is a {0}'.format(name, counter + start_offset, total))
            logger.debug(item[name])
            parse_url(item[name]['uri'])
        except Exception as e:
            logger.exception(e)
    logger.info('Downloaded all {2} {0}{1} of user {3.username}!'.format(name, s, total, user))


def download_all_of_user(user, name, download_function):
    """
    Download all items of a user. Can be playlist or track, or whatever handled by the download function.
    """
    logger.info('Retrieving the {1}s of user {0.username}...'.format(user, name))
    items = client.get_all('/users/{0.id}/{1}s'.format(user, name), offset=offset)
    total = len(items)
    s = '' if total == 1 else 's'
    logger.info('Retrieved {2} {0}{1}'.format(name, s, total))
    for counter, item in enumerate(items, 1):
        try:
            logger.info('{0} n°{1} of {2}'.format(name.capitalize(), counter + offset, total))
            download_function(item)
        except Exception as e:
            logger.exception(e)
    logger.info('Downloaded all {2} {0}{1} of user {3.username}!'.format(name, s, total, user))


def download_my_stream():
    """
    DONT WORK FOR NOW
    Download the stream of the current user
    """
    client = soundcloud.Client(access_token=token, client_id=scdl_client_id)
    activities = client.get('/me/activities')
    logger.debug(activities)


def download_playlist(playlist):
    """
    Download a playlist
    """
    global offset
    invalid_chars = '\/:*?|<>"'
    playlist_name = playlist.title.encode('utf-8', 'ignore').decode('utf-8')
    playlist_name = ''.join(c for c in playlist_name if c not in invalid_chars)

    if not os.path.exists(playlist_name):
        os.makedirs(playlist_name)
    os.chdir(playlist_name)

    with open(playlist_name + '.m3u', 'w+') as playlist_file:
        playlist_file.write('#EXTM3U' + os.linesep)
        for counter, track_raw in enumerate(playlist.tracks, 1):
            if offset > 0:
                offset -= 1
                continue
            logger.debug(track_raw)
            logger.info('Track n°{0}'.format(counter))
            download_track(track_raw, playlist.title, playlist_file)
    os.chdir('..')


def download_all(tracks):
    """
    Download all song of a page
    Not recommended
    """
    logger.error('NOTE: This will only download the songs of the page.(49 max)')
    logger.error('I recommend you to provide a user link and a download type.')
    for counter, track in enumerate(tracks, 1):
        logger.newline()
        logger.info('Track n°{0}'.format(counter))
        download_track(track)


def alternative_download(track):
    """
    Not sure if the url is sill correct...
    """
    logger.debug('alternative_download used')
    url = 'http://api.soundcloud.com/i1/tracks/{0.id}/streams?client_id=a3e059563d7fd3372b49b37f00a00bcf'.format(track)
    r = requests.get(url)
    json_data = r.json()
    try:
        mp3_url = json_data['http_mp3_128_url']
    except KeyError:
        logger.error('http_mp3_128_url not found in json response, report to developer.')
        mp3_url = None
    return mp3_url


def download_track(track, playlist_name=None, playlist_file=None):
    """
    Downloads a track
    """
    global arguments

    if track['streamable']:
        try:
            stream_url = client.get(track['stream_url'], allow_redirects=False)
            url = stream_url.location
        except requests.exceptions.HTTPError:
            url = alternative_download(track)
    else:
        logger.error('{0.title} is not streamable...'.format(track))
        logger.newline()
        return
    title = track['title']
    title = title.encode('utf-8', 'ignore').decode(sys.stdout.encoding)
    logger.info('Downloading {0}'.format(title))

    # filename
    if track['downloadable'] and not arguments['--onlymp3']:
        logger.info('Downloading the orginal file.')
        download_url = track['download_url']
        url = '{0}?client_id={1}'.format(download_url, scdl_client_id)
        r = requests.get(url, stream=True)
        d = r.headers['content-disposition']
        filename = re.findall("filename=(.+)", d)
    else:
        invalid_chars = '\/:*?|<>"'
        username = track['user']['username']
        if username not in title and arguments['--addtofile']:
            title = '{0} - {1}'.format(username, title)
        title = ''.join(c for c in title if c not in invalid_chars)
        filename = title + '.mp3'

    # Add the track to the generated m3u playlist file
    if playlist_file:
        duration = math.floor(track['duration'] / 1000)
        playlist_file.write('#EXTINF:{0},{1}{3}{2}{3}'.format(duration, title, filename, os.linesep))

    # Download
    if not os.path.isfile(filename):
        r = requests.get(url, stream=True)
        with open(filename, 'wb') as f:
            total_length = int(r.headers.get('content-length'))
            for chunk in progress.bar(r.iter_content(chunk_size=1024), expected_size=(total_length/1024) + 1):
                if chunk:
                    f.write(chunk)
                    f.flush()
        logger.newline()
        if '.mp3' in filename:
            try:
                if playlist_name is None:
                    settags(track, filename)
                else:
                    settags(track, filename, playlist_name)
            except Exception as e:
                logger.error('Error trying to set the tags...')
                logger.debug(e)
        else:
            logger.error("This type of audio doesn't support tagging...")
    else:
        if arguments['-c']:
            logger.info('{0} already Downloaded'.format(title))
            logger.newline()
            return
        else:
            logger.newline()
            logger.error('Music already exists ! (exiting)')
            sys.exit(0)

    logger.newline()
    logger.info('{0} Downloaded.'.format(filename))
    logger.newline()


def settags(track, filename, album=None):
    """
    Set the tags to the mp3
    """
    logger.info('Settings tags...')
    user_id = track['user_id']
    user = client.get('/users/{0}'.format(user_id), allow_redirects=False)

    artwork_url = track['artwork_url']
    if artwork_url is None:
        artwork_url = user.avatar_url
    artwork_url = artwork_url.replace('large', 't500x500')
    response = requests.get(artwork_url, stream=True)
    with open('/tmp/scdl.jpg', 'wb') as out_file:
        shutil.copyfileobj(response.raw, out_file)

    audio = mutagen.File(filename)
    audio['TIT2'] = mutagen.id3.TIT2(encoding=3, text=track['title'])
    audio['TPE1'] = mutagen.id3.TPE1(encoding=3, text=user.username)
    audio['TCON'] = mutagen.id3.TCON(encoding=3, text=track['genre'])
    if album is not None:
        audio['TALB'] = mutagen.id3.TALB(encoding=3, text=album)
    if artwork_url is not None:
        audio['APIC'] = mutagen.id3.APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover',
                                         data=open('/tmp/scdl.jpg', 'rb').read())
    else:
        logger.error('Artwork can not be set.')
    audio.save()


def signal_handler(signal, frame):
    """
    handle keyboardinterrupt
    """
    time.sleep(1)
    for path in os.listdir():
        if not os.path.isdir(path) and '.tmp' in path:
            os.remove(path)

    logger.newline()
    logger.info('Good bye!')
    sys.exit(0)

if __name__ == '__main__':
    main()
