
from udata.harvest.backends.base import BaseBackend
from udata.models import Resource, License

from unidecode import unidecode
import unicodedata

import feedparser
import requests
from urllib.parse import urlparse, urlencode

from time import sleep
from bs4 import BeautifulSoup

import os, ssl
import subprocess
import itertools


class IGSSBackend(BaseBackend):

    display_name = 'IGSS Harvester'

    def initialize(self):
        working_link = "https://igss.gouvernement.lu/fr/"
        if working_link == self.source.url:
            igss_harvester = IGSSDatasetsHarvester(self.source.url)
            categories = igss_harvester.get_categories()

            for category in categories:
                for dataset in category.datasets:
                    resources = dataset.resources
                    title = dataset.title
                    remote_id = dataset.remote_id
                    self.add_item(
                        remote_id,
                        title=title,
                        tags=dataset.tags,
                        resources=self.__get_resources_as_dict(resources),
                        remote_id=remote_id
                    )
                pass
            pass
    pass

    def __get_resources_as_dict(self, resources):
        new_resources = []
        for resource in resources:
            new_resource = {
                    'title': resource.title,
                    'url': resource.url,
                    'format': resource.file_format
            }
            new_resources.append(new_resource)
        return new_resources

    def process(self, item):
        kwargs = item.kwargs
        item.remote_id = kwargs['remote_id']
        dataset = self.get_dataset(item.remote_id)
        dataset.title = kwargs['title']
        tags = kwargs['tags']
        tags.append("igss-harvesting")
        dataset.tags = tags
        dataset.private = False
        dataset.frequency = kwargs.get('dataset_frequency', 'monthly')
        license = kwargs.get('dataset_license', 'cc-zero')
        dataset.license = License.objects.get(id=license)
        resources = kwargs['resources']

        description = u"This dataset includes the following resource(s): <br>"
        for resource in resources:
            description += resource["title"] + "<br>"
        description += "<br>---------------------------------------"
        description += """<br> Automatically synched from
                    IGSS (category %s)""" % dataset.title

        dataset.description = description

        # Force recreation of all resources
        dataset.resources = []
        for resource in resources:
            new_resource = Resource(
                title=resource["title"],
                url=resource["url"],
                filetype='remote',
                format=resource["format"]
            )
            dataset.resources.append(new_resource)
        return dataset


