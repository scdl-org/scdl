"""scdl allows you to download music from Soundcloud

Usage:
    scdl (-l <track_url> | -s <search_query> | me) [-a | -f | -C | -t | -p | -r]
    [-c | --force-metadata][-n <maxtracks>][-o <offset>][--hidewarnings][--debug | --error]
    [--path <path>][--addtofile][--addtimestamp][--onlymp3][--hide-progress][--min-size <size>]
    [--max-size <size>][--remove][--no-album-tag][--no-playlist-folder]
    [--download-archive <file>][--sync <file>][--extract-artist][--flac][--original-art]
    [--original-name][--original-metadata][--no-original][--only-original]
    [--name-format <format>][--strict-playlist][--playlist-name-format <format>]
    [--client-id <id>][--auth-token <token>][--overwrite][--no-playlist][--opus]
    [--add-description]

    scdl -h | --help
    scdl --version


Options:
    -h --help                       Show this screen
    --version                       Show version
    -l [url]                        URL can be track/playlist/user
    -s [search_query]               Search for a track/playlist/user and use the first result
    -n [maxtracks]                  Download the n last tracks of a playlist according to the
                                    creation date
    -a                              Download all tracks of user (including reposts)
    -t                              Download all uploads of a user (no reposts)
    -f                              Download all favorites (likes) of a user
    -C                              Download all tracks commented on by a user
    -p                              Download all playlists of a user
    -r                              Download all reposts of user
    -c                              Continue if a downloaded file already exists
    --force-metadata                This will set metadata on already downloaded track
    -o [offset]                     Start downloading a playlist from the [offset]th track
                                    Indexing starts with 1.
    --addtimestamp                  Add track creation timestamp to filename,
                                    which allows for chronological sorting
                                    (Deprecated. Use --name-format instead.)
    --addtofile                     Add artist to filename if missing
    --debug                         Set log level to DEBUG
    --error                         Set log level to ERROR
    --download-archive [file]       Keep track of track IDs in an archive file,
                                    and skip already-downloaded files
    --extract-artist                Set artist tag from title instead of username
    --hide-progress                 Hide the wget progress bar
    --hidewarnings                  Hide Warnings. (use with precaution)
    --max-size [max-size]           Skip tracks larger than size (k/m/g)
    --min-size [min-size]           Skip tracks smaller than size (k/m/g)
    --no-playlist-folder            Download playlist tracks into main directory,
                                    instead of making a playlist subfolder
    --onlymp3                       Download only mp3 files
    --path [path]                   Use a custom path for downloaded files
    --remove                        Remove any files not downloaded from execution
    --sync [file]                   Compares an archive file to a playlist and downloads/removes
                                    any changed tracks
    --flac                          Convert original files to .flac. Only works if the original
                                    file is lossless quality
    --no-album-tag                  On some player track get the same cover art if from the same
                                    album, this prevent it
    --original-art                  Download original cover art, not just 500x500 JPEG
    --original-name                 Do not change name of original file downloads
    --original-metadata             Do not change metadata of original file downloads
    --no-original                   Do not download original file; only mp3, m4a, or opus
    --only-original                 Only download songs with original file available
    --name-format [format]          Specify the downloaded file name format. Use "-" to download
                                    to stdout
    --playlist-name-format [format] Specify the downloaded file name format, if it is being
                                    downloaded as part of a playlist
    --client-id [id]                Specify the client_id to use
    --auth-token [token]            Specify the auth token to use
    --overwrite                     Overwrite file if it already exists
    --strict-playlist               Abort playlist downloading if one track fails to download
    --no-playlist                   Skip downloading playlists
    --add-description               Adds the description to a separate txt file
    --opus                          Prefer downloading opus streams over mp3 streams
"""

import atexit
import configparser
import contextlib
import io
import itertools
import logging
import math
import mimetypes
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import typing
import urllib.parse
import warnings
from dataclasses import asdict
from functools import lru_cache
from types import TracebackType
from typing import IO, Generator, List, NoReturn, Optional, Set, Tuple, Type, Union

from tqdm import tqdm

if sys.version_info < (3, 8):
    from typing_extensions import TypedDict
else:
    from typing import TypedDict

if sys.version_info < (3, 11):
    from typing_extensions import NotRequired
else:
    from typing import NotRequired

import filelock
import mutagen
import requests
from docopt import docopt
from pathvalidate import sanitize_filename
from soundcloud import (
    AlbumPlaylist,
    BasicAlbumPlaylist,
    BasicTrack,
    MiniTrack,
    PlaylistLike,
    PlaylistStreamItem,
    PlaylistStreamRepostItem,
    SoundCloud,
    Track,
    TrackLike,
    TrackStreamItem,
    TrackStreamRepostItem,
    Transcoding,
    User,
)

from scdl import __version__, utils
from scdl.metadata_assembler import MetadataInfo, assemble_metadata

mimetypes.init()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addFilter(utils.ColorizeFilter())

FFMPEG_PIPE_CHUNK_SIZE = 1024 * 1024  # 1 mb

files_to_keep = []


class SCDLArgs(TypedDict):
    C: bool
    a: bool
    add_description: bool
    addtimestamp: bool
    addtofile: bool
    auth_token: Optional[str]
    c: bool
    client_id: Optional[str]
    debug: bool
    download_archive: Optional[str]
    error: bool
    extract_artist: bool
    f: bool
    flac: bool
    force_metadata: bool
    hide_progress: bool
    hidewarnings: bool
    l: str  # noqa: E741
    max_size: Optional[int]
    me: bool
    min_size: Optional[int]
    n: Optional[str]
    name_format: str
    no_album_tag: bool
    no_original: bool
    no_playlist: bool
    no_playlist_folder: bool
    o: Optional[int]
    offset: NotRequired[int]
    only_original: bool
    onlymp3: bool
    opus: bool
    original_art: bool
    original_metadata: bool
    original_name: bool
    overwrite: bool
    p: bool
    path: Optional[str]
    playlist_name_format: str
    playlist_offset: NotRequired[int]
    r: bool
    remove: bool
    strict_playlist: bool
    sync: Optional[str]
    s: Optional[str]
    t: bool


class PlaylistInfo(TypedDict):
    author: str
    id: int
    title: str
    tracknumber_int: int
    tracknumber: str
    tracknumber_total: int


class SoundCloudException(Exception):  # noqa: N818
    pass


class MissingFilenameError(SoundCloudException):
    def __init__(self, content_disp_header: Optional[str]):
        super().__init__(
            f"Could not get filename from content-disposition header: {content_disp_header}",
        )


