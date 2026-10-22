"""scdl allows you to download music from Soundcloud

Usage:
    scdl (-l <track_url> | -s <search_query> | me) [-a | -f | -C | -t | -p | -r]
    [-c | --force-metadata][-o <offset>][-n <maxtracks>][--hidewarnings][--debug | --error]
    [--path <path>][--addtofile][--addtimestamp][--onlymp3][--hide-progress][--min-size <size>]
    [--max-size <size>][--no-album-tag][--no-playlist-folder]
    [--download-archive <file>][--sync <file>][--extract-artist][--flac][--original-art]
    [--original-name][--original-metadata][--no-original][--only-original]
    [--name-format <format>][--strict-playlist][--playlist-name-format <format>]
    [--client-id <id>][--auth-token <token>][--overwrite][--no-playlist][--opus]
    [--add-description][--min-duration <time>][--max-duration <time>][--skip-known-drm]
    [--audio-format <format>][--audio-quality <quality>][--sleep <seconds>][--write-cover]
    [--clean-tags][--parallel <n>][--concurrent-fragments <n>]
    [--yt-dlp-args <argstring>]

    scdl -h | --help
    scdl --version


Options:
    -h --help                       Show this screen
    --version                       Show version
    -l [url]                        URL can be track/playlist/user
    -s [search_query]               Search for a track/playlist/user and use the first result
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
    -n [maxtracks]                  Download at most [maxtracks] tracks (counted from the offset)
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
    --min-duration [time]           Skip tracks shorter than [time] (SS, MM:SS or HH:MM:SS)
    --max-duration [time]           Skip tracks longer than [time] (SS, MM:SS or HH:MM:SS)
    --skip-known-drm                Skip tracks with no downloadable formats (DRM/geo-restricted)
                                    and remember them so later runs skip them without requests
    --audio-format [format]         Convert audio with ffmpeg (mp3, m4a, opus, flac, wav, ...).
                                    Files already in that format are kept as-is
    --audio-quality [quality]       Quality for --audio-format: 0 (best VBR) to 10, or a
                                    bitrate such as 320K [default: 0]
    --sleep [seconds]               Wait [seconds] between requests and downloads
                                    (helps against HTTP 429 rate limiting)
    --write-cover                   Also keep the cover art as a separate image file
    --clean-tags                    Clean up artist/title: split "Artist - Title", move "feat. X"
                                    to the artist, drop promo text such as [Free Download], and
                                    name the files after the cleaned tags
    --parallel [n]                  Download up to [n] tracks at once (1-3) [default: 1]
    --concurrent-fragments [n]      Download up to [n] fragments of each track at once [default: 8]
    --yt-dlp-args [argstring]       String with custom args to forward to yt-dlp
"""

from __future__ import annotations

import concurrent.futures
import configparser
import importlib
import importlib.metadata
import logging
import os
import posixpath
import queue
import shlex
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict

from docopt import docopt
from soundcloud import (
    AlbumPlaylist,
    SoundCloud,
    Track,
    User,
)
from yt_dlp import YoutubeDL
from yt_dlp.extractor.soundcloud import SoundcloudIE
from yt_dlp.networking.exceptions import HTTPError
from yt_dlp.postprocessor.common import PostProcessor
from yt_dlp.utils import DownloadCancelled, DownloadError, locked_file

from scdl import utils
from scdl.patches.clean_tags_preprocessor import CleanTagsPP
from scdl.patches.mutagen_postprocessor import MutagenPP
from scdl.patches.original_filename_preprocessor import OriginalFilenamePP
from scdl.patches.switch_outtmpl_preprocessor import OuttmplPP
from scdl.patches.sync_download_archive import SyncDownloadHelper

if TYPE_CHECKING:
    if sys.version_info < (3, 11):
        from typing_extensions import Unpack
    else:
        from typing import Unpack

logging.setLoggerClass(utils.YTLogger)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SCDLArgs(TypedDict):
    C: bool
    a: bool
    add_description: bool
    audio_format: str | None
    audio_quality: str | None
    addtimestamp: bool
    addtofile: bool
    auth_token: str | None
    c: bool
    clean_tags: bool
    concurrent_fragments: int
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
    n: int | None
    max_duration: str | None
    min_duration: str | None
    min_size: str | None
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
    parallel: int
    path: Path
    playlist_name_format: str
    r: bool
    strict_playlist: bool
    sync: str | None
    s: str | None
    skip_known_drm: bool
    sleep: str | None
    t: bool
    write_cover: bool
    yt_dlp_args: str