class IGSSDatasetsHarvester():

    def __init__(self, url):
        self.igss_url = url
        self.categories = []
        self.__loaded()
    pass

    def __loaded(self):
        print("IGSS Harvester is ready!")
    pass 

    def get_categories(self):
        self.__harvest_categories()
        self.__harvest_pdf_publications()
        return self.categories

    def __harvest_pdf_publications(self):
        soup = self.__curl_publications()
        pdf_meta_count = self.__get_pdf_meta_count(soup)
        pdf_theme_dict = self.__get_pdf_theme_dict(pdf_meta_count)
        pdf_category = Category(u"publications", "")
        pdf_category.generate_pdf_datasets(pdf_theme_dict)
        self.categories.append(pdf_category)

    def __curl_publications(self):
        curl_link = self.igss_url + "publications.html"
        status, output = subprocess.getstatusoutput("curl --silent " + curl_link)
        soup = BeautifulSoup(output, "html.parser")
        return soup
    pass 

    def __get_pdf_meta_count(self, soup):
        span_meta_count = soup.findAll("span", {"class": "search-meta-count"})
        pdf_meta_results = span_meta_count[0].getText()
        pdf_meta_count = int(pdf_meta_results.split(" ")[0])

        #print(pdf_meta_count)

        return pdf_meta_count
    pass

    def __get_a_tag_pdf_on_site(self, pdf_index):
        curl_link = self.igss_url + "publications.html?b=" + str(pdf_index)
        status, output = subprocess.getstatusoutput("curl --silent " + curl_link)
        soup = BeautifulSoup(output, "html.parser")
        ol_col = soup.findAll("div", {"class": "mo-body"})
        a_tag = ol_col[0].findAll("a")[0]
        return a_tag

    def __get_pdf_download_link(self, soup, a_tag):
        div_book_action = soup.findAll("div", {"class": "book-actions"})[0]
        a_tag = div_book_action.findAll("a")[0]

        href_link = a_tag.get("href")
        link = href_link.replace("//igss", "https://igss")
        return link

    def __curl_pdf_download_page(self, a_tag):
        href_link = a_tag.get("href")
        link = href_link.replace("/fr", "https://igss.gouvernement.lu/fr")
        status, output = subprocess.getstatusoutput("curl --silent " + link)
        soup = BeautifulSoup(output, "html.parser")
        return soup

    def __get_theme_of_pdf(self, soup, a_tag, title):

        div_book_metas = soup.findAll("dl", {"class": "book-metas"})[0]
        dt_tag = div_book_metas.find("dt", text="Thème(s)")

        if dt_tag is not None:
            dt_tag = dt_tag.find_next()
            theme = dt_tag.getText()
            theme = self.__get_clean_str(theme)
            pass
        else:
            if title.split()[1] == "NEETs":
                theme = "IGSS/Statistiques"
            else:
                theme = title.split()[0]
        theme = self.__clean_theme_string(theme)

        return theme

    def __get_pdf_theme_dict(self, pdf_meta_count):

        pdf_theme_dict = {}
        resources = []

        for i in range(pdf_meta_count):
            a_tag = self.__get_a_tag_pdf_on_site(i)
            title = a_tag.getText()
            soup = self.__curl_pdf_download_page(a_tag)
            link = self.__get_pdf_download_link(soup,a_tag)
            theme = self.__get_theme_of_pdf(soup, a_tag, title)


            # print("------------Resource------------")

            # print(title)
            # print(link)
            # print(theme)

            # print("--------------------------------")


            resource = Resource_T(title, link, "pdf")

            if theme not in pdf_theme_dict:
                pdf_theme_dict[theme] = []
                pdf_theme_dict[theme].append(resource)
                pass
            else:
                pdf_theme_dict[theme].append(resource)
                pass
            pass

        return pdf_theme_dict

    def __clean_theme_string(self, theme):
        theme = u"IGSS/" + theme
        theme = theme.replace(" / ", "/")
        theme = theme.replace("/ ", "/")
        theme = theme.replace("  ", "/")
        if theme.endswith("/"):
            theme = theme[:-1]
            pass

        if u"Santé" in theme and "Justice sociale" not in theme:
            theme = "IGSS/Santé"
            pass
        if "Justice sociale" in theme:
            theme = "IGSS/Justice sociale"
            pass
        if "Statistiques" in theme and "Travail/Emploi" not in theme:
            theme = "IGSS/Statistiques"
            pass
        if "Emploi" in theme:
            theme = "IGSS/Emploi"
            pass
        if "absent" in theme:
            theme = "IGSS/Absentéisme"
            pass
        if "Troi" in theme:
            theme = "IGSS/Troisième âge"
            pass
        if "gislation" in theme:
            theme = "IGSS/Législation"
            pass

        return theme

    def __get_clean_str(self, string):
        removal_list = ['  ', '\t', '\n', '\r\n']
        for s in removal_list:
            if s == '\n':
                string = string.replace(s, ' ')
            else:
                string = string.replace(s, '')
        return string
        
    def __harvest_categories(self):
        soup = self.__curl_main_categories()
        self.__get_main_categories(soup)

        for category in self.categories:
            soup = category.curl_sub_categories()
            category.get_datasets(soup, "", False)
        pass

    def __curl_main_categories(self):
        curl_link = self.igss_url + "statistiques.html"
        status, output = subprocess.getstatusoutput("curl --silent " + curl_link)
        soup = BeautifulSoup(output, "html.parser")
        return soup

    def __get_main_categories(self, soup):
        div_index = soup.findAll("div", {"class": "index"})
        category_links = div_index[0].findAll("a")
        category_titles = div_index[0].findAll("h2")

        for category_link in category_links:
            href_link = category_link.get("href")
            stats_link = href_link.replace(".html", "/serie-statistique.html")
            url = "https://igss.gouvernement.lu/" + stats_link

            title_header2 = category_link.findAll("h2")
            title = title_header2[0].getText()

            catgeory = Category(title, url)
            self.categories.append(catgeory)
        pass

    


class Resource_T():
    def __init__(self, title, url, file_format):
        self.title = title
        self.url = url
        self.file_format = file_format
    pass

class Dataset_T():
    def __init__(self, title, resources):
        self.title = title
        self.resources = resources
        self.tags = self.__generateTags()
        self.remote_id = ""
    pass

    def __generateTags(self):
        title = self.title
        if "/" in self.title:
            title = self.title.replace("/", " ")
            pass

        if "-" in self.title:
            title = title.replace("-", " ")
            pass

        if "l\'" or "L\'" or "l'" in self.title:
            title = title.replace("l\'", "")

        if "d\'" in self.title:
            title = title.replace("d\'", "")

        preTagList = title.split(" ")
        # print(preTagList)

        tags = []
        for preTag in preTagList:
            preTag = preTag.lower()
            preTag = self.removeAccents(preTag)

            if "(" in preTag:
                preTag = preTag.replace("(", "")

            if ")" in preTag:
                preTag = preTag.replace(")", "")

            check_tag = (preTag == "vie" or preTag == "age" and preTag != "autre")
            if len(preTag) >= 5 or check_tag:
                if preTag.lower() not in tags:
                    check_tag = (preTag != "fonds" and preTag != "soins")
                    if preTag.endswith("s") and check_tag and preTag != "frais":
                        preTag = preTag[:-1]
                        pass
                    if preTag == "lallocation" or preTag == "l'allocation":
                        preTag = "allocation"
                        pass
                    if preTag == "laccueil":
                        preTag = "accueil"
                        pass
                    # print(preTag)
                    tags.append(preTag)
                    pass
                pass
            pass
        return tags

    def removeAccents(self, text):
        text = text.encode("utf-8")
        text = text.decode("utf-8")
        text = unicodedata.normalize('NFD', text)
        text = text.encode('ascii', 'ignore')
        return str(text)

    pass

    def format_title_for_id(self):
        dataset_title = self.title
        # if "IGSS/" in dataset_title:
        #     dataset_title = dataset_title.encode("utf-8")
        #     dataset_title = dataset_title.decode("utf-8")
        # pass
        # dataset_title = unicodedata.normalize('NFD', dataset_title)
        #dataset_title = dataset_title.encode('ascii', 'ignore')
        dataset_title = str(dataset_title)
        dataset_title = dataset_title.lower()
        dataset_title = dataset_title.replace("(", " ")
        dataset_title = dataset_title.replace(")", " ")
        dataset_title = dataset_title.replace(".", "")
        dataset_title = dataset_title.replace("-", " ")
        dataset_title = dataset_title.replace(" -", " ")
        dataset_title = dataset_title.replace("/", " ")
        dataset_title = dataset_title.replace(" : ", " ")
        dataset_title = dataset_title.replace("’", " ")
        dataset_title = dataset_title.replace("'", " ")
        dataset_title = dataset_title.replace("  ", " ")
        dataset_title = dataset_title.replace("   ", " ")
        dataset_title = dataset_title.replace(" ", "_")
        if dataset_title.endswith("_"):
            dataset_title = dataset_title[:-1]
        dataset_title = dataset_title.replace("__", "_")

        return dataset_title


