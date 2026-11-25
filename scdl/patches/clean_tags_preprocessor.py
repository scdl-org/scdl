import re

from yt_dlp.postprocessor.common import PostProcessor

# text inside brackets that is promotion rather than part of the title
_JUNK = re.compile(
    r"free\s*(?:dl|d/?l|download)|download|out\s*now|official\s*(?:music\s*)?(?:audio|video|visuali[sz]er)"
    r"|lyrics?(?:\s*video)?|premiere|exclusive|\bhq\b|\bhd\b|\d+\s*kbps|buy\s*link|link\s*in\s*bio|click"
    r"|bandcamp|beatport|spotify|supported\s+by|out\s+on|available\s+(?:now|on)|yukle|y[uü]kl[eə]"
    r"|www\.|https?://|\.(?:com|org|net|ru|ir|me|io|co|fm|to)\b",
    re.IGNORECASE,
)
_BRACKETED = re.compile(r"\s*[(\[{【]([^()\[\]{}【】]*)[)\]}】]")
_URL = re.compile(r"\s*(?:https?://\S+|www\.\S+)", re.IGNORECASE)
_PREFIX = re.compile(r"^\s*(?:premiere|exclusive|free\s*(?:dl|download)|out\s*now)\s*[:|\-–—]+\s*", re.IGNORECASE)  # noqa: RUF001
_SUFFIX = re.compile(r"\s*[|/]+\s*(?:free\s*(?:dl|download)|out\s*now|download|buy)\b.*$", re.IGNORECASE)
_ARTIST_SPLIT = re.compile(r"\s+[-−–—―]+\s+|\s+[-−–—―]+(?=\S)|(?<=\S)[−–—―]+\s+")  # noqa: RUF001
# "Mix 2024 - Part 1" is a title, not "Artist - Title"
_NOT_A_TITLE = re.compile(r"^(?:part|pt\.?|vol\.?|volume|episode|ep\.?|chapter|day|no\.?|#)\s*\d", re.IGNORECASE)
_FEAT = re.compile(r"\s*[(\[]?\s*\b(?:feat\.?|ft\.?|featuring)\s+([^()\[\]]+?)\s*[)\]]?\s*$", re.IGNORECASE)


def _tidy(s: str) -> str:
    s = re.sub(r"\s+", " ", s)
    return s.strip(" -–—|:•·_~")  # noqa: RUF001


def _remove_junk(s: str) -> str:
    s = _BRACKETED.sub(lambda m: "" if _JUNK.search(m.group(1)) else m.group(0), s)
    s = _URL.sub("", s)
    s = _PREFIX.sub("", s)
    s = _SUFFIX.sub("", s)
    return _tidy(s)


def clean_artist_title(title: str, artist: str | None) -> tuple[str, str]:
    """Return a cleaned (artist, title).

    "Artist - Title [Free Download]" -> ("Artist", "Title"); "Title (feat. X)" moves X to the artist;
    when the title does not contain an artist, ``artist`` (usually the uploader) is kept.
    """
    original_title, original_artist = title, artist or ""
    title = _remove_junk(title)

    parts = _ARTIST_SPLIT.split(title, maxsplit=1)
    if len(parts) == 2 and _tidy(parts[0]) and _tidy(parts[1]) and not _NOT_A_TITLE.match(_tidy(parts[1])):
        artist, title = _tidy(parts[0]), _tidy(parts[1])
    else:
        artist = _tidy(original_artist)

    for source in ("title", "artist"):
        text = title if source == "title" else artist
        m = _FEAT.search(text)
        if m and _tidy(text[: m.start()]):
            featured = _tidy(m.group(1))
            text = _tidy(text[: m.start()])
            if source == "title":
                title = text
            else:
                artist = text
            if featured.lower() not in artist.lower():
                artist = f"{artist} feat. {featured}"

    return (artist or original_artist, title or original_title)


class CleanTagsPP(PostProcessor):
    """Sets meta_artist/meta_title from a cleaned up title (used for both the tags and the filename)"""

    def run(self, info):
        title = info.get("meta_title") or info.get("title")
        if not title:
            return [], info
        artist = info.get("meta_artist") or info.get("uploader")
        new_artist, new_title = clean_artist_title(title, artist)
        if (new_artist, new_title) != (artist, title):
            self.to_screen(f'"{artist} - {title}" -> "{new_artist} - {new_title}"')
        info["meta_artist"] = new_artist
        info["meta_title"] = new_title
        return [], info
