"""
Benchmark tests for SCDL performance monitoring.
"""

import time
import pytest
import tempfile
import subprocess
import sys
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, List


@dataclass
class BenchmarkResult:
    """Store benchmark test results."""
    test_name: str
    url: str
    duration: float
    file_size: int
    download_speed_mbps: float
    success: bool
    error_message: str = ""


class TestBenchmarks:
    """Benchmark tests for performance monitoring."""

    @pytest.fixture(autouse=True)
    def setup_benchmark_dir(self):
        """Setup temporary directory for benchmarks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.benchmark_dir = Path(tmpdir)
            yield

    def run_scdl_benchmark(self, args: List[str], test_name: str, url: str) -> BenchmarkResult:
        """Run SCDL and collect performance metrics."""
        start_time = time.time()
        
        try:
            result = subprocess.run(
                [sys.executable, "-m", "scdl"] + args,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=self.benchmark_dir
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Calculate total file size
            file_size = sum(
                f.stat().st_size 
                for f in self.benchmark_dir.rglob("*") 
                if f.is_file() and f.suffix.lower() in {'.mp3', '.flac', '.m4a', '.opus'}
            )
            
            # Calculate download speed in Mbps
            download_speed_mbps = (file_size * 8) / (duration * 1_000_000) if duration > 0 else 0
            
            return BenchmarkResult(
                test_name=test_name,
                url=url,
                duration=duration,
                file_size=file_size,
                download_speed_mbps=download_speed_mbps,
                success=result.returncode == 0,
                error_message=result.stderr if result.returncode != 0 else ""
            )
            
        except subprocess.TimeoutExpired:
            return BenchmarkResult(
                test_name=test_name,
                url=url,
                duration=300.0,
                file_size=0,
                download_speed_mbps=0.0,
                success=False,
                error_message="Timeout"
            )
        except Exception as e:
            return BenchmarkResult(
                test_name=test_name,
                url=url,
                duration=0.0,
                file_size=0,
                download_speed_mbps=0.0,
                success=False,
                error_message=str(e)
            )

    @pytest.mark.benchmark
    def test_single_track_mp3_performance(self):
        """Benchmark single track MP3 download."""
        url = "https://soundcloud.com/7x11x13-testing/testing-test-track"
        args = [
            "-l", url,
            "--path", str(self.benchmark_dir),
            "--onlymp3"
        ]
        
        result = self.run_scdl_benchmark(args, "single_track_mp3", url)
        
        # Performance assertions
        assert result.success, f"Download failed: {result.error_message}"
        assert result.duration < 60, f"Download took too long: {result.duration}s"
        assert result.file_size > 1000, f"File too small: {result.file_size} bytes"
        assert result.download_speed_mbps > 0.1, f"Download speed too slow: {result.download_speed_mbps} Mbps"
        
        # Log results for CI monitoring
        print(f"\n📊 Benchmark Results - Single Track MP3:")
        print(f"   Duration: {result.duration:.2f}s")
        print(f"   File Size: {result.file_size / 1024 / 1024:.2f}MB")
        print(f"   Speed: {result.download_speed_mbps:.2f}Mbps")

    @pytest.mark.benchmark
    @pytest.mark.slow
    def test_playlist_performance(self):
        """Benchmark playlist download performance."""
        url = "https://soundcloud.com/7x11x13-testing/sets/testing-playlist"
        args = [
            "-l", url,
            "--path", str(self.benchmark_dir),
            "--onlymp3",
            "-n", "3"  # Limit to first 3 tracks
        ]
        
        result = self.run_scdl_benchmark(args, "playlist_3_tracks", url)
        
        # Performance assertions for playlist
        assert result.success, f"Playlist download failed: {result.error_message}"
        assert result.duration < 180, f"Playlist download took too long: {result.duration}s"
        
        print(f"\n📊 Benchmark Results - Playlist (3 tracks):")
        print(f"   Duration: {result.duration:.2f}s")
        print(f"   File Size: {result.file_size / 1024 / 1024:.2f}MB")
        print(f"   Speed: {result.download_speed_mbps:.2f}Mbps")

    @pytest.mark.benchmark
    def test_format_conversion_performance(self):
        """Benchmark format conversion performance."""
        url = "https://soundcloud.com/7x11x13-testing/testing-test-track"
        
        # Test MP3 conversion
        mp3_args = ["-l", url, "--path", str(self.benchmark_dir / "mp3"), "--onlymp3"]
        mp3_result = self.run_scdl_benchmark(mp3_args, "mp3_conversion", url)
        
        # Test FLAC conversion (if available)
        flac_args = ["-l", url, "--path", str(self.benchmark_dir / "flac"), "--flac"]
        flac_result = self.run_scdl_benchmark(flac_args, "flac_conversion", url)
        
        assert mp3_result.success, f"MP3 conversion failed: {mp3_result.error_message}"
        
        print(f"\n📊 Benchmark Results - Format Conversion:")
        print(f"   MP3: {mp3_result.duration:.2f}s ({mp3_result.file_size / 1024 / 1024:.2f}MB)")
        if flac_result.success:
            print(f"   FLAC: {flac_result.duration:.2f}s ({flac_result.file_size / 1024 / 1024:.2f}MB)")

    @pytest.mark.benchmark
    def test_memory_usage_single_track(self):
        """Test memory usage during single track download."""
        import psutil
        import os
        
        url = "https://soundcloud.com/7x11x13-testing/testing-test-track"
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Run download
        args = [
            "-l", url,
            "--path", str(self.benchmark_dir),
            "--onlymp3"
        ]
        
        start_time = time.time()
        result = subprocess.run(
            [sys.executable, "-m", "scdl"] + args,
            capture_output=True,
            text=True,
            cwd=self.benchmark_dir
        )
        duration = time.time() - start_time
        
        # Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        assert result.returncode == 0, f"Download failed: {result.stderr}"
        assert memory_increase < 500, f"Memory usage too high: {memory_increase}MB increase"
        
        print(f"\n📊 Memory Usage Benchmark:")
        print(f"   Duration: {duration:.2f}s")
        print(f"   Memory increase: {memory_increase:.2f}MB")
        print(f"   Peak memory: {final_memory:.2f}MB")

    @pytest.mark.benchmark
    def test_concurrent_downloads_performance(self):
        """Test performance with concurrent downloads (simulated)."""
        urls = [
            "https://soundcloud.com/7x11x13-testing/testing-test-track",
        ]
        
        results = []
        
        # Sequential downloads for comparison
        start_time = time.time()
        for i, url in enumerate(urls):
            args = [
                "-l", url,
                "--path", str(self.benchmark_dir / f"sequential_{i}"),
                "--onlymp3"
            ]
            result = self.run_scdl_benchmark(args, f"sequential_{i}", url)
            results.append(result)
        
        total_duration = time.time() - start_time
        successful_downloads = sum(1 for r in results if r.success)
        
        assert successful_downloads > 0, "No downloads succeeded"
        
        print(f"\n📊 Concurrent Download Simulation:")
        print(f"   Total duration: {total_duration:.2f}s")
        print(f"   Successful downloads: {successful_downloads}/{len(urls)}")
        print(f"   Average per download: {total_duration/len(urls):.2f}s")

    def save_benchmark_results(self, results: List[BenchmarkResult], filename: str):
        """Save benchmark results to file for tracking over time."""
        results_data = {
            "timestamp": time.time(),
            "results": [asdict(result) for result in results]
        }
        
        results_file = Path(filename)
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=2)
        
        print(f"📁 Benchmark results saved to: {results_file}")


@pytest.mark.benchmark
class TestRegressionBenchmarks:
    """Regression tests to ensure performance doesn't degrade."""
    
    def test_download_speed_regression(self):
        """Ensure download speed doesn't regress significantly."""
        # This would ideally compare against historical data
        # For now, just ensure reasonable minimum performance
        
        with tempfile.TemporaryDirectory() as tmpdir:
            benchmark_dir = Path(tmpdir)
            
            start_time = time.time()
            result = subprocess.run([
                sys.executable, "-m", "scdl",
                "-l", "https://soundcloud.com/7x11x13-testing/testing-test-track",
                "--path", str(benchmark_dir),
                "--onlymp3"
            ], capture_output=True, text=True, cwd=benchmark_dir)
            duration = time.time() - start_time
            
            assert result.returncode == 0, f"Download failed: {result.stderr}"
            
            # Ensure reasonable performance baseline
            assert duration < 120, f"Download regression detected: {duration}s (expected < 120s)"
            
            # Check file was actually downloaded
            audio_files = list(benchmark_dir.rglob("*.mp3"))
            assert len(audio_files) >= 1, "No audio files downloaded"
            
            file_size = sum(f.stat().st_size for f in audio_files)
            assert file_size > 1000, f"Downloaded file too small: {file_size} bytes"
            
            print(f"✅ Performance baseline met: {duration:.2f}s, {file_size/1024/1024:.2f}MB")
