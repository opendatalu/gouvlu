from udata.harvest.backends.base import BaseBackend
from udata.models import Resource, License
import feedparser

import os, ssl
import io, json
import subprocess
import requests
from bs4 import BeautifulSoup
from unidecode import unidecode
from urllib.parse import urlencode, urlparse, parse_qsl, urlunparse

from time import sleep

class STATECBackend(BaseBackend):

    display_name = 'STATEC Harvester'

    def initialize(self):
        working_link = "https://statistiques.public.lu/fr/"
        if working_link == self.source.url:
            statec_harvester = STATECDatasetsHarvester(self.source.url)
            datasets = statec_harvester.extractDatasets()

            for dataset in datasets:
                resources = dataset.resources
                title = dataset.categoryname
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

    def __get_resources_as_dict(self, resources):
        new_resources = []
        for resource in resources:
            new_resource = {
                    'title': resource.title,
                    'url': resource.url,
                    'format': resource.format
            }
            new_resources.append(new_resource)
        return new_resources

    def process(self, item):
        kwargs = item.kwargs
        item.remote_id = kwargs['remote_id']
        dataset = self.get_dataset(item.remote_id)
        dataset.title = kwargs['title']
        tags = kwargs['tags']
        tags.append("statec-harvesting")
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
                    STATEC statistics portal  (category %s)""" % dataset.title

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

class STATECDatasetsHarvester():

    def __init__(self, url):
            self.statec_url = url
            self.rubrics = [
                "territoire-environnement", 
                "population-emploi", 
                "conditions-sociales", 
                "entreprises", 
                "economie-finances"
            ]
            self.datasets = []
    pass

    def curlMainRubricHTMLContent(self, rubric):
        status, output = subprocess.getstatusoutput("curl --silent " + self.statec_url + "" + rubric +"/index.html")
        soup = BeautifulSoup(output, "html.parser")
        return soup

    def getSubContent(self, link):
        status, output = subprocess.getstatusoutput(link)  
        soup = BeautifulSoup(output, "html.parser")
        return self.getSubCategories(soup)

    def getMainCategoryName(self, soup):
        contentBody = soup.find(id="contentBody")
        categoryNameBody = contentBody.find_all("h1")
        removal_list = [' ', '\t', '\n', '\r\n']
        for s in removal_list:
            mainCategoryName = categoryNameBody[0].getText().replace(s, '')
        return mainCategoryName

    def getSubCategories(self, soup):
        subcategoriesBox = soup.find(id="subcategoriesBox")
        subcategories = subcategoriesBox.find_all("a")
        return subcategories

    def getReportFolderLink(self, rubric, subcategorie):
        if "index.html" in subcategorie.get('href'):
            link = "curl --silent https://statistiques.public.lu/fr/" + rubric + "/" + subcategorie.get('href')
            cleanLink = link.replace("&", "'&'")
            pass
        else:
            link = "curl --silent https://statistiques.public.lu/" + subcategorie.get('href')
            cleanLink = link.replace("&", "'&'")
            pass
        return cleanLink

    def getRFPathNumber(self, cleanlink):
        rfPathNumber = cleanlink.split("RFPath=")[1]
        return rfPathNumber

    def getCurlSubFolderLink(self, link):
        newlink = link.replace("&", "'&'")
        cleanlink = newlink.replace("http://www.", "https://")
        return "curl --silent " + cleanlink

    def getCurlTableauxCartesLink(self, rubric, link):
        return "curl --silent https://statistiques.public.lu/fr/" + rubric + "/rp2011/" + link

    def getResourcesTableauxCartes(self, link):
        status, output = subprocess.getstatusoutput(link)  
        soup = BeautifulSoup(output, "html.parser")
        readspeaker = soup.find(id="readspeaker")
        resourcesTableauxCartes = readspeaker.find_all("a")
        return resourcesTableauxCartes

    def returnDocumentType(self, internalFileTitle):
        documentType = ""
        if "Fichier xlsx" in internalFileTitle:
            documentType = "xlsx"
            pass
        else:
            if "Rapport en tableau" in internalFileTitle:
                documentType = "csv"
                pass
            else:
                if "Document PDF Adobe" in internalFileTitle:
                    documentType = "pdf"
                    pass
                else:
                    if "Feuille de calcul Excel" in internalFileTitle:
                        documentType = "xls"
                        pass
                    else:
                        documentType = "link"
                        pass
                pass
            pass
        return documentType

    def extractDatasets(self):
        print("Begin Harvest: " + self.statec_url)
        datasets = []

        for rubric in self.rubrics:
            print("Extracting from: " + rubric)
            # sleep 10 seconds so that statistiques.public.lu doesn't break down
            # sleep(10)

            soup = self.curlMainRubricHTMLContent(rubric)

            mainCategoryName = self.getMainCategoryName(soup)

            subCategories = self.getSubCategories(soup)

            # Get SubCategories for each rubric
            for subcategory in subCategories:
                link = self.getReportFolderLink(rubric, subcategory)
                subCategoryName = subcategory.getText()

                # sleep 10 seconds so that statistiques.public.lu doesn't break down
                # sleep(10)
                subCategoriesResources = self.getSubContent(link)

                subResourcesDict = {}
                subFolderList = []

                dataset = DatasetTemplate(subCategoryName)

                # Get each resource for a subcategory and curl eventual subFolder content
                for subCategoriesResource in subCategoriesResources:
                    subCategoriesResourceName = subCategoriesResource.getText()
                    subFolderLink = subCategoriesResource.get("href")

                    subFolder = {}

                    subFolder["link"] = subFolderLink
                    subFolder["parentCategory"] = subCategoryName
                    subFolder["resourceName"] = subCategoriesResourceName

                    # If RFPath is present, a subFolder can be curled for this specific subcategory
                    if "RFPath=" in subFolderLink and "index.html" not in subFolderLink:
                        # sleep(10)
                        subFolderList.append(subFolder)
                    else:
                        # print("---------------------------------------------------------------------")
                        # print(subCategoriesResource.get("href"))
                        # print(subCategoryName)
                        # print(subCategoriesResource.getText())
                        # print(subCategoriesResource.get("title"))

                        resourceInternalTitle = subCategoriesResource.get("title")

                        # Search for later reoccuring nested resources
                        doubledResources = {}
                        
                        for subFolderContentNew in subCategoriesResources:
                            if "ReportFolder.aspx" not in subFolderContentNew.get("href"):
                                doubledResources[subFolderContentNew.get("href")] = subFolderContentNew.getText()

                        docType = self.returnDocumentType(resourceInternalTitle)

                        resource = ResourceTemplate(subCategoryName + "/" + subCategoriesResourceName, 
                                                    subFolderLink, 
                                                    "", 
                                                    docType)
                        dataset.addResource(resource)

                        subResourcesDict[subCategoriesResource.get("href")] = subCategoriesResourceName
                        pass
                    pass

                    if "index.html" in subFolderLink:
                        # sleep(10)
                        
                        tableauxCarteslink = self.getCurlTableauxCartesLink(rubric, subFolderLink)
                        resourcesTableauxCartes = self.getResourcesTableauxCartes(tableauxCarteslink)
                        
                        # print("---Tableaux et Cartes---")
                        mainCategoryName = subCategoryName + "/" + subCategoriesResourceName
                        # print(mainCategoryName)
                        dataset = DatasetTemplate(mainCategoryName)
                        for resourceTableauCarte in resourcesTableauxCartes:
                            if (resourceTableauCarte.get("href") != None and 
                                "http://www.statistiques.public.lu/stat/" in resourceTableauCarte.get("href")):
                                # print(resourceTableauCarte.get("href"))
                                # print(resourceTableauCarte.getText())

                                docType = self.returnDocumentType(resourceTableauCarte.get("title"))

                                resource = ResourceTemplate(resourceTableauCarte.getText(), 
                                                            resourceTableauCarte.get("href"), 
                                                            subCategoriesResourceName, 
                                                            docType)
                                dataset.addResource(resource)
                            pass
                        if dataset.resources:
                            datasets.append(dataset)
                    pass

                if dataset.resources and dataset not in datasets:
                    datasets.append(dataset)
                    pass
                
                subSubResourcesDict = {}
                subSubFolderList = []

                for subFolder in subFolderList:
                    curlSubFolderLink = self.getCurlSubFolderLink(subFolder["link"])
                    subFolderContents = self.getSubContent(curlSubFolderLink)
                    # print("---------------------------------------------------------------------")
                    # print("---SubFolder---")
                    # print(subFolder["parentCategory"] + "/" + subFolder["resourceName"])

                    subFolderParentCategoryName = subFolder["parentCategory"] + "/" + subFolder["resourceName"]
                    dataset = DatasetTemplate(subFolderParentCategoryName)
        
                    # Get SubFolderResources for this subcategory
                    for subFolderContent in subFolderContents:

                        subFolderContentLink = subFolderContent.get("href")
                        subFolderContentLinkNoRFPath = subFolderContentLink.replace(
                            "RFPath="+self.getRFPathNumber(subFolder["link"]), "")

                        # Handle the reoccurrence of previous nested data by checking if they are not in the dictionnary
                        if ("RFPath="+self.getRFPathNumber(subFolder["link"]) in subFolderContentLink and 
                                subFolderContentLinkNoRFPath not in subResourcesDict.keys()):

                            subSubFolderRFPath = subFolderContent.get("href").split(
                                "RFPath=" + self.getRFPathNumber(subFolder["link"]))[1]
                            # print(subSubFolderRFPath)
                            if subSubFolderRFPath != "":
                                dataset = DatasetTemplate(subFolderParentCategoryName)

                                # Search for later reoccuring nested resources
                                nestedResources = {}
                                for subFolderContentNew in subFolderContents:
                                    if "ReportFolder.aspx" not in subFolderContentNew.get("href"):
                                        nestedResources[subFolderContentNew.get("href")] = subFolderContentNew.getText()

                                # Only perform curl on folders
                                if "ReportFolder.aspx" in subFolderContent.get("href"):
                                    link = self.getCurlSubFolderLink(subFolderContent.get("href"))
                                    subSubCategoryName = subcategory.getText()
                                    subSubCategoriesResources = self.getSubContent(link)

                                    # print("---SubSubFolder---")                            
                                    for subSubCategoriesResource in subSubCategoriesResources:
                                        subSubFolderNoRFPath = subSubCategoriesResource.get("href").split("%")[0]
                                        # Only display new resources, no Folders and no reoccuring datasets
                                        if ("ReportFolder.aspx" not in subSubCategoriesResource.get("href") 
                                            and subSubFolderNoRFPath not in nestedResources.keys()):
                                            # print("--")
                                            # print(subSubCategoriesResource.get("href"))
                                            # print(subFolderParentCategoryName + "/" + subFolderContent.getText())
                                            # print(subSubCategoriesResource.getText())
                                            # print("--")

                                            docType = self.returnDocumentType(subSubCategoriesResource.get("title"))

                                            resource = ResourceTemplate(subSubCategoriesResource.getText(), 
                                                                        subSubCategoriesResource.get("href"), 
                                                                        subFolderContent.getText(), 
                                                                        docType)
                                            dataset.addResource(resource)
                                            pass   
                                    dataset.setCategoryName(subFolderParentCategoryName + "/" + subFolderContent.getText())
                                    if dataset.resources:
                                        datasets.append(dataset)
                                    dataset = DatasetTemplate(subFolderParentCategoryName)
                            else:
                                subFolderNoRFPath = subFolderContent.get("href").split("&RFPath=")[0]
                                if ("ReportFolder.aspx" not in subFolderContent.get("href") and 
                                        subFolderNoRFPath not in doubledResources.keys()):
                                    # print("------------------------------")
                                    # print(subFolderContent.get("href"))
                                    # print(subFolderParentCategoryName)
                                    # print(subFolderContent.getText())

                                    docType = self.returnDocumentType(subFolderContent.get("title"))

                                    resource = ResourceTemplate(subFolderContent.getText(), 
                                                                subFolderContent.get("href"), 
                                                                subFolderParentCategoryName, 
                                                                docType)
                                    dataset.addResource(resource)
                                    pass

                                subSubResourcesDict[subFolderContentLink] = subFolderContent.getText()
                                pass

                        pass

                    # print("---------------")
                    # dataset.setCategoryName(subFolder["parentCategory"])
                    if dataset.resources:
                        datasets.append(dataset)
                    pass

        print("Finished Harvest: " + str(len(datasets)) + " datasets found!") 
        return datasets


class DatasetTemplate():

    def __init__(self, categoryname):
        self.categoryname = categoryname
        self.resources = []
        self.description = ""
        self.remote_id = unidecode("statec_" + self.__format_title_for_id(self.categoryname))
        self.tags = self.__generateTags()

    def __format_title_for_id(self, title):
        title = str(title)
        title = title.lower()
        title = title.replace("/", " ")
        title = title.replace("-", " ")
        title = title.replace(" ", "_")

        return title

    def __generateTags(self):
        categoryString = self.categoryname
        if "/" in self.categoryname:
            categoryString = self.categoryname.replace("/", " ")
            pass

        if "-" in self.categoryname:
            categoryString = categoryString.replace("-", " ")
            pass

        preTagList = categoryString.split(" ")

        tags = []
        for preTag in preTagList:
            if "(" in preTag:
                preTag = preTag.replace("(", "")

            if ")" in preTag:
                preTag = preTag.replace(")", "")

            if len(preTag) >= 5 or preTag == "Eau" or preTag == "Air" or preTag == "vie" or preTag == "prix":
                if preTag != "certains" and preTag != "(Base" and preTag != "2015)":
                    if "l\'" in preTag:
                        preTag = preTag.replace("l\'", "")

                    if "d\'" in preTag:
                        preTag = preTag.replace("d\'", "")
                    
                    preTag = self.removeAccents(preTag)
                    if preTag.lower() not in tags:
                        # print(preTag.lower())
                        tags.append(preTag.lower())
                        pass
                    pass
                pass
            pass
        return tags

    def removeAccents(self, text):
        return unidecode(text)


    def addResource(self, resource):
        self.resources.append(resource)

    def setCategoryName(self, categoryname):
        self.categoryname = categoryname
        self.tags = self.__generateTags()

    def getCategoryName(self):
        return self.categoryname

    def getResources(self):
        return self.resources

    def setDescription(self, description):
        self.description = description

    def getDescription(self):
        return self.description

    def printInJSONFormat(self):
        x = {
            "category": self.categoryname,
            "resources": self.resources
        }
        with io.open('datasets.json', 'a', encoding='utf-8') as f:
            y = json.dumps(x, ensure_ascii=False, indent=4)
            f.write(y)
            
        # print(y)

    def getResourcesinJSONFormat(self):
        jsonResources = []
        for resource in self.resources:
            jsonResources.append(resource.returnJSONFormat())
        return jsonResources
    pass

class ResourceTemplate():

    def __init__(self, title, url, subcategory, fileFormat):
        self.title = title
        self.originalURL = url
        self.subCategory = subcategory
        self.filetype = 'remote'
        self.format = fileFormat
        self.params = {
            'IF_DOWNLOADFORMAT': self.format,
            'IF_DOWNLOAD_ALL_ITEMS': 'yes'
        }

        if self.format == 'csv':
            if "tableView" in url:
                url = url.replace('tableViewHTML', 'download')
                url_parts = list(urlparse(url))
                query = dict(parse_qsl(url_parts[4]))
                query.update(self.params)
                url_parts[4] = urlencode(query)
                download_url = urlunparse(url_parts)
                self.url = download_url
            else:
                self.url = url
            pass
        else:
            self.url = url
        pass

    def returnJSONFormat(self):
        x = {
            "title": self.title,
            "url": self.url,
            "subCategory": self.subCategory
        }
        y = json.dumps(x, ensure_ascii=False, indent=4)
        return y
        pass

