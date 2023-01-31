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
        canon_search = jcs.canonicalize(search)
        try:
            return DocumentSearch.objects.get(search_params=canon_search)
        except DocumentSearch.DoesNotExist:
            return None

    def save_search(self,search):
        canon_search = jcs.canonicalize(search)
        doc_search = DocumentSearch()
        doc_search.search_params = canon_search
        doc_search.hit_count     = 0 
        doc_search.save()
        return doc_search

    def perform_search(self,search_obj):
        patterns   = search_obj.search_params.get('patterns',None)
        patterns_x = search_obj.search_params.get('exclude_patterns',None)
        is_raw     = search_obj.search_params.get('raw',False)
        domains    = search_obj.search_params.get('domains',None)
        domains_x  = search_obj.search_params.get('exclude_domains',None)
        doc_types  = search_obj.search_params.get('doc_types',None)
        level      = search_obj.search_params.get('level',1)

        if not pattern:
            return None

        query_set = SearchQuerySet()
        if pa