class InvalidFilesizeError(SoundCloudException):
    def __init__(self, min_size: float, max_size: float, size: float):
        super().__init__(
            f"File size: {size} not within --min-size={min_size} and --max-size={max_size}",
        )


class RegionBlockError(SoundCloudException):
    def __init__(self):
        super().__init__("Track is not available in your location. Try using a VPN")


class FFmpegError(SoundCloudException):
    def __init__(self, return_code: int, errors: str):
        super().__init__(f"FFmpeg error ({return_code}): {errors}")


def handle_exception(
    exc_type: Type[BaseException],
    exc_value: BaseException,
    exc_traceback: Optional[TracebackType],
) -> NoReturn:
    if issubclass(exc_type, KeyboardInterrupt):
        logger.error("\nGoodbye!")
    else:
        logger.error("".join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
    sys.exit(1)


sys.excepthook = handle_exception


file_lock_dirs: List[pathlib.Path] = []


def clean_up_locks() -> None:
    with contextlib.suppress(OSError):
        for dir in file_lock_dirs:
            for lock in dir.glob("*.scdl.lock"):
                lock.unlink()


atexit.register(clean_up_locks)


class SafeLock:
    def __init__(
        self,
        lock_file: Union[str, os.PathLike],
        timeout: float = -1,
        mode: int = 0o644,
        thread_local: bool = True,
    ) -> None:
        self._lock = filelock.FileLock(lock_file, timeout, mode, thread_local)
        self._soft_lock = filelock.SoftFileLock(lock_file, timeout, mode, thread_local)
        self._using_soft_lock = False

    def __enter__(self):
        try:
            self._lock.acquire()
            self._using_soft_lock = False
            return self._lock
        except NotImplementedError:
            self._soft_lock.acquire()
            self._using_soft_lock = True
            return self._soft_lock

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        if self._using_soft_lock:
            self._soft_lock.release()
        else:
            self._lock.release()


def get_filelock(path: Union[pathlib.Path, str], timeout: int = 10) -> SafeLock:
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path = path.resolve()
    file_lock_dirs.append(path.parent)
    lock_path = str(path) + ".scdl.lock"
    return SafeLock(lock_path, timeout=timeout)


def main() -> None:
    """Main function, parses the URL from command line arguments"""
    logger.addHandler(logging.StreamHandler())

    # Parse arguments
    arguments = docopt(__doc__, version=__version__)

    if arguments["--debug"]:
        logger.level = logging.DEBUG
    elif arguments["--error"]:
        logger.level = logging.ERROR

    if "XDG_CONFIG_HOME" in os.environ:
        config_file = pathlib.Path(os.environ["XDG_CONFIG_HOME"], "scdl", "scdl.cfg")
    else:
        config_file = pathlib.Path.home().joinpath(".config", "scdl", "scdl.cfg")

    # import conf file
    config = get_config(config_file)

    logger.info("Soundcloud Downloader")
    logger.debug(arguments)

    client_id = arguments["--client-id"] or config["scdl"]["client_id"]
    token = arguments["--auth-token"] or config["scdl"]["auth_token"]

    client = SoundCloud(client_id, token if token else None)

    if not client.is_client_id_valid():
        if arguments["--client-id"]:
            logger.warning(
                "Invalid client_id specified by --client-id argument. "
                "Using a dynamically generated client_id...",
            )
        elif config["scdl"]["client_id"]:
            logger.warning(
                f"Invalid client_id in {config_file}. Using a dynamically generated client_id...",
            )
        else:
            logger.info("Generating dynamic client_id")
        client = SoundCloud(None, token if token else None)
        if not client.is_client_id_valid():
            logger.error("Dynamically generated client_id is not valid")
            sys.exit(1)
        config["scdl"]["client_id"] = client.client_id
        # save client_id
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with get_filelock(config_file), open(config_file, "w", encoding="UTF-8") as f:
            config.write(f)

    if (token or arguments["me"]) and not client.is_auth_token_valid():
        if arguments["--auth-token"]:
            logger.error("Invalid auth_token specified by --auth-token argument")
        else:
            logger.error(f"Invalid auth_token in {config_file}")
        sys.exit(1)

    if arguments["-o"] is not None:
        try:
            arguments["--offset"] = int(arguments["-o"]) - 1
            if arguments["--offset"] < 0:
                raise ValueError
        except Exception:
            logger.error("Offset should be a positive integer...")
            sys.exit(1)
        logger.debug("offset: %d", arguments["--offset"])

    if arguments["--min-size"] is not None:
        try:
            arguments["--min-size"] = utils.size_in_bytes(arguments["--min-size"])
        except Exception:
            logger.exception("Min size should be an integer with a possible unit suffix")
            sys.exit(1)
        logger.debug("min-size: %d", arguments["--min-size"])

    if arguments["--max-size"] is not None:
        try:
            arguments["--max-size"] = utils.size_in_bytes(arguments["--max-size"])
        except Exception:
            logger.error("Max size should be an integer with a possible unit suffix")
            sys.exit(1)
        logger.debug("max-size: %d", arguments["--max-size"])

    if arguments["--hidewarnings"]:
        warnings.filterwarnings("ignore")

    if not arguments["--name-format"]:
        arguments["--name-format"] = config["scdl"]["name_format"]

    if not arguments["--playlist-name-format"]:
        arguments["--playlist-name-format"] = config["scdl"]["playlist_name_format"]

    if arguments["me"]:
        # set url to profile associated with auth token
        me = client.get_me()
        assert me is not None
        arguments["-l"] = me.permalink_url

    if arguments["-s"]:
        url = search_soundcloud(client, arguments["-s"])
        if url:
            arguments["-l"] = url
        else:
            logger.error("Search failed. Exiting...")
            sys.exit(1)

    arguments["-l"] = validate_url(client, arguments["-l"])

    if arguments["--download-archive"]:
        try:
            path = pathlib.Path(arguments["--download-archive"]).resolve()
            arguments["--download-archive"] = path
        except Exception:
            logger.error(f"Invalid download archive file {arguments['--download-archive']}")
            sys.exit(1)

    if arguments["--sync"]:
        try:
            path = pathlib.Path(arguments["--sync"]).resolve()
            arguments["--download-archive"] = path
            arguments["--sync"] = path
        except Exception:
            logger.error(f"Invalid sync archive file {arguments['--sync']}")
            sys.exit(1)

    # convert arguments dict to python_args (kwargs-friendly args)
    python_args = {}
    for key, value in arguments.items():
        key = key.strip("-").replace("-", "_")
        python_args[key] = value

    # change download path
    dl_path: str = arguments["--path"] or config["scdl"]["path"]
    if os.path.exists(dl_path):
        os.chdir(dl_path)
    else:
        if arguments["--path"]:
            logger.error(f"Invalid download path '{dl_path}' specified by --path argument")
        else:
            logger.error(f"Invalid download path '{dl_path}' in {config_file}")
        sys.exit(1)
    logger.debug("Downloading to " + os.getcwd() + "...")

    download_url(client, typing.cast(SCDLArgs, python_args))

    if arguments["--remove"]:
        remove_files()


def validate_url(client: SoundCloud, url: str) -> str:
    """If url is a valid soundcloud.com url, return it.
    Otherwise, try to fix the url so that it is valid.
    If it cannot be fixed, exit the program.
    """
    if url.startswith(("https://m.soundcloud.com", "http://m.soundcloud.com", "m.soundcloud.com")):
        url = url.replace("m.", "", 1)
    if url.startswith(
        ("https://www.soundcloud.com", "http://www.soundcloud.com", "www.soundcloud.com"),
    ):
        url = url.replace("www.", "", 1)
    if url.startswith("soundcloud.com"):
        url = "https://" + url
    if url.startswith(("https://soundcloud.com", "http://soundcloud.com")):
        return urllib.parse.urljoin(url, urllib.parse.urlparse(url).path)

    # see if link redirects to soundcloud.com
    try:
        resp = requests.get(url)
        if url.startswith(("https://soundcloud.com", "http://soundcloud.com")):
            return urllib.parse.urljoin(resp.url, urllib.parse.urlparse(resp.url).path)
    except Exception:
        # see if given a username instead of url
        if client.resolve(f"https://soundcloud.com/{url}"):
            return f"https://soundcloud.com/{url}"

    logger.error("URL is not valid")
    sys.exit(1)


def search_soundcloud(client: SoundCloud, query: str) -> Optional[str]:
    """Search SoundCloud and return the URL of the first result."""
    try:
        results = list(client.search(query, limit=1))
        if results:
            item = results[0]
            logger.info(f"Search resolved to url {item.permalink_url}")
            if isinstance(item, (Track, AlbumPlaylist, User)):
                return item.permalink_url
            logger.warning(f"Unexpected search result type: {type(item)}")
        logger.error(f"No results found for query: {query}")
        return None
    except Exception as e:
        logger.error(f"Error searching SoundCloud: {e}")
        return None


def get_config(config_file: pathlib.Path) -> configparser.ConfigParser:
    """Gets config from scdl.cfg"""
    config = configparser.ConfigParser()

    default_config_file = pathlib.Path(__file__).with_name("scdl.cfg")

    with get_filelock(config_file):
        # load default config first
        with open(default_config_file, encoding="UTF-8") as f:
            config.read_file(f)

        # load config file if it exists
        if config_file.exists():
            with open(config_file, encoding="UTF-8") as f:
                config.read_file(f)

        # save config to disk
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, "w", encoding="UTF-8") as f:
            config.write(f)

    return config


