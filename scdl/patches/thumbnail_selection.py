# https://github.com/yt-dlp/yt-dlp/pull/11809
import yt_dlp
import yt_dlp.options as options
from yt_dlp.YoutubeDL import YoutubeDL


def _sort_thumbnails_patched(self, thumbnails):
    thumbnails.sort(
        key=lambda t: (
            t.get("id") == self.params.get("thumbnail_id") if t.get("id") is not None else False,
            t.get("preference") if t.get("preference") is not None else -1,
            t.get("width") if t.get("width") is not None else -1,
            t.get("height") if t.get("height") is not None else -1,
            t.get("id") if t.get("id") is not None else "",
            t.get("url"),
        )
    )


old_parse_options = yt_dlp.parse_options


def parse_options_patched(argv=None):
    parsed = old_parse_options(argv)
    parsed[3]["thumbnail_id"] = parsed[1].thumbnail_id
    return parsed


old_create_parser = options.create_parser


def create_parser_patched():
    parser = old_create_parser()
    thumbnail = parser.get_option_group("--write-thumbnail")
    thumbnail.add_option("--thumbnail-id", metavar="ID", dest="thumbnail_id", help="ID of thumbnail to write to disk")
    return parser


YoutubeDL._sort_thumbnails = _sort_thumbnails_patched
yt_dlp.parse_options = parse_options_patched
options.create_parser = create_parser_patched