__version__ = importlib.metadata.version("scdl")


def _main() -> None:
    """Main function, parses the URL from command line arguments"""
    logger.addHandler(logging.StreamHandler())
    url, python_args = parse_args()
    download_url(url, **python_args)


def get_config_dir() -> Path:
    if os.environ.get("XDG_CONFIG_HOME"):
        # expand "~" in case the variable was set without shell expansion (#578)
        return Path(os.path.expanduser(os.environ["XDG_CONFIG_HOME"]), "scdl")
    return Path.home().joinpath(".config", "scdl")


def parse_args(argv: list[str] | None = None, client: SoundCloud | None = None) -> tuple[str, SCDLArgs]:
    """Parse CLI arguments (sys.argv if argv is None) into a url and kwargs for download_url.

    An already validated SoundCloud client can be passed to skip the client_id/token checks.
    """
    arguments = docopt(__doc__, argv=argv, version=__version__)

    logger.setLevel(logging.INFO)
    if arguments["--debug"]:
        logger.level = logging.DEBUG
    elif arguments["--error"]:
        logger.level = logging.ERROR

    config_file = get_config_dir() / "scdl.cfg"

    # import conf file
    config = _get_config(config_file)

    logger.info(f"[scdl] SCDL version {__version__}")

    client_id = arguments["--client-id"] or config["scdl"]["client_id"]
    token = arguments["--auth-token"] or config["scdl"]["auth_token"]

    if client is None:
        client = _validated_client(arguments, config, config_file, client_id, token)
    elif arguments["me"] and not client.is_auth_token_valid():
        logger.error("[scdl] Invalid auth_token")
        sys.exit(1)

    for opt, low, high in (("--parallel", 1, 3), ("--concurrent-fragments", 1, 32)):
        try:
            arguments[opt] = int(arguments[opt])
            if not low <= arguments[opt] <= high:
                raise ValueError
        except ValueError:  # noqa: PERF203
            logger.error(f"[scdl] {opt} should be an integer between {low} and {high}")
            sys.exit(1)

    python_args = _finish_args(arguments, config, client)
    url = python_args.pop("l")
    assert url is not None
    return _resolve_short_url(url), python_args


def _validated_client(arguments: dict, config, config_file: Path, client_id: str, token: str) -> SoundCloud:
    client = SoundCloud(client_id, token if token else None)

    if not client.is_client_id_valid():
        if arguments["--client-id"]:
            logger.warning(
                "[scdl] Invalid client_id specified by --client-id argument. "
                "Using a dynamically generated client_id",
            )
        elif config["scdl"]["client_id"]:
            logger.warning(
                f"[scdl] Invalid client_id in {config_file}. Using a dynamically generated client_id",
            )
        else:
            logger.info("[scdl] Generating dynamic client_id")
        client = SoundCloud(None, token if token else None)
        if not client.is_client_id_valid():
            logger.error("[scdl] Dynamically generated client_id is not valid")
            sys.exit(1)
        config["scdl"]["client_id"] = client.client_id
        arguments["--client-id"] = client.client_id
        # save client_id
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with locked_file(config_file, "w", encoding="utf-8") as f:
            config.write(f)

    if (token or arguments["me"]) and not client.is_auth_token_valid():
        if arguments["--auth-token"]:
            logger.error("[scdl] Invalid auth_token specified by --auth-token argument")
        else:
            logger.error(f"[scdl] Invalid auth_token in {config_file}")
        sys.exit(1)
    return client


