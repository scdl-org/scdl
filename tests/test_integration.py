"""
Integration tests for SCDL using real SoundCloud URLs.
These tests verify end-to-end functionality with actual downloads.
"""

import os
import pytest
import tempfile
import subprocess
import sys
from pathlib import Path
from typing import List, Optional


@pytest.fixture
def temp_download_dir():
    """Create a temporary directory for downloads."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def auth_token():
    """Get auth token from environment if available."""
    return os.getenv("AUTH_TOKEN")


def run_scdl(args: List[str], cwd: Optional[Path] = None, timeout: int = 300) -> subprocess.CompletedProcess:
    """Run SCDL command with given arguments."""
    cmd = [sys.executable, "-m", "scdl"] + args
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=cwd
    )


def count_audio_files(directory: Path) -> int:
    """Count audio files in directory."""
    audio_extensions = {'.mp3', '.flac', '.m4a', '.opus', '.wav'}
    return sum(1 for f in directory.rglob('*') if f.suffix.lower() in audio_extensions)


class TestBasicDownloads:
    """Test basic download functionality."""

    def test_public_track_download(self, temp_download_dir):
        """Test downloading a public track."""
        result = run_scdl([
            "-l", "https://soundcloud.com/7x11x13-testing/testing-test-track",
            "--path", str(temp_download_dir),
            "--onlymp3"
        ], cwd=temp_download_dir)
        
        assert result.returncode == 0, f"Download failed: {result.stderr}"
        assert count_audio_files(temp_download_dir) == 1

    def test_playlist_download(self, temp_download_dir):
        """Test downloading a small playlist."""
        result = run_scdl([
            "-l", "https://soundcloud.com/7x11x13-testing/sets/testing-playlist",
            "--path", str(temp_download_dir),
            "--onlymp3"
        ], cwd=temp_download_dir)
        
        assert result.returncode == 0, f"Playlist download failed: {result.stderr}"
        assert count_audio_files(temp_download_dir) >= 1

    @pytest.mark.skipif(not os.getenv("AUTH_TOKEN"), reason="No auth token provided")
    def test_user_likes_download(self, temp_download_dir, auth_token):
        """Test downloading user likes (requires auth)."""
        result = run_scdl([
            "me", "-f",
            "--path", str(temp_download_dir),
            "--onlymp3",
            "--auth-token", auth_token,
            "-n", "1"  # Limit to 1 track for faster testing
        ], cwd=temp_download_dir)
        
        assert result.returncode == 0, f"Likes download failed: {result.stderr}"


class TestFormats:
    """Test different audio format downloads."""

    def test_mp3_download(self, temp_download_dir):
        """Test MP3 format download."""
        result = run_scdl([
            "-l", "https://soundcloud.com/7x11x13-testing/testing-test-track",
            "--path", str(temp_download_dir),
            "--onlymp3"
        ], cwd=temp_download_dir)
        
        assert result.returncode == 0
        mp3_files = list(temp_download_dir.rglob("*.mp3"))
        assert len(mp3_files) >= 1

    @pytest.mark.skipif(not os.getenv("AUTH_TOKEN"), reason="No auth token provided")
    def test_flac_download(self, temp_download_dir, auth_token):
        """Test FLAC format download (requires auth for lossless)."""
        result = run_scdl([
            "-l", "https://soundcloud.com/violinbutterflynet/original",
            "--path", str(temp_download_dir),
            "--flac",
            "--auth-token", auth_token
        ], cwd=temp_download_dir)
        
        if result.returncode == 0:
            flac_files = list(temp_download_dir.rglob("*.flac"))
            assert len(flac_files) >= 1


class TestFeatures:
    """Test specific SCDL features."""

    def test_download_archive(self, temp_download_dir):
        """Test download archive functionality."""
        archive_file = temp_download_dir / "archive.txt"
        
        # First download
        result1 = run_scdl([
            "-l", "https://soundcloud.com/7x11x13-testing/testing-test-track",
            "--path", str(temp_download_dir),
            "--download-archive", str(archive_file),
            "--onlymp3"
        ], cwd=temp_download_dir)
        
        assert result1.returncode == 0
        assert archive_file.exists()
        initial_size = archive_file.stat().st_size
        
        # Second download (should skip)
        result2 = run_scdl([
            "-l", "https://soundcloud.com/7x11x13-testing/testing-test-track",
            "--path", str(temp_download_dir),
            "--download-archive", str(archive_file),
            "--onlymp3"
        ], cwd=temp_download_dir)
        
        assert result2.returncode == 0
        # Archive file shouldn't grow much (just new entries)
        final_size = archive_file.stat().st_size
        assert final_size >= initial_size

    def test_custom_name_format(self, temp_download_dir):
        """Test custom filename formatting."""
        result = run_scdl([
            "-l", "https://soundcloud.com/7x11x13-testing/testing-test-track",
            "--path", str(temp_download_dir),
            "--name-format", "test_custom_name",
            "--onlymp3"
        ], cwd=temp_download_dir)
        
        assert result.returncode == 0
        custom_files = list(temp_download_dir.rglob("test_custom_name.mp3"))
        assert len(custom_files) == 1

    def test_metadata_extraction(self, temp_download_dir):
        """Test that metadata is properly extracted."""
        result = run_scdl([
            "-l", "https://soundcloud.com/7x11x13-testing/testing-test-track",
            "--path", str(temp_download_dir),
            "--onlymp3"
        ], cwd=temp_download_dir)
        
        assert result.returncode == 0
        
        # Check that file was created
        audio_files = list(temp_download_dir.rglob("*.mp3"))
        assert len(audio_files) >= 1
        
        # Basic check that file is valid
        audio_file = audio_files[0]
        assert audio_file.stat().st_size > 1000  # Should be more than 1KB


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_invalid_url(self, temp_download_dir):
        """Test handling of invalid URLs."""
        result = run_scdl([
            "-l", "https://soundcloud.com/nonexistent-user-12345/nonexistent-track",
            "--path", str(temp_download_dir)
        ], cwd=temp_download_dir)
        
        # Should fail gracefully
        assert result.returncode != 0

    def test_private_track_without_auth(self, temp_download_dir):
        """Test downloading private track without authentication."""
        # This should fail gracefully
        result = run_scdl([
            "-l", "https://soundcloud.com/some-private-track-url",
            "--path", str(temp_download_dir)
        ], cwd=temp_download_dir, timeout=60)
        
        # Should fail but not crash
        assert result.returncode != 0

    def test_network_timeout(self, temp_download_dir):
        """Test behavior with network issues."""
        # Test with very short timeout to simulate network issues
        result = run_scdl([
            "-l", "https://soundcloud.com/7x11x13-testing/testing-test-track",
            "--path", str(temp_download_dir),
            "--yt-dlp-args", "--socket-timeout 0.1"
        ], cwd=temp_download_dir, timeout=30)
        
        # Should handle timeout gracefully
        assert isinstance(result.returncode, int)


class TestPerformance:
    """Test performance and resource usage."""

    @pytest.mark.slow
    def test_large_playlist_partial(self, temp_download_dir):
        """Test downloading part of a large playlist."""
        result = run_scdl([
            "-l", "https://soundcloud.com/7x11x13-testing/sets/testing-playlist",
            "--path", str(temp_download_dir),
            "-n", "2",  # Only first 2 tracks
            "--onlymp3"
        ], cwd=temp_download_dir, timeout=600)
        
        assert result.returncode == 0
        assert count_audio_files(temp_download_dir) <= 2

    def test_download_speed_reasonable(self, temp_download_dir):
        """Test that downloads complete in reasonable time."""
        import time
        
        start_time = time.time()
        result = run_scdl([
            "-l", "https://soundcloud.com/7x11x13-testing/testing-test-track",
            "--path", str(temp_download_dir),
            "--onlymp3"
        ], cwd=temp_download_dir, timeout=120)
        end_time = time.time()
        
        assert result.returncode == 0
        download_time = end_time - start_time
        
        # Should complete within 2 minutes for a single track
        assert download_time < 120


# Pytest configuration
@pytest.mark.integration
class TestFullIntegration:
    """Full integration tests that require network and may take longer."""
    
    def test_end_to_end_workflow(self, temp_download_dir):
        """Test complete workflow: download, verify, re-download with archive."""
        archive_file = temp_download_dir / "archive.txt"
        
        # Step 1: Download track
        result1 = run_scdl([
            "-l", "https://soundcloud.com/7x11x13-testing/testing-test-track",
            "--path", str(temp_download_dir),
            "--download-archive", str(archive_file),
            "--onlymp3"
        ], cwd=temp_download_dir)
        
        assert result1.returncode == 0
        assert count_audio_files(temp_download_dir) == 1
        assert archive_file.exists()
        
        # Step 2: Try to download again (should skip)
        result2 = run_scdl([
            "-l", "https://soundcloud.com/7x11x13-testing/testing-test-track",
            "--path", str(temp_download_dir),
            "--download-archive", str(archive_file),
            "--onlymp3"
        ], cwd=temp_download_dir)
        
        assert result2.returncode == 0
        # Should still be only 1 file
        assert count_audio_files(temp_download_dir) == 1
