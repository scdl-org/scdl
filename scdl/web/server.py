"""Small local web UI for scdl.

Run with ``scdl-web`` or ``python -m scdl.web``. The server only listens on 127.0.0.1,
downloads run one at a time in a background thread (to avoid SoundCloud rate limits)
and the page polls ``/api/jobs`` for progress.
"""

from __future__ import annotations

import argparse
import collections
import json
import logging
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import ClassVar
from urllib.parse import parse_qs, urlparse

from soundcloud import AlbumPlaylist, SoundCloud, Track, User

from scdl import scdl as cli

STATIC_DIR = Path(__file__).with_name("static")
DEFAULT_PORT = 8770

logger = cli.logger

# UI option name -> scdl CLI flag
MODES = {
    "auto": None,
    "tracks": "-t",
    "likes": "-f",
    "reposts": "-r",
    "all": "-a",
    "playlists": "-p",
    "comments": "-C",
}
FLAG_OPTIONS = {
    "continue": "-c",
    "skip_known_drm": "--skip-known-drm",
    "write_cover": "--write-cover",
    "add_description": "--add-description",
    "no_playlist_folder": "--no-playlist-folder",
    "original_art": "--original-art",
    "extract_artist": "--extract-artist",
    "no_original": "--no-original",
    "only_original": "--only-original",
    "opus": "--opus",
    "flac": "--flac",
}
VALUE_OPTIONS = {
    "offset": "-o",
    "max_tracks": "-n",
    "min_duration": "--min-duration",
    "max_duration": "--max-duration",
    "audio_format": "--audio-format",
    "audio_quality": "--audio-quality",
    "sleep": "--sleep",
}
ITEM_RE = re.compile(r"\[download\] Downloading item (\d+) of (\d+)")


class JobCancelled(BaseException):
    """Raised from yt-dlp hooks to stop a running job (BaseException so yt-dlp doesn't swallow it)"""


class Job:
    def __init__(self, url: str, mode: str, options: dict, label: str) -> None:
        self.id = uuid.uuid4().hex[:8]
        self.url = url
        self.mode = mode
        self.label = label or url
        self.path = str(Path(os.path.expanduser(options.get("path") or default_download_dir())).resolve())
        self.argv = build_argv(url, mode, options, self.path)
        self.status = "queued"
        self.error: str | None = None
        self.created = time.time()
        self.finished: float | None = None
        self.position: tuple[int, int] | None = None
        self.items: dict[str, dict] = {}
        self.current: str | None = None
        self.files: list[str] = []
        self.log: collections.deque[str] = collections.deque(maxlen=400)
        self.cancel_requested = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "url": self.url,
            "mode": self.mode,
            "label": self.label,
            "path": self.path,
            "command": "scdl " + " ".join(_quote(a) for a in self.argv),
            "status": self.status,
            "error": self.error,
            "created": self.created,
            "finished": self.finished,
            "position": self.position,
            "items": list(self.items.values()),
            "files": self.files,
            "log": list(self.log)[-120:],
        }

    # yt-dlp hooks -----------------------------------------------------------------

    def _item(self, info: dict) -> dict:
        key = str(info.get("id") or info.get("webpage_url") or "?")
        item = self.items.get(key)
        if item is None:
            item = self.items[key] = {
                "id": key,
                "title": info.get("title") or key,
                "uploader": info.get("uploader"),
                "status": "downloading",
                "percent": 0.0,
                "speed": None,
                "eta": None,
                "file": None,
            }
        self.current = key
        return item

    def progress_hook(self, d: dict) -> None:
        if self.cancel_requested:
            raise JobCancelled
        item = self._item(d.get("info_dict") or {})
        total = d.get("total_bytes") or d.get("total_bytes_estimate")
        if d.get("status") == "downloading":
            if total:
                item["percent"] = min(100.0, 100.0 * (d.get("downloaded_bytes") or 0) / total)
            elif d.get("fragment_count"):
                item["percent"] = 100.0 * (d.get("fragment_index") or 0) / d["fragment_count"]
            item["speed"] = d.get("speed")
            item["eta"] = d.get("eta")
            item["status"] = "downloading"
        elif d.get("status") == "finished":
            item.update(percent=100.0, speed=None, eta=None, status="processing")
        elif d.get("status") == "error":
            item["status"] = "error"

    def postprocessor_hook(self, d: dict) -> None:
        if self.cancel_requested:
            raise JobCancelled
        if d.get("status") == "started" and self.current in self.items:
            self.items[self.current]["status"] = "processing"

    def post_hook(self, filename: str) -> None:
        self.files.append(filename)
        if self.current in self.items:
            self.items[self.current].update(status="done", file=filename, percent=100.0)


