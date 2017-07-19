#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

"""scdl allow you to download music from soundcloud

Usage:
    scdl -l <track_url> [-a | -f | -t | -p][-c][-o <offset>]\
[--hidewarnings][--debug | --error][--path <path>][--addtofile][--onlymp3]
[--hide-progress][--min-size <size>][--max-size <size>]
    scdl me (-s | -a | -f | -t | -p | -m)[-c][-o <offset>]\
[--hidewarnings][--debug | --error][--path <path>][--addtofile][--onlymp3]
[--hide-progress][--min-size <size>][--max-size <size>]
    scdl -h | --help
    scdl --version


Options:
    -h --help             Show this screen
    --version             Show version
    me                    Use the user profile from the auth_token
    -l [url]              URL can be track/playlist/user
    -s                    Download the stream of a user (token needed)
    -a                    Download all tracks of a user (including repost)
    -t                    Download all uploads of a user
    -f                    Download all favorites of a user
    -p                    Download all playlists of a user
    -m                    Download all liked and owned playlists of a user
    -c                    Continue if a music already exist
    -o [offset]           Begin with a custom offset
    --path [path]         Use a custom path for this time
    --min-size [min-size] Skip tracks smaller than size (k/m/g)
    --max-size [max-size] Skip tracks larger than size (k/m/g)
    --hidewarnings        Hide Warnings. (use with precaution)
    --addtofile           Add the artist name to the filename if it isn't in the filename already
    --onlymp3             Download only the mp3 file even if the track is Downloadable
    --error               Only print debug information (Error/Warning)
    --debug               Print every information and
    --hide-progress       Hide the wget progress bar
"""

import logging
import os
import signal
import sys
import time
import warnings
import math
import shutil
import requests
import re
import tempfile
import codecs

import configparser
import mutagen
from docopt import docopt
from clint.textui import progress

from scdl import __version__, CLIENT_ID, ALT_CLIENT_ID
from scdl import client, utils


logging.basicConfig(level=logging.INFO, format='%(message)s')
logging.getLogger('requests').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addFilter(utils.ColorizeFilter())

arguments = None
token = ''
path = ''
offset = 0

url = {
    'playlists-liked': ('https://api-v2.soundcloud.com/users/{0}/playlists'
                        '/liked_and_owned?limit=200&offset={1}'),
    'favorites': ('https://api.soundcloud.com/users/{0}/favorites?'
                  'limit=200&offset={1}'),
    'tracks': ('https://api.soundcloud.com/users/{0}/tracks?'
               'limit=200&offset={1}'),
    'all': ('https://api-v2.soundcloud.com/profile/soundcloud:users:{0}?'
            'limit=200&offset={1}'),
    'playlists': ('https://api.soundcloud.com/users/{0}/playlists?'
                  'limit=200&offset={1}'),
    'resolve': ('https://api.soundcloud.com/resolve?url={0}'),
    'user': ('https://api.soundcloud.com/users/{0}'),
    'me': ('https://api.soundcloud.com/me?oauth_token={0}')
}

client = client.Client()


def main():
    """
    Main function, call parse_url
    """
    signal.signal(signal.SIGINT, signal_handler)
    global offset
    global arguments

    # Parse argument
    arguments = docopt(__doc__, version=__version__)

    if arguments['--debug']:
        logger.level = logging.DEBUG
    elif arguments['--error']:
        logger.level = logging.ERROR

    # import conf file
    get_config()

    logger.info('Soundcloud Downloader')
    logger.debug(arguments)

    if arguments['-o'] is not None:
        try:
            offset = int(arguments['-o']) - 1
        except:
            logger.error('Offset should be an integer...')
            sys.exit()
        logger.debug('offset: %d', offset)

    if arguments['--min-size'] is not None:
        try:
            arguments['--min-size'] = utils.size_in_bytes(
                arguments['--min-size']
            )
        except:
            logger.exception(
                'Min size should be an integer with a possible unit suffix'
            )
            sys.exit()
        logger.debug('min-size: %d', arguments['--min-size'])

    if arguments['--max-size'] is not None:
        try:
            arguments['--max-size'] = utils.size_in_bytes(
                arguments['--max-size']
            )
        except:
            logger.error(
                'Max size should be an integer with a possible unit suffix'
            )
            sys.exit()
        logger.debug('max-size: %d', arguments['--max-size'])

    if arguments['--hidewarnings']:
        warnings.filterwarnings('ignore')

    if arguments['--path'] is not None:
        if os.path.exists(arguments['--path']):
            os.chdir(arguments['--path'])
        else:
            logger.error('Invalid path in arguments...')
            sys.exit()
    logger.debug('Downloading to '+os.getcwd()+'...')

    if arguments['-l']:
        parse_url(arguments['-l'])
    elif arguments['me']:
        if arguments['-f']:
            download(who_am_i(), 'favorites', 'likes')
        elif arguments['-t']:
            download(who_am_i(), 'tracks', 'uploaded tracks')
        elif arguments['-a']:
            download(who_am_i(), 'all', 'tracks and reposts')
        elif arguments['-p']:
            download(who_am_i(), 'playlists', 'playlists')
        elif arguments['-m']:
            download(who_am_i(), 'playlists-liked', 'my and liked playlists')


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
        logger.error('Are you sure scdl.cfg is in $HOME/.config/scdl/ ? Are both "auth_token" and "path" defined there ?')
        sys.exit()
    if os.path.exists(path):
        os.chdir(path)
    else:
        logger.error('Invalid path in scdl.cfg...')
        sys.exit()


