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

    def __dataset_exists(self,title, existing_dataset):
        if title == existing_dataset['title']:
            if existing_dataset['deleted'] is None:
                print(title + ' exists')
                return True
            else:
                print(title + ' exists but is deleted')
                return False
        return False

    def __intersect(self, a, b):
        # return the intersection of two lists
        return list(set(a) & set(b))

    # returns similarity value by intersecting the lists and compare the length of the lists (return value 0-1)
    def __get_similarity_value(self, originalList, otherList):
        intersected_list = self.__intersect(originalList, otherList)
        return (len(intersected_list)/len(originalList))

    def __update_resources(self, item, existing_dataset):
        kwargs = item.kwargs

        dataset_exists = self.__dataset_exists(kwargs['title'].encode('utf-8'), existing_dataset)

        new_resources = []
        updated_resources = kwargs['resources']

        if dataset_exists:
            existing_resources = existing_dataset['resources']

            for updated_resource in updated_resources:
                updated_resource_title_list = updated_resource['title'].split()
                updated_resource_title_list = list(set(updated_resource_title_list))

                for existing_resource in existing_resources:
                    existing_resource_title_list = existing_resource['title'].split()
                    existing_resource_title_list = list(set(existing_resource_title_list))

                    similarity = self.__get_similarity_value(updated_resource_title_list, existing_resource_title_list)

                    if similarity >= 0.80:
                        updated_resource['format'] = existing_resource['format']
                        new_resources.append(updated_resource)
                        existing_resources.remove(existing_resource)
                    pass
                pass

            new_resources = new_resources + existing_resources
            return new_resources

        return updated_resources

    def process(self, item):
        dataset = self.get_dataset(item.remote_id)

        # Here you comes your implementation. You should :
        # - fetch the remote dataset (if necessary)
        # - validate the fetched payload
        # - map its content to the dataset fields
        # - store extra significant data in the `extra` attribute
        # - map resources data

        dataset.tags = ["statec-harvesting"] + dataset.tags
        resources = self.__update_resources(item, dataset)

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
                description=resource['title'],
                url=download_url,
                filetype='remote',
                format=resource['format']
            )
            if len(filter(lambda d: d['title'] in [resource['title']] and d['url'] in [download_url], dataset.resources)) == 0:  # noqa
                dataset.resources.append(new_resource)
            else:
                pass

        return dataset
