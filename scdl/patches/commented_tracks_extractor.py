from yt_dlp.extractor.lazy_extractors import SoundcloudIE as LazySC
from yt_dlp.extractor.lazy_extractors import SoundcloudUserIE as LazySCUser
from yt_dlp.extractor.soundcloud import SoundcloudIE, SoundcloudUserIE

SoundcloudIE._VALID_URL = r"""(?x)^(?:https?://)?
    (?:(?:(?:www\.|m\.)?soundcloud\.com/
            (?!stations/track)
            (?P<uploader>[\w\d-]+)/
            (?!(?:tracks|albums|sets(?:/.+?)?|reposts|likes|spotlight|comments)/?(?:$|[?#]))
            (?P<title>[\w\d-]+)
            (?:/(?P<token>(?!(?:albums|sets|recommended))[^?]+?))?
            (?:[?].*)?$)
        |(?:api(?:-v2)?\.soundcloud\.com/tracks/(?P<track_id>\d+)
            (?:/?\?secret_token=(?P<secret_token>[^&]+))?)
    )
    """

LazySC._VALID_URL = r"""(?x)^(?:https?://)?
    (?:(?:(?:www\.|m\.)?soundcloud\.com/
            (?!stations/track)
            (?P<uploader>[\w\d-]+)/
            (?!(?:tracks|albums|sets(?:/.+?)?|reposts|likes|spotlight|comments)/?(?:$|[?#]))
            (?P<title>[\w\d-]+)
            (?:/(?P<token>(?!(?:albums|sets|recommended))[^?]+?))?
            (?:[?].*)?$)
        |(?:api(?:-v2)?\.soundcloud\.com/tracks/(?P<track_id>\d+)
            (?:/?\?secret_token=(?P<secret_token>[^&]+))?)
    )
    """

SoundcloudUserIE._VALID_URL = r"""(?x)
    https?://
        (?:(?:www|m)\.)?soundcloud\.com/
        (?P<user>[^/]+)
        (?:/
            (?P<rsrc>tracks|albums|sets|reposts|likes|spotlight|comments)
        )?
        /?(?:[?#].*)?$
    """

LazySCUser._VALID_URL = r"""(?x)
    https?://
        (?:(?:www|m)\.)?soundcloud\.com/
        (?P<user>[^/]+)
        (?:/
            (?P<rsrc>tracks|albums|sets|reposts|likes|spotlight|comments)
        )?
        /?(?:[?#].*)?$
    """

SoundcloudUserIE._BASE_URL_MAP["comments"] = "users/%s/comments"