class JobLogHandler(logging.Handler):
    def __init__(self, job: Job) -> None:
        super().__init__(logging.INFO)
        self.job = job

    def emit(self, record: logging.LogRecord) -> None:
        if self.job.cancel_requested:
            raise JobCancelled
        msg = record.getMessage()
        if record.levelno >= logging.ERROR and not msg.startswith("ERROR"):
            msg = "ERROR: " + msg
        self.job.log.append(msg)
        m = ITEM_RE.search(msg)
        if m:
            self.job.position = (int(m.group(1)), int(m.group(2)))


class JobManager:
    def __init__(self) -> None:
        self.jobs: dict[str, Job] = {}
        self.queue: queue.Queue[Job] = queue.Queue()
        self.lock = threading.Lock()
        threading.Thread(target=self._worker, daemon=True, name="scdl-worker").start()

    def add(self, job: Job) -> Job:
        with self.lock:
            self.jobs[job.id] = job
        self.queue.put(job)
        return job

    def list(self) -> list[dict]:
        with self.lock:
            jobs = sorted(self.jobs.values(), key=lambda j: j.created, reverse=True)
        return [j.to_dict() for j in jobs]

    def cancel(self, job_id: str) -> bool:
        job = self.jobs.get(job_id)
        if job is None or job.status not in ("queued", "running"):
            return False
        job.cancel_requested = True
        if job.status == "queued":
            job.status = "cancelled"
            job.finished = time.time()
        return True

    def clear_finished(self) -> None:
        with self.lock:
            self.jobs = {k: j for k, j in self.jobs.items() if j.status in ("queued", "running")}

    def _worker(self) -> None:
        while True:
            job = self.queue.get()
            if job.status == "cancelled":
                continue
            self._run(job)

    def _run(self, job: Job) -> None:
        job.status = "running"
        handler = JobLogHandler(job)
        logger.addHandler(handler)
        try:
            Path(job.path).mkdir(parents=True, exist_ok=True)
            url, scdl_args = cli.parse_args(job.argv)
            cli.download_url(
                url,
                ydl_opts={
                    "progress_hooks": [job.progress_hook],
                    "postprocessor_hooks": [job.postprocessor_hook],
                    "post_hooks": [job.post_hook],
                },
                **scdl_args,
            )
            job.status = "done"
        except JobCancelled:
            job.status = "cancelled"
        except SystemExit:
            job.status = "error"
            job.error = _last_error(job) or "scdl terminó con error (ver log)"
        except Exception as err:
            job.status = "error"
            job.error = str(err)
        finally:
            logger.removeHandler(handler)
            job.finished = time.time()
            for item in job.items.values():
                if item["status"] in ("downloading", "processing"):
                    item["status"] = "error" if job.status == "error" else job.status


def _last_error(job: Job) -> str | None:
    return next((line for line in reversed(job.log) if line.startswith("ERROR")), None)


def _quote(arg: str) -> str:
    return f'"{arg}"' if (" " in arg or not arg) else arg


def default_download_dir() -> Path:
    return Path.home() / "Music" / "scdl"


def build_argv(url: str, mode: str, options: dict, path: str) -> list[str]:
    if mode not in MODES:
        raise ValueError(f"Modo desconocido: {mode}")
    argv = ["-l", url, "--path", path, "--hide-progress"]
    if MODES[mode]:
        argv.append(MODES[mode])
    for key, flag in FLAG_OPTIONS.items():
        if options.get(key):
            argv.append(flag)
    for key, flag in VALUE_OPTIONS.items():
        value = options.get(key)
        if value not in (None, ""):
            argv += [flag, str(value).strip()]
    if options.get("only_new"):
        argv += ["--download-archive", str(Path(path) / "scdl-archive.txt")]
    return argv


# SoundCloud API (search / preview) ---------------------------------------------------

_client: SoundCloud | None = None
_client_lock = threading.Lock()