class Category():
    def __init__(self, title, url):
        self.title = title
        self.url = url
        self.datasets = []
    pass

    def curl_sub_categories(self):
        status, output = subprocess.getstatusoutput("curl --silent " + self.url)
        soup = BeautifulSoup(output, "html.parser")
        return soup

    def __get_clean_title(self, title):
        removal_list = ['  ', '\t', '\n', '\r\n']
        for s in removal_list:
            title = title.replace(s, '')
        return title

    def __get_resources(self, soup):
        resource_links = soup.findAll("a")
        resources = []
        for resource_link in resource_links:
            title = resource_link.getText()
            url = resource_link.get("href")
            if "http://" not in url:
                url = url.replace("//", "https://")

            url_split = url.split(".")
            file_format = url_split[len(url_split)-1]
            resource = Resource_T(title, url, file_format)

            # print("------------Resource------------")

            # print(title)
            # print(url)

            # print("--------------------------------")

            resources.append(resource)
            pass
        return resources

    def generate_pdf_datasets(self, pdf_theme_dict):
        for title, resources in pdf_theme_dict.items():
            dataset = Dataset_T(title, resources)
            dataset.tags.append("document")
            dataset.tags.append("dokument")
            categ_title = self.__format_title_for_id()
            dataset_title = dataset.format_title_for_id()
            combined_title = unidecode(categ_title + "_" + dataset_title)
            dataset.remote_id = "igss_" + combined_title

            self.datasets.append(dataset)

    def get_datasets(self, soup, title, recursive):

        div_accordion = soup.findAll("div", {"class": "accordion"})
        details = div_accordion[0].findChildren("details", recursive=False)

        for detail in details:
            summary = detail.findChildren("summary", recursive=False)

            if recursive:
                dataset_title = title + "/" + summary[0].getText()
            else:
                dataset_title = summary[0].getText()
            dataset_title = self.__get_clean_title(dataset_title)

            div_resources = detail.findChildren("div", recursive=False)

            for div_resource in div_resources:
                decode_div_res = str(div_resource)#.decode("ascii", "ignore")
                if not recursive and "<div class=\"accordion\">" in decode_div_res:
                    ul_resource = div_resource.findChildren("ul", recursive=False)
                    if len(ul_resource) != 0:
                        resources = self.__get_resources(ul_resource[0])
                        dataset = Dataset_T(dataset_title, resources)
                        categ_title = self.__format_title_for_id()
                        format_title = dataset.format_title_for_id()
                        combined_title = categ_title + "_" + format_title
                        dataset.remote_id = unidecode("igss_" + combined_title)
                        self.datasets.append(dataset)

                if "<div class=\"accordion\">" in decode_div_res:
                    self.get_datasets(div_resource, dataset_title, True)
                    pass
                else:
                    resources = self.__get_resources(div_resource)
                    dataset = Dataset_T(dataset_title, resources)
                    categ_title = self.__format_title_for_id()
                    format_title = dataset.format_title_for_id()
                    combined_title = categ_title + "_" + format_title
                    dataset.remote_id = unidecode("igss_" + combined_title)
                    self.datasets.append(dataset)
                    pass
                pass
            pass
        pass

    def __format_title_for_id(self):
        category_title = self.title

        #print(category_title)

        # category_title = unicodedata.normalize('NFD', category_title)
        # category_title = category_title.encode('ascii', 'ignore')
        category_title = str(category_title)
        category_title = category_title.lower()
        category_title = category_title.replace("-", " ")
        category_title = category_title.replace(" ", "_")

        return category_title