def _finish_args(arguments: dict, config, client: SoundCloud) -> dict:
    """Validate/complete the remaining arguments and convert them to download_url kwargs"""
    if arguments["-o"] is not None:
        try:
            arguments["-o"] = int(arguments["-o"])
            if arguments["-o"] < 1:
                raise ValueError
        except Exception:
            logger.error("[scdl] Offset should be a positive integer")
            sys.exit(1)

    if arguments["-n"] is not None:
        try:
            arguments["-n"] = int(arguments["-n"])
            if arguments["-n"] < 1:
                raise ValueError
        except Exception:
            logger.error("[scdl] Max tracks should be a positive integer")
            sys.exit(1)

    for opt in ("--min-duration", "--max-duration"):
        if arguments[opt] is not None:
            try:
                _parse_duration(arguments[opt])
            except ValueError:
                logger.error(f"[scdl] {opt} should be SS, MM:SS or HH:MM:SS")
                sys.exit(1)

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
        url = _search_soundcloud(client, arguments["-s"])
        if url:
            arguments["-l"] = url
        else:
            logger.error("[scdl] Search failed")
            sys.exit(1)

    arguments["--path"] = Path(os.path.expanduser(arguments["--path"] or config["scdl"]["path"] or ".")).resolve()

    # convert arguments dict to python-friendly kwarg names (no hyphens)
    python_args = {}
    for key, value in arguments.items():
        key = key.strip("-").replace("-", "_")
        python_args[key] = value

    python_args["client_id"] = client.client_id
    python_args["auth_token"] = client.auth_token
    return python_args


def _resolve_short_url(url: str) -> str:
    """Expand share links from the mobile app (on.soundcloud.com/...), which yt-dlp does not support (#546)"""

    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):  # noqa: ARG002
            return None

    if urllib.parse.urlparse(url).netloc != "on.soundcloud.com":
        return url
    short_url = url
    opener = urllib.request.build_opener(_NoRedirect)
    for _ in range(5):
        parsed = urllib.parse.urlparse(url)
        if parsed.netloc != "on.soundcloud.com":
            break
        try:
            opener.open(urllib.request.Request(url, method="HEAD"), timeout=15)
            break
        except urllib.error.HTTPError as err:
            location = err.headers.get("Location")
            if err.code not in (301, 302, 303, 307, 308) or not location:
                logger.warning(f"[scdl] Could not resolve short link {url}: HTTP {err.code}")
                return url
            url = urllib.parse.urljoin(url, location)
        except OSError as err:
            logger.warning(f"[scdl] Could not resolve short link {url}: {err}")
            return url
    else:
        return url
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc.endswith("soundcloud.com") and parsed.netloc != "on.soundcloud.com":
        # drop tracking parameters (?ref=clipboard&utm_source=...) added to share links
        url = urllib.parse.urlunparse(parsed._replace(query="", fragment=""))
    logger.info(f"[scdl] Resolved {short_url} to {url}")
    return url


def _parse_duration(value: str) -> int:
    """Convert SS, MM:SS or HH:MM:SS into seconds"""
    parts = value.strip().split(":")
    if not 1 <= len(parts) <= 3 or not all(p.isdigit() for p in parts):
        raise ValueError(value)
    return sum(int(x) * 60**i for i, x in enumerate(reversed(parts)))


def _search_soundcloud(client: SoundCloud, query: str) -> str | None:
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


def _get_config(config_file: Path) -> configparser.RawConfigParser:
    """Gets config from scdl.cfg"""
    config = configparser.RawConfigParser()

    default_config_file = Path(__file__).with_name("scdl.cfg")

    config_file.parent.mkdir(parents=True, exist_ok=True)

    # load default config first
    with open(default_config_file, encoding="utf-8") as f:
        config.read_file(f)

    try:
        with locked_file(config_file, "r", encoding="utf-8") as f:
            config.read_file(f)
    except Exception as err:
        logger.warning(f"Error while reading config file: {err}")

    try:
        with locked_file(config_file, "w", encoding="utf-8") as f:
            config.write(f)
    except Exception as err:
        logger.warning(f"Error while writing config file: {err}")

    return config


def _convert_v2_name_format(s: str) -> str:
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


