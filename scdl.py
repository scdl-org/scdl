#!/usr/bin/python3
"""scdl.
 
Usage:
	scdl.py -l <track_url>
	scdl.py -h | --help
	scdl.py --version

 
Options:
	-h --help		Show this screen.
	--version 		Show version.  
	-l [url]   		Necessary. URL is the url of the soundcloud's page
"""
from docopt import docopt

import soundcloud
import urllib
import urllib.request

client = soundcloud.Client(client_id='b45b1aa10f1ac2941910a7f0d10f8e28')


def main():
    print("Soundcloud Downloader")

    arguments = docopt(__doc__, version='0.1')
    print(arguments)
    print("End of arguments\n")

    #track_url = 'https://soundcloud.com/iskel/apprenti-sorcier'
    track_url = arguments["<track_url>"]
    parse_url(track_url)



def get_item(track_url):
	"""
	
	Fetches metadata for an track or playlist
	
	"""
	# Fetches metadata from soundcloud
	try:
		item = client.get('/resolve', url=track_url)
	except Exception as e:
		print("Could not resolve url " + track_url)
		print(e, exc_info=True)
		return False 
	return item



def parse_url(track_url):
	"""
	
	Detects if the URL is a track or playlists, and parses the track(s) to the track downloader
	
	"""
	
	item = get_item(track_url)
	if not item:
		return

	if item.kind == 'track':
		print("Found a track")
		download_track(item)
	
	elif item.kind == "playlist":
		print("Found a playlist")
		for track_raw in item.tracks:
			mp3_url = get_item(track_raw["permalink_url"])
			if item:
				download_track(track)
			else:
				print("Could not find track " + track_raw["title"])
	else:
		print("Unknown item type")



def download_track(track):
	"""
	
	Downloads a track
	
	"""

	stream_url = client.get(track.stream_url, allow_redirects=False)
	url = stream_url.location
	title = track.title
	print("Downloading " + title)
	filename = title +'.mp3'
	path = filename

	urllib.request.urlretrieve (url, path)

if __name__ == "__main__":
    main()
