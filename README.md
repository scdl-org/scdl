<p align="center">
  <img src="http://soundcloud-dl.com/soundcloud-download-logo.png" alt="Logo"/>
</p>
# Souncloud Music Downloader
## Changelog
Current state : [Here](https://github.com/flyingrub/scdl/issues/2)

## Description

This script is able to download music from http://www.soundcloud.com.
It should work with OS X, Linux, Windows.

## System requirements

* Python3
* You need this lib to install it with pip correctly `python3-dev`
* Install eyed3 from source
```
wget https://bitbucket.org/nicfit/eyed3/get/py3.zip
unzip py3.zip
cd nicfit-eyed3-a95f6ccd6388/
python3 setup.py install
```

## Instructions
### Installation
___
1. Install scdl `pip3 install scdl`
2. Setup your path &/or your auth_token in `$HOME/.config/scdl/scdl.cfg`


### Auth_token :
___
> get your auth token here : http://flyingrub.tk/soundcloud/

* This permitt scdl to access to your user profile data.
* For now scdl use it only to use `scdl.py me [OPTIONS]` instead of `scdl.py -l [url] [OPTIONS]`
* (soon) scdl will download an user's stream thanks to this

## Help
### Usage:
```
  scdl.py -l <track_url> [-a | -f | -t | -p][-c][-o <offset>][--hidewarnings][--addtofile]
  scdl.py me (-s | -a | -f | -t | -p)[-c][-o <offset>][--hidewarnings][--addtofile]
  scdl.py -h | --help
  scdl.py --version
```

### Options:
```
  -h --help          Show this screen.
  --version          Show version.
  me                 Use the user profile from the auth_token
  -l [url]           URL can be track/playlist/user.
  -s                 Download the stream of an user (token needed)
  -a                 Download all track of an user (including repost)
  -t                 Download all upload of an user
  -f                 Download all favorite of an user
  -p                 Download all playlist of an user
  -c                 Continue if a music already exist
  -o [offset]        Begin with a custom offset.
  --hidewarnings     Hide Warnings. (use with precaution)
  --addtofile        Add the artist name to the filename if
```


## Features
* Automatically detect which kind of Soundcloud's link you have provided
* Download all song of an user
* Download all song & repost of an user
* Download all song of one playlist
* Download all song of all playlist of an user
* Download all song of an user's favorites
* Set tags with eyeD3 (soon)(the soft need to be updated to work with python3 by the owner)


## Old version
 * This will be the new python version of : https://github.com/lukapusic/soundcloud-dl

## License

[GPL v2](https://www.gnu.org/licenses/gpl-2.0.txt), orignal author [Flyingrub](https://github.com/flyingrub)