def _build_ytdl_output_filename(scdl_args: SCDLArgs, in_playlist: bool, force_suffix: str | None = None) -> str:
    if scdl_args.get("name_format") == "-":
        return "-"

    playlist_format = "%(playlist|)s"
    if in_playlist:
        track_format = _convert_v2_name_format(scdl_args["playlist_name_format"])
    else:
        track_format = _convert_v2_name_format(scdl_args["name_format"])

    if scdl_args.get("addtimestamp") or scdl_args.get("addtofile"):
        track_format = "%(title)s.%(ext)s"
        if scdl_args.get("addtofile"):
            track_format = "%(uploader)s - " + track_format
        if scdl_args.get("addtimestamp"):
            track_format = "%(timestamp)s_" + track_format

    if scdl_args.get("clean_tags"):
        track_format = track_format.replace("%(uploader)s", "%(meta_artist,uploader)s")
        track_format = track_format.replace("%(title)s", "%(meta_title,title)s")

    base = scdl_args["path"]
    if scdl_args.get("no_playlist_folder") or not in_playlist:
        ret = base / track_format
    else:
        ret = base / playlist_format / track_format

    if force_suffix:
        ret = ret.with_suffix(force_suffix)

    return ret.as_posix()


def _build_ytdl_format_specifier(scdl_args: SCDLArgs) -> str:
    fmt = "ba"
    if scdl_args.get("min_size"):
        fmt += f"[filesize_approx>={scdl_args['min_size']}]"
    if scdl_args.get("max_size"):
        fmt += f"[filesize_approx<={scdl_args['max_size']}]"
    if scdl_args.get("no_original"):
        fmt += "[format_id!=download]"
    if scdl_args.get("only_original"):
        fmt += "[format_id=download]"
    if scdl_args.get("onlymp3"):
        fmt += "[format_id*=mp3]"
    return fmt


