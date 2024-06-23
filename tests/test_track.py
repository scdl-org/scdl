import os
from pathlib import Path

from tests.utils import assert_not_track, assert_track, call_scdl_with_auth


def test_original_download(tmp_path: Path):
    os.chdir(tmp_path)
    r = call_scdl_with_auth(
        "-l",
        "https://soundcloud.com/one-thousand-and-one/test-track",
        "--name-format",
        "track",
    )
    assert r.returncode == 0
    assert_track(tmp_path, "track.wav")


def test_flac(tmp_path: Path):
    os.chdir(tmp_path)
    r = call_scdl_with_auth(
        "-l",
        "https://soundcloud.com/one-thousand-and-one/test-track",
        "--name-format",
        "track",
        "--flac",
    )
    assert r.returncode == 0
    assert_track(tmp_path, "track.flac")


def test_opus(tmp_path: Path):
    os.chdir(tmp_path)
    r = call_scdl_with_auth(
        "-l",
        "https://soundcloud.com/one-thousand-and-one/test-track",
        "--name-format",
        "track",
        "--no-original",
        "--opus",
    )
    assert r.returncode == 0
    assert_track(tmp_path, "track.opus")


def test_mp3(tmp_path: Path):
    os.chdir(tmp_path)
    r = call_scdl_with_auth(
        "-l",
        "https://soundcloud.com/one-thousand-and-one/test-track",
        "--name-format",
        "track",
        "--onlymp3",
    )
    assert r.returncode == 0
    assert_track(tmp_path, "track.mp3")


def test_unlisted_track(tmp_path: Path):
    os.chdir(tmp_path)
    r = call_scdl_with_auth(
        "-l",
        "https://soundcloud.com/one-thousand-and-one/test-track-2/s-fgLQFAzNIMP",
        "--name-format",
        "track",
        "--onlymp3",
    )
    assert r.returncode == 0
    assert_track(tmp_path, "track.mp3", "test track 2")


def test_original_art(tmp_path: Path):
    os.chdir(tmp_path)
    r = call_scdl_with_auth(
        "-l",
        "https://soundcloud.com/one-thousand-and-one/test-track",
        "--name-format",
        "track",
        "--onlymp3",
        "--original-art",
    )
    assert r.returncode == 0
    assert_track(tmp_path, "track.mp3", expected_artwork_len=3409)


def test_original_name(tmp_path: Path):
    os.chdir(tmp_path)
    r = call_scdl_with_auth(
        "-l",
        "https://soundcloud.com/one-thousand-and-one/test-track",
        "--name-format",
        "track",
        "--original-name",
    )
    assert r.returncode == 0
    assert_track(tmp_path, "original.wav", check_metadata=False)


def test_original_metadata(tmp_path: Path):
    os.chdir(tmp_path)
    r = call_scdl_with_auth(
        "-l",
        "https://soundcloud.com/one-thousand-and-one/test-track",
        "--name-format",
        "track",
        "--original-metadata",
    )
    assert r.returncode == 0
    assert_track(tmp_path, "track.wav", "og title", "og artist", "og genre", False)


def test_force_metadata(tmp_path: Path):
    os.chdir(tmp_path)
    r = call_scdl_with_auth(
        "-l",
        "https://soundcloud.com/one-thousand-and-one/test-track",
        "--name-format",
        "track",
        "--original-metadata",
    )
    assert r.returncode == 0
    assert_track(tmp_path, "track.wav", "og title", "og artist", "og genre", False)

    r = call_scdl_with_auth(
        "-l",
        "https://soundcloud.com/one-thousand-and-one/test-track",
        "--name-format",
        "track",
        "--force-metadata",
    )
    assert_track(tmp_path, "track.wav")


def test_addtimestamp(tmp_path: Path):
    os.chdir(tmp_path)
    r = call_scdl_with_auth(
        "-l",
        "https://soundcloud.com/one-thousand-and-one/test-track",
        "--onlymp3",
        "--addtimestamp",
    )
    assert r.returncode == 0
    assert_track(tmp_path, "1719169486_testing - test track.mp3", check_metadata=False)