def truncate_str(s: str, length: int) -> str:
    """Truncate string to a certain number of bytes using the file system encoding"""
    encoding = sys.getfilesystemencoding()
    bytes = s.encode(encoding)
    bytes = bytes[:length]
    return bytes.decode(encoding, errors="ignore")


def sanitize_str(
    filename: str,
    ext: str = "",
    replacement_char: str = "�",
    max_length: int = 255,
) -> str:
    """Sanitizes a string for use as a filename. Does not allow the file to be hidden"""
    if filename.startswith("."):
        filename = "_" + filename
    if filename.endswith(".") and not ext:
        filename = filename + "_"
    max_filename_length = max_length - len(ext)
    sanitized = sanitize_filename(
        filename,
        replacement_text=replacement_char,
        max_len=max_filename_length,
    )
    # sanitize_filename truncates incorrectly, use our own method
    sanitized = truncate_str(sanitized, max_filename_length)
    return sanitized + ext


def download_url(client: SoundCloud, kwargs: SCDLArgs) -> None:
    """Detects if a URL is a track or a playlist, and parses the track(s)
    to the track downloader
    """
    url = kwargs["l"]
    item = client.resolve(url)
    logger.debug(item)
    offset = kwargs.get("offset", 0)
    if item is None:
        logger.error("URL is not valid")
        sys.exit(1)
    elif isinstance(item, Track):
        logger.info("Found a track")
        download_track(client, item, kwargs)
    elif isinstance(item, AlbumPlaylist):
        logger.info("Found a playlist")
        kwargs["playlist_offset"] = offset
        download_playlist(client, item, kwargs)
    elif isinstance(item, User):
        user = item
        logger.info("Found a user profile")
        if kwargs.get("f"):
            logger.info(f"Retrieving all likes of user {user.username}...")
            likes = client.get_user_likes(user.id, limit=1000)
            for i, like in itertools.islice(enumerate(likes, 1), offset, None):
                logger.info(f"like n°{i} of {user.likes_count}")
                if isinstance(like, TrackLike):
                    download_track(
                        client,
                        like.track,
                        kwargs,
                        exit_on_fail=kwargs["strict_playlist"],
                    )
                elif isinstance(like, PlaylistLike):
                    playlist = client.get_playlist(like.playlist.id)
                    assert playlist is not None
                    download_playlist(client, playlist, kwargs)
                else:
                    logger.error(f"Unknown like type {like}")
                    if kwargs.get("strict_playlist"):
                        sys.exit(1)
            logger.info(f"Downloaded all likes of user {user.username}!")
        elif kwargs.get("C"):
            logger.info(f"Retrieving all commented tracks of user {user.username}...")
            comments = client.get_user_comments(user.id, limit=1000)
            for i, comment in itertools.islice(enumerate(comments, 1), offset, None):
                logger.info(f"comment n°{i} of {user.comments_count}")
                track = client.get_track(comment.track.id)
                assert track is not None
                download_track(
                    client,
                    track,
                    kwargs,
                    exit_on_fail=kwargs["strict_playlist"],
                )
            logger.info(f"Downloaded all commented tracks of user {user.username}!")
        elif kwargs.get("t"):
            logger.info(f"Retrieving all tracks of user {user.username}...")
            tracks = client.get_user_tracks(user.id, limit=1000)
            for i, track in itertools.islice(enumerate(tracks, 1), offset, None):
                logger.info(f"track n°{i} of {user.track_count}")
                download_track(client, track, kwargs, exit_on_fail=kwargs["strict_playlist"])
            logger.info(f"Downloaded all tracks of user {user.username}!")
        elif kwargs.get("a"):
            logger.info(f"Retrieving all tracks & reposts of user {user.username}...")
            items = client.get_user_stream(user.id, limit=1000)
            for i, stream_item in itertools.islice(enumerate(items, 1), offset, None):
                logger.info(
                    f"item n°{i} of "
                    f"{user.track_count + user.reposts_count if user.reposts_count else '?'}",
                )
                if isinstance(stream_item, (TrackStreamItem, TrackStreamRepostItem)):
                    download_track(
                        client,
                        stream_item.track,
                        kwargs,
                        exit_on_fail=kwargs["strict_playlist"],
                    )
                elif isinstance(stream_item, (PlaylistStreamItem, PlaylistStreamRepostItem)):
                    download_playlist(client, stream_item.playlist, kwargs)
                else:
                    logger.error(f"Unknown item type {stream_item.type}")
                    if kwargs.get("strict_playlist"):
                        sys.exit(1)
            logger.info(f"Downloaded all tracks & reposts of user {user.username}!")
        elif kwargs.get("p"):
            logger.info(f"Retrieving all playlists of user {user.username}...")
            playlists = client.get_user_playlists(user.id, limit=1000)
            for i, playlist in itertools.islice(enumerate(playlists, 1), offset, None):
                logger.info(f"playlist n°{i} of {user.playlist_count}")
                download_playlist(client, playlist, kwargs)
            logger.info(f"Downloaded all playlists of user {user.username}!")
        elif kwargs.get("r"):
            logger.info(f"Retrieving all reposts of user {user.username}...")
            reposts = client.get_user_reposts(user.id, limit=1000)
            for i, repost in itertools.islice(enumerate(reposts, 1), offset, None):
                logger.info(f"item n°{i} of {user.reposts_count or '?'}")
                if isinstance(repost, TrackStreamRepostItem):
                    download_track(
                        client,
                        repost.track,
                        kwargs,
                        exit_on_fail=kwargs["strict_playlist"],
                    )
                elif isinstance(repost, PlaylistStreamRepostItem):
                    download_playlist(client, repost.playlist, kwargs)
                else:
                    logger.error(f"Unknown item type {repost.type}")
                    if kwargs.get("strict_playlist"):
                        sys.exit(1)
            logger.info(f"Downloaded all reposts of user {user.username}!")
        else:
            logger.error("Please provide a download type...")
            sys.exit(1)
    else:
        logger.error(f"Unknown item type {item.kind}")
        sys.exit(1)


