from base64 import b64encode
from dataclasses import dataclass
from functools import singledispatch
from typing import Optional, Union

from mutagen import (
    FileType,
    aiff,
    flac,
    id3,
    mp3,
    mp4,
    oggopus,
    oggspeex,
    oggtheora,
    wave,
)

JPEG_MIME_TYPE: str = "image/jpeg"


@dataclass(frozen=True)
class MetadataInfo:
    artist: str
    title: str
    description: Optional[str]
    genre: Optional[str]

    artwork_jpeg: Optional[bytes]

    link: Optional[str]
    date: Optional[str]

    album_title: Optional[str]
    album_author: Optional[str]
    album_track_num: Optional[int]
    album_total_track_num: Optional[int]


@singledispatch
def assemble_metadata(file: FileType, meta: MetadataInfo) -> None:
    raise NotImplementedError


def _get_flac_pic(jpeg_data: bytes) -> flac.Picture:
    pic = flac.Picture()
    pic.data = jpeg_data
    pic.mime = JPEG_MIME_TYPE
    pic.type = id3.PictureType.COVER_FRONT
    return pic


def _get_apic(jpeg_data: bytes) -> id3.APIC:
    return id3.APIC(
        encoding=3,
        mime=JPEG_MIME_TYPE,
        type=3,
        desc="Cover",
        data=jpeg_data,
    )


def _assemble_vorbis_tags(file: FileType, meta: MetadataInfo) -> None:
    file["artist"] = meta.artist
    file["title"] = meta.title

    if meta.genre:
        file["genre"] = meta.genre

    if meta.link:
        # https://getmusicbee.com/forum/index.php?topic=39759.0
        file["WWWAUDIOFILE"] = meta.link

    if meta.date:
        file["date"] = meta.date

    if meta.album_title:
        file["album"] = meta.album_title

    if meta.album_author:
        file["albumartist"] = meta.album_author

    if meta.album_track_num is not None:
        file["tracknumber"] = str(meta.album_track_num)

    if meta.description:
        # https://xiph.org/vorbis/doc/v-comment.html
        # prefer 'description' over 'comment'
        file["description"] = meta.description


@assemble_metadata.register(flac.FLAC)
def _(file: flac.FLAC, meta: MetadataInfo) -> None:
    _assemble_vorbis_tags(file, meta)

    if meta.artwork_jpeg:
        file.add_picture(_get_flac_pic(meta.artwork_jpeg))


@assemble_metadata.register(oggtheora.OggTheora)
@assemble_metadata.register(oggspeex.OggSpeex)
@assemble_metadata.register(oggopus.OggOpus)
def _(file: oggopus.OggOpus, meta: MetadataInfo) -> None:
    _assemble_vorbis_tags(file, meta)

    if meta.artwork_jpeg:
        pic = _get_flac_pic(meta.artwork_jpeg).write()
        file["metadata_block_picture"] = b64encode(pic).decode()


@assemble_metadata.register(aiff.AIFF)
@assemble_metadata.register(mp3.MP3)
@assemble_metadata.register(wave.WAVE)
def _(file: Union[wave.WAVE, mp3.MP3], meta: MetadataInfo) -> None:
    file["TIT2"] = id3.TIT2(encoding=3, text=meta.title)
    file["TPE1"] = id3.TPE1(encoding=3, text=meta.artist)

    if meta.description:
        file["COMM"] = id3.COMM(encoding=3, lang="ENG", text=meta.description)

    if meta.genre:
        file["TCON"] = id3.TCON(encoding=3, text=meta.genre)

    if meta.link:
        file["WOAF"] = id3.WOAF(url=meta.link)

    if meta.date:
        file["TDAT"] = id3.TDAT(encoding=3, text=meta.date)

    if meta.album_title:
        file["TALB"] = id3.TALB(encoding=3, text=meta.album_title)

    if meta.album_author:
        file["TPE2"] = id3.TPE2(encoding=3, text=meta.album_author)

    if meta.album_track_num is not None:
        file["TRCK"] = id3.TRCK(encoding=3, text=str(meta.album_track_num))

    if meta.artwork_jpeg:
        file["APIC"] = _get_apic(meta.artwork_jpeg)


@assemble_metadata.register(mp4.MP4)
def _(file: mp4.MP4, meta: MetadataInfo) -> None:
    file["\251ART"] = meta.artist
    file["\251nam"] = meta.title

    if meta.genre:
        file["\251gen"] = meta.genre

    if meta.link:
        # https://getmusicbee.com/forum/index.php?topic=39759.0
        file["----:com.apple.iTunes:WWWAUDIOFILE"] = meta.link.encode()

    if meta.date:
        file["\251day"] = meta.date

    if meta.album_title:
        file["\251alb"] = meta.album_title

    if meta.album_author:
        file["aART"] = meta.album_author

    if meta.album_track_num is not None:
        file["trkn"] = [(meta.album_track_num, meta.album_total_track_num)]

    if meta.description:
        file["\251cmt"] = meta.description

    if meta.artwork_jpeg:
        file["covr"] = [mp4.MP4Cover(meta.artwork_jpeg)]
