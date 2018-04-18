# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.harvest.backends.base import BaseBackend
from udata.models import Resource, License
import csv
import urllib2


class UnicodeDictReader(csv.DictReader, object):
    def next(self):
        row = super(UnicodeDictReader, self).next()
        return {unicode(key, 'utf-8'): unicode(value, 'utf-8') for key, value in row.iteritems()}


class CSVBackend(BaseBackend):
    display_name = 'Generic CSV Harvester'

    def initialize(self):
        self.items = []
        response = urllib2.urlopen(self.source.url)
        for row in UnicodeDictReader(response):
            self.items.append(row)
        datasets = self.__get_datasets(self.items)

        for dataset in datasets:
            resources = self.__get_dataset_resources(self.items, dataset)
            title = dataset['dataset_title']
            remote_id = "igss_" + dataset['dataset_id']
            self.add_item(
                    remote_id,
                    title=title,
                    tags=dataset['tags'],
                    resources=resources,
                    remote_id=remote_id
                )

    def __get_datasets(self, items):
        dataset_ids = []
        datasets = []
        for item in items:
            if item['dataset_id'] not in dataset_ids:
                dataset_ids.append(item['dataset_id'])
                datasets.append(item)
        return datasets

    def __get_dataset_resources(self, items, dataset):
        resources = []
        for item in items:
            if item['dataset_id'] == dataset['dataset_id']:
                resource = {
                        'resource_id': item['resource_id'],
                        'title': item['resource_title'],
                        'link': item['resource_url'],
                        'filetype': item['resource_file_type'],
                        'format': item['resource_file_format'],
                        'description': item.get('description', '')
                }
                resources.append(resource)
        return resources

    def process(self, item):
        kwargs = item.kwargs
        item.remote_id = kwargs['remote_id']
        dataset = self.get_dataset(item.remote_id)
        dataset.title = kwargs['title']
        dataset.tags = kwargs.get('tags', '').split(',')
        dataset.private = True
        dataset.frequency = kwargs.get('dataset_frequency', 'annual')
        license = kwargs.get('dataset_license', 'cc-zero')
        dataset.license = License.objects.get(id=license)
        resources = kwargs['resources']

        description = u"Ce jeu de données contient: <br>"
        for resource in resources:
            description += resource['title'] + "<br>"

        dataset.description = description

        # Force recreation of all resources
        dataset.resources = []
        for resource in resources:
            new_resource = Resource(
                title=resource['title'],
                url=resource['link'],
                filetype=resource['filetype'],
                format=resource['format'],
                description=resource.get('description', '')
            )
            dataset.resources.append(new_resource)
        return dataset