def remove_files() -> None:
    """Removes any pre-existing tracks that were not just downloaded"""
    logger.info("Removing local track files that were not downloaded...")
    files = [f for f in os.listdir(".") if os.path.isfile(f)]
    for f in files:
        if f not in files_to_keep:
            os.remove(f)


def sync(
    client: SoundCloud,
    playlist: Union[AlbumPlaylist, BasicAlbumPlaylist],
    playlist_info: PlaylistInfo,
    kwargs: SCDLArgs,
) -> Tuple[Union[BasicTrack, MiniTrack], ...]:
    """Downloads/Removes tracks that have been changed on playlist since last archive file"""
    logger.info("Comparing tracks...")
    archive = kwargs.get("sync")
    assert archive is not None
    with get_filelock(archive):
        with open(archive) as f:
            try:
                old = [int(i) for i in "".join(f.readlines()).strip().split("\n")]
            except OSError as ioe:
                logger.error(f"Error trying to read download archive {archive}")
                logger.debug(ioe)
                sys.exit(1)
            except ValueError as verr:
                logger.error("Error trying to convert track ids. Verify archive file is not empty.")
                logger.debug(verr)
                sys.exit(1)

        new = [track.id for track in playlist.tracks]
        add = set(new).difference(old)  # find tracks to download
        rem = set(old).difference(new)  # find tracks to remove

        if not (add or rem):
            logger.info("No changes found. Exiting...")
            sys.exit(0)

        if rem:
            for track_id in rem:
                removed = False
                track = client.get_track(track_id)
                if track is None:
                    logger.warning(f"Could not find track with id: {track_id}. Skipping removal")
                    continue
                for ext in (".mp3", ".m4a", ".opus", ".flac", ".wav"):
                    filename = get_filename(
                        track,
                        kwargs,
                        ext,
                        playlist_info=playlist_info,
                    )
                    if filename in os.listdir("."):
                        removed = True
                        os.remove(filename)
                        logger.info(f"Removed {filename}")
                if not removed:
                    logger.info(f"Could not find {filename} to remove")
            with open(archive, "w") as f:
                for track_id in old:
                    if track_id not in rem:
                        f.write(str(track_id) + "\n")
        else:
            logger.info("No tracks to remove.")

        if add:
            return tuple(track for track in playlist.tracks if track.id in add)
        logger.info("No tracks to download. Exiting...")
        sys.exit(0)


def download_playlist(
    client: SoundCloud,
    playlist: Union[AlbumPlaylist, BasicAlbumPlaylist],
    kwargs: SCDLArgs,
) -> None:
    """Downloads a playlist"""
    if kwargs.get("no_playlist"):
        logger.info("Skipping playlist...")
        return
    playlist_name = playlist.title.encode("utf-8", "ignore").decode("utf-8")
    playlist_name = sanitize_str(playlist_name)
    playlist_info: PlaylistInfo = {
        "author": playlist.user.username,
        "id": playlist.id,
        "title": playlist.title,
        "tracknumber_int": 0,
        "tracknumber": "0",
        "tracknumber_total": playlist.track_count,
    }

    if not kwargs.get("no_playlist_folder"):
        if not os.path.exists(playlist_name):
            os.makedirs(playlist_name)
        os.chdir(playlist_name)

    try:
        n = kwargs.get("n")
        if n is not None:  # Order by creation date and get the n lasts tracks
            playlist.tracks = tuple(
                sorted(playlist.tracks, key=lambda track: track.id, reverse=True)[: int(n)],
            )
            kwargs["playlist_offset"] = 0
        s = kwargs.get("sync")
        if s:
            if os.path.isfile(s):
                playlist.tracks = sync(client, playlist, playlist_info, kwargs)
            else:
                logger.error(f'Invalid sync archive file {kwargs.get("sync")}')
                sys.exit(1)

        tracknumber_digits = len(str(len(playlist.tracks)))
        for counter, track in itertools.islice(
            enumerate(playlist.tracks, 1),
            kwargs.get("playlist_offset", 0),
            None,
        ):
            logger.debug(track)
            logger.info(f"Track n°{counter}")
            playlist_info["tracknumber_int"] = counter
            playlist_info["tracknumber"] = str(counter).zfill(tracknumber_digits)
            if isinstance(track, MiniTrack):
                if playlist.secret_token:
                    track = client.get_tracks([track.id], playlist.id, playlist.secret_token)[0]
                else:
                    track = client.get_track(track.id)  # type: ignore[assignment]
            assert isinstance(track, BasicTrack)
            download_track(
                client,
                track,
                kwargs,
                playlist_info,
                kwargs["strict_playlist"],
            )
    finally:
        if not kwargs.get("no_playlist_folder"):
            os.chdir("..")


