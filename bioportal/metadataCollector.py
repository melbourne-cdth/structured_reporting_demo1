"""Includes MetadataCollector class.

Responsible for keeping track of when widget values change or are selected.

"""

import ipywidgets as widgets
from IPython.display import display
import requests
import ipywidgets as ipw
from markdown import markdown
from jinja2 import Template
from collections import defaultdict
import datetime
import uuid
import json
import os

# When I naively tried to have ConceptSelector inherit from ipywidgets.HBox
# I lost all my interactivity with the Bioportal search. I couldn't figure out what
# magic method I needed to overload
class ConceptSelector(widgets.VBox):
    """Handle information inside the widgets."""

    def __init__(self, topic, ontologies, value_changed=None,
                 bioportal_api_key='',
                 subtree_root_id=None):
        """Provide bioportal key, create widgets.

        Create (but not display) needed widgets. If the topic is required
        before upload, highlight the text box red.

        :param topic: The topic name to be associated with the key words
        :param ontolgies: The ontolgies to be searched.
        :param required: Whether or not the topic is required to have at least
                         one key word added before upload.
        :param value_changed: Callback which is called everytime the first word
                              is added to an empty added words widget or when
                              the last word is removed from the added words
                              widget.
        :param bioportal_api_key: The key used to access the bioportal REST API

        """
        self._ontologies = ontologies
        self._subtree_root_id = subtree_root_id
        # self._results_info stores keywords as keys and bioportal
        # results as values
        self._results_info = dict()
        self._selected = None

        self._topic = widgets.Label(value=topic)
        self._search_input_widget = widgets.Text(value='', width='49%')
        self._search_results_widget = widgets.Select(options=[],
                                                     width='300')



        self._api_url = 'http://data.bioontology.org/'
        self._key = bioportal_api_key
        self._headers = {'Authorization': 'apikey token=' + self._key}
        super(ConceptSelector, self).__init__(children=[widgets.VBox([self._topic,
                                                                      self._search_input_widget]),
                                                        self._search_results_widget])

    def on_change(self, *args):
        pass

    def GET(self, url, params=None):
        """Convenient method for requests.get().

        Headers already included in call. JSON response data is returned.

        :param url: The website to access JSON data from.
        :param params: Parameters for the REST request.

        """
        request = requests.get(url, headers=self._headers, params=params)
        return request.json()


    def display(self, show=True):
        """Display the 5 widgets to be used for the topic(s)."""
        if show:
            display(self)
        # display(widgets.VBox([self._topic, self._search_input_widget]))
        # display(self._search_results_widget)
        self._search_input_widget.observe(self.__search_value_changed,
                                          names='value')
        self._search_results_widget.observe(self.on_change,
                                            names='value')


    def __search(self, search_term, ontologies):
        """Search specified ontologies using bioportals REST API.

        Returns list of suggested keywords and a dictionary with the
        keywords as keys and bioportal response data as values.

        :param searchTerm: The term to search bioportal with.
        :param ontologies: A list of ontology IDs to search.

        """
        parameters = {'ontology': ontologies,
                      'suggest': 'true', 'pagesize': 30,
                       'include': 'prefLabel,synonym,definition'}
        if self._subtree_root_id:
            parameters["subtree_root_id"] = self._subtree_root_id
        search = self._api_url + 'search?q=' + search_term

        data = self.GET(search, params=parameters)
        nameList = []
        nameDict = {}
        if "collection" in data:
            collection = data["collection"]
        else:
            return (nameList, nameDict)

        for d in collection:
            nameDict[d["prefLabel"]] = d
            nameList.append(d["prefLabel"])

        return (nameList, nameDict)

    def __search_value_changed(self, change):
        new_keyword = change['new'].strip()
        if new_keyword:
            keywords, info = self.__search(new_keyword, self._ontologies)
            if len(keywords) == 0:
                temp = ['NO RESULTS FOUND']
                self._search_results_widget.options = temp
            else:
                self._search_results_widget.options = keywords
                self._results_info = info
        else:
            temp = []
            self._search_results_widget.options = temp
            self._selected = None


    @property
    def term(self):
        return self._search_results_widget.value

    @property
    def id(self):
        return self._results_info[self.term]['@id']


class RadFinding(ipw.VBox):
    def __init__(self, apiKey):
        self.anatomy = ConceptSelector('Anatomical Location', "RADLEX", 
                                       bioportal_api_key=apiKey,
                                       subtree_root_id="http://radlex.org/RID/RID3")
        self.finding = ConceptSelector('Finding', "RADLEX", bioportal_api_key=apiKey,
                                       subtree_root_id="http://radlex.org/RID/RID5")
        self.modifier = ConceptSelector('Modifier', "RADLEX", bioportal_api_key=apiKey,
                                       subtree_root_id="http://radlex.org/RID/RID6")
        super(RadFinding, self).__init__(children=[self.anatomy, self.finding, self. modifier])

    def get_finding(self):
        return ((self.anatomy.term, self.anatomy.id), 
                (self.finding.term, self.finding.id), 
                (self.modifier.term, self.modifier.id))
    def display(self, show=True):
        self.anatomy.display(show=show)
        self.finding.display(show=show)
        self.modifier.display(show=show)
        
