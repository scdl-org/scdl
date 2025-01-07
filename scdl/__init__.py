"""Python Soundcloud Music Downloader."""

from scdl.scdl import download_url

from . import patches  # noqa: F401

__version__ = "v3.0.0"

__all__ = ["download_url"]
