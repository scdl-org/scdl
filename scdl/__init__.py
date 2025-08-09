"""Python Soundcloud Music Downloader."""

from . import patches  # noqa: F401, I001
from scdl.scdl import download_url

__all__ = ["download_url"]
