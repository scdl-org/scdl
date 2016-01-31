# -*- encoding: utf-8 -*-

import soundcloud

__all__ = ('Client', 'resource')


class Client(soundcloud.Client):

    def get_all(self, url, offset=0, limit=200, **kwargs):
        resources = []
        while url:
            response = self.get(url, order='created_at', offset=offset, limit=limit, linked_partitioning=1)
            resources.extend(response.collection)
            try:
                url = response.next_href
            except AttributeError:
                url = None
        return resources

resource = soundcloud.resource
