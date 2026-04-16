import errno
from functools import partial
from pathlib import Path

from yt_dlp import YoutubeDL
from yt_dlp.utils import locked_file


class SyncDownloadHelper:
    def __init__(self, scdl_args, ydl: YoutubeDL):
        self._ydl = ydl
        self._enabled = bool(scdl_args.get("sync"))
        self._sync_file = scdl_args.get("sync")
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
        old_match_entry = self._ydl._match_entry

        def _match_entry(ydl, info_dict, incomplete=False, silent=False):
            self._downloaded.add(ydl._make_archive_id(info_dict))
            return old_match_entry(info_dict, incomplete, silent)

        self._ydl._match_entry = partial(_match_entry, self._ydl)

    def post_download(self):
        if not self._enabled:
            return

        # remove extra files
        to_remove = {self._all_files[key] for key in (set(self._all_files.keys()) - self._downloaded)}
        self._ydl._delete_downloaded_files(*to_remove)

        with locked_file(self._sync_file, "w", encoding="utf-8") as archive_file:
            for k, v in self._all_files.items():
                if k in self._downloaded:
                    archive_file.write(f"{k} {v}\n")