def get_item(track_url, client_id=CLIENT_ID):
    """
    Fetches metadata for an track or playlist
    """
    try:
        item_url = url['resolve'].format(track_url)

        r = requests.get(item_url, params={'client_id': client_id})
        logger.debug(r.url)
        if r.status_code == 403:
            return get_item(track_url, ALT_CLIENT_ID)

        item = r.json()
        no_tracks = item['kind'] == 'playlist' and not item['tracks']
        if no_tracks and client_id != ALT_CLIENT_ID:
            return get_item(track_url, ALT_CLIENT_ID)
    except Exception:
        if client_id == ALT_CLIENT_ID:
            logger.error('Get item failed...')
            return
        logger.error('Error resolving url, retrying...')
        time.sleep(5)
        try:
            return get_item(track_url, ALT_CLIENT_ID)
        except Exception as e:
            logger.error('Could not resolve url {0}'.format(track_url))
            logger.exception(e)
            sys.exit(0)
    return item


def parse_url(track_url):
    """
    Detects if the URL is a track or playlists, and parses the track(s)
    to the track downloader
    """
    global arguments
    item = get_item(track_url)
    logger.debug(item)
    if not item:
        return
    elif item['kind'] == 'track':
        logger.info('Found a track')
        download_track(item)
    elif item['kind'] == 'playlist':
        logger.info('Found a playlist')
        download_playlist(item)
    elif item['kind'] == 'user':
        logger.info('Found a user profile')
        if arguments['-f']:
            download(item, 'favorites', 'likes')
        elif arguments['-t']:
            download(item, 'tracks', 'uploaded tracks')
        elif arguments['-a']:
            download(item, 'all', 'tracks and reposts')
        elif arguments['-p']:
            download(item, 'playlists', 'playlists')
        elif arguments['-m']:
            download(item, 'playlists-liked', 'my and liked playlists')
        else:
            logger.error('Please provide a download type...')
    else:
        logger.error('Unknown item type')


def who_am_i():
    """
    display to who the current token correspond, check if the token is valid
    """
    me = url['me'].format(token)
    r = requests.get(me, params={'client_id': CLIENT_ID})
    r.raise_for_status()
    current_user = r.json()
    logger.debug(me)

    logger.info('Hello {0}!'.format(current_user['username']))
    return current_user


def download(user, dl_type, name):
    """
    Download all items of a user
    """
    username = user['username']
    user_id = user['id']
    logger.info(
        'Retrieving all {0} of user {1}...'.format(name, username)
    )
    dl_url = url[dl_type].format(user_id, offset)
    logger.debug(dl_url)
    ressources = client.get_collection(dl_url, token)
    logger.debug(ressources)
    total = len(ressources)
    logger.info('Retrieved {0} {1}'.format(total, name))
    for counter, item in enumerate(ressources, 1):
        try:
            logger.debug(item)
            logger.info('{0} n°{1} of {2}'.format(
                name.capitalize(), counter + offset, total)
            )
            if dl_type == 'all':
                item_name = item['type'].split('-')[0]  # remove the '-repost'
                uri = item[item_name]['uri']
                parse_url(uri)
            elif dl_type == 'playlists':
                download_playlist(item)
            elif dl_type == 'playlists-liked':
                parse_url(item['playlist']['uri'])
            else:
                download_track(item)
        except Exception as e:
            logger.exception(e)
    logger.info('Downloaded all {0} {1} of user {2}!'.format(
        total, name, username)
    )


def download_playlist(playlist):
    """
    Download a playlist
    """
    invalid_chars = '\/:*?|<>"'
    playlist_name = playlist['title'].encode('utf-8', 'ignore')
    playlist_name = playlist_name.decode('utf8')
    playlist_name = ''.join(c for c in playlist_name if c not in invalid_chars)

    if not os.path.exists(playlist_name):
        os.makedirs(playlist_name)
    os.chdir(playlist_name)

    try:
        with codecs.open(playlist_name + '.m3u', 'w+', 'utf8') as playlist_file:
            playlist_file.write('#EXTM3U' + os.linesep)
            for counter, track_raw in enumerate(playlist['tracks'], 1):
                logger.debug(track_raw)
                logger.info('Track n°{0}'.format(counter))
                download_track(track_raw, playlist['title'], playlist_file)
    finally:
        os.chdir('..')


def download_my_stream():
    """
    DONT WORK FOR NOW
    Download the stream of the current user
    """
    # TODO
    # Use Token


