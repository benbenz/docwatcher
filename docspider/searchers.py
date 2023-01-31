from urllib.parse import urlparse
from crawler.handlers import get_filename , get_content_type , FileStatus 
from crawler.helper import clean_url

import os
import re
import traceback
import json
import jcs
from email.utils import parsedate_to_datetime
from datetime import datetime, timedelta
from django.utils.timezone import make_aware

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

        return queryset
