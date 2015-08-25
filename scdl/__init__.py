# -*- encoding: utf-8 -*-

"""Python Soundcloud Music Downloader."""

__version__ = 'v1.4.0b1'


import os

dir_path_to_conf = os.path.join(os.path.expanduser('~'), '.config/scdl')
file_path_to_conf = os.path.join(os.path.expanduser('~'), '.config/scdl/scdl.cfg')
text = """[scdl]
auth_token =
path = ."""

if not os.path.exists(dir_path_to_conf):
    os.makedirs(dir_path_to_conf)

if not os.path.exists(file_path_to_conf):
    f = open(file_path_to_conf, "w")
    f.write(text)
    f.close
