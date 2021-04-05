#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

"""scdl allows you to download music from Soundcloud

Usage:
    scdl -l <track_url> [-a | -f | -C | -t | -p][-c | --force-metadata][-n <maxtracks>]\
[-o <offset>][--hidewarnings][--debug | --error][--path <path>][--addtofile][--addtimestamp]
[--onlymp3][--hide-progress][--min-size <size>][--max-size <size>][--remove][--no-album-tag]
[--no-playlist-folder][--download-archive <file>][--extract-artist][--flac]
    scdl me (-s | -a | -f | -t | -p | -m)[-c | --force-metadata][-n <maxtracks>]\
[-o <offset>][--hidewarnings][--debug | --error][--path <path>][--addtofile][--addtimestamp]
[--onlymp3][--hide-progress][--min-size <size>][--max-size <size>][--remove]
[--no-playlist-folder][--download-archive <file>][--extract-artist][--flac][--no-album-tag]
    scdl -h | --help
    scdl --version


Options:
    -h --help                   Show this screen
    --version                   Show version
    me                          Use the user profile from the auth_token
    -l [url]                    URL can be track/playlist/user
    -n [maxtracks]              Download the n last tracks of a playlist according to the creation date
    -s                          Download the stream of a user (token needed)
    -a                          Download all tracks of user (including reposts)
    -t                          Download all uploads of a user (no reposts)
    -f                          Download all favorites of a user
    -C                          Download all commented by a user
    -p                          Download all playlists of a user
    -m                          Download all liked and owned playlists of user
    -c                          Continue if a downloaded file already exists
    --force-metadata            This will set metadata on already downloaded track
    -o [offset]                 Begin with a custom offset
    --addtimestamp              Add track creation timestamp to filename,
                                which allows for chronological sorting
    --addtofile                 Add artist to filename if missing
    --debug                     Set log level to DEBUG
    --download-archive [file]   Keep track of track IDs in an archive file,
                                and skip already-downloaded files
    --error                     Set log level to ERROR
    --extract-artist            Set artist tag from title instead of username
    --hide-progress             Hide the wget progress bar
    --hidewarnings              Hide Warnings. (use with precaution)
    --max-size [max-size]       Skip tracks larger than size (k/m/g)
    --min-size [min-size]       Skip tracks smaller than size (k/m/g)
    --no-playlist-folder        Download playlist tracks into main directory,
                                instead of making a playlist subfolder
    --onlymp3                   Download only the streamable mp3 file,
                                even if track has a Downloadable file
    --path [path]               Use a custom path for downloaded files
    --remove                    Remove any files not downloaded from execution
    --flac                      Convert original files to .flac
    --no-album-tag              On some player track get the same cover art if from the same album, this prevent it
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
import shlex
import shutil

import configparser
import mutagen

from mutagen.easymp4 import EasyMP4
EasyMP4.RegisterTextKey('website', '\xa9cmt')

from docopt import docopt
from clint.textui import progress

from scdl import __version__, CLIENT_ID, ALT_CLIENT_ID
from scdl import client, utils

from datetime import datetime
import subprocess

logging.basicConfig(level=logging.INFO, format='%(message)s')
logging.getLogger('requests').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addFilter(utils.ColorizeFilter())

arguments = None
token = ''
path = ''
offset = 1

url = {
    'playlists-liked': ('https://api-v2.soundcloud.com/users/{0}/playlists'
                        '/liked_and_owned?limit=200'),
    'favorites': ('https://api-v2.soundcloud.com/users/{0}/track_likes?'
                  'limit=200'),
    'commented': ('https://api-v2.soundcloud.com/users/{0}/comments'),
    'tracks': ('https://api-v2.soundcloud.com/users/{0}/tracks?'
               'limit=200'),
    'all': ('https://api-v2.soundcloud.com/profile/soundcloud:users:{0}?'
            'limit=200'),
    'playlists': ('https://api-v2.soundcloud.com/users/{0}/playlists?'
                  'limit=5'),
    'resolve': ('https://api-v2.soundcloud.com/resolve?url={0}'),
    'trackinfo': ('https://api-v2.soundcloud.com/tracks/{0}'),
    'original_download' : ("https://api-v2.soundcloud.com/tracks/{0}/download"),
    'user': ('https://api-v2.soundcloud.com/users/{0}'),
    'me': ('https://api-v2.soundcloud.com/me?oauth_token={0}')
}
client = client.Client()

fileToKeep = []


def main():
    """
    Main function, parses the URL from command line arguments
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
            offset = int(arguments['-o'])
            if offset < 0:
                raise
        except:
            logger.error('Offset should be a positive integer...')
            sys.exit(-1)
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
            sys.exit(-1)
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
            sys.exit(-1)
        logger.debug('max-size: %d', arguments['--max-size'])

    if arguments['--hidewarnings']:
        warnings.filterwarnings('ignore')

    if arguments['--path'] is not None:
        if os.path.exists(arguments['--path']):
            os.chdir(arguments['--path'])
        else:
            logger.error('Invalid path in arguments...')
            sys.exit(-1)
    logger.debug('Downloading to ' + os.getcwd() + '...')

    if arguments['-l']:
        parse_url(arguments['-l'])
    elif arguments['me']:
        if arguments['-f']:
            download(who_am_i(), 'favorites', 'likes')
        if arguments['-C']:
            download(who_am_i(), 'commented', 'commented tracks')
        elif arguments['-t']:
            download(who_am_i(), 'tracks', 'uploaded tracks')
        elif arguments['-a']:
            download(who_am_i(), 'all', 'tracks and reposts')
        elif arguments['-p']:
            download(who_am_i(), 'playlists', 'playlists')
        elif arguments['-m']:
            download(who_am_i(), 'playlists-liked', 'my and liked playlists')

    if arguments['--remove']:
        remove_files()