def _build_ytdl_params(url: str, scdl_args: SCDLArgs) -> tuple[str, dict, list]:
    # return download url, ytdl params, and postprocessors

    if scdl_args.get("a"):
        pass
    elif scdl_args.get("t"):
        url = posixpath.join(url, "tracks")
    elif scdl_args.get("f"):
        url = posixpath.join(url, "likes")
    elif scdl_args.get("C"):
        url = posixpath.join(url, "comments")
    elif scdl_args.get("p"):
        url = posixpath.join(url, "sets")
    elif scdl_args.get("r"):
        url = posixpath.join(url, "reposts")

    params: dict = {}

    # default params
    params["--embed-metadata"] = True
    params["--embed-thumbnail"] = True
    params["--remux-video"] = "aac>m4a"
    params["--extractor-args"] = "soundcloud:formats=*_aac,*_mp3"  # ignore opus by default
    params["--use-extractors"] = "soundcloud.*"
    params["--output-na-placeholder"] = ""
    params["--parse-metadata"] = []
    params["--trim-filenames"] = "240b"
    # playlist-level files (e.g. the playlist cover) were written to the working directory as "..jpg"
    params["--no-write-playlist-metafiles"] = True
    postprocessors = [
        (
            OuttmplPP(
                _build_ytdl_output_filename(scdl_args, False),
                _build_ytdl_output_filename(scdl_args, True),
            ),
            "pre_process",
        )
    ]

    if scdl_args.get("strict_playlist"):
        params["--abort-on-error"] = True

    if scdl_args.get("concurrent_fragments") and scdl_args.get("name_format") != "-":
        params["--concurrent-fragments"] = str(scdl_args["concurrent_fragments"])

    if not scdl_args.get("c") and not scdl_args.get("download_archive") and not scdl_args.get("sync"):
        params["--break-on-existing"] = True

    # if not scdl_args.get("force_metadata"):
    #     https://github.com/yt-dlp/yt-dlp/issues/1467
    #     params["--no-post-overwrites"] = True  # noqa: ERA001

    offset, max_tracks = scdl_args.get("o"), scdl_args.get("n")
    if offset or max_tracks:
        start = offset or 1
        end = start + max_tracks - 1 if max_tracks else ""
        params["--playlist-items"] = f"{start}:{end}"

    if scdl_args.get("extract_artist"):
        params["--parse-metadata"] += [
            r"%(title)s:(?P<meta_artist>.*?)\s+[-−–—―]\s*(?P<meta_title>.*)",  # noqa: RUF001
        ]

    if scdl_args.get("debug"):
        params["--verbose"] = True

    if scdl_args.get("error"):
        params["--quiet"] = True

    if scdl_args.get("download_archive"):
        params["--download-archive"] = scdl_args.get("download_archive")

    if scdl_args.get("hide_progress"):
        params["--no-progress"] = True

    if scdl_args.get("max_size"):
        params["--max-filesize"] = scdl_args.get("max_size")
    if scdl_args.get("min_size"):
        params["--min-filesize"] = scdl_args.get("min_size")

    params["-f"] = _build_ytdl_format_specifier(scdl_args)

    if scdl_args.get("flac"):
        params["--recode-video"] = "aiff>flac/alac>flac/wav>flac"

    if not scdl_args.get("no_album_tag"):
        params["--parse-metadata"] += [
            "%(playlist)s:%(meta_album)s",
            "%(playlist_uploader)s:%(meta_album_artist)s",
            "%(playlist_index)s:%(meta_track)s",
        ]

    if scdl_args.get("original_name") and not scdl_args.get("no_original"):
        postprocessors.append((OriginalFilenamePP(), "pre_process"))

    if scdl_args.get("clean_tags"):
        postprocessors.append((CleanTagsPP(), "pre_process"))

    if not scdl_args.get("original_art"):
        params["--thumbnail-id"] = "t500x500"

    if scdl_args.get("name_format") == "-":
        # https://github.com/yt-dlp/yt-dlp/issues/8815
        # https://github.com/yt-dlp/yt-dlp/issues/126
        params["--embed-metadata"] = False
        params["--embed-thumbnail"] = False

    if scdl_args.get("original_metadata"):
        params["--embed-metadata"] = False
        params["--embed-thumbnail"] = False
    else:
        postprocessors.append(
            (MutagenPP(scdl_args["force_metadata"], keep_thumbnail=bool(scdl_args.get("write_cover"))), "post_process")
        )

    if scdl_args.get("auth_token"):
        params["--username"] = "oauth"
        params["--password"] = scdl_args.get("auth_token")

    if scdl_args.get("overwrite"):
        params["--force-overwrites"] = True

    match_filters = []
    if scdl_args.get("min_duration"):
        match_filters.append(f"duration >=? {_parse_duration(scdl_args['min_duration'])}")
    if scdl_args.get("max_duration"):
        match_filters.append(f"duration <=? {_parse_duration(scdl_args['max_duration'])}")
    if scdl_args.get("no_playlist"):
        match_filters.append("!playlist_uploader")
    if match_filters:
        params["--match-filters"] = " & ".join(match_filters)

    if scdl_args.get("sleep"):
        params["--sleep-requests"] = scdl_args["sleep"]
        params["--sleep-interval"] = scdl_args["sleep"]

    if scdl_args.get("audio_format"):
        params["--extract-audio"] = True
        params["--audio-format"] = scdl_args["audio_format"]
        params["--audio-quality"] = scdl_args.get("audio_quality") or "0"

    if scdl_args.get("write_cover"):
        params["--write-thumbnail"] = True

    if scdl_args.get("add_description"):
        params["--print-to-file"] = (
            "description",
            _build_ytdl_output_filename(scdl_args, False, ".txt"),
        )

    if scdl_args.get("opus"):
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

    logger.debug(f"[debug] yt-dlp args: {url} {' '.join(argv)}")

    return url, utils.cli_to_api(argv), postprocessors


def _skip_known_drm_filter(base_filter, cache_file: Path):
    """Wrap a yt-dlp match_filter to skip (and remember) tracks without downloadable formats"""
    known: set[str] = set()
    if cache_file.exists():
        with locked_file(cache_file, "r", encoding="utf-8") as f:
            known = {line.strip() for line in f if line.strip()}

    def match_filter(info_dict: dict, incomplete: bool = False):
        if info_dict.get("_type") != "playlist" and info_dict.get("id") is not None:
            track_id = str(info_dict["id"])
            title = info_dict.get("title") or track_id
            if track_id in known:
                return f"{title} is known to have no downloadable formats, skipping"
            if "formats" in info_dict and not info_dict["formats"]:
                known.add(track_id)
                with locked_file(cache_file, "a", encoding="utf-8") as f:
                    f.write(track_id + "\n")
                return f"{title} has no downloadable formats (DRM or geo-restricted), skipping"
        if base_filter is None:
            return None
        return base_filter(info_dict, incomplete=incomplete)

    return match_filter