def test_addtofile(tmp_path: Path):
    os.chdir(tmp_path)
    r = call_scdl_with_auth(
        "-l",
        "https://soundcloud.com/one-thousand-and-one/test-track-2/s-fgLQFAzNIMP",
        "--onlymp3",
        "--addtofile",
    )
    assert r.returncode == 0
    assert_track(tmp_path, "7x11x13-testing - test track 2.mp3", check_metadata=False)


def test_extract_artist(tmp_path: Path):
    os.chdir(tmp_path)
    r = call_scdl_with_auth(
        "-l",
        "https://soundcloud.com/one-thousand-and-one/test-track",
        "--onlymp3",
        "--name-format",
        "track",
        "--extract-artist",
    )
    assert r.returncode == 0
    assert_track(tmp_path, "track.mp3", "test track", "testing")


def test_maxsize(tmp_path: Path):
    os.chdir(tmp_path)
    r = call_scdl_with_auth(
        "-l",
        "https://soundcloud.com/one-thousand-and-one/test-track",
        "--onlymp3",
        "--max-size=10kb",
    )
    assert r.returncode == 1
    assert "not within --min-size and --max-size bounds" in r.stderr


def test_minsize(tmp_path: Path):
    os.chdir(tmp_path)
    r = call_scdl_with_auth(
        "-l",
        "https://soundcloud.com/one-thousand-and-one/test-track",
        "--onlymp3",
        "--min-size=1mb",
    )
    assert r.returncode == 1
    assert "not within --min-size and --max-size bounds" in r.stderr


def test_only_original(tmp_path: Path):
    os.chdir(tmp_path)
    r = call_scdl_with_auth(
        "-l",
        "https://soundcloud.com/one-thousand-and-one/test-track-2/s-fgLQFAzNIMP",
        "--only-original",
    )
    assert r.returncode == 1
    assert "does not have original file available" in r.stderr


def test_overwrite(tmp_path: Path):
    os.chdir(tmp_path)
    r = call_scdl_with_auth(
        "-l",
        "https://soundcloud.com/one-thousand-and-one/test-track",
        "--name-format",
        "track",
        "--onlymp3",
    )
    assert r.returncode == 0

    r = call_scdl_with_auth(
        "-l",
        "https://soundcloud.com/one-thousand-and-one/test-track",
        "--name-format",
        "track",
        "--onlymp3",
    )
    assert r.returncode == 1
    assert "already exists" in r.stderr

    r = call_scdl_with_auth(
        "-l",
        "https://soundcloud.com/one-thousand-and-one/test-track",
        "--name-format",
        "track",
        "--onlymp3",
        "--overwrite",
    )
    assert r.returncode == 0


def test_path(tmp_path: Path):
    r = call_scdl_with_auth(
        "-l",
        "https://soundcloud.com/one-thousand-and-one/test-track",
        "--name-format",
        "track",
        "--onlymp3",
        "--path",
        str(tmp_path),
    )
    assert r.returncode == 0
    assert_track(tmp_path, "track.mp3", check_metadata=False)


def test_remove(tmp_path: Path):
    os.chdir(tmp_path)
    r = call_scdl_with_auth(
        "-l",
        "https://soundcloud.com/one-thousand-and-one/test-track",
        "--name-format",
        "track",
        "--onlymp3",
    )
    assert r.returncode == 0
    assert_track(tmp_path, "track.mp3", check_metadata=False)
    r = call_scdl_with_auth(
        "-l",
        "https://soundcloud.com/one-thousand-and-one/test-track",
        "--name-format",
        "track",
        "--remove",
    )
    assert r.returncode == 0
    assert_track(tmp_path, "track.wav", check_metadata=False)
    assert_not_track(tmp_path, "track.mp3")
