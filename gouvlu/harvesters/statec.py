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
            self.add_item(category.encode('utf-8'), title=category, resources=resources)

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
                            'url': item['link']
                    }
                    resources.append(resource)
            except KeyError:
                pass
        return resources

    # Check if a dataset already exists
    def __dataset_exists(self,title, existing_dataset):
        if title == existing_dataset['title']:
            if existing_dataset['deleted'] is None:
                return True
            else:
                return False
        return False

    # Take a string and return a list of bigrams.
    def __get_bigrams(self, string):
        s = string.lower()
        return [s[i:i+2] for i in list(range(len(s) - 1))]

    # Perform bigram comparison between two strings and return a percentage match in decimal form.
    def __string_similarity(self, str1, str2):
        pairs1 = self.__get_bigrams(str1)
        pairs2 = self.__get_bigrams(str2)
        union  = len(pairs1) + len(pairs2)
        hit_count = 0
        for x in pairs1:
            for y in pairs2:
                if x == y:
                    hit_count += 1
                    break
        return (2.0 * hit_count) / union

    # Update the resources of an exisiting dataset with the harvested resources or return the harvested resources if it is a new dataset
    def __update_resources(self, item, existing_dataset):
        kwargs = item.kwargs

        dataset_exists = self.__dataset_exists(kwargs['title'].decode('utf-8', 'ignore'), existing_dataset.decode('utf-8', 'ignore'))

        new_resources = []
        updated_resources = kwargs['resources']

        if dataset_exists:
            existing_resources = existing_dataset['resources']

            for updated_resource in updated_resources:
                updated_resource_title = updated_resource['title']

                for existing_resource in existing_resources:
                    existing_resource_title = existing_resource['title']

                    similarity = self.__string_similarity(updated_resource_title, existing_resource_title)

                    # Titles are more than 90% the same and therefore qualifie for an update
                    if similarity >= 0.90:

                        new_resource = {
                            'title': updated_resource['title'],
                            'url': updated_resource['url'],
                            'format': existing_resource['format']
                        }
                        new_resources.append(new_resource)
                        existing_resources.remove(existing_resource)
                pass

            pass

            for exisiting_resource in existing_resources:
                new_resource = {
                    'title': exisiting_resource['title'],
                    'url': exisiting_resource['url'],
                    'format': exisiting_resource['format']
                }
                new_resources.append(new_resource)
            pass

            return new_resources
        else:
            return updated_resources

    def process(self, item):
        dataset = self.get_dataset(item.remote_id)

        # Here you comes your implementation. You should :
        # - fetch the remote dataset (if necessary)
        # - validate the fetched payload
        # - map its content to the dataset fields
        # - store extra significant data in the `extra` attribute
        # - map resources data

        dataset.tags = [u"statec-harvesting"] + dataset.tags
        resources = self.__update_resources(item, dataset)

        # check if this is a new dataset and give it a title
        if dataset.title is None:
            dataset.title = item.kwargs['title']
            pass

        # Rebuild the dataset description
        description = u"This dataset includes the following resource(s): <br>"
        for resource in resources:
            description += resource['title'] + "<br>"
        description += "<br>---------------------------------------"
        description += """<br> Automatically synched from
                    portail statistique (category %s)""" % dataset.title

        dataset.description = description

        # Force recreation of all resources
        dataset.resources = []
        for resource in resources:
            url = resource['url']
            download_url = url

            # check to see that this is a new resource with no known format
            if "format" not in resource:
                resource['format'] = 'csv'
            pass

            # check if the resource format is csv and handle the link creation accordingly
            if resource['format'] == 'csv':
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
                pass

            # The newly created resource
            new_resource = Resource(
                title=resource['title'],
                description=resource['title'],
                url=download_url,
                filetype='remote',
                format=resource['format']
            )
            if len(filter(lambda d: d['title'] in [resource['title']] and d['url'] in [download_url], dataset.resources)) == 0:  # noqa
                dataset.resources.append(new_resource)
                pass
            else:
                pass

        return dataset
