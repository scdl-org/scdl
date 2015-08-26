# -*- encoding: utf-8 -*-

import soundcloud

__all__ = ('Client', 'resource')


class Client(soundcloud.Client):

    def get_all(self, url, offset=0, limit=200, **kwargs):
        resources = list()
        prev_offset, start_offset = None, offset
        while offset != prev_offset:
            resources.extend(self.get(url, offset=offset, limit=limit, **kwargs))
            prev_offset, offset = offset, start_offset + len(resources)
        return resources

resource = soundcloud.resource
