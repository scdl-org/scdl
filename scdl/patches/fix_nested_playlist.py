from yt_dlp.extractor.soundcloud import SoundcloudUserIE

old_extract = SoundcloudUserIE._real_extract


def _real_extract(self, url):
    ret = old_extract(self, url)
    ret.update({"title": None, "id": None})
    return ret


SoundcloudUserIE._real_extract = _real_extract