def get_client() -> SoundCloud:
    global _client  # noqa: PLW0603
    with _client_lock:
        if _client is None:
            config = cli._get_config(cli.get_config_dir() / "scdl.cfg")
            token = config["scdl"]["auth_token"] or None
            client = SoundCloud(config["scdl"]["client_id"] or None, token)
            if not client.is_client_id_valid():
                client = SoundCloud(None, token)
            _client = client
        return _client


def _artwork(url: str | None, size: str = "t300x300") -> str | None:
    return url.replace("-large.", f"-{size}.") if url else None


def describe(item: object) -> dict | None:
    if isinstance(item, Track):
        return {
            "kind": "track",
            "title": item.title,
            "user": item.user.username,
            "url": item.permalink_url,
            "artwork": _artwork(item.artwork_url or item.user.avatar_url),
            "duration": (item.full_duration or item.duration or 0) / 1000,
            "plays": item.playback_count,
            "likes": item.likes_count,
            "policy": item.policy,
            "downloadable": item.downloadable,
        }
    if isinstance(item, AlbumPlaylist):
        return {
            "kind": "album" if item.is_album else "playlist",
            "title": item.title,
            "user": item.user.username,
            "url": item.permalink_url,
            "artwork": _artwork(item.artwork_url or item.user.avatar_url),
            "duration": (item.duration or 0) / 1000,
            "track_count": item.track_count,
            "likes": item.likes_count,
        }
    if isinstance(item, User):
        return {
            "kind": "user",
            "title": item.username,
            "user": item.full_name or item.city or "",
            "url": item.permalink_url,
            "artwork": _artwork(item.avatar_url),
            "followers": item.followers_count,
            "track_count": getattr(item, "track_count", None),
            "likes_count": getattr(item, "public_favorites_count", None) or getattr(item, "likes_count", None),
            "reposts_count": getattr(item, "reposts_count", None),
            "playlist_count": getattr(item, "playlist_count", None),
            "comments_count": getattr(item, "comments_count", None),
        }
    return None


def search(query: str, limit: int) -> list[dict]:
    results = []
    for item in get_client().search(query, limit=limit):
        info = describe(item)
        if info:
            results.append(info)
        if len(results) >= limit:
            break
    return results


def resolve(url: str) -> dict | None:
    url = cli._resolve_short_url(url.strip())
    info = describe(get_client().resolve(url))
    if info:
        info["url"] = info["url"] or url
    return info


# HTTP ------------------------------------------------------------------------------------


