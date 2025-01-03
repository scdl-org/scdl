import errno
from functools import partial
from pathlib import Path

from yt_dlp import YoutubeDL
from yt_dlp.utils import locked_file


class SyncDownloadHelper:
    def __init__(self, scdl_args, ydl: YoutubeDL):
        self._ydl = ydl
        self._enabled = bool(scdl_args["sync"])
        self._sync_file = scdl_args["sync"]
        self._all_files: dict[str, Path] = {}
        self._downloaded: set[str] = set()
        self._init()

    def _init(self):
        if not self._enabled:
            return

        # track downloaded ids/filenames
        def track_downloaded(d):
            if d["status"] != "finished":
                return

            info = d["info_dict"]

            id_ = f"soundcloud {info['id']}"
            self._downloaded.add(id_)
            self._all_files[id_] = d["filename"]

        self._ydl.add_progress_hook(track_downloaded)

        # add already downloaded files to the archive
        try:
            with locked_file(self._sync_file, "r", encoding="utf-8") as archive_file:
                for line in archive_file:
                    line = line.strip()
                    if not line:
                        continue
                    ie, id_, filename = line.split(maxsplit=2)
                    self._ydl.archive.add(f"{ie} {id_}")
                    self._all_files[f"{ie} {id_}"] = Path(filename)
        except OSError as ioe:
            if ioe.errno != errno.ENOENT:
                raise

        # track ids checked against the archive
        def in_download_archive(ydl, info_dict):
            if not ydl.archive:
                return False

            vid_ids = [ydl._make_archive_id(info_dict)]
            vid_ids.extend(info_dict.get("_old_archive_ids") or [])
            self._downloaded.update(vid_ids)
            return any(id_ in ydl.archive for id_ in vid_ids) or any(
                id_.split()[1] in ydl.archive for id_ in vid_ids if id_
            )

        self._ydl.in_download_archive = partial(in_download_archive, self._ydl)

    def post_download(self):
        if not self._enabled:
            return

        # remove extra files
        to_remove = {
            self._all_files[key] for key in (set(self._all_files.keys()) - self._downloaded)
        }
        self._ydl._delete_downloaded_files(*to_remove)

        with locked_file(self._sync_file, "w", encoding="utf-8") as archive_file:
            for k, v in self._all_files.items():
                if k in self._downloaded:
                    archive_file.write(f"{k} {v}\n")
