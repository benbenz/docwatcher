from urllib.parse import urlparse
from crawler.handlers import get_filename , get_extension , LocalStorageHandler , FileStatus
import os
import csv
import uuid

# load django stuff
# MAKE SURE ROOT/www is also in the PYTHONPATH !!!
os.environ['DJANGO_SETTINGS_MODULE'] = 'docwatcher.settings'
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
# now we can load the model :)
# note that we don't have www.docs.models (because of PYTHONPATH)
from docs.models import Document

def get_doctype(response):
    extension   = get_extension(response).lower()

    if extension == '.pdf':
        return Document.DocumentType.PDF
    elif extension == '.txt':
        return Document.DocumentType.TEXT
    elif extension == '.doc':
        return Document.DocumentType.DOC
    elif extension == '.docx':
        return Document.DocumentType.DOC
    elif extension == '.html':
        return Document.DocumentType.HTML
    return Document.DocumentType.UNKNOWN

class AllInOneHandler(LocalStorageHandler):

    def __init__(self, directory, subdirectory):
        super().__init__(directory,subdirectory)

    def handle(self, response, depth, previous_url, *args, **kwargs):
        path , file_status = super().handle(response,*args,**kwargs)

        # the file already existed
        if file_status == FileStatus.EXISTING:
            return path , file_status 

        parsed_url  = urlparse(response.url)
        domain_name = parsed_url.netloc
        filename    = get_filename(parsed_url,response)

        doc = Document(
            domain      = domain_name , 
            url         = response.url , 
            referer     = previous_url or '' ,
            depth       = depth ,
#            record_date = AUTO
            remote_name = filename ,

            # Content: HTML/PDF + file
            doc_type    = get_doctype(response) ,
            title       = filename ,
            body        = response.content ,
            size        = response.headers.get('Content-Length') or len(response.content) ,
            local_file  = path #local_name
        )
        # save the new entry
        doc.save()

        return path , file_status  

class DBStatsHandler:

    def __init__(self,domain):
        self.domain = domain

    def get_handled_list(self):
        list_handled = []
        if self.domain:
            for doc in Document.objects.filter(domain=self.domain):
                list_handled.append(doc.local_file)
        return list_handled

    def handle(self, response, depth, previous_url, local_name, *args, **kwargs):
        # the job has already been done by the storage handler
        pass

    def get_filenames(self,response):
        result = []
        for doc in Document.objects.filter(url=response.url):
            result.append(doc.local_file)
        return result