def try_utime(path: str, filetime: float) -> None:
    try:
        os.utime(path, (time.time(), filetime))
    except Exception:
        logger.error("Cannot update utime of file")


def is_downloading_to_stdout(kwargs: SCDLArgs) -> bool:
    return kwargs.get("name_format") == "-"


@contextlib.contextmanager
def get_stdout() -> Generator[IO, None, None]:
    # Credits: https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/utils/_utils.py#L575
    if sys.platform == "win32":
        import msvcrt

        # stdout may be any IO stream, e.g. when using contextlib.redirect_stdout
        with contextlib.suppress(io.UnsupportedOperation):
            msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

    yield getattr(sys.stdout, "buffer", sys.stdout)


def get_filename(
    track: Union[BasicTrack, Track],
    kwargs: SCDLArgs,
    ext: Optional[str] = None,
    original_filename: Optional[str] = None,
    playlist_info: Optional[PlaylistInfo] = None,
) -> str:
    # Force stdout name on tracks that are being downloaded to stdout
    if is_downloading_to_stdout(kwargs):
        return "stdout"

    username = track.user.username
    title = track.title.encode("utf-8", "ignore").decode("utf-8")

    if kwargs.get("addtofile") and username not in title and "-" not in title:
        title = f"{username} - {title}"
        logger.debug(f'Adding "{username}" to filename')

    timestamp = str(int(track.created_at.timestamp()))
    if kwargs.get("addtimestamp"):
        title = timestamp + "_" + title

    if not kwargs.get("addtofile") and not kwargs.get("addtimestamp"):
        if playlist_info:
            title = kwargs["playlist_name_format"].format(
                **asdict(track),
                playlist=playlist_info,
                timestamp=timestamp,
            )
        else:
            title = kwargs["name_format"].format(**asdict(track), timestamp=timestamp)

    if original_filename is not None:
        original_filename = original_filename.encode("utf-8", "ignore").decode("utf-8")
        ext = os.path.splitext(original_filename)[1]
    return sanitize_str(title, ext or "")


def download_original_file(
    client: SoundCloud,
    track: Union[BasicTrack, Track],
    title: str,
    kwargs: SCDLArgs,
    playlist_info: Optional[PlaylistInfo] = None,
) -> Tuple[Optional[str], bool]:
    logger.info("Downloading the original file.")
    to_stdout = is_downloading_to_stdout(kwargs)

    # Get the requests stream
    url = client.get_track_original_download(track.id, track.secret_token)

    if not url:
        logger.info("Could not get original download link")
        return None, False

    r = requests.get(url, stream=True)
    if r.status_code == 401:
        logger.info("The original file has no download left.")
        return None, False

    if r.status_code == 404:
        logger.info("Could not get name from stream - using basic name")
        return None, False

    # Find filename
    header = r.headers.get("content-disposition")
    params = utils.parse_header(header)
    if "filename" in params:
        filename = urllib.parse.unquote(params["filename"][-1], encoding="utf-8")
    else:
        raise MissingFilenameError(header)

    orig_filename = filename
    _, ext = os.path.splitext(filename)

    if not kwargs.get("original_name"):
        orig_filename, ext = os.path.splitext(filename)

        # Find file extension
        ext = (
            ext
            or mimetypes.guess_extension(r.headers["content-type"])
            or ("." + r.headers["x-amz-meta-file-type"])
        )
        orig_filename += ext

        filename = get_filename(
            track,
            kwargs,
            original_filename=orig_filename,
            playlist_info=playlist_info,
        )

    logger.debug(f"filename : {filename}")
    encoding_to_flac = bool(kwargs.get("flac")) and can_convert(orig_filename)

    if encoding_to_flac:
        filename = filename[:-4] + ".flac"

    # Skip if file ID or filename already exists
    # We are always re-downloading to stdout
    if not to_stdout and already_downloaded(track, title, filename, kwargs):
        return filename, True

    re_encode_to_out(
        track,
        r,
        ext[1:] if not encoding_to_flac else "flac",
        not encoding_to_flac,  # copy the stream only if we aren't re-encoding to flac
        filename,
        kwargs,
        playlist_info=playlist_info,
        skip_re_encoding=not encoding_to_flac,
    )

    return filename, False


def get_transcoding_m3u8(
    client: SoundCloud,
    transcoding: Transcoding,
    kwargs: SCDLArgs,
) -> str:
    url = transcoding.url
    bitrate_KBps = 256 / 8 if "aac" in transcoding.preset else 128 / 8  # noqa: N806
    total_bytes = bitrate_KBps * transcoding.duration

    min_size = kwargs.get("min_size") or 0
    max_size = kwargs.get("max_size") or math.inf  # max size of 0 treated as no max size

    if not min_size <= total_bytes <= max_size:
        raise InvalidFilesizeError(min_size, max_size, total_bytes)

    if url is not None:
        headers = client._get_default_headers()
        if client.auth_token:
            headers["Authorization"] = f"OAuth {client.auth_token}"

        params = {
            "client_id": client.client_id,
        }

        r: Optional[requests.Response] = None
        delay: int = 0

        # If we got ratelimited
        while not r or r.status_code == 429:
            if delay > 0:
                logger.warning(f"Got rate-limited, delaying for {delay}sec")
                time.sleep(delay)

            r = requests.get(url, headers=headers, params=params)
            delay = (delay or 1) * 2  # exponential backoff, what could possibly go wrong

        if r.status_code != 200:
            raise SoundCloudException(f"Unable to get transcoding m3u8({r.status_code}): {r.text}")

        logger.debug(r.url)
        return r.json()["url"]
    raise SoundCloudException(f"Transcoding does not contain URL: {transcoding}")


