# Soundcloud Music Downloader [![PyPI version](https://img.shields.io/pypi/v/scdl.svg)](https://pypi.python.org/pypi/scdl/)
## Description

This script is able to download music from SoundCloud and set id3tag to the downloaded music.
Compatible with Windows, OS X, Linux.


## System requirements

* Python3


## Instructions
### Installation
```
pip3 install scdl
```
or
```
git clone https://github.com/flyingrub/scdl.git && cd scdl
python3 setup.py install
```
(Optional) Setup your path and your auth_token in `$HOME/.config/scdl/scdl.cfg`


### Authentication
> Soundcloud has banned all our client_id so we cannot use authentication for now.

* This allows scdl to access to your user profile data.
* You need to have this set to be able to use the `me` option


## Help
### Examples:
```
# Download track & repost of the user QUANTA
scdl -l https://soundcloud.com/quanta-uk -a

# Download likes of the user Blastoyz
scdl -l https://soundcloud.com/kobiblastoyz -f

# Download one track
scdl -l https://soundcloud.com/jumpstreetpsy/low-extender

# Download one playlist
scdl -l https://soundcloud.com/pandadub/sets/the-lost-ship

# Download your likes (with authentification token)
scdl me -f
```

### Options:
```
    -h --help             Show this screen
    --version             Show version
    me                    Use the user profile from the auth_token
    -l [url]              URL can be track/playlist/user
    -s                    Download the stream of a user (token needed)
    -a                    Download all tracks of a user (including reposts)
    -t                    Download all uploads of a user (no reposts)
    -f                    Download all favorites of a user
    -C                    Download all commented by a user
    -p                    Download all playlists of a user
    -m                    Download all liked and owned playlists of a user
    -c                    Continue if a downloaded file already exists
    -o [offset]           Begin with a custom offset
    --path [path]         Use a custom path for downloaded files
    --min-size [min-size] Skip tracks smaller than size (k/m/g)
    --max-size [max-size] Skip tracks larger than size (k/m/g)
    --hidewarnings        Hide Warnings. (use with precaution)
    --addtofile           Add the artist name to the filename if it isn't in the filename already
    --onlymp3             Download only the mp3 file even if the track is Downloadable
    --error               Set log level to ERROR
    --debug               Set log level to DEBUG
    --hide-progress       Hide the wget progress bar
```


## Features
* Automatically detect the type of link provided
* Download all songs from a user
* Download all songs and reposts from a user
* Download all songs from one playlist
* Download all songs from all playlists from a user
* Download all songs from a user's favorites
* Set the tags with mutagen (Title / Artist / Album / Artwork)
* Create playlist files when downloading a playlist


## License

[GPL v2](https://www.gnu.org/licenses/gpl-2.0.txt), original author [flyingrub](https://github.com/flyingrub)
