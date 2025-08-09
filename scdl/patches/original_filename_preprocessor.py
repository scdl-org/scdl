import email.message
import urllib.parse
from pathlib import Path

from yt_dlp.networking.common import Request, Response
from yt_dlp.postprocessor.common import PostProcessor


def _parse_header(content_disposition):
    if not content_disposition:
        return {}
    message = email.message.Message()
    message["content-type"] = content_disposition
    return dict(message.get_params({}))


class OriginalFilenamePP(PostProcessor):
    def run(self, info):
        for format in info.get("formats", ()):
            if format.get("format_id") == "download":
                res: Response = self._downloader.urlopen(Request(format["url"], headers=format["http_headers"]))
                params = _parse_header(res.get_header("content-disposition"))
                if "filename" not in params:
                    break
                filename = urllib.parse.unquote(params["filename"][-1], encoding="utf-8")
                old_outtmpl = self._downloader.params["outtmpl"]["default"]
                self._downloader.params["outtmpl"]["default"] = (
                    Path(old_outtmpl).with_name(filename).with_suffix(".%(ext)s").as_posix()
                )
                break

        return [], info
