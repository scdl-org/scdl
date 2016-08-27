# -*- encoding: utf-8 -*-

import requests
from scdl import CLIENT_ID


class Client():

    def get_collection(self, url):
        resources = list()
        while url:
            url = '{0}&client_id={1}&linked_partitioning=1'.format(
                url, CLIENT_ID)
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
