# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.harvest.backends.base import BaseBackend
from udata.models import Resource
from urllib import urlencode
import feedparser
import urlparse


class StatecBackend(BaseBackend):
    display_name = 'Statec RSS Feed Harvester'

    def initialize(self):
        self.items = []
        d = feedparser.parse(self.source.url)
        items = d['items']
        categories = self.__get_categories(items)

        for category in categories:
            resources = self.__get_category_resources(items, category)
            self.add_item(category, title=category, resources=resources)

    def __get_categories(self, items):
        categories = []
        for item in items:
            try:
                if item['category'] not in categories:
                    categories.append(item['category'])
            except KeyError:
                pass
        return categories

    def __get_category_resources(self, items, category):
        resources = []
        for item in items:
            try:
                if item['category'] == category:
                    resource = {
                            'title': item['title'],
                            'link': item['link']
                    }
                    resources.append(resource)
            except KeyError:
                pass
        return resources

    def process(self, item):
        dataset = self.get_dataset(item.remote_id)

        # Here you comes your implementation. You should :
        # - fetch the remote dataset (if necessary)
        # - validate the fetched payload
        # - map its content to the dataset fields
        # - store extra significant data in the `extra` attribute
        # - map resources data

        kwargs = item.kwargs
        dataset.title = kwargs['title']
        dataset.tags = ["statec-harvesting"]
        resources = kwargs['resources']

        description = u"Ce jeu de données contient: <br>"
        for resource in resources:
            description += resource['title'] + "<br>"
        description += "<br>---------------------------------------"
        description += """<br> Automatically synched from
                    portail statistique (category %s)""" % dataset.title

        dataset.description = description

        # Force recreation of all resources
        dataset.resources = []
        for resource in resources:
            url = resource['link']
            url = url.replace('tableView', 'download')
            params = {
                'IF_DOWNLOADFORMAT': 'csv',
                'IF_DOWNLOAD_ALL_ITEMS': 'yes'
            }

            url_parts = list(urlparse.urlparse(url))
            query = dict(urlparse.parse_qsl(url_parts[4]))
            query.update(params)
            url_parts[4] = urlencode(query)
            download_url = urlparse.urlunparse(url_parts)

            new_resource = Resource(
                title=resource['title'],
                url=download_url,
                filetype='remote',
                format='csv'
            )
            if len(filter(lambda d: d['title'] in [resource['title']] and d['url'] in [download_url], dataset.resources)) == 0:  # noqa
                dataset.resources.append(new_resource)
            else:
                pass

        return dataset
