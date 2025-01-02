"""scdl allows you to download music from Soundcloud

Usage:
    scdl (-l <track_url> | -s <search_query> | me) [-a | -f | -C | -t | -p | -r]
    [-c | --force-metadata][-n <maxtracks>][-o <offset>][--hidewarnings][--debug | --error]
    [--path <path>][--addtofile][--addtimestamp][--onlymp3][--hide-progress][--min-size <size>]
    [--max-size <size>][--no-album-tag][--no-playlist-folder]
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

from __future__ import annotations

import atexit
import configparser
import contextlib
import logging
import os
import posixpath
import sys
import traceback
import typing
from pathlib import Path
from typing import NoReturn, TypedDict

from scdl.patches.original_filename_preprocessor import OriginalFilenamePP
from scdl.patches.switch_outtmpl_preprocessor import OuttmplPP

import filelock
from docopt import docopt
from soundcloud import (
    AlbumPlaylist,
    SoundCloud,
    Track,
    User,
)
from yt_dlp import YoutubeDL

from scdl import __version__, utils
from scdl.patches.mutagen_postprocessor import MutagenPostProcessorError, MutagenPP

if typing.TYPE_CHECKING:
    from types import TracebackType

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SCDLArgs(TypedDict):
    C: bool
    a: bool
    add_description: bool
    addtimestamp: bool
    addtofile: bool
    auth_token: str | None
    c: bool
    client_id: str | None
    debug: bool
    download_archive: str | None
    error: bool
    extract_artist: bool
    f: bool
    flac: bool
    force_metadata: bool
    hide_progress: bool
    hidewarnings: bool
    l: str  # noqa: E741
    max_size: str | None
    me: bool
    min_size: str | None
    n: str | None
    name_format: str
    no_album_tag: bool
    no_original: bool
    no_playlist: bool
    no_playlist_folder: bool
    o: int | None
    only_original: bool
    onlymp3: bool
    opus: bool
    original_art: bool
    original_metadata: bool
    original_name: bool
    overwrite: bool
    p: bool
    path: Path
    playlist_name_format: str
    r: bool
    strict_playlist: bool
    sync: str | None
    s: str | None
    t: bool


class PlaylistInfo(TypedDict):
    author: str
    id: int
    title: str
    tracknumber_int: int
    tracknumber: str
    tracknumber_total: int


def handle_exception(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_traceback: TracebackType | None,
) -> NoReturn:
    if issubclass(exc_type, KeyboardInterrupt):
        logger.error("\nGoodbye!")
    else:
        logger.error("".join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
    sys.exit(1)


sys.excepthook = handle_exception


file_lock_dirs: list[Path] = []


def clean_up_locks() -> None:
    with contextlib.suppress(OSError):
        for dir in file_lock_dirs:
            for lock in dir.glob("*.scdl.lock"):
                lock.unlink()


atexit.register(clean_up_locks)


class SafeLock:
    def __init__(
        self,
        lock_file: str | os.PathLike,
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
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._using_soft_lock:
            self._soft_lock.release()
        else:
            self._lock.release()


def get_filelock(path: Path | str, timeout: int = 10) -> SafeLock:
    path = Path(path)
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
        config_file = Path(os.environ["XDG_CONFIG_HOME"], "scdl", "scdl.cfg")
    else:
        config_file = Path.home().joinpath(".config", "scdl", "scdl.cfg")

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
            arguments["-o"] = int(arguments["-o"])
            if arguments["-o"] < 1:
                raise ValueError
        except Exception:
            logger.error("Offset should be a positive integer...")
            sys.exit(1)
        logger.debug("offset: %d", arguments["-o"])

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

    arguments["--path"] = Path(arguments["--path"] or config["scdl"]["path"] or ".").resolve()

    # convert arguments dict to python-friendly names (no hyphens)
    python_args = {}
    for key, value in arguments.items():
        key = key.strip("-").replace("-", "_")
        python_args[key] = value

    logger.debug("Downloading to " + os.getcwd() + "...")

    download_url(client, typing.cast(SCDLArgs, python_args))


def search_soundcloud(client: SoundCloud, query: str) -> str | None:
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


def get_config(config_file: Path) -> configparser.ConfigParser:
    """Gets config from scdl.cfg"""
    config = configparser.ConfigParser()

    default_config_file = Path(__file__).with_name("scdl.cfg")

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


def convert_scdl_name_format(s: str) -> str:
    # {user[id]}_{id}_{user[username]}_{title}
    replacements = {
        "{id}": "%(id)s",
        "{user[username]}": "%(uploader)s",
        "{user[id]}": "%(uploader_id)s",
        "{user[permalink_url]}": "%(uploader_url)s",
        "{timestamp}": "%(timestamp)s",
        "{title}": "%(title)s",
        "{description}": "%(description)s",
        "{duration}": "%(duration)s",
        "{permalink_url}": "%(webpage_url)s",
        "{license}": "%(license)s",
        "{playback_count}": "%(view_count)s",
        "{likes_count}": "%(like_count)s",
        "{comment_count}": "%(comment_count)s",
        "{reposts_count}": "%(respost_count)s",
        "{playlist[author]}": "%(playlist_uploader)s",
        "{playlist[title]}": "%(playlist)s",
        "{playlist[id]}": "%(playlist_id)s",
        "{playlist[tracknumber]}": "%(playlist_index)s",
        "{playlist[tracknumber_total]}": "%(playlist_count)s",
    }
    for old, new in replacements.items():
        s = s.replace(old, new)
    if not s.endswith(".%(ext)s"):
        s += ".%(ext)s"
    return s


def build_ytdl_output_filename(
    scdl_args: SCDLArgs, in_playlist: bool, force_suffix: str = None
) -> str:
    if scdl_args["name_format"] == "-":
        return "-"

    playlist_format = "%(playlist|)s"
    if in_playlist:
        track_format = convert_scdl_name_format(scdl_args["playlist_name_format"])
    else:
        track_format = convert_scdl_name_format(scdl_args["name_format"])

    if scdl_args["addtimestamp"] or scdl_args["addtofile"]:
        track_format = "%(title)s.%(ext)s"
        if scdl_args["addtofile"]:
            track_format = "%(uploader)s - " + track_format
        if scdl_args["addtimestamp"]:
            track_format = "%(timestamp)s_" + track_format

    base = scdl_args["path"]
    if scdl_args["no_playlist_folder"] or not in_playlist:
        ret = base / track_format
    else:
        ret = base / playlist_format / track_format

    if force_suffix:
        ret = ret.with_suffix(force_suffix)

    return ret.as_posix()


def build_ytdl_format_specifier(scdl_args: SCDLArgs) -> str:
    fmt = "ba"
    if scdl_args["min_size"]:
        fmt += f"[filesize_approx>={scdl_args['min_size']}]"
    if scdl_args["max_size"]:
        fmt += f"[filesize_approx<={scdl_args['max_size']}]"
    if scdl_args["no_original"]:
        fmt += "[format_id!=download]"
    if scdl_args["only_original"]:
        fmt += "[format_id=download]"
    if scdl_args["onlymp3"]:
        fmt += "[format_id*=mp3]"
    return fmt


def build_ytdl_params(scdl_args: SCDLArgs) -> tuple[str, dict]:
    # return download url, ytdl params, and postprocessors

    url = scdl_args["l"]

    if scdl_args["a"]:
        pass
    elif scdl_args["t"]:
        url = posixpath.join(url, "tracks")
    elif scdl_args["f"]:
        url = posixpath.join(url, "likes")
    elif scdl_args["C"]:
        # TODO
        raise NotImplementedError
    elif scdl_args["p"]:
        url = posixpath.join(url, "sets")
    elif scdl_args["r"]:
        url = posixpath.join(url, "reposts")

    params: dict = {}

    # default params
    params["--embed-metadata"] = True
    params["--embed-thumbnail"] = True
    params["--remux-video"] = "aac>m4a"
    params["--extractor-args"] = "soundcloud:formats=*_aac,*_mp3"  # ignore opus by default
    params["--use-extractors"] = "soundcloud.*"
    params["--output-na-placeholder"] = ""
    postprocessors = [
        (
            OuttmplPP(
                build_ytdl_output_filename(scdl_args, False),
                build_ytdl_output_filename(scdl_args, True),
            ),
            "pre_process",
        )
    ]

    if scdl_args["n"]:
        # TODO
        raise NotImplementedError

    if scdl_args["strict_playlist"]:
        params["--abort-on-error"] = True

    if not scdl_args["c"]:
        params["--break-on-existing"] = True

    if not scdl_args["force_metadata"]:
        # TODO
        pass

    if scdl_args["o"]:
        params["--playlist-items"] = f"{scdl_args["o"]}:"

    if scdl_args["extract_artist"]:
        params["--parse-metadata"].append(r"title:(?P<meta_artist>)\s*[-−–—―]\s+(?P<meta_title>)")  # noqa: RUF001

    if scdl_args["debug"]:
        params["--verbose"] = True

    if scdl_args["error"]:
        params["--quiet"] = True

    if scdl_args["download_archive"]:
        params["--download-archive"] = scdl_args["download_archive"]

    if scdl_args["hide_progress"]:
        params["--no-progress"] = True

    if scdl_args["max_size"]:
        params["--max-filesize"] = scdl_args["max_size"]
    if scdl_args["min_size"]:
        params["--min-filesize"] = scdl_args["min_size"]

    params["-f"] = build_ytdl_format_specifier(scdl_args)

    if scdl_args["sync"]:
        # TODO
        raise NotImplementedError

    if scdl_args["flac"]:
        params["--recode-video"] = "aiff>flac/alac>flac/wav>flac"

    if not scdl_args["no_album_tag"]:
        params["--parse-metadata"] = [
            "%(playlist)s:%(meta_album)s",
            "%(playlist_uploader)s:%(meta_album_artist)s",
            "%(playlist_index)s:%(meta_track)s",
        ]

    if scdl_args["original_name"] and not scdl_args["no_original"]:
        postprocessors.append((OriginalFilenamePP(), "pre_process"))

    if not scdl_args["original_art"]:
        params["--thumbnail-id"] = "t500x500"

    if scdl_args["name_format"] == "-":
        # https://github.com/yt-dlp/yt-dlp/issues/8815
        # https://github.com/yt-dlp/yt-dlp/issues/126
        params["--embed-metadata"] = False
        params["--embed-thumbnail"] = False

    if scdl_args["original_metadata"]:
        params["--embed-metadata"] = False
        params["--embed-thumbnail"] = False
    else:
        postprocessors.append((MutagenPP(), "post_process"))

    if scdl_args["auth_token"]:
        params["--username"] = "oauth"
        params["--password"] = scdl_args["auth_token"]

    # TODO
    if scdl_args["overwrite"]:
        params["--force-overwrites"] = True
    else:
        params["--no-overwrites"] = True

    if scdl_args["no_playlist"]:
        # TODO
        raise NotImplementedError

    if scdl_args["add_description"]:
        params["--print-to-file"] = (
            "description",
            build_ytdl_output_filename(scdl_args, False, ".txt"),
        )

    if scdl_args["opus"]:
        params["--extractor-args"] = "soundcloud:formats=*_aac,*_opus,*_mp3"

    argv = []
    for param, value in params.items():
        if value is False:
            continue
        if value is True:
            argv.append(param)
        elif isinstance(value, list):
            for v in value:
                argv.append(param)
                argv.append(v)
        elif isinstance(value, tuple):
            argv.append(param)
            argv += list(value)
        else:
            argv.append(param)
            argv.append(value)

    return url, utils.cli_to_api(argv), postprocessors


def download_url(client: SoundCloud, scdl_args: SCDLArgs) -> None:
    url, params, postprocessors = build_ytdl_params(scdl_args)
    # we handle this with custom MutagenPP for now
    params["postprocessors"] = [
        pp
        for pp in params["postprocessors"]
        if pp["key"] not in ("EmbedThumbnail", "FFmpegMetadata")
    ]
    with YoutubeDL(params) as ydl:
        # handle old version archive files
        for id_ in ydl.archive:
            if not id_.startswith("soundcloud"):
                ydl.archive.discard(id_)
                ydl.archive.add(f"soundcloud {id_}")
        ydl.cache.store("soundcloud", "client_id", client.client_id)
        for pp, when in postprocessors:
            ydl.add_post_processor(pp, when)

        ydl.download(url)


if __name__ == "__main__":
    main()
