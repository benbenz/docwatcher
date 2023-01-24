from urllib.parse import urlparse
from crawler.handlers import get_filename , get_content_type , LocalStorageHandler , FileStatus
# .pdf
from PyPDF4 import PdfFileReader
# .doc , .docx
from docx import Document as WordDocument
# .ppt , .pptx , .pptm
from pptx import Presentation
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
    content_type = get_content_type(response)
    if content_type=="application/pdf" :
        return Document.DocumentType.PDF
    elif content_type=="text/html":
        return Document.DocumentType.HTML
    elif content_type=="text/plain":
        return Document.DocumentType.TEXT
    elif content_type=="application/rtf":
        return Document.DocumentType.RTF
    elif content_type=="application/msword":
        return Document.DocumentType.DOC
    elif content_type=="application/vnd.openxmlformats" or content_type=="officedocument.wordprocessingml.document":
        return Document.DocumentType.DOCX
    elif content_type=="application/vnd.ms-powerpoint":
        return Document.DocumentType.PPT
    elif content_type=="application/vnd.openxmlformats-officedocument.presentationml.presentation":
        return Document.DocumentType.PPTX
    elif content_type=="application/vnd.ms-powerpoint.presentation.macroEnabled.12":
        return Document.DocumentType.PPTM
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
        doc_type    = get_doctype(response)

        title       = filename
        num_pages   = -1 
        body        = response.content

        if doc_type == Document.DocumentType.PDF:
            try:
                with open(path, 'rb') as f:
                    pdf         = PdfFileReader(f)
                    information = pdf.getDocumentInfo()
                    num_pages   = pdf.getNumPages()
                    title       = information.title
                    body        = "\n".join([p.extract_text() for p in pdf.pages])
            except:
                pass

        elif doc_type in [Document.DocumentType.DOC , Document.DocumentType.DOCX]:
            try:
                with open(path,'rb') as f:
                    worddoc  = Document(f)
                    body     = "\n".join([p.text for p in worddoc.paragraphs])
            except:
                pass

        elif doc_type in [Document.DocumentType.PPT , Document.DocumentType.PPTX , Document.DocumentType.PPTM]:
            try:
                with open(path,'rb') as f:
                    prez  = Presentation(f)
                    body  = ""
                    for slide in prez.slides:
                            for shape in slide.shapes:
                                if hasattr(shape, "text"):
                                    body += shape.text + '\n'
            except:
                pass

        doc = Document(
            domain      = domain_name , 
            url         = response.url , 
            referer     = previous_url or '' ,
            depth       = depth ,
#            record_date = AUTO
            remote_name = filename ,

            # Content: HTML/PDF + file
            doc_type    = doc_type ,
            title       = title ,
            body        = body ,
            size        = response.headers.get('Content-Length') or len(response.content) ,
            num_pages   = num_pages ,
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
                list_handled.append(doc.local_file.name)
        return list_handled

    def handle(self, response, depth, previous_url, local_name, *args, **kwargs):
        # the job has already been done by the storage handler
        pass

    def get_filenames(self,response):
        result = []
        for doc in Document.objects.filter(url=response.url):
            result.append(doc.local_file.name)
        return result