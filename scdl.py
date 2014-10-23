#!/usr/bin/python3
"""scdl allow you to download music from soundcloud

Usage:
	scdl.py -l <track_url> [-a | -f | -t | -p][--hidewarnings]
	scdl.py me [-s | -a | -f | -t | -p][--hidewarnings]
	scdl.py -h | --help
	scdl.py --version


Options:
	-h --help          Show this screen.
	--version          Show version.
	-l [url]           URL can be track/playlist/user.
	-s                 Download the stream of an user (token needed)
	-a                 Download all track of an user (including repost)
	-t                 Download all upload of an user
	-f                 Download all favorite of an user
	-p                 Download all playlist of an user
	--hidewarnings     Hide Warnings. (use with precaution)
"""
from docopt import docopt
import configparser

import warnings
import os
import signal
import sys
import string

import time
import soundcloud
import wget
import urllib.request
import json

token = ''
filename = ''
scdl_client_id = '9dbef61eb005cb526480279a0cc868c4'
client = soundcloud.Client(client_id=scdl_client_id)

def main():
	"""
	Main function, call parse_url
	"""
	print("Soundcloud Downloader")

	arguments = docopt(__doc__, version='0.1')
	print(arguments)

	get_config()

	if arguments["--hidewarnings"]:
		warnings.filterwarnings("ignore")
		print("no warnings!")

	print('')
	if arguments["-l"]:
		parse_url(arguments["<track_url>"])
	elif arguments["me"]:
		if arguments["-a"]:
			download_all_user_tracks(who_am_i())
		elif arguments["-f"]:
			download_user_favorites(who_am_i())
		elif arguments["-t"]:
			download_user_tracks(who_am_i())
		elif arguments["-p"]:
			download_user_playlists(who_am_i())


def get_config():
	"""
	read the path where to store music
	"""
	global token
	config = configparser.ConfigParser()
	config.read('scdl.cfg')
	token = config['scdl']['auth_token']
	path = config['scdl']['path']
	os.chdir(path)

def get_item(track_url):
	"""
	Fetches metadata for an track or playlist
	"""

	try:
		item = client.get('/resolve', url=track_url)
	except Exception as e:
		print("Could not resolve url " + track_url)
		sys.exit(0)
	return item

def parse_url(track_url):
	"""
	Detects if the URL is a track or playlists, and parses the track(s) to the track downloader
	"""
	item = get_item(track_url)
	if not item:
		return
	elif item.kind == 'track':
		print("Found a track")
		download_track(item)
	elif item.kind == "playlist":
		print("Found a playlist")
		download_playlist(item)
	elif item.kind == 'user':
		print("Found an user profile")
		if arguments["-f"]:
			download_user_favorites(item)
		elif arguments["-t"]:
			download_user_tracks(item)
		elif arguments["-a"]:
			download_all_user_tracks(item)
		elif arguments["-p"]:
			download_user_playlists(item)
	else:
		print("Unknown item type")

def who_am_i():
	"""
	display to who the current token correspond, check if the token is valid
	"""
	global client
	client = soundcloud.Client(access_token=token, client_id=scdl_client_id)

	try:
		current_user = client.get('/me')
	except:
		print('Invalid token...')
		sys.exit(0)
	print('Hello',current_user.username, '!')
	print('')
	return current_user

def download_all_user_tracks(user):
	"""
	Find track & repost of the user
	"""
	offset=23
	user_id = user.id

	url = "https://api.sndcdn.com/e1/users/%s/sounds.json?limit=1&offset=%d&client_id=9dbef61eb005cb526480279a0cc868c4" % (user_id, offset)
	response = urllib.request.urlopen(url)
	data = response.read()
	text = data.decode('utf-8')
	json_data = json.loads(text)
	while json_data != '[]':
		offset += 1
		try:
			this_url = json_data[0]['track']['uri']
		except:
			this_url = json_data[0]['playlist']['uri']
		print('Track n°%d' % (offset))
		parse_url(this_url)

		url = "https://api.sndcdn.com/e1/users/%s/sounds.json?limit=1&offset=%d&client_id=9dbef61eb005cb526480279a0cc868c4" % (user_id, offset)
		response = urllib.request.urlopen(url)
		data = response.read()
		text = data.decode('utf-8')
		json_data = json.loads(text)

def download_user_tracks(user):
	"""
	Find track in user upload --> no repost
	"""
	offset = 0
	end_of_tracks = False
	songs = client.get('/users/' + str(user.id) + '/tracks', limit = 10, offset = offset)
	while not end_of_tracks:
		for track in songs:
			if track.kind == 'track':
				print("")
				download_track(track)
			else:
				print("End of favorites")
				end_of_tracks =True
		offset += 10


def download_user_playlists(user):
	"""
	Find playlists of the user
	"""
	offset = 0
	end_of_tracks = False
	songs = client.get('/users/' + str(user.id) + '/tracks', limit = 10, offset = offset)
	while not end_of_tracks:
		for track in songs:
			if track.kind == 'track':
				print("")
				download_track(track)
			else:
				print("End of favorites")
				end_of_tracks =True
		offset += 10

def download_user_favorites(user):
	"""
	Find tracks in user favorites
	"""
	offset = 0
	end_of_tracks = False
	songs = client.get('/users/' + str(user.id) + '/favorites', limit = 10, offset = offset)
	while not end_of_tracks:
		for track in songs:
			if track.kind == 'track':
				print("")
				download_track(track)
			else:
				print("End of favorites")
				end_of_tracks =True
		offset += 10

def download_my_stream():
	"""
	DONT WORK FOR NOW
	Download the stream of the current user
	"""
	client = soundcloud.Client(access_token=token, client_id=scdl_client_id)

	current_user = client.get('/me')
	activities = client.get('/me/activities')
	print(activities)

def download_playlist(playlist):
	"""
	Download a playlist
	"""
	for track_raw in playlist.tracks:
		mp3_url = get_item(track_raw["permalink_url"])
		download_track(mp3_url)

def download_track(track):
	"""
	Downloads a track
	"""
	if track.streamable:
		stream_url = client.get(track.stream_url, allow_redirects=False)
	else:
		print('This track is not streamable...')
		print('')
		return
	url = stream_url.location
	title = track.title
	print("Downloading " + title)

	valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
	global filename
	filename = title +'.mp3'
	filename = ''.join(c for c in filename if c in valid_chars)

	if not os.path.isfile(filename):
		if track.downloadable:
			print('Downloading the orginal file.')
			url = track.download_url + '?client_id=' + scdl_client_id
			wget.download(url, filename)
		elif track.streamable:
			wget.download(url, filename)
	else:
		print('')
		print("Music already exists ! (exiting)")
		sys.exit(0)
	#settags(track)

	print('')
	print(filename + ' Downloaded.')
	print('')

def settags(track):
	"""
	Set the tags to the mp3
	"""
	print("Settings tags...")
	user = client.get('/users/' + str(track.user_id), allow_redirects=False)
	audiofile = my_eyed3.load(filename)
	audiofile.tag.artist = user.username
	audiofile.tag.album = track.title
	audiofile.tag.title = track.title

	audiofile.tag.save()

def signal_handler(signal, frame):
	"""
	handle keyboardinterrupt
	"""
	time.sleep(2)
	files = os.listdir()
	for f in files:
		if not os.path.isdir(f) and ".tmp" in f:
			os.remove(f)

	print('')
	print('Good bye!')
	sys.exit(0)

if __name__ == "__main__":
	signal.signal(signal.SIGINT, signal_handler)
	main()
