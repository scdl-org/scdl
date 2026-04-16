from yt_dlp import YoutubeDL


def in_download_archive(self, info_dict):
    if not self.archive:
        return False

    vid_ids = [self._make_archive_id(info_dict)]
    vid_ids.extend(info_dict.get("_old_archive_ids") or [])
    return any(id_ in self.archive for id_ in vid_ids) or any(id_.split()[1] in self.archive for id_ in vid_ids if id_)


YoutubeDL.in_download_archive = in_download_archive
