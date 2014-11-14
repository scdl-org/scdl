#!/usr/bin/python3
"""scdl allow you to download music from soundcloud

Usage:
	scdl.py -l <track_url> [-a | -f | -t | -p][-c][-o <offset>][--hidewarnings][--addtofile]
	scdl.py me (-s | -a | -f | -t | -p)[-c][-o <offset>][--hidewarnings][--addtofile]
	scdl.py -h | --help
	scdl.py --version


Options:
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
	--addtofile        Add the artist name to the filename if it isn't in the filename already
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

from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TALB, TPE1, TPE2, COMM, USLT, TCOM, TCON, TDRC, APIC

token = ''

offset=0

filename = ''
scdl_client_id = 'b45b1aa10f1ac2941910a7f0d10f8e28'
client = soundcloud.Client(client_id=scdl_client_id)


def main():
	"""
	Main function, call parse_url
	"""
	signal.signal(signal.SIGINT, signal_handler)
	print("Soundcloud Downloader")
	global offset

	# import conf file
	get_config()

	# Parse argument
	arguments = docopt(__doc__, version='0.1')
	#print(arguments)
	if arguments["<offset>"] is not None:
		try:
			offset=int(arguments["<offset>"])
		except:
			print('Offset should be an Integer...')
			sys.exit()

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
	config.read(os.path.join(os.path.expanduser('~'), '.config/scdl/scdl.cfg'))
	try:
		token = config['scdl']['auth_token']
		path = config['scdl']['path']
	except:
		print('Are you sure scdl.cfg is in $HOME/.config/scdl/ ?')
		sys.exit()
	if os.path.exists(path):
		os.chdir(path)
	else:
		print('Invalid path...')
		sys.exit()

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
	arguments = docopt(__doc__, version='0.1')
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
			print('Please provide a download type...')
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
	global offset
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
	global offset
	count=0
	tracks = client.get('/users/' + str(user.id) + '/tracks', limit = 10, offset = offset)
	for track in tracks:
		for track in tracks:
			count +=1
			print("")
			print('Track n°%d' % (count))
			download_track(track)
		offset += 10
		tracks = client.get('/users/' + str(user.id) + '/tracks', limit = 10, offset = offset)
	print('All users track downloaded!')


def download_user_playlists(user):
	"""
	Find playlists of the user
	"""
	global offset
	count=0
	playlists = client.get('/users/' + str(user.id) + '/playlists', limit = 10, offset = offset)
	for playlist in playlists:
		for playlist in playlists:
			count +=1
			print("")
			print('Playlist n°%d' % (count))
			download_playlist(playlist)
		offset += 10
		playlists = client.get('/users/' + str(user.id) + '/playlists', limit = 10, offset = offset)
	print('All users playlists downloaded!')


def download_user_favorites(user):
	"""
	Find tracks in user favorites
	"""
	global offset
	count=0
	favorites = client.get('/users/' + str(user.id) + '/favorites', limit = 10, offset = offset)
	for track in favorites:
		for track in favorites:
			count +=1
			print("")
			print('Favorite n°%d' % (count))
			download_track(track)
		offset += 10
		favorites = client.get('/users/' + str(user.id) + '/favorites', limit = 10, offset = offset)
	print('All users favorites downloaded!')

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
	count=0
	for track_raw in playlist.tracks:
		count +=1
		mp3_url = get_item(track_raw["permalink_url"])
		print('Track n°%d' % (count))
		download_track(mp3_url)

def download_track(track):
	"""
	Downloads a track
	"""
	global filename
	arguments = docopt(__doc__, version='0.1')

	if track.streamable:
		stream_url = client.get(track.stream_url, allow_redirects=False)
	else:
		print('%s is not streamable...' % (track.title))
		print('')
		return
	url = stream_url.location
	title = track.title
	print("Downloading " + title)

	# validate title
	invalid_chars = '\/:*?|<>'
	if track.user['username'] not in title and arguments["--addtofile"]:
		title = track.user['username'] + ' - ' + title
	title = ''.join(c for c in title if c not in invalid_chars)
	filename = title +'.mp3'

	# Download
	if not os.path.isfile(filename):
		if track.downloadable:
			print('Downloading the orginal file.')
			url = track.download_url + '?client_id=' + scdl_client_id
			wget.download(url, filename)
		else:
			wget.download(url, filename)
		print('')
	else:
		if arguments["-c"]:
			print(title + " already Downloaded")
			print('')
			return
		else:
			print('')
			print("Music already exists ! (exiting)")
			sys.exit(0)
	settags(track)

	print('')
	print(filename + ' Downloaded.')
	print('')

def settags(track):
	"""
	Set the tags to the mp3
	"""
	print("Settings tags...")
	user = client.get('/users/' + str(track.user_id), allow_redirects=False)

	artwork_url = track.artwork_url
	if artwork_url is None:
		artwork_url = user.avatar_url
	artwork_url = artwork_url.replace('large', 't500x500')
	urllib.request.urlretrieve(artwork_url, '/tmp/scdl.jpg')

	tags = MP3(filename)
	tags["TIT2"] = TIT2(encoding=3, text=track.title)
	tags["TALB"] = TALB(encoding=3, text='Soundcloud')
	tags["TPE1"] = TPE1(encoding=3, text=user.username)
	tags["TCON"] = TCON(encoding=3, text=track.genre)
	if artwork_url is not None:
		tags["APIC"] = APIC(
	           encoding=3, 
	           mime='image/jpeg', 
	           type=3, 
	           desc='Cover',
	           data=open('/tmp/scdl.jpg', 'rb').read()
	           )
	tags.save()

def signal_handler(signal, frame):
	"""
	handle keyboardinterrupt
	"""
	time.sleep(1)
	files = os.listdir()
	for f in files:
		if not os.path.isdir(f) and ".tmp" in f:
			os.remove(f)

	print('')
	print('Good bye!')
	sys.exit(0)

if __name__ == "__main__":
	main()
