#!/usr/bin/env python3
"""
Performance monitoring script for SCDL downloads.
Tracks download speed, file sizes, and error rates.
"""

import time
import json
import argparse
from pathlib import Path
from typing import Dict, Any
from dataclasses import dataclass, asdict
import subprocess
import sys

@dataclass
class DownloadMetrics:
    """Metrics collected during download."""
    url: str
    start_time: float
    end_time: float
    duration: float
    file_size: int
    success: bool
    error_message: str = ""
    
    @property
    def download_speed(self) -> float:
        """Calculate download speed in MB/s."""
        if self.duration > 0 and self.file_size > 0:
            return (self.file_size / 1024 / 1024) / self.duration
        return 0.0

def run_scdl_download(url: str, output_dir: Path) -> DownloadMetrics:
    """Run SCDL download and collect metrics."""
    start_time = time.time()
    
    try:
        # Run SCDL command
        cmd = [
            sys.executable, "-m", "scdl",
            "-l", url,
            "--path", str(output_dir),
            "--onlymp3"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Calculate file size
        file_size = 0
        for file_path in output_dir.rglob("*"):
            if file_path.is_file():
                file_size += file_path.stat().st_size
        
        success = result.returncode == 0
        error_message = result.stderr if not success else ""
        
        return DownloadMetrics(
            url=url,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            file_size=file_size,
            success=success,
            error_message=error_message
        )
        
    except subprocess.TimeoutExpired:
        end_time = time.time()
        return DownloadMetrics(
            url=url,
            start_time=start_time,
            end_time=end_time,
            duration=end_time - start_time,
            file_size=0,
            success=False,
            error_message="Download timeout"
        )
    except Exception as e:
        end_time = time.time()
        return DownloadMetrics(
            url=url,
            start_time=start_time,
            end_time=end_time,
            duration=end_time - start_time,
            file_size=0,
            success=False,
            error_message=str(e)
        )

def main():
    """Main performance monitoring function."""
    parser = argparse.ArgumentParser(description="Monitor SCDL performance")
    parser.add_argument("urls", nargs="+", help="SoundCloud URLs to test")
    parser.add_argument("--output-dir", "-o", type=Path, default=Path("./perf_test"), 
                       help="Output directory for downloads")
    parser.add_argument("--results-file", "-r", type=Path, default=Path("./performance_results.json"),
                       help="JSON file to save results")
    
    args = parser.parse_args()
    
    # Create output directory
    args.output_dir.mkdir(exist_ok=True)
    
    results = []
    
    print(f"Testing {len(args.urls)} URLs...")
    
    for i, url in enumerate(args.urls, 1):
        print(f"[{i}/{len(args.urls)}] Testing {url}...")
        
        # Create subdirectory for this test
        test_dir = args.output_dir / f"test_{i}"
        test_dir.mkdir(exist_ok=True)
        
        # Run download and collect metrics
        metrics = run_scdl_download(url, test_dir)
        results.append(asdict(metrics))
        
        # Print results
        if metrics.success:
            print(f"  ✅ Success: {metrics.file_size/1024/1024:.1f}MB in {metrics.duration:.1f}s "
                  f"({metrics.download_speed:.1f}MB/s)")
        else:
            print(f"  ❌ Failed: {metrics.error_message}")
    
    # Save results
    with open(args.results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    successful = [r for r in results if r['success']]
    print(f"\n📊 Summary:")
    print(f"  Total tests: {len(results)}")
    print(f"  Successful: {len(successful)}")
    print(f"  Failed: {len(results) - len(successful)}")
    
    if successful:
        avg_speed = sum(r['download_speed'] for r in successful) / len(successful)
        avg_duration = sum(r['duration'] for r in successful) / len(successful)
        print(f"  Average speed: {avg_speed:.1f}MB/s")
        print(f"  Average duration: {avg_duration:.1f}s")
    
    print(f"\nResults saved to: {args.results_file}")

if __name__ == "__main__":
    main()
