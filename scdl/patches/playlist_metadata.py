# https://github.com/yt-dlp/yt-dlp/pull/11945
from yt_dlp.extractor.soundcloud import SoundcloudIE, SoundcloudPlaylistBaseIE
from yt_dlp.utils import str_or_none, traverse_obj


def _extract_set(self, playlist, token=None):
    playlist_id = str(playlist["id"])
    tracks = playlist.get("tracks") or []
    if not all(t.get("permalink_url") for t in tracks) and token:
        tracks = self._call_api(
            self._API_V2_BASE + "tracks",
            playlist_id,
            "Downloading tracks",
            query={
                "ids": ",".join([str(t["id"]) for t in tracks]),
                "playlistId": playlist_id,
                "playlistSecretToken": token,
            },
            headers=self._HEADERS,
        )
    entries = []
    for track in tracks:
        track_id = str_or_none(track.get("id"))
        url = track.get("permalink_url")
        if not url:
            if not track_id:
                continue
            url = self._API_V2_BASE + "tracks/" + track_id
            if token:
                url += "?secret_token=" + token
        entries.append(self.url_result(url, SoundcloudIE.ie_key(), track_id))
    return self.playlist_result(
        entries,
        playlist_id,
        playlist.get("title"),
        playlist.get("description"),
        uploader=traverse_obj(playlist, ("user", "username")),
        uploader_id=str_or_none(traverse_obj(playlist, ("user", "id"))),
    )


SoundcloudPlaylistBaseIE._extract_set = _extract_set