def download_hls(
    client: SoundCloud,
    track: Union[BasicTrack, Track],
    title: str,
    kwargs: SCDLArgs,
    playlist_info: Optional[PlaylistInfo] = None,
) -> Tuple[str, bool]:
    if not track.media.transcodings:
        raise SoundCloudException(f"Track {track.permalink_url} has no transcodings available")

    logger.debug(f"Transcodings: {track.media.transcodings}")

    transcodings = [t for t in track.media.transcodings if t.format.protocol == "hls"]
    to_stdout = is_downloading_to_stdout(kwargs)

    # ordered in terms of preference best -> worst
    valid_presets = [("mp3", ".mp3")]

    if not kwargs.get("onlymp3"):
        if kwargs.get("opus"):
            valid_presets = [("opus", ".opus"), *valid_presets]
        valid_presets = [("aac_256k", ".m4a"), ("aac", ".m4a"), *valid_presets]

    transcoding = None
    ext = None
    for preset_name, preset_ext in valid_presets:
        for t in transcodings:
            if t.preset.startswith(preset_name):
                transcoding = t
                ext = preset_ext
        if transcoding:
            break
    else:
        raise SoundCloudException(
            "Could not find valid transcoding. Available transcodings: "
            f"{[t.preset for t in track.media.transcodings if t.format.protocol == 'hls']}",
        )

    filename = get_filename(track, kwargs, ext=ext, playlist_info=playlist_info)
    logger.debug(f"filename : {filename}")
    # Skip if file ID or filename already exists
    if not to_stdout and already_downloaded(track, title, filename, kwargs):
        return filename, True

    # Get the requests stream
    url = get_transcoding_m3u8(client, transcoding, kwargs)
    _, ext = os.path.splitext(filename)

    re_encode_to_out(
        track,
        url,
        preset_name
        if not preset_name.startswith("aac")
        else "ipod",  # We are encoding aac files to m4a, so an ipod codec is used
        True,  # no need to fully re-encode the whole hls stream
        filename,
        kwargs,
        playlist_info,
    )

    return filename, False


def download_track(
    client: SoundCloud,
    track: Union[BasicTrack, Track],
    kwargs: SCDLArgs,
    playlist_info: Optional[PlaylistInfo] = None,
    exit_on_fail: bool = True,
) -> None:
    """Downloads a track"""
    try:
        title = track.title
        title = title.encode("utf-8", "ignore").decode("utf-8")
        logger.info(f"Downloading {title}")

        # Not streamable
        if not track.streamable:
            logger.warning("Track is not streamable...")

        # Geoblocked track
        if track.policy == "BLOCK":
            raise RegionBlockError

        # Get user_id from the client
        me = client.get_me() if kwargs["auth_token"] else None
        client_user_id = me and me.id

        lock = get_filelock(pathlib.Path(f"./{track.id}"), 0)

        # Downloadable track
        filename = None
        is_already_downloaded = False
        if (
            (track.downloadable or track.user_id == client_user_id)
            and not kwargs["onlymp3"]
            and not kwargs.get("no_original")
            and client.auth_token
        ):
            try:
                with lock:
                    filename, is_already_downloaded = download_original_file(
                        client,
                        track,
                        title,
                        kwargs,
                        playlist_info,
                    )
            except filelock.Timeout:
                logger.debug(f"Could not acquire lock: {lock}. Skipping")
                return

        if filename is None:
            if kwargs.get("only_original"):
                raise SoundCloudException(
                    f'Track "{track.permalink_url}" does not have original file '
                    "available. Not downloading...",
                )
            try:
                with lock:
                    filename, is_already_downloaded = download_hls(
                        client,
                        track,
                        title,
                        kwargs,
                        playlist_info,
                    )
            except filelock.Timeout:
                logger.debug(f"Could not acquire lock: {lock}. Skipping")
                return

        if kwargs.get("remove"):
            files_to_keep.append(filename)

        record_download_archive(track, kwargs)
        if kwargs["add_description"]:
            create_description_file(track.description, filename)

        to_stdout = is_downloading_to_stdout(kwargs)

        # Skip if file ID or filename already exists
        if is_already_downloaded and not kwargs.get("force_metadata"):
            raise SoundCloudException(f"{filename} already downloaded.")

        # If file does not exist an error occurred
        # If we are downloading to stdout and reached this point, then most likely
        # we downloaded the track
        if not os.path.isfile(filename) and not to_stdout:
            raise SoundCloudException(f"An error occurred downloading {filename}.")

        # Add metadata to an already existing file if needed
        if is_already_downloaded and kwargs.get("force_metadata"):
            with open(filename, "rb") as f:
                file_data = io.BytesIO(f.read())

            _add_metadata_to_stream(track, file_data, kwargs, playlist_info)

            with open(filename, "wb") as f:
                file_data.seek(0)
                f.write(file_data.getbuffer())

        # Try to change the real creation date
        if not to_stdout:
            filetime = int(time.mktime(track.created_at.timetuple()))
            try_utime(filename, filetime)

        logger.info(f"{filename} Downloaded.\n")
    except SoundCloudException as err:
        logger.error(err)
        if exit_on_fail:
            sys.exit(1)


def can_convert(filename: str) -> bool:
    ext = os.path.splitext(filename)[1]
    return "wav" in ext or "aif" in ext


def create_description_file(description: Optional[str], filename: str) -> None:
    """
    Creates txt file containing the description
    """
    desc = description or ""
    if desc:
        try:
            description_filename = pathlib.Path(filename).with_suffix(".txt")
            with open(description_filename, "w", encoding="utf-8") as f:
                f.write(desc)
            logger.info("Created description txt file")
        except OSError as ioe:
            logger.error("Error trying to write description txt file...")
            logger.error(ioe)


def already_downloaded(
    track: Union[BasicTrack, Track],
    title: str,
    filename: str,
    kwargs: SCDLArgs,
) -> bool:
    """Returns True if the file has already been downloaded"""
    already_downloaded = False

    if os.path.isfile(filename):
        already_downloaded = True
    if kwargs.get("flac") and can_convert(filename) and os.path.isfile(filename[:-4] + ".flac"):
        already_downloaded = True
    if kwargs.get("download_archive") and in_download_archive(track, kwargs):
        already_downloaded = True

    if kwargs.get("flac") and can_convert(filename) and os.path.isfile(filename):
        already_downloaded = False

    if kwargs.get("overwrite"):
        already_downloaded = False

    if already_downloaded:
        if kwargs.get("c") or kwargs.get("remove") or kwargs.get("force_metadata"):
            return True
        logger.error(f'Track "{title}" already exists!')
        logger.error("Exiting... (run again with -c to continue)")
        sys.exit(1)
    return False


def in_download_archive(track: Union[BasicTrack, Track], kwargs: SCDLArgs) -> bool:
    """Returns True if a track_id exists in the download archive"""
    archive_filename = kwargs.get("download_archive")
    if not archive_filename:
        return False

    try:
        with get_filelock(archive_filename), open(archive_filename, "a+", encoding="utf-8") as file:
            file.seek(0)
            track_id = str(track.id)
            for line in file:
                if line.strip() == track_id:
                    return True
    except OSError as ioe:
        logger.error("Error trying to read download archive...")
        logger.error(ioe)

    return False


