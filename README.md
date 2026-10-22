# Soundcloud Music Downloader

## Status of the project

As of version 3, this script is a wrapper around `yt-dlp` with some defaults/patches for backwards compatibility.
Development is not active and new features will likely not be merged, especially if they can be covered with the
use of `--yt-dlp-args`. Bug reports/fixes are welcome.

## Description

This script is able to download music from SoundCloud and set id3tag to the downloaded music.
Compatible with Windows, OS X, Linux.

## System requirements

* python3
* ffmpeg

## Installation Instructions
https://github.com/flyingrub/scdl/wiki/Installation-Instruction

## Configuration
There is a configuration file left in `~/.config/scdl/scdl.cfg` (or `$XDG_CONFIG_HOME/scdl/scdl.cfg`)

## Interfaz local (scdl-web)

Este fork incluye una interfaz web local y ligera (Python estándar + Preact, sin compilación):

* **Windows:** doble clic en `scdl-web.bat`. La primera vez crea `.venv` e instala scdl; después solo arranca.
  `scdl-web.bat --update` reinstala dependencias.
* **Cualquier sistema:** `pip install -e .` y luego `scdl-web` (o `python -m scdl.web`).

Se abre en una ventana de Edge/Chrome en modo app (o en el navegador por defecto) en `http://127.0.0.1:8770` (o el siguiente puerto libre).
Permite buscar o pegar URLs (incluidos los enlaces `on.soundcloud.com`), elegir qué bajar de un usuario
(subidas, likes, reposts, playlists…), ajustar formato/calidad y filtros, y ver la cola con el progreso.
Las descargas se hacen de una en una para evitar bloqueos por exceso de peticiones (HTTP 429).
Opciones: `--port <n>`, `--no-window`.

## Examples:
```
# Download track & repost of the user QUANTA
scdl -l https://soundcloud.com/quanta-uk -a

# Download likes of the user Blastoyz
scdl -l https://soundcloud.com/kobiblastoyz -f

# Download one track
scdl -l https://soundcloud.com/jumpstreetpsy/low-extender

# Download one playlist
scdl -l https://soundcloud.com/pandadub/sets/the-lost-ship

# Download only new tracks from a playlist
scdl -l https://soundcloud.com/pandadub/sets/the-lost-ship --download-archive archive.txt -c

# Sync playlist
scdl -l https://soundcloud.com/pandadub/sets/the-lost-ship --sync archive.txt

# Download your likes (with authentification token)
scdl me -f

# Download the 20 most recent uploads of a user, skipping tracks longer than 10 minutes
scdl -l https://soundcloud.com/quanta-uk -t -n 20 --max-duration 10:00

# Convert to 320kbps mp3 (mp3 sources are kept as-is) and keep the cover as a separate file
scdl -l https://soundcloud.com/jumpstreetpsy/low-extender --audio-format mp3 --audio-quality 320K --write-cover

# Share links from the mobile app work too
scdl -l https://on.soundcloud.com/jSPcrMemAGzRcU4M6
```

## Options:
```
-h --help                       Show this screen
--version                       Show version
-l [url]                        URL can be track/playlist/user
-s [search_query]               Search for a track/playlist/user and use the first result
-a                              Download all tracks of user (including reposts)
-t                              Download all uploads of a user (no reposts)
-f                              Download all favorites (likes) of a user
-C                              Download all tracks commented on by a user
-p                              Download all playlists of a user
-r                              Download all reposts of user
-c                              Continue if a downloaded file already exists
--force-metadata                This will set metadata on already downloaded track
-o [offset]                     Start downloading a playlist from the [offset]th track (starting with 1)
-n [maxtracks]                  Download at most [maxtracks] tracks (counted from the offset)
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
--min-duration [time]           Skip tracks shorter than [time] (SS, MM:SS or HH:MM:SS)
--max-duration [time]           Skip tracks longer than [time] (SS, MM:SS or HH:MM:SS)
--skip-known-drm                Skip tracks with no downloadable formats (DRM/geo-restricted)
                                and remember them so later runs skip them without requests
--audio-format [format]         Convert audio with ffmpeg (mp3, m4a, opus, flac, wav, ...).
                                Files already in that format are kept as-is
--audio-quality [quality]       Quality for --audio-format: 0 (best VBR) to 10, or a bitrate such as 320K
--sleep [seconds]               Wait [seconds] between requests and downloads (helps against HTTP 429)
--write-cover                   Also keep the cover art as a separate image file
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
