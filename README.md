[![PyPI version](https://img.shields.io/pypi/v/scdl.svg)](https://pypi.python.org/pypi/scdl/)
[![PyPI version](https://img.shields.io/github/issues-raw/flyingrub/scdl.svg)](https://github.com/flyingrub/scdl/issues)
[![PyPI version](https://img.shields.io/pypi/dm/scdl.svg)](https://pypi.python.org/pypi/scdl/)
# Soundcloud Music Downloader
## Description

This script is able to download music from http://www.soundcloud.com and set id3tag to the downloaded music.
It should work with OS X, Linux, Windows.


## System requirements

* Python3


## Instructions
### Installation
___
1. Install scdl `pip3 install scdl`
2. (Optional) Setup your path and your auth_token in `$HOME/.config/scdl/scdl.cfg`


### Authentication:
___
> Get your auth token here: [Token](http://flyingrub.tk/soundcloud/)

* This allows scdl to access to your user profile data.
* You need to have this set to be able to use the `me` option
* Soon scdl will be able to download a user's stream


## Help
### Usage:
```
  scdl -l <track_url> [-a | -f | -t | -p][-c][-o <offset>][--hidewarnings][--debug | --error][--path <path>][--addtofile][--onlymp3][--hide-progress]
  scdl me (-s | -a | -f | -t | -p)[-c][-o <offset>][--hidewarnings][--debug | --error][--path <path>][--addtofile][--onlymp3][--hide-progress]
  scdl -h | --help
  scdl --version
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
  --path [path]      Use a custom path for this time
  --hidewarnings     Hide Warnings. (use with precaution)
  --addtofile        Add the artist name to the filename if it isn't in the filename already
  --onlymp3          Download only the mp3 file even if the track is Downloadable
  --error            Only print debug information (Error/Warning)
  --debug            Print every information and
  --hide-progress    Hide the wget progress bar
```


## Features
* Automatically detect the type of link provided
* Download all songs from a user
* Download all songs and reposts from a user
* Download all songs from one playlist
* Download all songs from all playlists from a user
* Download all songs from a user's favorites
* Set the tags with mutagen (Title / Artist / Album = 'Soundcloud' / Artwork)


## License

[GPL v2](https://www.gnu.org/licenses/gpl-2.0.txt), orignal author [Flyingrub](https://github.com/flyingrub)
