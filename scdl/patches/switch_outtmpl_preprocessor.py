# https://github.com/yt-dlp/yt-dlp/issues/11583 workaround
from yt_dlp.postprocessor.common import PostProcessor


class OuttmplPP(PostProcessor):
    def __init__(self, video_outtmpl: str, playlist_outtmpl: str, downloader=None):
        super().__init__(downloader)
        self._outtmpls = {False: video_outtmpl, True: playlist_outtmpl}

    def run(self, info):
        in_playlist = info.get("playlist_uploader") is not None
        self._downloader.params["outtmpl"]["default"] = self._outtmpls[in_playlist]
        if not in_playlist:
            for meta in ("track", "album_artist", "album"):
                info[f"meta_{meta}"] = None
        return [], info
