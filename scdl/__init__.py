# -*- encoding: utf-8 -*-

"""Python Soundcloud Music Downloader."""

import os

__version__ = 'v1.6.12'
CLIENT_ID = 'a3e059563d7fd3372b49b37f00a00bcf'
ALT_CLIENT_ID = '2t9loNQH90kzJcsFCODdigxfp325aq4z'
ALT2_CLIENT_ID = 'NONE'

USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36'


default_config = """[scdl]
auth_token =
path = .
"""

if 'XDG_CONFIG_HOME' in os.environ:
    config_dir = os.path.join(os.environ['XDG_CONFIG_HOME'], 'scdl')
else:
    config_dir = os.path.join(os.path.expanduser('~'), '.config', 'scdl')

config_file = os.path.join(config_dir, 'scdl.cfg')

if not os.path.exists(config_file):
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)

    with open(config_file, 'w') as f:
        f.write(default_config)