def download_all_of_a_page(tracks):
    """
    NOT RECOMMENDED
    Download all song of a page
    """
    logger.error(
        'NOTE: This will only download the songs of the page.(49 max)'
    )
    logger.error('I recommend you to provide a user link and a download type.')
    for counter, track in enumerate(tracks, 1):
        logger.info('\nTrack n°{0}'.format(counter))
        download_track(track)

def get_filename(track, title):
    username = track['user']['username']
    if username not in title and arguments['--addtofile']:
        title = '{0} - {1}'.format(username, title)
    return title + '.mp3'


def download_track(track, playlist_name=None, playlist_file=None):
    """
    Downloads a track
    """
    global arguments

    title = track['title']
    title = title.encode('utf-8', 'ignore').decode('utf8')
    if track['streamable']:
        url = track['stream_url']
    else:
        logger.error('{0} is not streamable...'.format(title))
        return
    logger.info('Downloading {0}'.format(title))

    r = None
    # filename
    if track['downloadable'] and not arguments['--onlymp3']:
        logger.info('Downloading the original file.')
        original_url = track['download_url']
        r = requests.get(original_url, params={'client_id': CLIENT_ID}, stream=True)
        if r.status_code == 401:
            logger.info('The original file has no download left.')
            filename = get_filename(track, title)
        else:
            if r.headers['content-disposition']:
                d = r.headers['content-disposition']
                filename = re.findall("filename=(.+)", d)[0][1:-1]
            else:
                filename = get_filename(track, title)
    else:
        filename = get_filename(track, title)

    invalid_chars = '\/:*?|<>"'
    filename = ''.join(c for c in filename if c not in invalid_chars)
    base, ext = os.path.splitext(filename)
    filename = base + ext.lower()
    logger.debug("filename : {0}".format(filename))
    # Add the track to the generated m3u playlist file
    if playlist_file:
        duration = math.floor(track['duration'] / 1000)
        playlist_file.write(
            '#EXTINF:{0},{1}{3}{2}{3}'.format(
                duration, title, filename, os.linesep
            )
        )

    # Download
    if not os.path.isfile(filename):
        if r is None or r.status_code == 401:
            r = requests.get(url, params={'client_id': CLIENT_ID}, stream=True)
            logger.debug(r.url)
            if r.status_code == 401 or r.status_code == 429:
                r = requests.get(url, params={'client_id': ALT_CLIENT_ID}, stream=True)
                logger.debug(r.url)
                r.raise_for_status()
        temp = tempfile.NamedTemporaryFile(delete=False)

        total_length = int(r.headers.get('content-length'))

        min_size = arguments.get('--min-size')
        max_size = arguments.get('--max-size')

        if min_size is not None and total_length < min_size:
            logging.info('{0} not large enough, skipping'.format(title))
            return

        if max_size is not None and total_length > max_size:
            logging.info('{0} too large, skipping'.format(title))
            return

        with temp as f:
            for chunk in progress.bar(
                r.iter_content(chunk_size=1024),
                expected_size=(total_length/1024) + 1,
                hide=True if arguments["--hide-progress"] else False
            ):
                if chunk:
                    f.write(chunk)
                    f.flush()

        shutil.move(temp.name, os.path.join(os.getcwd(), filename))
        if filename.endswith('.mp3') or filename.endswith('.m4a'):
            try:
                setMetadata(track, filename, playlist_name)
            except Exception as e:
                logger.error('Error trying to set the tags...')
                logger.debug(e)
        else:
            logger.error("This type of audio doesn't support tagging...")
    else:
        if arguments['-c']:
            logger.info('{0} already Downloaded'.format(title))
            return
        else:
            logger.error('Music already exists ! (exiting)')
            sys.exit(0)

    logger.info('{0} Downloaded.\n'.format(filename))


def setMetadata(track, filename, album=None):
    """
    Set the tags to the mp3
    """
    logger.info('Settings tags...')
    artwork_url = track['artwork_url']
    user = track['user']
    if not artwork_url:
        artwork_url = user['avatar_url']
    artwork_url = artwork_url.replace('large', 't500x500')
    response = requests.get(artwork_url, stream=True)
    with tempfile.NamedTemporaryFile() as out_file:
        shutil.copyfileobj(response.raw, out_file)
        out_file.seek(0)

        audio = mutagen.File(filename)
        audio['TIT2'] = mutagen.id3.TIT2(encoding=3, text=track['title'])
        audio['TPE1'] = mutagen.id3.TPE1(encoding=3, text=user['username'])
        audio['TCON'] = mutagen.id3.TCON(encoding=3, text=track['genre'])
        if album:
            audio['TALB'] = mutagen.id3.TALB(encoding=3, text=album)
        if artwork_url:
            audio['APIC'] = mutagen.id3.APIC(
                encoding=3, mime='image/jpeg', type=3, desc='Cover',
                data=out_file.read()
                )
        else:
            logger.error('Artwork can not be set.')
    audio.save()


def signal_handler(signal, frame):
    """
    Handle Keyboardinterrupt
    """
    logger.info('\nGood bye!')
    sys.exit(0)

if __name__ == '__main__':
    main()