def get_config():
    """
    Reads the music download filepath from scdl.cfg
    """
    global token
    config = configparser.ConfigParser()

    if 'XDG_CONFIG_HOME' in os.environ:
        config_file = os.path.join(
            os.environ['XDG_CONFIG_HOME'], 'scdl', 'scdl.cfg',
        )
    else:
        config_file = os.path.join(
            os.path.expanduser('~'), '.config', 'scdl', 'scdl.cfg',
        )
    config.read(config_file, 'utf8')
    try:
        token = config['scdl']['auth_token']
        path = config['scdl']['path']
    except:
        logger.error('Are you sure scdl.cfg is in $HOME/.config/scdl/ ?')
        logger.error('Are both "auth_token" and "path" defined there?')
        sys.exit(-1)
    if os.path.exists(path):
        os.chdir(path)
    else:
        logger.error('Invalid path in scdl.cfg...')
        sys.exit(-1)


def get_item(track_url, client_id=CLIENT_ID):
    """
    Fetches metadata for a track or playlist
    """
    try:
        item_url = url['resolve'].format(track_url)

        headers = {'Authorization': 'OAuth {0}'.format(token)} if token else {}
        r = requests.get(item_url, params={'client_id': client_id}, headers=headers)
        logger.debug(r.url)
        if r.status_code == 403:
            return get_item(track_url, ALT_CLIENT_ID)

        item = r.json()
        no_tracks = item['kind'] == 'playlist' and not item['tracks']
        if no_tracks and client_id != ALT_CLIENT_ID:
            return get_item(track_url, ALT_CLIENT_ID)
    except Exception:
        if client_id == ALT_CLIENT_ID:
            logger.error('Failed to get item...')
            return
        logger.error('Error resolving url, retrying...')
        time.sleep(5)
        try:
            return get_item(track_url, ALT_CLIENT_ID)
        except Exception as e:
            logger.error('Could not resolve url {0}'.format(track_url))
            logger.exception(e)
            sys.exit(-1)
    return item


