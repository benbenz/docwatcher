from urllib.parse import urlparse
from crawler.handlers import get_filename , get_content_type 
from crawler.core import FileStatus 
from crawler.helper import clean_url
from crawler.log import logger

import os
import re
import traceback
import json
import jcs
from email.utils import parsedate_to_datetime
from datetime import datetime, timedelta
from django.utils.timezone import make_aware
from django.core.mail import EmailMultiAlternatives
from django.conf import settings


# load django stuff
# MAKE SURE ROOT/www is also in the PYTHONPATH !!!
os.environ['DJANGO_SETTINGS_MODULE'] = 'docwatcher.settings'
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
# now we can load the model :)
# note that we don't have www.docs.models (because of PYTHONPATH)
from docs.models import Document , DocumentSearch
from django.db.models import Q
from django.db import models
from haystack import indexes        
from haystack.query import SearchQuerySet

class DocumentSearcher:

    def __init__(self):
        try:
            with open('config.json','r') as jsonfile:
                self.config = json.load(jsonfile)
        except:
            pass
    

    def get_search(self,search):
        canon_search = json.loads(jcs.canonicalize(search))
        try:
            return DocumentSearch.objects.prefetch_related('hits').get(params=canon_search)
        except DocumentSearch.DoesNotExist:
            return None

    def save_search(self,search):
        canon_search = json.loads(jcs.canonicalize(search))
        doc_search = DocumentSearch()
        doc_search.params = canon_search
        doc_search.hit_count = 0 
        doc_search.save()
        return doc_search

    def perform_search(self,search_obj):
        patterns   = search_obj.params.get('patterns',None)
        patterns_x = search_obj.params.get('exclude_patterns',None)
        domains    = search_obj.params.get('domains',None)
        domains_x  = search_obj.params.get('exclude_domains',None)
        doc_types  = search_obj.params.get('doc_types',None)
        level      = search_obj.params.get('level',1)

        if not patterns:
            return None

        queryset = SearchQuerySet()
        for pattern in patterns or []:
            queryset= queryset.filter(content=pattern)
        for pattern_x in patterns_x or []:
            queryset = queryset.exclude(content=pattern_x)
        for domain in domains or []:
            queryset = queryset.filter(domain=domain)
        for domain_x in domains_x or []:
            queryset = queryset.exclude(domain=domain_x)
        for doc_type in doc_types or []:
            queryset = queryset.filter(doc_type=doc_type)

        return queryset.highlight()

    def mark_of_interest(self,docs):
        for doc in docs:
            doc.of_interest = True
        try:
            Document.objects.bulk_update(docs,['of_interest'])
        except Exception as e:
            logger.error("Error with bulk_update {0}".format(e))

    def get_document(self,id):
        try:
            return Document.objects.get(id=id)
        except Document.DoesNotExist:
            return None

    def mail(self,docs_add_dict,docs_rmv_dict,highlights=None):
        if len(docs_add_dict)==0 and len(docs_rmv_dict)==0:
            return
        
        if highlights is None:
            highlights = dict()

        from_email = settings.EMAIL_HOST_USER
        if not from_email:
            logger.critical("Email configuration invalid. Aborting sending email")
        domain  = from_email[from_email.index('@') + 1 : ]
        urlroot = "https://" + domain 
        subject = 'Matching documents from ' + from_email
        emails = self.config.get('emails') or []
        text_content = 'Des documents ont changés:\n'
        html_content = '<h2>Des documents ont chang&eacute;s</h2>'
        for search_name , docs_add in docs_add_dict.items():
            highlights_s = highlights.get(search_name)
            if not highlights_s:
                highlights_s = dict()
            docs_rmv = docs_rmv_dict.get(search_name)
            text_content += 'Recherche "'+search_name+'":\n'
            html_content += '<h3>Recherche "'+search_name+'":</h3>'
            if docs_add and len(docs_add)>0:
                text_content += 'Ajoutés:\n'
                html_content += '<h4>Ajoutés:</h4><ul>'
                for doc in docs_add:
                    title = str(doc.title or doc.remote_name or 'Sans titre')
                    text_content += '\n' + str(doc.domain)+': ' + title + ': ' + urlroot + doc.get_absolute_url()
                    html_content += '<li>'+str(doc.domain)+': <a href="'+urlroot+doc.get_absolute_url()+'">'+title+'</a></li>'
                    if highlights_s.get(doc.id):
                        highlight_text = highlights_s.get(doc.id)
                        highlight_text = highlight_text.replace('<em>','<span style="font-weight:800">')
                        highlight_text = highlight_text.replace('</em>','</span>')
                        html_content += '<div style="font-size:10px">'+highlight_text+'</div>'

                html_content += "</ul>"
            if docs_rmv and len(docs_rmv)>0:
                text_content += '\nEnlevés:'
                html_content += '<h4>Enlev&eacute;s:</h4><ul>'
                for doc in docs_rmv:
                    title = str(doc.title or doc.remote_name or 'Sans titre')
                    text_content += '\n' + str(doc.domain)+': '+title + ': ' + urlroot + doc.get_absolute_url()
                    html_content += '<li>'+str(doc.domain)+': <a href="'+urlroot+doc.get_absolute_url()+'">'+title+'</a></li>'
                html_content += "</ul>"
        msg = EmailMultiAlternatives(subject, text_content, from_email, emails)
        msg.attach_alternative(html_content, "text/html")
        msg.send()        