def record_download_archive(track: Union[BasicTrack, Track], kwargs: SCDLArgs) -> None:
    """Write the track_id in the download archive"""
    archive_filename = kwargs.get("download_archive")
    if not archive_filename:
        return

    try:
        with get_filelock(archive_filename), open(archive_filename, "a", encoding="utf-8") as file:
            file.write(f"{track.id}\n")
    except OSError as ioe:
        logger.error("Error trying to write to download archive...")
        logger.error(ioe)


def _try_get_artwork(url: str, size: str = "original") -> Optional[requests.Response]:
    new_artwork_url = url.replace("large", size)

    try:
        artwork_response = requests.get(new_artwork_url, allow_redirects=False, timeout=5)

        if artwork_response.status_code != 200:
            return None

        content_type = artwork_response.headers.get("Content-Type", "").lower()
        if content_type not in ("image/png", "image/jpeg", "image/jpg"):
            return None

        return artwork_response
    except requests.RequestException:
        return None


def build_ffmpeg_encoding_args(
    input_file: str,
    output_file: str,
    out_codec: str,
    kwargs: SCDLArgs,
    *args: str,
) -> List[str]:
    supported = get_ffmpeg_supported_options()
    ffmpeg_args = [
        "ffmpeg",
        "-loglevel",
        "debug" if kwargs["debug"] else "error",
        # Input stream
        "-i",
        input_file,
        # Encoding
        "-f",
        out_codec,
    ]

    if not kwargs.get("hide_progress"):
        ffmpeg_args += [
            # Progress to stderr
            "-progress",
            "pipe:2",
        ]
        if "-stats_period" in supported:
            # more frequent progress updates
            ffmpeg_args += [
                "-stats_period",
                "0.1",
            ]

    ffmpeg_args += [
        # User provided arguments
        *args,
        # Output file
        output_file,
    ]
    return ffmpeg_args


def _write_streaming_response_to_pipe(
    response: requests.Response,
    pipe: Union[IO[bytes], io.BytesIO],
    kwargs: SCDLArgs,
) -> None:
    total_length = int(response.headers["content-length"])

    min_size = kwargs.get("min_size") or 0
    max_size = kwargs.get("max_size") or math.inf  # max size of 0 treated as no max size

    if not min_size <= total_length <= max_size:
        raise InvalidFilesizeError(min_size, max_size, total_length)

    logger.info("Receiving the streaming response")
    received = 0
    chunk_size = 8192

    with memoryview(bytearray(chunk_size)) as buffer:
        for chunk in tqdm(
            iter(lambda: response.raw.read(chunk_size), b""),
            total=(total_length / chunk_size) + 1,
            disable=bool(kwargs.get("hide_progress")),
            unit="Kb",
            unit_scale=chunk_size / 1024,
        ):
            if not chunk:
                break

            buffer_view = buffer[: len(chunk)]
            buffer_view[:] = chunk

            received += len(chunk)
            pipe.write(buffer_view)

    pipe.flush()

    if received != total_length:
        logger.error("connection closed prematurely, download incomplete")
        sys.exit(1)

    if not isinstance(pipe, io.BytesIO):
        pipe.close()


def _add_metadata_to_stream(
    track: Union[BasicTrack, Track],
    stream: io.BytesIO,
    kwargs: SCDLArgs,
    playlist_info: Optional[PlaylistInfo] = None,
) -> None:
    logger.info("Applying metadata...")

    artwork_base_url = track.artwork_url or track.user.avatar_url
    artwork_response = None

    if kwargs.get("original_art"):
        artwork_response = _try_get_artwork(artwork_base_url, "original")

    if artwork_response is None:
        artwork_response = _try_get_artwork(artwork_base_url, "t500x500")

    artist: str = track.user.username
    if bool(kwargs.get("extract_artist")):
        for dash in (" - ", " − ", " – ", " — ", " ― "):  # noqa: RUF001
            if dash not in track.title:
                continue

            artist_title = track.title.split(dash, maxsplit=1)
            artist = artist_title[0].strip()
            track.title = artist_title[1].strip()
            break

    album_available: bool = (playlist_info is not None) and not kwargs.get("no_album_tag")

    metadata = MetadataInfo(
        artist=artist,
        title=track.title,
        description=track.description,
        genre=track.genre,
        artwork_jpeg=artwork_response.content if artwork_response else None,
        link=track.permalink_url,
        date=track.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        album_title=playlist_info["title"] if album_available else None,  # type: ignore[index]
        album_author=playlist_info["author"] if album_available else None,  # type: ignore[index]
        album_track_num=playlist_info["tracknumber_int"] if album_available else None,  # type: ignore[index]
        album_total_track_num=playlist_info["tracknumber_total"] if album_available else None,  # type: ignore[index]
    )

    mutagen_file = mutagen.File(stream)

    try:
        # Delete all the existing tags and write our own tags
        if mutagen_file is not None:
            stream.seek(0)
            mutagen_file.delete(stream)
        assemble_metadata(mutagen_file, metadata)
    except NotImplementedError:
        logger.error(
            "Metadata assembling for this track is unsupported.\n"
            "Please create an issue at https://github.com/flyingrub/scdl/issues "
            "and we will look into it",
        )

        kwargs_no_sensitive = {k: v for k, v in kwargs.items() if k not in ("auth_token",)}
        logger.error(
            f"Here is the information that you should attach to your issue:\n"
            f"- Track: {track.permalink_url}\n"
            f"- First 16 bytes: {stream.getvalue()[:16].hex()}\n"
            f"- Identified as: {type(mutagen_file)}\n"
            f"- Configuration: {kwargs_no_sensitive}",
        )
        return

    stream.seek(0)
    mutagen_file.save(stream)


def re_encode_to_out(
    track: Union[BasicTrack, Track],
    in_data: Union[requests.Response, str],
    out_codec: str,
    should_copy: bool,
    filename: str,
    kwargs: SCDLArgs,
    playlist_info: Optional[PlaylistInfo],
    skip_re_encoding: bool = False,
) -> None:
    to_stdout = is_downloading_to_stdout(kwargs)

    encoded = re_encode_to_buffer(
        track,
        in_data,
        out_codec,
        should_copy,
        kwargs,
        playlist_info,
        skip_re_encoding,
    )

    # see https://github.com/python/mypy/issues/5512
    with get_stdout() if to_stdout else open(filename, "wb") as out_handle:  # type: ignore[attr-defined]
        shutil.copyfileobj(encoded, out_handle)


