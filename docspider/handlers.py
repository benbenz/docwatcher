from urllib.parse import urlparse
from crawler.handlers import get_filename , get_content_type , LocalStorageHandler , FileStatus , bcolors
# .pdf
from PyPDF4 import PdfFileReader
# .doc , .docx
from docx import Document as WordDocument
# .ppt , .pptx , .pptm
from pptx import Presentation
# .rtf
from striprtf.striprtf import rtf_to_text
# .html
from bs4 import BeautifulSoup

import os
import csv
import uuid
import traceback

# load django stuff
# MAKE SURE ROOT/www is also in the PYTHONPATH !!!
os.environ['DJANGO_SETTINGS_MODULE'] = 'docwatcher.settings'
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
# now we can load the model :)
# note that we don't have www.docs.models (because of PYTHONPATH)
from docs.models import Document

def get_doctype_by_content(response):
    try:
        content = response.text.strip()
        if "<!doctype html>" in content[:64]:
            return Document.DocumentType.HTML
        elif "%PDF-" in content[:32]:
            return Document.DocumentType.PDF
        elif "word/" in content[:32]:
            return Document.DocumentType.DOCX
    except:
        pass
    return Document.DocumentType.UNKNOWN

def get_doctype_by_extension(file_extension):
    if file_extension==".pdf" :
        return Document.DocumentType.PDF
    elif file_extension==".html":
        return Document.DocumentType.HTML
    elif file_extension=="text/plain":
        return Document.DocumentType.TEXT
    elif file_extension=="application/rtf":
        return Document.DocumentType.RTF
    elif file_extension=="application/msword":
        return Document.DocumentType.DOC
    elif file_extension==".docx":
        return Document.DocumentType.DOCX
    elif file_extension==".ppt":
        return Document.DocumentType.PPT
    elif file_extension==".pptx":
        return Document.DocumentType.PPTX
    elif file_extension==".pptm":
        return Document.DocumentType.PPTM   
    return Document.DocumentType.UNKNOWN    

def get_doctype_by_url(response):
    try:
        last_part = response.url.rsplit('/', 1)[-1]
        file_name, file_extension = os.path.splitext(last_part)
        if file_extension:
            file_extension = file_extension.lower()
            return get_doctype_by_extension(file_extension)
    except:
        pass
    return Document.DocumentType.UNKNOWN        

def get_doctype(response,try_all_methods=False):
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

    if try_all_methods:
        doctype = get_doctype_by_content(response)
        if doctype != Document.DocumentType.UNKNOWN:
            return doctype
        doctype = get_doctype_by_url(response)
        if doctype != Document.DocumentType.UNKNOWN:
            return doctype

    return Document.DocumentType.UNKNOWN

def reset_eof_of_pdf_return_stream(pdf_stream_in:list):
    # find the line position of the EOF
    found_it = False
    for i, x in enumerate(pdf_stream_in[::-1]):
        if b'%%EOF' in x:
            actual_line = len(pdf_stream_in)-i
            print(f'EOF found at line position {-i} = actual {actual_line}, with value {x}')
            found_it = True
            break

    # return the list up to that point
    if found_it:
        return pdf_stream_in[:actual_line]   
    else:
        pdf_stream_in.append(b'%%EOF')
        return pdf_stream_in

def recover_PDF(path):
    with open(path, 'rb') as p:
        txt = (p.readlines())
        # get the new list terminating correctly
        txtx = reset_eof_of_pdf_return_stream(txt)
        # write to new pdf
        tmp_file = str(uuid.uuid4())[:8] + ".pdf"
        with open(tmp_file, 'wb') as tmpf:
            tmpf.writelines(txtx)
        try:
            pdf = PdfFileReader(tmp_file)
            os.remove(tmp_file)
            return pdf
        except Exception as e:
            os.remove(tmp_file)
            raise e
    return None

class AllInOneHandler(LocalStorageHandler):

    def __init__(self, directory, subdirectory):
        #super().__init__(directory,subdirectory)
        super().__init__(directory,None) # we will dynamically use the netloc for the subdirectory

    def handle(self, response, depth, previous_url, *args, **kwargs):
        path , file_status = super().handle(response,*args,**kwargs)

        # the file already existed
        if file_status == FileStatus.EXISTING:
            return path , file_status 
        elif file_status == FileStatus.SKIPPED:
            return path , file_status

        parsed_url  = urlparse(response.url)
        domain_name = parsed_url.netloc
        filename    = get_filename(parsed_url,response)
        doc_type    = get_doctype(response)

        title       = filename
        num_pages   = -1 
        body        = response.content
        needs_ocr   = False
        has_error   = False

        if doc_type == Document.DocumentType.PDF:
            try:
                with open(path, 'rb') as f:
                    pdf         = PdfFileReader(f)
                    information = pdf.getDocumentInfo()
                    num_pages   = pdf.getNumPages()
                    title       = information.title or filename
                    body        = "\n".join([p.extractText() for p in pdf.pages])
                    if body == '':
                        needs_ocr = True
            except Exception as e:
                msg = str(e)
                if "EOF" in msg:
                    try:
                        pdf         = recover_PDF(path)
                        information = pdf.getDocumentInfo()
                        num_pages   = pdf.getNumPages()
                        title       = information.title or filename
                        body        = "\n".join([p.extractText() for p in pdf.pages])    
                    except Exception as e2:
                        has_error = True
                        print(bcolors.FAIL,"ERROR recovering file",response.url,path,e2,bcolors.CEND)
                        #traceback.print_exc()

                else:
                    has_error = True
                    print(bcolors.FAIL,"ERROR processing file",path,e,bcolors.CEND)
                    #traceback.print_exc()

        elif doc_type in [Document.DocumentType.DOC , Document.DocumentType.DOCX]:
            try:
                with open(path,'rb') as f:
                    worddoc  = Document(f)
                    body     = "\n".join([p.text for p in worddoc.paragraphs])
            except Exception as e:
                has_error = True
                print(bcolors.FAIL,"ERROR processing file",path,e,bcolors.CEND)
                traceback.print_exc()

        elif doc_type in [Document.DocumentType.PPT , Document.DocumentType.PPTX , Document.DocumentType.PPTM]:
            try:
                with open(path,'rb') as f:
                    prez  = Presentation(f)
                    body  = ""
                    for slide in prez.slides:
                            for shape in slide.shapes:
                                if hasattr(shape, "text"):
                                    body += shape.text + '\n'
            except Exception as e:
                has_error = True
                print(bcolors.FAIL,"ERROR processing file",path,e,bcolors.CEND)
                traceback.print_exc()
        
        elif doc_type == Document.DocumentType.RTF:
            body = rtf_to_text(body)

        elif doc_type == Document.DocumentType.HTML:
            try:
                soup  = BeautifulSoup(body,'html.parser')
                body  = soup.get_text()
                title = soup.title.string
            except Exception as e:
                has_error = True
                print(bcolors.FAIL,"ERROR processing file",path,e,bcolors.CEND)
                traceback.print_exc()

        doc = Document(
            domain      = domain_name , 
            url         = response.url , 
            referer     = previous_url or '' ,
            depth       = depth ,
#            record_date = AUTO
            remote_name = filename ,

            # Content: HTML/PDF + file
            doc_type    = doc_type ,
            title       = title or filename,
            body        = body ,
            size        = response.headers.get('Content-Length') or len(response.content) ,
            num_pages   = num_pages ,
            needs_ocr   = needs_ocr ,
            has_error   = has_error ,
            local_file  = path #local_name
        )
        # save the new entry
        #print("saving new entry ...")
        doc.save()
        #print("done saving.")

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