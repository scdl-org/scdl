#!/usr/bin/python

import soundcloud
import urllib

client = soundcloud.Client(client_id='b45b1aa10f1ac2941910a7f0d10f8e28')

track_url = 'https://soundcloud.com/iskel/apprenti-sorcier'

# resolve track URL into track resource
track = client.get('/resolve', url=track_url)

# fetch track to stream
#track = client.get('/tracks/293')

# get the tracks streaming URL
stream_url = client.get(track.stream_url, allow_redirects=False)

# print the tracks stream URL
url = stream_url.location
title = track.title

urllib.urlretrieve (url, title + '.mp3')
