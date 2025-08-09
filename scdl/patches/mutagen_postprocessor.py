# https://github.com/yt-dlp/yt-dlp/pull/11817
import base64
import collections
import functools
import os
import re
from typing import ClassVar

import mutagen
from mutagen import (
    FileType,
    aiff,
    dsdiff,
    dsf,
    flac,
    id3,
    mp3,
    mp4,
    oggopus,
    oggspeex,
    oggtheora,
    oggvorbis,
    trueaudio,
    wave,
)
from yt_dlp.compat import imghdr
from yt_dlp.postprocessor.common import PostProcessor
from yt_dlp.utils import PostProcessingError, date_from_str, variadic


class MutagenPostProcessorError(PostProcessingError):
    pass


class MutagenPP(PostProcessor):
    _MUTAGEN_SUPPORTED_EXTS = ("alac", "aiff", "flac", "mp3", "m4a", "ogg", "opus", "vorbis", "wav")
    _VORBIS_METADATA: ClassVar[dict[str, str]] = {
        "title": "title",
        "artist": "artist",
        "genre": "genre",
        "album": "album",
        "albumartist": "album_artist",
        "comment": "description",
        "composer": "composer",
        "tracknumber": "track",
        "WWWAUDIOFILE": "purl",  # https://getmusicbee.com/forum/index.php?topic=39759.0
    }
    _ID3_METADATA: ClassVar[dict[str, str]] = {
        "TIT2": "title",
        "TPE1": "artist",
        "COMM": "description",
        "TCON": "genre",
        "WOAF": "purl",
        "TALB": "album",
        "TPE2": "album_artist",
        "TRCK": "track",
        "TCOM": "composer",
        "TPOS": "disc",
    }
    _MP4_METADATA: ClassVar[dict[str, str]] = {
        "\251ART": "artist",
        "\251nam": "title",
        "\251gen": "genre",
        "\251alb": "album",
        "aART": "album_artist",
        "\251cmt": "description",
        "\251wrt": "composer",
        "disk": "disc",
        "tvsh": "show",
        "tvsn": "season_number",
        "egid": "episode_id",
        "tven": "episode_sort",
    }

    def __init__(self, post_overwrites: bool, downloader=None):
        super().__init__(downloader)
        self._post_overwrites = post_overwrites

    def _get_flac_pic(self, thumbnail: dict) -> flac.Picture:
        pic = flac.Picture()
        pic.data = thumbnail["data"]
        pic.mime = f"image/{thumbnail['type']}"
        pic.type = id3.PictureType.COVER_FRONT
        return pic

    def _get_metadata_dict(self, info):
        meta_prefix = "meta"
        metadata = collections.defaultdict(dict)

        def add(meta_list, info_list=None):
            value = next(
                (
                    info[key]
                    for key in [f"{meta_prefix}_", *variadic(info_list or meta_list)]
                    if info.get(key) is not None
                ),
                None,
            )
            if value not in ("", None):
                value = ", ".join(map(str, variadic(value)))
                value = value.replace("\0", "")  # nul character cannot be passed in command line
                metadata["common"].update({meta_f: value for meta_f in variadic(meta_list)})

        # Info on media metadata/metadata supported by ffmpeg:
        # https://wiki.multimedia.cx/index.php/FFmpeg_Metadata
        # https://kdenlive.org/en/project/adding-meta-data-to-mp4-video/
        # https://kodi.wiki/view/Video_file_tagging

        add("title", ("track", "title"))
        add("date", "upload_date")
        add(("description", "synopsis"), "description")
        add(("purl", "comment"), "webpage_url")
        add("track", "track_number")
        add("artist", ("artist", "artists", "creator", "creators", "uploader", "uploader_id"))
        add("composer", ("composer", "composers"))
        add("genre", ("genre", "genres"))
        add("album")
        add("album_artist", ("album_artist", "album_artists"))
        add("disc", "disc_number")
        add("show", "series")
        add("season_number")
        add("episode_id", ("episode", "episode_id"))
        add("episode_sort", "episode_number")
        if "embed-metadata" in self.get_param("compat_opts", []):
            add("comment", "description")
            metadata["common"].pop("synopsis", None)

        meta_regex = rf"{re.escape(meta_prefix)}(?P<i>\d+)?_(?P<key>.+)"
        for key, value in info.items():
            mobj = re.fullmatch(meta_regex, key)
            if value is not None and mobj:
                metadata[mobj.group("i") or "common"][mobj.group("key")] = value.replace("\0", "")
        return metadata

    @functools.singledispatchmethod
    def _assemble_metadata(self, file: FileType, meta: dict) -> None:  # noqa: ARG002
        raise MutagenPostProcessorError(f"Filetype {file.__class__.__name__} is not currently supported")

    @_assemble_metadata.register(flac.FLAC)
    def _(self, file: flac.FLAC, meta: dict) -> None:
        for file_key, meta_key in self._VORBIS_METADATA.items():
            if meta.get(meta_key):
                file[file_key] = meta[meta_key]

        if meta.get("date"):
            # Vorbis uses ISO 8601 format YYYY-MM-DD
            date = date_from_str(meta["date"])
            file["date"] = date.strftime("%Y-%m-%d")

        if meta.get("thumbnail"):
            pic = self._get_flac_pic(meta["thumbnail"])
            file.add_picture(pic)

    @_assemble_metadata.register(oggvorbis.OggVorbis)
    @_assemble_metadata.register(oggtheora.OggTheora)
    @_assemble_metadata.register(oggspeex.OggSpeex)
    @_assemble_metadata.register(oggopus.OggOpus)
    def _(self, file: oggopus.OggOpus, meta: dict) -> None:
        for file_key, meta_key in self._VORBIS_METADATA.items():
            if meta.get(meta_key):
                file[file_key] = meta[meta_key]

        if meta.get("date"):
            # Vorbis uses ISO 8601 format YYYY-MM-DD
            date = date_from_str(meta["date"])
            file["date"] = date.strftime("%Y-%m-%d")

        if meta.get("thumbnail"):
            pic = self._get_flac_pic(meta["thumbnail"])
            file["METADATA_BLOCK_PICTURE"] = base64.b64encode(pic.write()).decode("ascii")

    @_assemble_metadata.register(trueaudio.TrueAudio)
    @_assemble_metadata.register(dsf.DSF)
    @_assemble_metadata.register(dsdiff.DSDIFF)
    @_assemble_metadata.register(aiff.AIFF)
    @_assemble_metadata.register(mp3.MP3)
    @_assemble_metadata.register(wave.WAVE)
    def _(self, file: wave.WAVE, meta: dict) -> None:
        for file_key, meta_key in self._ID3_METADATA.items():
            if meta.get(meta_key):
                id3_class = getattr(id3, file_key)
                if issubclass(id3_class, id3.UrlFrame):
                    file[file_key] = id3_class(url=meta[meta_key])
                else:
                    file[file_key] = id3_class(encoding=id3.Encoding.UTF8, text=meta[meta_key])

        if meta.get("date"):
            # ID3 uses ISO 8601 format YYYY-MM-DD
            date = date_from_str(meta["date"])
            file["TDRC"] = id3.TDRC(encoding=id3.Encoding.UTF8, text=date.strftime("%Y-%m-%d"))

        if meta.get("thumbnail"):
            file["APIC"] = id3.APIC(
                encoding=3,
                mime=f'image/{meta["thumbnail"]["type"]}',
                type=3,
                desc="Cover (front)",
                data=meta["thumbnail"]["data"],
            )

    @_assemble_metadata.register(mp4.MP4)
    def _(self, file: mp4.MP4, meta: dict) -> None:
        for file_key, meta_key in self._MP4_METADATA.items():
            if meta.get(meta_key):
                file[file_key] = meta[meta_key]

        if meta.get("date"):
            # no standard but iTunes uses YYYY-MM-DD format
            date = date_from_str(meta["date"])
            file["\251day"] = date.strftime("%Y-%m-%d")

        if meta.get("purl"):
            # https://getmusicbee.com/forum/index.php?topic=39759.0
            file["----:com.apple.iTunes:WWWAUDIOFILE"] = meta["purl"].encode()
            file["purl"] = meta["purl"]

        if meta.get("track"):
            file["trkn"] = [(meta["track"], 0)]

        if meta.get("covr"):
            f = {"jpeg": mp4.MP4Cover.FORMAT_JPEG, "png": mp4.MP4Cover.FORMAT_PNG}
            file["covr"] = [mp4.MP4Cover(meta["covr"]["data"], f[meta["covr"]["type"]])]

    def _get_thumbnail(self, info: dict):
        if not info.get("thumbnails"):
            self.to_screen("There aren't any thumbnails to embed")
            return None

        idx = next((-i for i, t in enumerate(info["thumbnails"][::-1], 1) if t.get("filepath")), None)
        if idx is None:
            self.to_screen("There are no thumbnails on disk")
            return None
        thumbnail_filename = info["thumbnails"][idx]["filepath"]
        if not os.path.exists(thumbnail_filename):
            self.report_warning("Skipping embedding the thumbnail because the file is missing.")
            return None

        with open(thumbnail_filename, "rb") as thumbfile:
            thumb_data = thumbfile.read()

        self._delete_downloaded_files(
            thumbnail_filename,
            info=info,
        )

        type_ = imghdr.what(h=thumb_data)
        if not type_:
            self.report_warning("Could not determine thumbnail image type")
            return None

        if type_ not in {"jpeg", "png"}:
            self.report_warning(f"Incompatible thumbnail image type: {type_}")
            return None

        return {"data": thumb_data, "type": type_}

    def run(self, info: dict):
        thumbnail = self._get_thumbnail(info)
        if not info["__real_download"] and not self._post_overwrites:
            return [], info

        filename = info["filepath"]
        metadata = self._get_metadata_dict(info)["common"]

        if thumbnail:
            metadata["thumbnail"] = thumbnail

        if not metadata:
            self.to_screen("There isn't any metadata to add")
            return [], info

        if info["ext"] not in self._MUTAGEN_SUPPORTED_EXTS:
            raise MutagenPostProcessorError(f'Unsupported file extension: {info["ext"]}')

        self.to_screen(f'Adding metadata to "{filename}"')
        try:
            f = mutagen.File(filename)
            self._assemble_metadata(f, metadata)
            f.save()
        except Exception as err:
            raise MutagenPostProcessorError("Unable to embed metadata") from err

        return [], info