class _ApiRateLimiter:
    """Spaces out requests to the SoundCloud API across all download threads"""

    def __init__(self, min_interval: float) -> None:
        self._lock = threading.Lock()
        self._min_interval = min_interval
        self._next_at = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            at = max(now, self._next_at)
            self._next_at = at + self._min_interval
        if at > now:
            time.sleep(at - now)

    def pause(self, seconds: float) -> None:
        with self._lock:
            self._next_at = max(self._next_at, time.monotonic() + seconds)


_SOUNDCLOUD_API_HOSTS = {
    "soundcloud.com",
    "www.soundcloud.com",
    "m.soundcloud.com",
    "api.soundcloud.com",
    "api-v2.soundcloud.com",
    "api-auth.soundcloud.com",
}
_api_limiter = _ApiRateLimiter(0.25)


class _ScdlYoutubeDL(YoutubeDL):
    def urlopen(self, req):
        url = req if isinstance(req, str) else req.url
        if urllib.parse.urlparse(url).netloc not in _SOUNDCLOUD_API_HOSTS:
            # media files/fragments come from the CDN and are not rate limited
            return super().urlopen(req)
        retries = 3
        for attempt in range(retries + 1):
            _api_limiter.wait()
            try:
                return super().urlopen(req)
            except HTTPError as err:
                if err.status != 429 or attempt == retries:
                    raise
                retry_after = err.response.headers.get("Retry-After") or ""
                delay = int(retry_after) if retry_after.isdigit() else 30 * 2**attempt
                self.report_warning(f"SoundCloud rate limit (HTTP 429), pausing {delay}s before retrying")
                # pause every download thread, not just this one
                _api_limiter.pause(delay)
        raise AssertionError  # unreachable


class _ListingLogger:
    """Logger for the playlist listing pass: hides the per-item lines, which belong to the download pass"""

    def debug(self, msg: str) -> None:
        if not msg.startswith("[download] Downloading item"):
            logger.debug(msg)

    def warning(self, msg: str) -> None:
        logger.warning(msg)

    def error(self, msg: str) -> None:
        logger.error(msg)


class _RecordPP(PostProcessor):
    def __init__(self, callback) -> None:
        super().__init__()
        self._callback = callback

    def run(self, info):
        self._callback(info)
        return [], info


def _playlist_entries(ydl: YoutubeDL, url: str) -> list[tuple[dict, dict]] | None:
    """List the (filtered, sliced) entries of a playlist without resolving them; None if url is a track.

    Each entry comes with the playlist fields yt-dlp would add during a normal playlist download,
    so names, folders and album tags stay the same.
    """
    if SoundcloudIE.suitable(url):
        return None
    info = ydl.extract_info(url, download=False)
    if not info or info.get("_type") != "playlist":
        return None
    entries = info.get("entries") or []
    indices = info.get("requested_entries") or range(1, len(entries) + 1)
    common = YoutubeDL._playlist_infodict(info, n_entries=len(entries))
    return [
        (entry, {**common, "playlist_index": index, "playlist_autonumber": i})
        for i, (index, entry) in enumerate(zip(indices, entries), 1)
        if entry
    ]


def _download_parallel(entries: list[tuple[dict, dict]], workers: int, new_ydl) -> None:
    total = len(entries)
    logger.info(f"[scdl] Downloading {total} items, {workers} at a time")
    pending: queue.SimpleQueue[tuple[int, tuple[dict, dict]]] = queue.SimpleQueue()
    for item in enumerate(entries, 1):
        pending.put(item)
    stop = threading.Event()

    def worker() -> None:
        with new_ydl() as ydl:
            while not stop.is_set():
                try:
                    i, (entry, extra) = pending.get_nowait()
                except queue.Empty:
                    return
                logger.info(f"[download] Downloading item {i} of {total}")
                try:
                    ydl.extract_info(entry["url"], ie_key=entry.get("ie_key"), extra_info=extra)
                except DownloadCancelled:  # --break-on-existing and friends
                    stop.set()
                except DownloadError:
                    pass  # already reported by yt-dlp
                except Exception as err:
                    logger.error(f"[scdl] {entry.get('title') or entry['url']}: {err}")
                except BaseException:
                    stop.set()
                    raise

    with concurrent.futures.ThreadPoolExecutor(workers, thread_name_prefix="scdl") as pool:
        futures = [pool.submit(worker) for _ in range(min(workers, total))]
        try:
            for future in futures:
                future.result()
        except BaseException:
            stop.set()
            raise


