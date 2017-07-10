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
> Get your auth token here: [https://dev.vm0.eu/scdl/](https://dev.vm0.eu/scdl/)

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
  -h --help          Show this screen
  --version          Show version
  me                 Use the user profile from the auth_token
  -l [url]           URL can be track/playlist/user
  -s                 Download the stream of an user (token needed)
  -a                 Download all track of an user (including repost)
  -t                 Download all upload of an user
  -f                 Download all favorite of an user
  -p                 Download all playlist of an user
  -c                 Continue if a music already exist
  -o [offset]        Begin with a custom offset
  --path [path]      Download the music to a custom path
  --hidewarnings     Hide Warnings. (use with precaution)
  --addtofile        Add the artist name to the filename if it isn't in the filename already
  --onlymp3          Download only the mp3 file even if the track is Downloadable
  --error            Swho only error and warning
  --debug            Print debugging information
  --hide-progress    Hide the progress bar
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