def _is_ffmpeg_progress_line(parameters: List[str]) -> bool:
    return len(parameters) == 2 and parameters[0] in (
        "progress",
        "speed",
        "drop_frames",
        "dup_frames",
        "out_time",
        "out_time_ms",
        "out_time_us",
        "total_size",
        "bitrate",
    )


def _get_ffmpeg_pipe(
    in_data: Union[requests.Response, str],  # streaming response or url
    out_codec: str,
    should_copy: bool,
    output_file: str,
    kwargs: SCDLArgs,
) -> subprocess.Popen:
    logger.info("Creating the ffmpeg pipe...")

    commands = build_ffmpeg_encoding_args(
        in_data if isinstance(in_data, str) else "-",
        output_file,
        out_codec,
        kwargs,
        *(
            (
                "-c",
                "copy",
            )
            if should_copy
            else ()
        ),
    )

    logger.debug(f"ffmpeg command: {' '.join(commands)}")
    return subprocess.Popen(
        commands,
        stdin=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        bufsize=FFMPEG_PIPE_CHUNK_SIZE,
    )


def _is_unsupported_codec_for_streaming(codec: str) -> bool:
    return codec in ("ipod", "flac")


def _re_encode_ffmpeg(
    in_data: Union[requests.Response, str],  # streaming response or url
    out_file_name: str,
    out_codec: str,
    track_duration_ms: int,
    should_copy: bool,
    kwargs: SCDLArgs,
) -> io.BytesIO:
    pipe = _get_ffmpeg_pipe(in_data, out_codec, should_copy, out_file_name, kwargs)

    logger.info("Encoding..")
    errors_output = ""
    stdout = io.BytesIO()

    # Sadly, we have to iterate both stdout and stderr at the same times in order for
    # things to work. This is why we have 2 threads that are reading stderr, and
    # writing stuff to stdin at the same time. I don't think there is any other way
    # to get this working and make it as fast as it is now.

    # A function that reads encoded track to our `stdout` BytesIO object
    def read_stdout() -> None:
        assert pipe.stdout is not None
        shutil.copyfileobj(pipe.stdout, stdout, FFMPEG_PIPE_CHUNK_SIZE)
        pipe.stdout.close()

    stdout_thread = None
    stdin_thread = None

    # Read from stdout only if we expect ffmpeg to write something there
    if out_file_name == "pipe:1":
        stdout_thread = threading.Thread(target=read_stdout, daemon=True)

    # Stream the response to ffmpeg if needed
    if isinstance(in_data, requests.Response):
        assert pipe.stdin is not None
        stdin_thread = threading.Thread(
            target=_write_streaming_response_to_pipe,
            args=(in_data, pipe.stdin, kwargs),
            daemon=True,
        )

    # Start the threads
    if stdout_thread:
        stdout_thread.start()
    if stdin_thread:
        stdin_thread.start()

    # Read progress from stderr line by line
    hide_progress = bool(kwargs.get("hide_progress"))
    total_sec = track_duration_ms / 1000
    with tqdm(total=total_sec, disable=hide_progress, unit="s") as progress:
        last_secs = 0.0
        assert pipe.stderr is not None
        for line in io.TextIOWrapper(pipe.stderr, encoding="utf-8", errors=None):
            parameters = line.split("=", maxsplit=1)
            if hide_progress or not _is_ffmpeg_progress_line(parameters):
                errors_output += line
                continue

            if not line.startswith("out_time_ms"):
                continue

            try:
                seconds = int(parameters[1]) / 1_000_000
            except ValueError:
                seconds = 0.0

            seconds = min(seconds, total_sec)  # clamp just to be sure
            changed = seconds - last_secs
            last_secs = seconds
            progress.update(changed)

    # Wait for threads to finish
    if stdout_thread:
        stdout_thread.join()
    if stdin_thread:
        stdin_thread.join()

    logger.debug(f"FFmpeg output: {errors_output}")

    # Make sure that process has exited and get its exit code
    pipe.wait()
    if pipe.returncode != 0:
        raise FFmpegError(pipe.returncode, errors_output)

    # Read from the temp file, if needed
    if out_file_name != "pipe:1":
        with open(out_file_name, "rb") as f:
            shutil.copyfileobj(f, stdout)

    stdout.seek(0)
    return stdout


def _copy_stream(
    in_data: requests.Response,  # streaming response or url
    kwargs: SCDLArgs,
) -> io.BytesIO:
    result = io.BytesIO()
    _write_streaming_response_to_pipe(in_data, result, kwargs)
    result.seek(0)
    return result


def re_encode_to_buffer(
    track: Union[BasicTrack, Track],
    in_data: Union[requests.Response, str],  # streaming response or url
    out_codec: str,
    should_copy: bool,
    kwargs: SCDLArgs,
    playlist_info: Optional[PlaylistInfo] = None,
    skip_re_encoding: bool = False,
) -> io.BytesIO:
    if skip_re_encoding and isinstance(in_data, requests.Response):
        encoded_data = _copy_stream(in_data, kwargs)
    else:
        streaming_supported = not _is_unsupported_codec_for_streaming(out_codec)
        if streaming_supported:
            out_file_name = "pipe:1"  # stdout
            encoded_data = _re_encode_ffmpeg(
                in_data, out_file_name, out_codec, track.duration, should_copy, kwargs
            )
        else:
            with tempfile.TemporaryDirectory() as d:
                out_file_name = str(pathlib.Path(d) / "scdl")
                encoded_data = _re_encode_ffmpeg(
                    in_data, out_file_name, out_codec, track.duration, should_copy, kwargs
                )

    # Remove original metadata, add our own, and we are done
    if not kwargs.get("original_metadata"):
        _add_metadata_to_stream(track, encoded_data, kwargs, playlist_info)

    encoded_data.seek(0)
    return encoded_data


@lru_cache(maxsize=1)
def get_ffmpeg_supported_options() -> Set[str]:
    """Returns supported ffmpeg options which we care about"""
    if shutil.which("ffmpeg") is None:
        logger.error("ffmpeg is not installed")
        sys.exit(1)
    r = subprocess.run(
        ["ffmpeg", "-help", "long", "-loglevel", "quiet"],
        check=True,
        stdout=subprocess.PIPE,
        encoding="utf-8",
    )
    supported = set()
    for line in r.stdout.splitlines():
        if line.startswith("-"):
            opt = line.split(maxsplit=1)[0]
            supported.add(opt)
    return supported


if __name__ == "__main__":
    main()
