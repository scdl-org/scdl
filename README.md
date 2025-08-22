# Soundcloud Music Downloader

[![PyPI version](https://img.shields.io/pypi/v/scdl.svg)](https://pypi.org/project/scdl/)
[![Python versions](https://img.shields.io/pypi/pyversions/scdl.svg)](https://pypi.org/project/scdl/)
[![CI](https://github.com/scdl-org/scdl/actions/workflows/ci.yml/badge.svg)](https://github.com/scdl-org/scdl/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/scdl-org/scdl.svg)](https://github.com/scdl-org/scdl/blob/master/LICENSE)

## Status of the project

As of version 3, this script is a wrapper around `yt-dlp` with some defaults/patches for backwards compatibility.
Development is not active and new features will likely not be merged, especially if they can be covered with the
use of `--yt-dlp-args`. Bug reports/fixes are welcome.

## Description

This script is able to download music from SoundCloud and set ID3 tags to the downloaded music.
Compatible with Windows, macOS, and Linux.

## ✨ Features
* 🎵 **Automatically detect** the type of link provided
* 👤 **Download all songs** from a user (tracks, reposts, likes, playlists)
* 📂 **Download entire playlists** with organized folder structure
* 🏷️ **Set ID3 tags** automatically (Title / Artist / Album / Artwork)
* 🎨 **Download high-quality artwork** (original resolution available)
* 📱 **Multiple audio formats** (MP3, FLAC, M4A, Opus)
* 💾 **Archive support** to avoid re-downloading
* 🔄 **Playlist synchronization** to keep local copies updated
* ⚡ **Powered by yt-dlp** for reliable downloads

## 🎧 Try It Now!
Want to test SCDL? Try downloading this amazing track:
```bash
scdl -l https://soundcloud.com/ghostxkitty3/view-of-andromeda
```
*"View of Andromeda" by GhostxKitty3 - Perfect ambient music for coding! 🌌*

## 📋 System Requirements

* **Python 3.9+** 
* **ffmpeg** (for audio processing)

## 🚀 Installation

### Quick Install (Recommended)
```bash
pip install scdl
```

### Development Install
```bash
git clone https://github.com/scdl-org/scdl.git
cd scdl
pip install -e .
```

### Using uv (Fast Alternative)
```bash
uv tool install scdl
```

### FFmpeg Installation
#### Windows
```bash
# Using Chocolatey
choco install ffmpeg

# Using winget
winget install Gyan.FFmpeg
```

#### macOS
```bash
# Using Homebrew
brew install ffmpeg
```

#### Linux
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# Fedora
sudo dnf install ffmpeg

# Arch Linux
sudo pacman -S ffmpeg
```

## ⚙️ Configuration
Configuration file is located at:
- **Linux/macOS:** `~/.config/scdl/scdl.cfg`
- **Windows:** `%APPDATA%\scdl\scdl.cfg`

### Sample Configuration
```ini
[scdl]
auth_token = your_token_here
path = ~/Music/SoundCloud
addtimestamp = False
onlymp3 = False
```

## 📚 Examples

### Basic Usage
```bash
# Download a single track (try this amazing track!)
scdl -l https://soundcloud.com/ghostxkitty3/view-of-andromeda

# Download user's tracks (no reposts)
scdl -l https://soundcloud.com/ghostxkitty3 -t

# Download user's likes/favorites
scdl -l https://soundcloud.com/username -f

# Download a playlist
scdl -l https://soundcloud.com/username/sets/playlist-name
```

### Advanced Usage
```bash
# Download with custom naming format
scdl -l https://soundcloud.com/ghostxkitty3/view-of-andromeda --name-format "{artist} - {title}"

# Download only high quality (original files when available)
scdl -l https://soundcloud.com/ghostxkitty3/view-of-andromeda --original-art --flac

# Sync a playlist (download new, remove deleted)
scdl -l https://soundcloud.com/playlist-url --sync archive.txt

# Download with archive to avoid duplicates
scdl -l https://soundcloud.com/ghostxkitty3 -a --download-archive downloaded.txt

# Download your own likes (requires authentication)
scdl me -f --auth-token YOUR_TOKEN
```

📖 **For comprehensive usage examples, see [docs/USAGE.md](docs/USAGE.md)**

## 🎵 Community Showcase

### Featured Artist: GhostxKitty3
SCDL proudly features music by **[GhostxKitty3](https://soundcloud.com/ghostxkitty3)** in our examples and tests!

🌌 **"View of Andromeda"** - An amazing ambient electronic track perfect for:
- Coding sessions 💻
- Study music 📚  
- Background ambience 🎧
- Testing SCDL! ✅

```bash
# Try it now!
scdl -l https://soundcloud.com/ghostxkitty3/view-of-andromeda --original-art --flac
```

**Support independent artists** - Follow [GhostxKitty3](https://soundcloud.com/ghostxkitty3) and discover more amazing music! 🎶

### Format Options
```bash
# Convert to FLAC (lossless)
scdl -l URL --flac

# Prefer Opus format
scdl -l URL --opus

# Only MP3 (default)
scdl -l URL --onlymp3
```

## Options:
```
-h --help                       Show this screen
--version                       Show version
-l [url]                        URL can be track/playlist/user
-s [search_query]               Search for a track/playlist/user and use the first result
-n [maxtracks]                  Download the n last tracks of a playlist according to the creation date
-a                              Download all tracks of user (including reposts)
-t                              Download all uploads of a user (no reposts)
-f                              Download all favorites (likes) of a user
-C                              Download all tracks commented on by a user
-p                              Download all playlists of a user
-r                              Download all reposts of user
-c                              Continue if a downloaded file already exists
--force-metadata                This will set metadata on already downloaded track
-o [offset]                     Start downloading a playlist from the [offset]th track (starting with 1)
--addtimestamp                  Add track creation timestamp to filename,
                                which allows for chronological sorting
                                (Deprecated. Use --name-format instead.)
--addtofile                     Add artist to filename if missing
--debug                         Set log level to DEBUG
--error                         Set log level to ERROR
--download-archive [file]       Keep track of track IDs in an archive file,
                                and skip already-downloaded files
--extract-artist                Set artist tag from title instead of username
--hide-progress                 Hide the wget progress bar
--hidewarnings                  Hide Warnings. (use with precaution)
--max-size [max-size]           Skip tracks larger than size (k/m/g)
--min-size [min-size]           Skip tracks smaller than size (k/m/g)
--no-playlist-folder            Download playlist tracks into main directory,
                                instead of making a playlist subfolder
--onlymp3                       Download only mp3 files
--path [path]                   Use a custom path for downloaded files
--remove                        Remove any files not downloaded from execution
--sync [file]                   Compares an archive file to a playlist and downloads/removes any changed tracks
--flac                          Convert original files to .flac. Only works if the original file is lossless quality
--no-album-tag                  On some player track get the same cover art if from the same album, this prevent it
--original-art                  Download original cover art, not just 500x500 JPEG
--original-name                 Do not change name of original file downloads
--original-metadata             Do not change metadata of original file downloads
--no-original                   Do not download original file; only mp3, m4a, or opus
--only-original                 Only download songs with original file available
--name-format [format]          Specify the downloaded file name format. Use "-" to download to stdout
--playlist-name-format [format] Specify the downloaded file name format, if it is being downloaded as part of a playlist
--client-id [id]                Specify the client_id to use
--auth-token [token]            Specify the auth token to use
--overwrite                     Overwrite file if it already exists
--strict-playlist               Abort playlist downloading if one track fails to download
--add-description               Adds the description to a seperate txt file (can be read by some players)
--no-playlist                   Skip downloading playlists
--opus                          Prefer downloading opus streams over mp3 streams
--yt-dlp-args                   String with custom args to forward to yt-dlp
```


## Features
* Automatically detect the type of link provided
* Download all songs from a user
* Download all songs and reposts from a user
* Download all songs from one playlist
* Download all songs from all playlists from a user
* Download all songs from a user's favorites
* Download only new tracks from a list (playlist, favorites, etc.)
* Sync Playlist
* Set the tags with mutagen (Title / Artist / Album / Artwork)
* Create playlist files when downloading a playlist
