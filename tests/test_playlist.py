import os
from pathlib import Path

from tests.utils import assert_not_track, assert_track, call_scdl_with_auth


def assert_track_playlist_1(
    tmp_path: Path,
    playlist_folder: str = "test playlist",
    check_metadata: bool = True,
) -> None:
    expected_name = "1_testing - test track.mp3"
    assert_track(
        tmp_path / playlist_folder,
        expected_name,
        expected_album="test playlist",
        expected_albumartist="7x11x13-testing",
        expected_tracknumber=1,
        check_metadata=check_metadata,
    )


def assert_track_playlist_2(
    tmp_path: Path,
    playlist_folder: str = "test playlist",
    check_metadata: bool = True,
) -> None:
    expected_name = "2_test track 2.mp3"
    assert_track(
        tmp_path / playlist_folder,
        expected_name,
        expected_title="test track 2",
        expected_album="test playlist",
        expected_albumartist="7x11x13-testing",
        expected_tracknumber=2,
        check_metadata=check_metadata,
    )


def test_playlist(tmp_path: Path) -> None:
    os.chdir(tmp_path)
    r = call_scdl_with_auth(
        "-l",
        "https://soundcloud.com/one-thousand-and-one/sets/test-playlist/s-ZSLfNrbPoXR",
        "--playlist-name-format",
        "{playlist[tracknumber]}_{title}",
        "--onlymp3",
    )
    assert r.returncode == 0
    assert_track_playlist_1(tmp_path)
    assert_track_playlist_2(tmp_path)


def test_n(tmp_path: Path) -> None:
    os.chdir(tmp_path)
    r = call_scdl_with_auth(
        "-l",
        "https://soundcloud.com/one-thousand-and-one/sets/test-playlist/s-ZSLfNrbPoXR",
        "--playlist-name-format",
        "{playlist[tracknumber]}_{title}",
        "--onlymp3",
        "-n",
        "1",
    )
    assert r.returncode == 0
    assert_track(tmp_path / "test playlist", "1_test track 2.mp3", check_metadata=False)
    assert_not_track(tmp_path / "test playlist", "2_testing - test track.mp3")


def test_offset(tmp_path: Path) -> None:
    os.chdir(tmp_path)
    r = call_scdl_with_auth(
        "-l",
        "https://soundcloud.com/one-thousand-and-one/sets/test-playlist/s-ZSLfNrbPoXR",
        "--playlist-name-format",
        "{playlist[tracknumber]}_{title}",
        "--onlymp3",
        "-o",
        "2",
    )
    assert r.returncode == 0
    assert_not_track(
        tmp_path / "test playlist",
        "1_testing - test track.mp3",
    )
    assert_track_playlist_2(tmp_path)


def test_no_playlist_folder(tmp_path: Path) -> None:
    os.chdir(tmp_path)
    r = call_scdl_with_auth(
        "-l",
        "https://soundcloud.com/one-thousand-and-one/sets/test-playlist/s-ZSLfNrbPoXR",
        "--playlist-name-format",
        "{playlist[tracknumber]}_{title}",
        "--onlymp3",
        "--no-playlist-folder",
    )
    assert r.returncode == 0
    assert_track_playlist_1(tmp_path, ".", False)
    assert_track_playlist_2(tmp_path, ".", False)
    assert_not_track(tmp_path / "test playlist", "1_testing - test track.mp3")
    assert_not_track(tmp_path / "test playlist", "2_test track 2.mp3")


def test_no_strict_playlist(tmp_path: Path) -> None:
    os.chdir(tmp_path)
    r = call_scdl_with_auth(
        "-l",
        "https://soundcloud.com/one-thousand-and-one/sets/test-playlist/s-ZSLfNrbPoXR",
        "--playlist-name-format",
        "{playlist[tracknumber]}_{title}",
        "--onlymp3",
        "--max-size=10kb",
    )
    assert r.returncode == 0
    assert_not_track(tmp_path / "test playlist", "1_testing - test track.mp3")
    assert_not_track(tmp_path / "test playlist", "2_test track 2.mp3")


def test_strict_playlist(tmp_path: Path) -> None:
    os.chdir(tmp_path)
    r = call_scdl_with_auth(
        "-l",
        "https://soundcloud.com/one-thousand-and-one/sets/test-playlist/s-ZSLfNrbPoXR",
        "--playlist-name-format",
        "{playlist[tracknumber]}_{title}",
        "--onlymp3",
        "--max-size=10kb",
        "--strict-playlist",
    )
    assert r.returncode == 1
    assert_not_track(tmp_path / "test playlist", "1_testing - test track.mp3")
    assert_not_track(tmp_path / "test playlist", "2_test track 2.mp3")


def test_sync(tmp_path: Path) -> None:
    os.chdir(tmp_path)
    os.makedirs("test playlist")
    r = call_scdl_with_auth(
        "-l",
        "https://soundcloud.com/7x11x13/wan-bushi-eurodance-vibes-part-123",
        "--onlymp3",
        "--name-format",
        "{title}",
        "--path",
        "test playlist",
    )
    assert r.returncode == 0
    assert_track(
        tmp_path / "test playlist",
        "Wan Bushi - Eurodance Vibes (part 1+2+3).mp3",
        check_metadata=False,
    )
    with open("archive.txt", "w", encoding="utf-8") as f:
        f.writelines(["1032303631"])
    r = call_scdl_with_auth(
        "-l",
        "https://soundcloud.com/one-thousand-and-one/sets/test-playlist/s-ZSLfNrbPoXR",
        "--playlist-name-format",
        "{title}",
        "--sync",
        "archive.txt",
    )
    assert r.returncode == 0
    assert_not_track(tmp_path / "test playlist", "Wan Bushi - Eurodance Vibes (part 1+2+3).mp3")
    with open("archive.txt") as f:
        assert f.read().split() == ["1855267053", "1855318536"]