def download_url(
    url: str,
    ydl_opts: dict | None = None,
    on_file=None,
    **scdl_args: Unpack[SCDLArgs],
) -> list[str]:
    """Download url with scdl options. Extra yt-dlp params (e.g. progress_hooks) can be passed in ydl_opts
    and on_file is called with the info dict of every finished file (path in info["filepath"]).

    Returns the paths of the files that were downloaded.
    """
    url, params, _ = _build_ytdl_params(url, scdl_args)

    params["logger"] = logger

    # we handle this with custom MutagenPP for now
    params["postprocessors"] = [
        pp for pp in params["postprocessors"] if pp["key"] not in ("EmbedThumbnail", "FFmpegMetadata")
    ]

    yt_dlp_args = scdl_args.get("yt_dlp_args")
    if yt_dlp_args:
        argv = shlex.split(yt_dlp_args)
        overrides = utils.cli_to_api(argv)
        params = {**params, **overrides}

    if scdl_args.get("skip_known_drm"):
        # report tracks without formats as a normal result so the match filter can reject them
        params["ignore_no_formats_error"] = True
        cache_file = get_config_dir() / "no_formats.txt"
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        params["match_filter"] = _skip_known_drm_filter(params.get("match_filter"), cache_file)

    for key, value in (ydl_opts or {}).items():
        if isinstance(value, list) and isinstance(params.get(key), list):
            params[key] = [*params[key], *value]
        else:
            params[key] = value

    downloaded: list[str] = []
    lock = threading.Lock()

    def record(info: dict) -> None:
        with lock:
            downloaded.append(info["filepath"])
        if on_file:
            on_file(info)

    cache_stored = False

    def new_ydl(extra_params: dict | None = None, listing: bool = False) -> YoutubeDL:
        nonlocal cache_stored
        ydl = _ScdlYoutubeDL({**params, **(extra_params or {})})
        if scdl_args["client_id"] and not cache_stored:
            # once, from the main thread: concurrent writes to the yt-dlp cache fail on Windows
            ydl.cache.store("soundcloud", "client_id", scdl_args["client_id"])
            cache_stored = True
        if listing:
            return ydl
        # postprocessors keep per-downloader state, so every downloader gets its own
        for pp, when in _build_ytdl_params(url, scdl_args)[2]:
            ydl.add_post_processor(pp, when)
        ydl.add_post_processor(_RecordPP(record), "after_move")
        return ydl

    workers = scdl_args.get("parallel") or 1
    if workers > 1 and (
        scdl_args.get("sync") or scdl_args.get("strict_playlist") or scdl_args.get("name_format") == "-"
    ):
        logger.warning("[scdl] --parallel is ignored with --sync, --strict-playlist and stdout output")
        workers = 1

    entries = None
    if workers > 1:
        listing_params = {
            "extract_flat": "in_playlist",
            "logger": _ListingLogger(),
            # yt-dlp runs pre-processors and hooks on flat entries too; they belong to the download pass
            "postprocessors": [],
            "progress_hooks": [],
            "postprocessor_hooks": [],
            # the listing pass must not write anything (e.g. the playlist cover as "..jpg")
            "writethumbnail": False,
            "write_all_thumbnails": False,
            "writedescription": False,
            "writeinfojson": False,
        }
        with new_ydl(listing_params, listing=True) as ydl:
            entries = _playlist_entries(ydl, url)

    if entries is None:
        with new_ydl() as ydl:
            sync = SyncDownloadHelper(scdl_args, ydl)
            ydl.download(url)
            sync.post_download()
    elif entries:
        # interleaved progress bars from several threads are unreadable
        params["noprogress"] = True
        _download_parallel(entries, workers, new_ydl)

    return downloaded


if __name__ == "__main__":
    _main()
