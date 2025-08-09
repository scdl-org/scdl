# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- This changelog file

### Fixed

- Make `--sync` method work as intended

### Changed

- Use [yt-dlp](https://github.com/yt-dlp/yt-dlp/) to download and process tracks
- Store description in "comment" tag instead of "description" tag for Ogg/FLAC files
- Change default track format string to include track artist and ID
- Drop `termcolor`, `requests`, `tqdm`, `pathvalidate`, `filelock` dependencies
- Switch to `pyproject.toml` instead of `setup.py`
- **Breaking:** Change `--sync` file format to include downloaded filenames

### Removed

- **Breaking:** Remove `--remove`
- **Breaking:** Remove `-n`
- **Breaking:** Drop support for Python 3.7 and 3.8
- **Breaking:** When writing to stdout, files no longer contain metadata

[unreleased]: https://github.com/scdl-org/scdl/compare/v2.12.3...HEAD
