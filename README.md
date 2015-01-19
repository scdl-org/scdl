<p align="center">
  <img src="http://soundcloud-dl.com/soundcloud-download-logo.png" alt="Logo"/>
</p>
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
  scdl -l <track_url> [-a | -f | -t | -p][-c][-o <offset>][--hidewarnings][--debug | --error][--path <path>][--addtofile][--onlymp3]
  scdl me (-s | -a | -f | -t | -p)[-c][-o <offset>][--hidewarnings][--debug | --error][--path <path>][--addtofile][--onlymp3]
  scdl -h | --help
  scdl --version
```

### Options:
```
  -h --help          Show this screen.
  --version          Show version.
  me                 Uses the auth_token specified in the config to get access to the user's profile
  -l [url]           URL can be a track, playlist or a user.
  -s                 Download the stream of a user (token needed)
  -a                 Download all of a user's tracks, including reposts
  -t                 Download all of a user's uploads
  -f                 Download all of a user's favorites
  -p                 Download all of a user's playlists
  -c                 Continue if a music already exist
  -o [offset]        Start on a custom offset.
  --hidewarnings     Hide Warnings. Use with precaution
  --addtofile        Add the artist name to the filename if it isn't in the filename already
  --path             Path to download directory, can be set in the config. If none of this is set, it uses the current working directory
  --silent           Disables output, useful for scripters
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
