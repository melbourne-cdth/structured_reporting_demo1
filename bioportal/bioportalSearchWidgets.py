"""Includes bioportalSearchWidgets class.

bioportalSearchWidgets uses ipywidgets to create search boxes for the purpose
of collecting metadata via searching the Bioportal ontology API.

"""

import ipywidgets as widgets
import requests
from IPython.display import display
from .metadataCollector import MetadataCollector


class BioportalSearchWidgets:
    """Uses ipwidgets to create search boxes.

    Provides a template for a search box and a results box.
    Connects to the bioportal REST API to return ontology information.

    Use of this class must adhear to a strict call order as follows.

    1) Initialize object to provide callback.
    2) add_search_widget, this may be called as many times as needed to
       add the necessary metadata collecting widgets.
    3) display_widgets, this displays the already created widgets which step
       2 created.

    """

    def __init__(self, submit_callback,
                 bioportal_api_key='efa3babf-b23c-4399-89f7-689bb9d576fb'):
        """Initialize variables, provide valid api key for bioportal.

        param: submit_callback: Callback to be executed on submit. The
               single parameter to the callback is a dictionary whose keys
               are the topics and whose values are a dictionary whose keys
               are selected keywords and whose values are bioportal responses
               for the keyword.

        """
        self._widgets = []
        self._submit_callback = submit_callback
        self._apply_widget = None
        self._api_url = 'http://data.bioontology.org/'
        self._key = bioportal_api_key
        self._headers = {'Authorization': 'apikey token=' + self._key}
    
    def add_search_widget(self, topic, ontologies, required=False):
        mc = MetadataCollector(topic, ontologies, required, self.__value_changed_callback)
        self._widgets.append(mc)
        
    def GET(self, url, params=None):
        """Convenient method for requests.get().

        Headers already included in call. JSON response data is returned.

        :param url: The website to access JSON data from.
        :param params: Parameters for the REST request.

        """
        request = requests.get(url, headers=self._headers, params=params)
        return request.json()

    def display_widgets(self):
        self._apply_widget = widgets.Button(description='Submit',
                                            disabled=True)
        for widget in self._widgets:
            widget.display()
        display(self._apply_widget)
        self._apply_widget.on_click(self.__on_apply_clicked)

    def __value_changed_callback(self):
        for widget in self._widgets:
            if widget.is_required():
                if not widget.has_results():
                    self._apply_widget.disabled = True
                    return
        self._apply_widget.disabled = False

    def __on_apply_clicked(self, change):
        final_results = dict()
        for widget in self._widgets:
            if widget.has_results():
                results = widget.get_results()
                topic = widget.get_topic()
                final_results[topic] = results
        self._submit_callback(final_results)


