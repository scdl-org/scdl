# -*- encoding: utf-8 -*-

"""Python Soundcloud Music Downloader."""

import os

__version__ = 'v1.6.1'
CLIENT_ID = 'bed20744714e9c5962c351efe15840ff'
ALT_CLIENT_ID = 'a3e059563d7fd3372b49b37f00a00bcf'
B_CLIENT_ID = '02gUJC0hH2ct1EGOcYXQIzRFU91c72Ea'

dir_path_to_conf = os.path.join(os.path.expanduser('~'), '.config/scdl')
file_path_to_conf = os.path.join(
    os.path.expanduser('~'), '.config/scdl/scdl.cfg'
)
text = """[scdl]
auth_token =
path = ."""

if not os.path.exists(dir_path_to_conf):
    os.makedirs(dir_path_to_conf)

if not os.path.exists(file_path_to_conf):
    with open(file_path_to_conf, 'w') as f:
        f.write(text)