def parse_url(track_url):
    """
    Detects if a URL is a track or a playlist, and parses the track(s)
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
        elif arguments['-C']:
            download(item, 'commented', 'commented tracks')
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
        logger.error('Unknown item type {0}'.format(item['kind']))


def who_am_i():
    """
    Display username from current token and check for validity
    """
    me = url['me'].format(token)
    r = requests.get(me, params={'client_id': CLIENT_ID})
    r.raise_for_status()
    current_user = r.json()
    logger.debug(me)

    logger.info('Hello {0}!'.format(current_user['username']))
    return current_user


def remove_files():
    """
    Removes any pre-existing tracks that were not just downloaded
    """
    logger.info("Removing local track files that were not downloaded...")
    files = [f for f in os.listdir('.') if os.path.isfile(f)]
    for f in files:
        if f not in fileToKeep:
            os.remove(f)


def get_track_info(track):
    """
    Fetches track info from Soundcloud, given a track_id
    """
    if 'media' in track:
        return track

    logger.info('Retrieving more info on the track')
    info_url = url["trackinfo"].format(track['id'])
    r = requests.get(info_url, params={'client_id': CLIENT_ID}, stream=True)
    item = r.json()
    logger.debug(item)
    return item


def download(user, dl_type, name):
    """
    Download user items of dl_type (ie. all, playlists, liked, commented, etc.)
    """
    if not is_ffmpeg_available():
        logger.error('ffmpeg is not available and download cannot continue. Please install ffmpeg and re-run the program.')
        return
    
    username = user['username']
    user_id = user['id']
    logger.info(
        'Retrieving all {0} of user {1}...'.format(name, username)
    )
    dl_url = url[dl_type].format(user_id)
    logger.debug(dl_url)
    resources = client.get_collection(dl_url, token)
    del resources[:offset - 1]
    logger.debug(resources)
    total = len(resources)
    logger.info('Retrieved {0} {1}'.format(total, name))
    for counter, item in enumerate(resources, offset):
        try:
            logger.debug(item)
            logger.info('{0} n°{1} of {2}'.format(
                name.capitalize(), counter, total)
            )
            if dl_type == 'all':
                item_name = item['type'].split('-')[0]  # remove the '-repost'
                uri = item[item_name]['uri']
                parse_url(uri)
            elif dl_type == 'playlists':
                download_playlist(item)
            elif dl_type == 'playlists-liked':
                parse_url(item['playlist']['uri'])
            elif dl_type == 'tracks':
                download_track(item)
            else:
                download_track(item['track'])
        except Exception as e:
            logger.exception(e)
    logger.info('Downloaded all {0} {1} of user {2}!'.format(
        total, name, username)
    )


def download_playlist(playlist):
    """
    Downloads a playlist
    """
    global arguments
    invalid_chars = '\/:*?|<>"'
    playlist_name = playlist['title'].encode('utf-8', 'ignore')
    playlist_name = playlist_name.decode('utf8')
    playlist_name = ''.join(c for c in playlist_name if c not in invalid_chars)

    if not arguments['--no-playlist-folder']:
        if not os.path.exists(playlist_name):
            os.makedirs(playlist_name)
        os.chdir(playlist_name)

    try:
        with codecs.open(playlist_name + '.m3u', 'w+', 'utf8') as playlist_file:
            playlist_file.write('#EXTM3U' + os.linesep)
            if arguments['-n']: # Order by creation date and get the n lasts tracks
                playlist['tracks'].sort(key=lambda track: track['created_at'], reverse=True)
                playlist['tracks'] = playlist['tracks'][:int(arguments['-n'])]
            else:
                del playlist['tracks'][:offset - 1]
            for counter, track_raw in enumerate(playlist['tracks'], offset):
                logger.debug(track_raw)
                logger.info('Track n°{0}'.format(counter))
                playlist_info = {'title': playlist['title'], 'file': playlist_file, 'tracknumber': counter}
                download_track(track_raw, playlist_info)
    finally:
        if not arguments['--no-playlist-folder']:
            os.chdir('..')


def download_my_stream():
    """
    DONT WORK FOR NOW
    Download the stream of the current user
    """
    # TODO
    # Use Token


def try_utime(path, filetime):
    try:
        os.utime(path, (time.time(), filetime))
    except:
        logger.error("Cannot update utime of file")


def get_filename(track, original_filename=None, aac=False):
    invalid_chars = '\/:*?|<>"'
    username = track['user']['username']
    title = track['title'].encode('utf-8', 'ignore').decode('utf8')

    if arguments['--addtofile']:
        if username not in title and '-' not in title:
            title = '{0} - {1}'.format(username, title)
            logger.debug('Adding "{0}" to filename'.format(username))

    if arguments['--addtimestamp']:
        # created_at sample: 2019-01-30T11:11:37Z
        ts = datetime \
            .strptime(track['created_at'], "%Y-%m-%dT%H:%M:%SZ") \
            .timestamp()

        title = str(int(ts)) + "_" + title

    ext = ".m4a" if aac else ".mp3" # contain aac in m4a to write metadata
    if original_filename is not None:
        original_filename.encode('utf-8', 'ignore').decode('utf8')
        ext = os.path.splitext(original_filename)[1]
    filename = title[:251] + ext.lower()
    filename = ''.join(c for c in filename if c not in invalid_chars)
    return filename


def download_original_file(track, title):
    logger.info('Downloading the original file.')
    original_url = url['original_download'].format(track['id'])

    # Get the requests stream
    r = requests.get(
        original_url, params={'client_id': CLIENT_ID}
    )
    r = requests.get(r.json()['redirectUri'], stream=True)
    if r.status_code == 401:
        logger.info('The original file has no download left.')
        return (None, False)

    if r.status_code == 404:
        logger.info('Could not get name from stream - using basic name')
        return (None, False)

    # Find filename
    d = r.headers.get('content-disposition')
    filename = re.findall("filename=(.+)", d)[0]
    filename = get_filename(track, filename)
    logger.debug("filename : {0}".format(filename))

    # Skip if file ID or filename already exists
    if already_downloaded(track, title, filename):
        if arguments['--flac'] and can_convert(filename):
            filename = filename[:-4] + ".flac"
        return (filename, True)

    # Write file
    total_length = int(r.headers.get('content-length'))
    temp = tempfile.NamedTemporaryFile(delete=False)
    received = 0
    with temp as f:
        for chunk in progress.bar(
                r.iter_content(chunk_size=1024),
                expected_size=(total_length / 1024) + 1,
                hide=True if arguments["--hide-progress"] else False
        ):
            if chunk:
                received += len(chunk)
                f.write(chunk)
                f.flush()

    if received != total_length:
        logger.error('connection closed prematurely, download incomplete')
        sys.exit(-1)

    shutil.move(temp.name, os.path.join(os.getcwd(), filename))
    if arguments['--flac'] and can_convert(filename):
        logger.info('Converting to .flac...')
        newfilename = filename[:-4] + ".flac"

        commands = ['ffmpeg', '-i', filename, newfilename, '-loglevel', 'error']
        logger.debug("Commands: {}".format(commands))
        subprocess.call(commands)
        os.remove(filename)
        filename = newfilename

    return (filename, False)


def get_track_m3u8(track, aac=False):
    url = None
    for transcoding in track['media']['transcodings']:
        if transcoding['format']['protocol'] == 'hls':
            if (not aac and transcoding['format']['mime_type'] == 'audio/mpeg') \
                    or (aac and transcoding['format']['mime_type'].startswith('audio/mp4')):
                url = transcoding['url']

    if url is not None:
        headers = {'Authorization': 'OAuth {0}'.format(token)} if token else {}
        r = requests.get(url, params={'client_id': CLIENT_ID}, headers=headers)
        logger.debug(r.url)
        return r.json()['url']


def download_hls(track, title):

    if arguments['--onlymp3']:
        aac = False
    else:
        aac = any(t['format']['mime_type'].startswith('audio/mp4') for t in track['media']['transcodings'])

    filename = get_filename(track, None, aac)
    logger.debug("filename : {0}".format(filename))
    # Skip if file ID or filename already exists
    if already_downloaded(track, title, filename):
        return (filename, True)

    # Get the requests stream
    url = get_track_m3u8(track, aac)
    filename_path = os.path.abspath(filename)

    subprocess.call(['ffmpeg', '-i', url, '-c', 'copy', filename_path, '-loglevel', 'fatal'])
    return (filename, False)


def download_track(track, playlist_info=None):
    """
    Downloads a track
    """
    global arguments
    track = get_track_info(track)
    title = track['title']
    title = title.encode('utf-8', 'ignore').decode('utf8')
    logger.info('Downloading {0}'.format(title))

    # Not streamable
    if not track['streamable']:
        logger.error('{0} is not streamable...'.format(title))
        return

    # Geoblocked track
    if track['policy'] == 'BLOCK':
        logger.error('{0} is not available in your location...\n'.format(title))
        return

    # Downloadable track
    filename = None
    is_already_downloaded = False
    if track['downloadable'] and track['has_downloads_left'] and not arguments['--onlymp3']:
        filename, is_already_downloaded = download_original_file(track, title)

    if filename is None:
        filename, is_already_downloaded = download_hls(track, title)

    # Add the track to the generated m3u playlist file
    if playlist_info:
        duration = math.floor(track['duration'] / 1000)
        playlist_info['file'].write(
            '#EXTINF:{0},{1}{3}{2}{3}'.format(
                duration, title, filename, os.linesep
            )
        )

    if arguments['--remove']:
        fileToKeep.append(filename)

    record_download_archive(track)

    # Skip if file ID or filename already exists
    if is_already_downloaded and not arguments['--force-metadata']:
        logger.info('Track "{0}" already downloaded.'.format(title))
        return

    # If file does not exist an error occurred
    if not os.path.isfile(filename):
        logger.error('An error occurred downloading {0}.\n'.format(filename))
        logger.error('Exiting...')
        sys.exit(-1)

    # Try to set the metadata
    if filename.endswith('.mp3') or filename.endswith('.flac') or filename.endswith('.m4a'):
        try:
            set_metadata(track, filename, playlist_info)
        except Exception as e:
            logger.error('Error trying to set the tags...')
            logger.debug(e)
    else:
        logger.error("This type of audio doesn't support tagging...")

    # Try to change the real creation date
    created_at = track['created_at']
    timestamp = datetime.strptime(created_at, '%Y-%m-%dT%H:%M:%SZ')
    filetime = int(time.mktime(timestamp.timetuple()))
    try_utime(filename, filetime)

    logger.info('{0} Downloaded.\n'.format(filename))


def can_convert(filename):
    ext = os.path.splitext(filename)[1]
    return 'wav' in ext or 'aif' in ext


def already_downloaded(track, title, filename):
    """
    Returns True if the file has already been downloaded
    """
    global arguments
    already_downloaded = False

    if os.path.isfile(filename):
        already_downloaded = True
    if arguments['--flac'] and can_convert(filename) \
            and os.path.isfile(filename[:-4] + ".flac"):
        already_downloaded = True
    if arguments['--download-archive'] and in_download_archive(track):
        already_downloaded = True

    if arguments['--flac'] and can_convert(filename) and os.path.isfile(filename):
        already_downloaded = False

    if already_downloaded:
        if arguments['-c'] or arguments['--remove'] or arguments['--force-metadata']:
            return True
        else:
            logger.error('Track "{0}" already exists!'.format(title))
            logger.error('Exiting... (run again with -c to continue)')
            sys.exit(-1)
    return False


def in_download_archive(track):
    """
    Returns True if a track_id exists in the download archive
    """
    global arguments
    if not arguments['--download-archive']:
        return

    archive_filename = arguments.get('--download-archive')
    try:
        with open(archive_filename, 'a+', encoding='utf-8') as file:
            file.seek(0)
            track_id = '{0}'.format(track['id'])
            for line in file:
                if line.strip() == track_id:
                    return True
    except IOError as ioe:
        logger.error('Error trying to read download archive...')
        logger.debug(ioe)

    return False


def record_download_archive(track):
    """
    Write the track_id in the download archive
    """
    global arguments
    if not arguments['--download-archive']:
        return

    archive_filename = arguments.get('--download-archive')
    try:
        with open(archive_filename, 'a', encoding='utf-8') as file:
            file.write('{0}'.format(track['id']) + '\n')
    except IOError as ioe:
        logger.error('Error trying to write to download archive...')
        logger.debug(ioe)


def set_metadata(track, filename, playlist_info=None):
    """
    Sets the mp3 file metadata using the Python module Mutagen
    """
    logger.info('Setting tags...')
    global arguments
    artwork_url = track['artwork_url']
    user = track['user']
    if not artwork_url:
        artwork_url = user['avatar_url']
    artwork_url = artwork_url.replace('large', 't500x500')
    response = requests.get(artwork_url, stream=True)
    with tempfile.NamedTemporaryFile() as out_file:
        shutil.copyfileobj(response.raw, out_file)
        out_file.seek(0)

        track_created = track['created_at']
        track_date = datetime.strptime(track_created, "%Y-%m-%dT%H:%M:%SZ")
        debug_extract_dates = '{0} {1}'.format(track_created, track_date)
        logger.debug('Extracting date: {0}'.format(debug_extract_dates))
        track['date'] = track_date.strftime("%Y-%m-%d %H::%M::%S")

        track['artist'] = user['username']
        if arguments['--extract-artist']:
            for dash in [' - ', ' − ', ' – ', ' — ', ' ― ']:
                if dash in track['title']:
                    artist_title = track['title'].split(dash)
                    track['artist'] = artist_title[0].strip()
                    track['title'] = artist_title[1].strip()
                    break

        audio = mutagen.File(filename, easy=True)
        audio['title'] = track['title']
        audio['artist'] = track['artist']
        if track['genre']: audio['genre'] = track['genre']
        if track['permalink_url']: audio['website'] = track['permalink_url']
        if track['date']: audio['date'] = track['date']
        if playlist_info:
            if not arguments['--no-album-tag']:
                audio['album'] = playlist_info['title']
            audio['tracknumber'] = str(playlist_info['tracknumber'])

        audio.save()

        a = mutagen.File(filename)
        if track['description']:
            if a.__class__ == mutagen.flac.FLAC:
                a['description'] = track['description']
            elif a.__class__ == mutagen.mp3.MP3:
                a['COMM'] = mutagen.id3.COMM(
                    encoding=3, lang=u'ENG', text=track['description']
                )
            elif a.__class__ == mutagen.mp4.MP4:
                a['desc'] = track['description']
        if artwork_url:
            if a.__class__ == mutagen.flac.FLAC:
                p = mutagen.flac.Picture()
                p.data = out_file.read()
                p.width = 500
                p.height = 500
                p.type = mutagen.id3.PictureType.COVER_FRONT
                a.add_picture(p)
            elif a.__class__ == mutagen.mp3.MP3:
                a['APIC'] = mutagen.id3.APIC(
                    encoding=3, mime='image/jpeg', type=3,
                    desc='Cover', data=out_file.read()
                )
            elif a.__class__ == mutagen.mp4.MP4:
                a['covr'] = [mutagen.mp4.MP4Cover(out_file.read())]
        a.save()


def signal_handler(signal, frame):
    """
    Handle keyboard interrupt
    """
    logger.info('\nGood bye!')
    sys.exit(0)

def is_ffmpeg_available():
    """
    Returns true if ffmpeg is available in the operating system
    """
    return shutil.which('ffmpeg') is not None

if __name__ == '__main__':
    main()
