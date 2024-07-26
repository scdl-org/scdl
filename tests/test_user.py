import os
from pathlib import Path

from tests.utils import assert_track, call_scdl_with_auth


def count_files(folder: Path) -> int:
    return len(list(folder.rglob("*")))


def test_all(tmp_path: Path) -> None:
    os.chdir(tmp_path)
    r = call_scdl_with_auth(
        "-l",
        "https://soundcloud.com/one-thousand-and-one",
        "-a",
        "-o",
        "3",
        "--onlymp3",
    )
    assert r.returncode == 0
    assert count_files(tmp_path) == 3


def test_tracks(tmp_path: Path) -> None:
    os.chdir(tmp_path)
    r = call_scdl_with_auth(
        "-l",
        "https://soundcloud.com/one-thousand-and-one",
        "-t",
        "--name-format=track",
        "--onlymp3",
    )
    assert r.returncode == 0
    assert_track(tmp_path, "track.mp3")
    assert count_files(tmp_path) == 1


def test_likes(tmp_path: Path) -> None:
    os.chdir(tmp_path)
    r = call_scdl_with_auth(
        "-l",
        "https://soundcloud.com/one-thousand-and-one",
        "-f",
        "--onlymp3",
        "--name-format={title}",
    )
    assert r.returncode == 0
    assert_track(tmp_path, "Wan Bushi - Eurodance Vibes (part 1+2+3).mp3", check_metadata=False)
    assert count_files(tmp_path) == 1


def test_commented(tmp_path: Path) -> None:
    os.chdir(tmp_path)
    r = call_scdl_with_auth(
        "-l",
        "https://soundcloud.com/one-thousand-and-one",
        "-C",
        "--onlymp3",
        "--name-format={title}",
    )
    assert r.returncode == 0
    assert_track(tmp_path, "Wan Bushi - Eurodance Vibes (part 1+2+3).mp3", check_metadata=False)
    assert count_files(tmp_path) == 1


def test_playlists(tmp_path: Path) -> None:
    os.chdir(tmp_path)
    r = call_scdl_with_auth(
        "-l",
        "https://soundcloud.com/one-thousand-and-one",
        "-p",
        "--onlymp3",
    )
    assert r.returncode == 0
    assert count_files(tmp_path) == 3


def test_reposts(tmp_path: Path) -> None:
    os.chdir(tmp_path)
    r = call_scdl_with_auth(
        "-l",
        "https://soundcloud.com/one-thousand-and-one",
        "-r",
        "--name-format={title}",
        "--onlymp3",
    )
    assert r.returncode == 0
    assert_track(tmp_path, "Wan Bushi - Eurodance Vibes (part 1+2+3).mp3", check_metadata=False)
    assert count_files(tmp_path) == 1
