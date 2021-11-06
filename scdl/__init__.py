# -*- encoding: utf-8 -*-

"""Python Soundcloud Music Downloader."""

import os

__version__ = "v2.1.2"
CLIENT_ID = "a3e059563d7fd3372b49b37f00a00bcf"
ALT_CLIENT_ID = "2t9loNQH90kzJcsFCODdigxfp325aq4z"
ALT2_CLIENT_ID = "NONE"

default_config = """[scdl]
auth_token =
path = .
name_format = {id}_{user[username]}_{title}
"""

if "XDG_CONFIG_HOME" in os.environ:
    config_dir = os.path.join(os.environ["XDG_CONFIG_HOME"], "scdl")
else:
    config_dir = os.path.join(os.path.expanduser("~"), ".config", "scdl")

config_file = os.path.join(config_dir, "scdl.cfg")

def write_default_config():
    with open(config_file, "w") as f:
        f.write(default_config)

if not os.path.exists(config_file):
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)

    write_default_config()
