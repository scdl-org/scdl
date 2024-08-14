import os
import secrets
from pathlib import Path

from tests.utils import assert_track, call_scdl_with_auth


def test_search(tmp_path: Path) -> None:
    os.chdir(tmp_path)
    r = call_scdl_with_auth(
        "-s",
        "7x11x13-testing test track",
        "--name-format",
        "track",
        "--onlymp3",
    )
    assert r.returncode == 0
    assert_track(tmp_path, "track.mp3")


def test_search_no_results(tmp_path: Path) -> None:
    os.chdir(tmp_path)
    r = call_scdl_with_auth(
        "-s",
        f"this query should not return any results {secrets.token_hex(16)}",
        "--name-format",
        "track",
        "--onlymp3",
    )
    assert r.returncode == 1
    assert "No results found for query" in r.stderr


def test_search_playlist(tmp_path: Path) -> None:
    os.chdir(tmp_path)
    r = call_scdl_with_auth(
        "-s",
        "playlist1 7x11x13-testing",
        "--playlist-name-format",
        "{playlist[tracknumber]}_{title}",
        "--onlymp3",
    )
    assert r.returncode == 0
    assert_track(tmp_path / "playlist1", "1_OK Bye.mp3", check_metadata=False)
    assert_track(
        tmp_path / "playlist1",
        "2_Wan Bushi - Eurodance Vibes (part 1+2+3).mp3",
        check_metadata=False,
    )
