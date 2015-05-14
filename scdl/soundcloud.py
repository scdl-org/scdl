# -*- encoding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals

import soundcloud

__all__ = ('Client', 'resource')


class Client(soundcloud.Client):

    def get_all(self, url, offset=0, limit=200, **kwargs):
        resources = set()
        prev_offset, start_offset = None, offset
        while offset != prev_offset:
            resources.update(self.get(url, offset=offset, limit=limit, **kwargs))
            prev_offset, offset = offset, start_offset + len(resources)
        return resources

resource = soundcloud.resource
