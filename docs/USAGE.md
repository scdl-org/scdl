# 🎵 SCDL Complete Usage Guide

Welcome to the comprehensive usage guide for SCDL (SoundCloud Downloader)! This guide covers everything from basic downloads to advanced automation.

## 🚀 Quick Start

### Test SCDL with a Featured Track
```bash
# Download this amazing ambient track to test SCDL
scdl -l https://soundcloud.com/ghostxkitty3/view-of-andromeda
```
*"View of Andromeda" by GhostxKitty3 - Perfect for coding sessions! 🌌*

## 📖 Table of Contents

1. [Basic Downloads](#basic-downloads)
2. [User Content](#user-content)
3. [Playlists & Sets](#playlists--sets)
4. [Audio Formats](#audio-formats)
5. [Metadata & Organization](#metadata--organization)
6. [Authentication](#authentication)
7. [Automation & Scripting](#automation--scripting)
8. [Docker Usage](#docker-usage)
9. [Troubleshooting](#troubleshooting)
10. [Advanced Features](#advanced-features)

## 🎵 Basic Downloads

### Single Track
```bash
# Basic download
scdl -l https://soundcloud.com/artist/track-name

# With custom path
scdl -l https://soundcloud.com/ghostxkitty3/view-of-andromeda --path ~/Music/Ambient

# Force MP3 format
scdl -l https://soundcloud.com/ghostxkitty3/view-of-andromeda --onlymp3
```

### Download with Original Quality
```bash
# Download in highest available quality
scdl -l https://soundcloud.com/ghostxkitty3/view-of-andromeda --only-original

# Convert to FLAC (if lossless source available)
scdl -l https://soundcloud.com/ghostxkitty3/view-of-andromeda --flac
```

## 👤 User Content

### All Tracks from User
```bash
# All uploads + reposts
scdl -l https://soundcloud.com/ghostxkitty3 -a

# Only uploads (no reposts)
scdl -l https://soundcloud.com/ghostxkitty3 -t

# Only liked tracks
scdl -l https://soundcloud.com/ghostxkitty3 -f

# Only tracks user commented on
scdl -l https://soundcloud.com/ghostxkitty3 -C

# All playlists from user
scdl -l https://soundcloud.com/ghostxkitty3 -p

# Only reposts
scdl -l https://soundcloud.com/ghostxkitty3 -r
```

### Discover Amazing Music
```bash
# Explore GhostxKitty3's full discography
scdl -l https://soundcloud.com/ghostxkitty3 -t --name-format "{artist} - {title}"

# Download their playlists for curated collections
scdl -l https://soundcloud.com/ghostxkitty3 -p
```

## 📂 Playlists & Sets

### Basic Playlist Download
```bash
# Download entire playlist
scdl -l https://soundcloud.com/username/sets/playlist-name

# Download without creating playlist folder
scdl -l https://soundcloud.com/username/sets/playlist-name --no-playlist-folder
```

### Playlist Synchronization
```bash
# Sync playlist (download new, remove deleted)
scdl -l https://soundcloud.com/username/sets/playlist-name --sync archive.txt

# Download only new tracks
scdl -l https://soundcloud.com/username/sets/playlist-name --download-archive archive.txt -c
```

### Partial Downloads
```bash
# Download from 5th track onwards
scdl -l https://soundcloud.com/username/sets/playlist-name -o 5

# Download only last 10 tracks
scdl -l https://soundcloud.com/username/sets/playlist-name -n 10
```

## 🎼 Audio Formats

### Format Selection
```bash
# Download as MP3 (default)
scdl -l https://soundcloud.com/ghostxkitty3/view-of-andromeda --onlymp3

# Prefer Opus format
scdl -l https://soundcloud.com/ghostxkitty3/view-of-andromeda --opus

# Convert to FLAC (lossless)
scdl -l https://soundcloud.com/ghostxkitty3/view-of-andromeda --flac

# Download original file only
scdl -l https://soundcloud.com/ghostxkitty3/view-of-andromeda --only-original

# Download transcoded version (no original)
scdl -l https://soundcloud.com/ghostxkitty3/view-of-andromeda --no-original
```

### Quality Control
```bash
# Skip files larger than 50MB
scdl -l https://soundcloud.com/username/sets/large-playlist --max-size 50m

# Skip files smaller than 1MB
scdl -l https://soundcloud.com/username/sets/playlist --min-size 1m
```

## 🏷️ Metadata & Organization

### File Naming
```bash
# Custom naming format
scdl -l https://soundcloud.com/ghostxkitty3/view-of-andromeda --name-format "{artist} - {title}"

# Include timestamp
scdl -l https://soundcloud.com/ghostxkitty3/view-of-andromeda --name-format "{artist} - {title} ({timestamp})"

# Playlist-specific naming
scdl -l https://soundcloud.com/username/sets/playlist --playlist-name-format "{playlist} - {track_number:02d} - {title}"
```

### Metadata Options
```bash
# Download original artwork (high res)
scdl -l https://soundcloud.com/ghostxkitty3/view-of-andromeda --original-art

# Keep original filename
scdl -l https://soundcloud.com/ghostxkitty3/view-of-andromeda --original-name

# Keep original metadata
scdl -l https://soundcloud.com/ghostxkitty3/view-of-andromeda --original-metadata

# Extract artist from title instead of username
scdl -l https://soundcloud.com/ghostxkitty3/view-of-andromeda --extract-artist

# Disable album tags
scdl -l https://soundcloud.com/ghostxkitty3/view-of-andromeda --no-album-tag

# Add track description to separate file
scdl -l https://soundcloud.com/ghostxkitty3/view-of-andromeda --add-description
```

## 🔐 Authentication

### Setting Up Authentication
```bash
# Use auth token for private content
scdl -l https://soundcloud.com/private-track --auth-token YOUR_TOKEN

# Download your own likes
scdl me -f --auth-token YOUR_TOKEN

# Save token in config file (~/.config/scdl/scdl.cfg)
[scdl]
auth_token = YOUR_TOKEN_HERE
```

### Custom Client ID
```bash
# Use specific client ID
scdl -l https://soundcloud.com/ghostxkitty3/view-of-andromeda --client-id YOUR_CLIENT_ID
```

## 🤖 Automation & Scripting

### Archive Management
```bash
# Track downloaded files to avoid duplicates
scdl -l https://soundcloud.com/ghostxkitty3 -a --download-archive my_archive.txt

# Continue previous download session
scdl -l https://soundcloud.com/username/sets/large-playlist -c --download-archive archive.txt
```

### Batch Downloads
```bash
# Create a file with URLs (one per line)
echo "https://soundcloud.com/ghostxkitty3/view-of-andromeda" > urls.txt
echo "https://soundcloud.com/artist2/track2" >> urls.txt

# Download all URLs
while read url; do
  scdl -l "$url" --download-archive archive.txt
done < urls.txt
```

### Error Handling
```bash
# Continue on errors (don't stop playlist download)
scdl -l https://soundcloud.com/username/sets/playlist --no-strict-playlist

# Hide warnings
scdl -l https://soundcloud.com/ghostxkitty3/view-of-andromeda --hidewarnings

# Debug mode
scdl -l https://soundcloud.com/ghostxkitty3/view-of-andromeda --debug
```

## 🐳 Docker Usage

### Basic Docker Usage
```bash
# Pull the image
docker pull ghcr.io/scdl-org/scdl:latest

# Download featured track
docker run --rm -v $(pwd)/downloads:/downloads \
  ghcr.io/scdl-org/scdl:latest \
  -l https://soundcloud.com/ghostxkitty3/view-of-andromeda
```

### Docker Compose
```bash
# Quick demo
docker-compose --profile demo up

# Interactive session
docker-compose run --rm scdl -l https://soundcloud.com/ghostxkitty3/view-of-andromeda

# Batch processing
docker-compose --profile batch up
```

### Docker with Authentication
```bash
# Set environment variable
export AUTH_TOKEN=your_token_here

# Run with authentication
docker run --rm -v $(pwd)/downloads:/downloads \
  -e AUTH_TOKEN=$AUTH_TOKEN \
  ghcr.io/scdl-org/scdl:latest \
  me -f
```

## 🔧 Troubleshooting

### Common Issues

#### Authentication Problems
```bash
# Test if token is valid
scdl me --auth-token YOUR_TOKEN --debug

# Use dynamic client ID
scdl -l https://soundcloud.com/ghostxkitty3/view-of-andromeda --client-id ""
```

#### Download Failures
```bash
# Increase verbosity for debugging
scdl -l https://soundcloud.com/ghostxkitty3/view-of-andromeda --debug

# Skip problematic tracks in playlists
scdl -l https://soundcloud.com/username/sets/playlist --no-strict-playlist

# Force metadata update on existing files
scdl -l https://soundcloud.com/ghostxkitty3/view-of-andromeda --force-metadata
```

#### Performance Issues
```bash
# Hide progress bar for better performance
scdl -l https://soundcloud.com/username/sets/large-playlist --hide-progress

# Process playlists without folder creation
scdl -l https://soundcloud.com/username/sets/playlist --no-playlist-folder
```

### FFmpeg Issues
```bash
# Verify FFmpeg installation
ffmpeg -version

# Install FFmpeg (Ubuntu/Debian)
sudo apt update && sudo apt install ffmpeg

# Install FFmpeg (macOS)
brew install ffmpeg

# Install FFmpeg (Windows)
choco install ffmpeg
```

## 🚀 Advanced Features

### Search Functionality
```bash
# Search and download first result
scdl -s "view of andromeda ghostxkitty3"

# Search for artist
scdl -s "ghostxkitty3" -t
```

### Advanced yt-dlp Integration
```bash
# Pass custom yt-dlp arguments
scdl -l https://soundcloud.com/ghostxkitty3/view-of-andromeda \
  --yt-dlp-args "--extract-flat --write-info-json"

# Use specific extractor options
scdl -l https://soundcloud.com/ghostxkitty3/view-of-andromeda \
  --yt-dlp-args "--extractor-args soundcloud:client_id=YOUR_ID"
```

### Output to stdout
```bash
# Stream audio directly
scdl -l https://soundcloud.com/ghostxkitty3/view-of-andromeda --name-format "-" | mpv -

# Save to specific file
scdl -l https://soundcloud.com/ghostxkitty3/view-of-andromeda --name-format "-" > track.mp3
```

### Configuration File
Create `~/.config/scdl/scdl.cfg`:
```ini
[scdl]
auth_token = YOUR_TOKEN
client_id = YOUR_CLIENT_ID
path = ~/Music/SoundCloud
name_format = {artist} - {title}
playlist_name_format = {playlist}/{track_number:02d} - {artist} - {title}
addtimestamp = False
onlymp3 = True
original_art = True
extract_artist = False
no_album_tag = False
```

## 💡 Pro Tips

1. **Start with the featured track** to test your setup:
   ```bash
   scdl -l https://soundcloud.com/ghostxkitty3/view-of-andromeda
   ```

2. **Use archives** to avoid re-downloading:
   ```bash
   scdl -l URL --download-archive archive.txt
   ```

3. **Batch process safely** with continue flag:
   ```bash
   scdl -l PLAYLIST_URL -c --download-archive archive.txt
   ```

4. **Organize with custom naming**:
   ```bash
   --name-format "{artist} - {title} [{id}]"
   ```

5. **Monitor performance** with the included benchmark scripts

6. **Use Docker** for isolated environments and easy deployment

## 🎵 Music Recommendations

While you're here, check out more amazing tracks from the featured artist:
- 🌌 **GhostxKitty3**: [soundcloud.com/ghostxkitty3](https://soundcloud.com/ghostxkitty3)
- Perfect ambient/electronic music for coding, studying, and relaxation
- Support independent artists by following and sharing their music!

## 🆘 Getting Help

- **Issues**: [GitHub Issues](https://github.com/scdl-org/scdl/issues)
- **Discussions**: [GitHub Discussions](https://github.com/scdl-org/scdl/discussions)
- **Contributing**: See [CONTRIBUTING.md](CONTRIBUTING.md)

---

*Made with ❤️ by the SCDL community. Featuring music by [GhostxKitty3](https://soundcloud.com/ghostxkitty3)! 🎵*