class RadDiagnosis(ipw.VBox):
    def __init__(self, apiKey):

        self.diagnosis = ConceptSelector('Diagnosis', "DOID", bioportal_api_key=apiKey,
                subtree_root_id=None)
        self.modifier = ConceptSelector('Modifier', 'RADLEX', bioportal_api_key=apiKey,
                subtree_root_id="http://radlex.org/RID/RID29")
        
        super(RadDiagnosis, self).__init__(children=[self.diagnosis, self.modifier])

    def get_diagnosis(self):
        return ((self.diagnosis.term, self.diagnosis.id), (self.modifier.term, self.modifier.id))

    def display(self, show=True):
        self.diagnosis.display(show=show)
        self.modifier.display(show=show)

class RadiologyReport(ipw.HBox):
    rt = Template("""
<h1> REPORT </h1>
<h3> DATE: {{date}}</h3>
<h3> PROCEDURES: </h3>

<ul>
{% for p in procedures %}
   <li> <a href="{{p[1]}}">{{p[0]}}</a> </li>
{% endfor %}
</ul>

<h3> FINDINGS: </h3>

<ul>
{% for f in findings %}
   <li> <a href="{{f[0][1]}}">{{f[0][0]}}</a>: <a href="{{f[1][1]}}">{{f[1][0]}}</a>:  <a href="{{f[2][1]}}">{{f[2][0]}}</a></li>
{% endfor %}
</ul>

<h3> DIAGNOSES: </h3>

<ul>
{% for d in diagnoses %}
   <li> <a href="{{d[0][1]}}">{{d[0][0]}}</a>: <a href="{{d[1][1]}}">{{d[1][0]}} </li>
{% endfor %}
</ul>

<h3>SIGNED:</h3>

{{name}}
""")
    def __init__(self, apiKey, rdir=None):
        if not rdir:
            rdir = "."
        self._rdir = rdir
        
        self._report = defaultdict(list)
        self.report = ipw.HTML()
        
        self.date = ipw.DatePicker(description="Procedure Date", value=datetime.datetime.today().date())
        self.date.observe(self.render_report)
        
        self.provider = ipw.Text(description="Provider")
        self.date.observe(self.render_report)
        
        self.addProc = ipw.Button(description='Add Procedure',)
        self.addProc.on_click(self.add_proc)
        self.remProc = ipw.Button(description='Remove Procedure',)
        self.remProc.on_click(self.rem_proc)
        procBox = ipw.HBox([self.addProc, self.remProc])

        self.procs = ConceptSelector('Procedure', ["RADLEX"], bioportal_api_key=apiKey,
                subtree_root_id="http://radlex.org/RID/RID1559")

        # findings
        self.addFinding = ipw.Button(description='Add Finding')
        self.addFinding.on_click(self.add_finding)
        self.remFinding = ipw.Button(description='Remove Finding')
        self.remFinding.on_click(self.rem_finding)
        findBox = ipw.HBox([self.addFinding, self.remFinding])

        self.findings = RadFinding(apiKey)

        # diagnosis

        self.addDiagnosis = ipw.Button(description='Add Diagnosis')
        self.addDiagnosis.on_click(self.add_diagnosis)
        self.remDiagnosis = ipw.Button(description='Remove Diagnosis')
        self.remDiagnosis.on_click(self.rem_diagnosis)
        diagBox = ipw.HBox([self.addDiagnosis, self.remDiagnosis])

        # signature
        self.diagnosis = RadDiagnosis(apiKey)
        self.create = ipw.Button(description='Create Report')
        self.create.on_click(self.create_report)
        tab_titles = ["Admin", "Procedures", "Findings", "Diagnoses", "Report"]

        self.tab = ipw.Tab([ipw.HBox([self.date, self.provider]), 
                            ipw.VBox([procBox, self.procs], layout=ipw.Layout(border="solid")),
                            ipw.VBox([findBox, self.findings], layout=ipw.Layout(border="dashed")),
                            ipw.VBox([diagBox, self.diagnosis], layout=ipw.Layout(border="solid")),
                            ipw.VBox([self.create, self.report])], 
                               layout=ipw.Layout(width="100%"))
        for i in range(len(self.tab.children)):
            self.tab.set_title(i,tab_titles[i])

        super(RadiologyReport, self).__init__(children=[self.tab], 
                                                        layout=ipw.Layout(border="solid"))
    def add_proc(self, *args):
        self._report["procedures"].append((self.procs.term, self.procs.id))
        self.render_report()
    def rem_proc(self, *args):
        _ = self._report["procedures"].pop()
        self.render_report()    
    
    def add_finding(self, *args):
        self._report["findings"].append(self.findings.get_finding())
        self.render_report()
    def rem_finding(self, *args):
        _ = self._report["findings"].pop()
        self.render_report() 
        
    def add_diagnosis(self, *args):
        self._report["diagnoses"].append(self.diagnosis.get_diagnosis())
        self.render_report()
    def rem_diagnosis(self, *args):
        self._report["diagnoses"].pop()
        self.render_report()
        
    def display(self):
        display(self)
        self.procs.display(show=False)
        self.findings.display(show=False)
        self.diagnosis.display(show=False)
        
    def create_report(self, *args):
        fname = str(uuid.uuid1()) + ".json"
        with open(os.path.join(self._rdir,fname), "w") as f:
            json.dump(self._report, f)

    
    def render_report(self, *args):
        try:
            date = self.date.value.strftime("%Y-%m-%d")
        except Exception as error:
            date = str(error)
        self.report.value = \
        self.rt.render(date=date,
                       procedures = self._report["procedures"],
                       findings = self._report["findings"],
                       diagnoses = self._report["diagnoses"],
                       name=self.provider.value)
        
        
    
        


