

from udata.harvest.backends.base import BaseBackend
from udata.models import Resource
from urllib import urlencode
import feedparser
from urllib.parse import urlparse, parse_qsl, urlunparse

import copy


class StatecBackend(BaseBackend):

    display_name = 'Statec RSS Feed Harvester'

    # Feed the harvester with the gathered items
    def initialize(self):
        self.items = []
        d = feedparser.parse(self.source.url)
        items = d['items']
        categories = self.__get_categories(items)

        for category in categories:
            resources = self.__get_category_resources(items, category)
            self.add_item(category.encode('utf-8'), title=category, resources=resources)

    # Gather all the catgeories of the source url
    def __get_categories(self, items):
        categories = []
        for item in items:
            try:
                if item['category'] not in categories:
                    categories.append(item['category'])
            except KeyError:
                pass
        return categories

    # Gather all resources of a Category
    def __get_category_resources(self, items, category):
        resources = []
        for item in items:
            try:
                if item['category'] == category:
                    resource = {
                            'title': item['title'],
                            'url': item['link'],
                            'format': 'csv'
                    }
                    resources.append(resource)
            except KeyError:
                pass
        return resources

    # Check if a dataset already exists
    def __dataset_exists(self, title, existing_dataset):
        exisiting_dataset_title = existing_dataset.title
        if title.encode('utf-8') == exisiting_dataset_title.encode('utf-8'):
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
        union = len(pairs1) + len(pairs2)
        hit_count = 0
        for x in pairs1:
            for y in pairs2:
                if x == y:
                    hit_count += 1
                    break
        return (2.0 * hit_count) / union

    # Update the resources of an exisiting dataset with the harvested resources
    # or return the harvested resources if it is a new dataset
    def __update_resources(self, item, existing_dataset):
        kwargs = item.kwargs

        dataset_exists = self.__dataset_exists(kwargs['title'], existing_dataset)

        new_resources = []
        updated_resources = kwargs['resources']

        # if the dataset already exists: iterate over the gathered item's resources(kwargs)
        # and perform a similarity check to check if a resource has changed its title
        if dataset_exists:
            existing_resources = existing_dataset['resources']
            copy_exisiting_resources = copy.deepcopy(existing_resources)

            for updated_resource in updated_resources:
                updated_title = updated_resource['title']

                for existing_resource in existing_resources:
                    existing_title = existing_resource['title']

                    similarity = self.__string_similarity(updated_title, existing_title)

                    # Titles are more than 90% the same and therefore qualifie for an update
                    if similarity >= 0.90:
                        url = updated_resource['url']
                        format = existing_resource['format']
                        resource = ResourceTemplate(updated_title, url, format)
                        new_resources.append(resource)

                        i = 0
                        for copy_exisiting_resource in copy_exisiting_resources:
                            encode_copy_title = copy_exisiting_resource['title'].encode('utf-8')
                            encode_exist_title = existing_title.encode('utf-8')
                            if encode_copy_title == encode_exist_title:
                                del copy_exisiting_resources[i]
                                break
                            i += 1
                            pass
                pass

            pass

            # Add the remaining unchanged resources back to the to-be-returned list
            for copy_exisiting_resource in copy_exisiting_resources:
                title = copy_exisiting_resource['title']
                url = copy_exisiting_resource['url']
                format = copy_exisiting_resource['format']
                resource = ResourceTemplate(title, url, format)
                new_resources.append(resource)
            pass

            return new_resources
        else:
            # Else: return only the gathered item's resources
            for updated_resource in updated_resources:
                title = updated_resource['title']
                url = updated_resource['url']
                format = updated_resource['format']
                resource = ResourceTemplate(title, url, format)
                new_resources.append(resource)
            pass

            return new_resources

    # Process each gathered item of the initialization
    def process(self, item):
        dataset = self.get_dataset(item.remote_id)

        # Here you comes your implementation. You should :
        # - fetch the remote dataset (if necessary)
        # - validate the fetched payload
        # - map its content to the dataset fields
        # - store extra significant data in the `extra` attribute
        # - map resources data

        # check if this is a new dataset and give it a title
        if dataset.title is None:
            dataset.title = ''
            pass

        # Create the new list of tags and mmake sure the list has only unique tags
        tags = []
        for tag in dataset.tags:
            tags.append(tag)
            pass
        tags.append("statec-harvesting")
        tags = list(set(tags))
        dataset.tags = tags

        # return the gathered resources of the items
        # or return the updated list of all the resources of the given dataset
        resources = self.__update_resources(item, dataset)

        if dataset.title == '':
            dataset.title = item.kwargs['title']

        # Rebuild the dataset description
        description = u"This dataset includes the following resource(s): <br>"
        for resource in resources:
            description += resource.title + "<br>"
        description += "<br>---------------------------------------"
        description += """<br> Automatically synched from
                    portail statistique (category %s)""" % dataset.title

        dataset.description = description

        # Force recreation of all resources
        dataset.resources = []
        for resource in resources:
            url = resource.url
            download_url = url

            # check if the resource format is csv and handle the link creation accordingly
            if resource.format == 'csv':
                url = url.replace('tableView', 'download')
                params = {
                    'IF_DOWNLOADFORMAT': 'csv',
                    'IF_DOWNLOAD_ALL_ITEMS': 'yes'
                }

                url_parts = list(urlparse(url))
                query = dict(parse_qsl(url_parts[4]))
                query.update(params)
                url_parts[4] = urlencode(query)
                download_url = urlunparse(url_parts)
                pass

            # The newly created resource
            new_resource = Resource(
                title=resource.title,
                description=resource.title,
                url=download_url,
                filetype='remote',
                format=resource.format
            )

            dataset.resources.append(new_resource)

        return dataset


# Helper class to access the resource data more easily
class ResourceTemplate():

    def __init__(self, title, url, fileFormat):
        self.title = title
        self.url = url
        self.filetype = 'remote'
        self.format = fileFormat
