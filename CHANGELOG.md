# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0] - 2025-08-21

### Added
- Complete migration to yt-dlp as backend
- Improved error handling and logging
- Better support for various audio formats (FLAC, Opus, M4A)
- Enhanced metadata handling with mutagen

### Changed
- **BREAKING**: Now requires Python 3.9+ 
- Rewrote core functionality as yt-dlp wrapper
- Updated all dependencies to latest versions
- Improved command-line interface consistency

### Deprecated
- `--addtimestamp` option (use `--name-format` instead)

### Fixed
- Various authentication issues
- Improved playlist downloading reliability
- Better handling of private tracks

### Security
- Updated all dependencies to latest secure versions
- Improved token handling

## [2.12.4] - Previous Release
- Fixed CI issues
- Various bug fixes

## [2.12.3] - Previous Release  
- Fix aac transcoding priority
- Compatibility improvements

## [2.12.2] - Previous Release
- Fix typecheck for Python 3.7
- Code quality improvements

---

For older versions, please check the git history.