class Handler(SimpleHTTPRequestHandler):
    manager: JobManager
    allowed_hosts: set[str]
    # the Windows registry sometimes maps .js to text/plain, which breaks ES modules
    extensions_map: ClassVar[dict[str, str]] = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".js": "text/javascript",
        ".css": "text/css",
        ".html": "text/html",
    }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def log_message(self, format: str, *args) -> None:
        pass

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _check_origin(self) -> bool:
        # only answer requests addressed to this local server (blocks DNS rebinding / cross-site posts)
        if self.headers.get("Host") not in self.allowed_hosts:
            return False
        origin = self.headers.get("Origin")
        return origin is None or urlparse(origin).netloc in self.allowed_hosts

    def _json(self, data: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _error(self, msg: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        self._json({"error": msg}, status)

    def do_GET(self) -> None:
        if not self._check_origin():
            return self._error("forbidden", HTTPStatus.FORBIDDEN)
        parsed = urlparse(self.path)
        qs = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        try:
            if parsed.path == "/api/config":
                return self._json(
                    {
                        "version": cli.__version__,
                        "download_dir": str(default_download_dir()),
                        "ffmpeg": shutil.which("ffmpeg") is not None,
                        "config_dir": str(cli.get_config_dir()),
                    }
                )
            if parsed.path == "/api/jobs":
                return self._json(self.manager.list())
            if parsed.path == "/api/search":
                limit = max(1, min(int(qs.get("limit", 24)), 50))
                return self._json(search(qs.get("q", ""), limit))
            if parsed.path == "/api/resolve":
                info = resolve(qs.get("url", ""))
                if info is None:
                    return self._error("No se pudo resolver la URL", HTTPStatus.NOT_FOUND)
                return self._json(info)
        except Exception as err:
            return self._error(str(err), HTTPStatus.BAD_GATEWAY)
        if parsed.path.startswith("/api/"):
            return self._error("not found", HTTPStatus.NOT_FOUND)
        return super().do_GET()

    def do_POST(self) -> None:
        if not self._check_origin():
            return self._error("forbidden", HTTPStatus.FORBIDDEN)
        if not (self.headers.get("Content-Type") or "").startswith("application/json"):
            return self._error("expected application/json", HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
        try:
            length = int(self.headers.get("Content-Length") or 0)
            data = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            return self._error("invalid json")

        path = urlparse(self.path).path
        if path == "/api/jobs":
            url = (data.get("url") or "").strip()
            if not url:
                return self._error("Falta la URL")
            try:
                job = Job(url, data.get("mode") or "auto", data.get("options") or {}, data.get("label") or "")
            except ValueError as err:
                return self._error(str(err))
            return self._json(self.manager.add(job).to_dict(), HTTPStatus.CREATED)
        if path == "/api/jobs/clear":
            self.manager.clear_finished()
            return self._json({"ok": True})
        if path == "/api/pick-folder":
            try:
                return self._json({"path": pick_folder(data.get("initial") or "")})
            except ImportError:
                return self._error("tkinter no está disponible en este Python", HTTPStatus.NOT_IMPLEMENTED)
        m = re.fullmatch(r"/api/jobs/([0-9a-f]+)/(cancel|open)", path)
        if m:
            job = self.manager.jobs.get(m.group(1))
            if job is None:
                return self._error("not found", HTTPStatus.NOT_FOUND)
            if m.group(2) == "cancel":
                return self._json({"ok": self.manager.cancel(job.id)})
            open_folder(job.path)
            return self._json({"ok": True})
        return self._error("not found", HTTPStatus.NOT_FOUND)


_dialog_lock = threading.Lock()


def pick_folder(initial: str) -> str | None:
    """Show the native folder picker (blocks the request thread until it is closed)"""
    import tkinter as tk  # noqa: PLC0415 (optional: not every Python ships tkinter)
    from tkinter import filedialog  # noqa: PLC0415

    start = Path(os.path.expanduser(initial or default_download_dir()))
    while not start.exists() and start.parent != start:
        start = start.parent
    with _dialog_lock:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)  # otherwise it can open behind the app window
        try:
            chosen = filedialog.askdirectory(parent=root, initialdir=str(start), title="Carpeta de destino")
        finally:
            root.destroy()
    return str(Path(chosen)) if chosen else None


def open_folder(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def open_app_window(url: str) -> None:
    """Open the UI in a chromeless Edge/Chrome window, falling back to the default browser"""
    candidates = [shutil.which(n) for n in ("msedge", "chrome", "google-chrome", "chromium", "chromium-browser")]
    if sys.platform == "win32":
        for base in (
            os.environ.get("PROGRAMFILES(X86)"),
            os.environ.get("PROGRAMFILES"),
            os.environ.get("LOCALAPPDATA"),
        ):
            if base:
                candidates += [
                    os.path.join(base, "Microsoft", "Edge", "Application", "msedge.exe"),
                    os.path.join(base, "Google", "Chrome", "Application", "chrome.exe"),
                ]
    for exe in candidates:
        if exe and os.path.exists(exe):
            subprocess.Popen([exe, f"--app={url}", "--window-size=1180,820"])
            return
    webbrowser.open(url)


class Server(ThreadingHTTPServer):
    # SO_REUSEADDR on Windows lets a second process bind a port that is already in use
    allow_reuse_address = sys.platform != "win32"
    daemon_threads = True


def _bind(ports: list[int]) -> Server:
    for port in ports:
        try:
            return Server(("127.0.0.1", port), Handler)
        except OSError:  # noqa: PERF203
            continue
    raise OSError("no free port")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="scdl-web", description="Interfaz web local para scdl")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-window", action="store_true", help="no abrir la ventana automáticamente")
    args = parser.parse_args(argv)

    logger.addHandler(logging.StreamHandler())

    server = _bind([*range(args.port, args.port + 10), 0])
    port = server.server_address[1]
    Handler.manager = JobManager()
    Handler.allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}

    url = f"http://127.0.0.1:{port}/"
    print(f"scdl-web {cli.__version__} escuchando en {url}  (Ctrl+C para salir)")  # noqa: T201
    if not args.no_window:
        threading.Timer(0.5, open_app_window, (url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
