<p align="center">
  <img src="http://soundcloud-dl.com/soundcloud-download-logo.png" alt="Logo"/>
</p>
# Souncloud Music Downloader
## WIP
 * Current state : https://github.com/flyingrub/scdl/issues/2

## Description

This shell script is able to download music from http://www.soundcloud.com.
It should work with OS X, Linux, Windows.

## System requirements

* Python3

## Instructions
### i will provide a easy install script soon
 * soon
 * You can use this script now by donwloading the repo
 * Set up your path (mandatory) & your auth_token (if you want)

### Auth_token
* This permitt scdl to access to your user profile data.
* scdl use it only to use 'scdl.py me' instead of scdl.py [url]
* (soon) scdl will download an user's stream thanks to this
> get your auth token here : http://flyingrub.tk/soundcloud/

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
  -l [url]           URL can be track/playlist/user.
  -s                 Download the stream of an user (token needed)
  -a                 Download all track of an user (including repost)
  -t                 Download all upload of an user
  -f                 Download all favorite of an user
  -p                 Download all playlist of an user
  -c                 Continue if a music already exist
  -o [offset]        Begin with a custom offset.
  --hidewarnings     Hide Warnings. (use with precaution)
```


## Features
* Automatically detect which kind of Soundcloud's link you have provided
* Download all song of an user
* Download all song & repost of an user
* Download all song of one playlist
* Download all song of an user's all playlist
* Download all song of an user's favorites
* Set tags with eyeD3 (soon)


## Old version
 * This will be the new python version of : https://github.com/lukapusic/soundcloud-dl

## License

[GPL v2](https://www.gnu.org/licenses/gpl-2.0.txt), orignal author [Flyingrub](https://github.com/flyingrub)
