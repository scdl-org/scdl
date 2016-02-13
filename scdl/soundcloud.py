# -*- encoding: utf-8 -*-

import requests
import soundcloud

scdl_client_id = '95a4c0ef214f2a4a0852142807b54b35'

__all__ = ('Client', 'resource')


class Client(soundcloud.Client):

    def get_collection(self, url):
        resources = list()
        while url:
            url = '{0}&client_id={1}&linked_partitioning=1'.format(
                url, scdl_client_id)
            response = requests.get(url)
            json_data = response.json()
            if 'collection' in json_data:
                resources.extend(json_data['collection'])
            else:
                resources.extend(json_data)
            if 'next_href' in json_data:
                url = json_data['next_href']
            else:
                url = None
        return resources

resource = soundcloud.resource
