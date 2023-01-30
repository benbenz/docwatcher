from urllib.parse import urlparse
from crawler.handlers import get_filename , get_content_type , LocalStorageHandler , FileStatus 
from crawler.core import CrawlerMode, bcolors
from crawler.helper import clean_url
# .pdf
#from PyPDF4 import PdfFileReader
from pypdf import PdfReader
# .doc , .docx
from docx import Document as WordDocument
# .ppt , .pptx , .pptm
from pptx import Presentation
# .rtf
from striprtf.striprtf import rtf_to_text
# .html
from bs4 import BeautifulSoup
# PDF image treatment
from PIL import Image

import os
import re
import csv
import uuid
import traceback
import subprocess
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
from docs.models import Document
from django.db.models import Q
from django.db import models

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
            pdf = PdfReader(tmp_file) #PdfFileReader(tmp_file)
            os.remove(tmp_file)
            return pdf
        except Exception as e:
            os.remove(tmp_file)
            raise e
    return None

def get_header_http_last_modified(response):
    last_modified = response.headers.get('Last-Modified') or response.headers.get('last-modified')
    if last_modified:
        last_modified = parsedate_to_datetime(last_modified)
    return last_modified

def get_header_http_length(response):
    return response.headers.get('Content-Length') or response.headers.get('content-length') or -1    

def get_header_http_encoding(response):
    return response.headers.get('Content-Encoding') or response.headers.get('content-encoding') or '' 

class AllInOneHandler(LocalStorageHandler):

    def __init__(self, directory, subdirectory):
        #super().__init__(directory,subdirectory)
        super().__init__(directory,None) # we will dynamically use the netloc for the subdirectory
        self.using_ocr = False
        try:
            import easyocr.easyocr
            print(bcolors.OKCYAN,"using OCR",bcolors.CEND)
            self.process_PDF_body = self.process_PDF_body_with_OCR
            self.using_ocr = True
        except (ImportError,ModuleNotFoundError) as e:
            print(bcolors.WARNING,"NOT using OCR",bcolors.CEND)
            self.process_PDF_body = self.process_PDF_body_NO_OCR
            print(e)
            #traceback.print_exc()

    def process_PDF_body_NO_OCR(self,url,path,pdf):
        needs_ocr = False
        
        body = "\n".join([p.extract_text() for p in pdf.pages])
        
        if body == '':
            print(bcolors.WARNING,"file needs OCR",bcolors.CEND)
            needs_ocr = True        

        return body , needs_ocr 

    def process_PDF_page_with_OCR(self,path,page,page_count,ocr_reader):
        
        pdffile = None

        if page is None:
            pdffile = open(path,'rb')
            pdf  = PdfReader(pdffile)
            page = pdf.pages[page_count]

        if ocr_reader is None:
            import easyocr.easyocr as easyocr
            ocr_reader = easyocr.Reader(['fr']) 
        
        debug = True
        if debug:
            print("processing page",page_count)
        page_body = page.extract_text()
        img_count = 0
        rotation  = page.get('/Rotate')
        found_extra_text = False
        file_root = str(uuid.uuid4())[:8]

        for image in page.images:
            if debug:
                print("processing image",img_count)
            filename = file_root + "_p"+str(page_count)+"_"+str(img_count)+".jpg"
            with open(image.name, "wb") as fp:
                fp.write(image.data)
            im0 = Image.open(image.name)
            t_img_name = "t"+image.name+".png"
            best_text  = None
            best_proba = -1
            for rotate in [-90,0,90] : # lets assume the document is not reversed....
                if debug:
                    print("rotation",rotate)
                im1 = im0.rotate(rotate, Image.NEAREST, expand = 1)
                im1.save(t_img_name)
                try:
                    result = ocr_reader.readtext(t_img_name)
                    proba_total = 0
                    text_total  = ''
                    num = 0 
                    for position , text , proba in result:
                        if proba > 0.3:
                            if debug:
                                print("text={0} (proba={1})".format(text,proba))
                            proba_total += proba
                            found_extra_text = True
                            text_total += text + '\n'
                            num += 1
                    if num>0:
                        proba_total /= num
                    proba_total *= len(text_total) # we gotta reward the fact we recognized more characters
                    if proba_total > best_proba:
                        best_proba = proba_total
                        best_text  = text_total
                except Exception as e:
                    print("Error while processing image",t_img_name,e)
                    #traceback.print_exc()
            if best_text is not None:
                if debug:
                    print("Found text:",best_text)
                page_body += '\n' + best_text 
            os.remove(image.name)
            os.remove(t_img_name)
            img_count += 1
        
        if pdffile is not None:
            pdffile.close()
        
        return page_body , found_extra_text

    def process_PDF_body_with_OCR(self,url,path,pdf):

        default_body = "\n".join([p.extract_text() for p in pdf.pages])
                    
        # 1) https://github.com/JaidedAI/EasyOCR
        # 2) https://github.com/PaddlePaddle/PaddleOCR
        # 3) https://github.com/madmaze/pytesseract

        #import easyocr 
        import easyocr.easyocr as easyocr
        ocr_reader = easyocr.Reader(['fr']) 

        found_extra_text = False

        # https://stackoverflow.com/questions/63983531/use-tesseract-ocr-to-extract-text-from-a-scanned-pdf-folders
        page_count = 0
        body = ''

        for page in pdf.pages: 
            process_args = [
                    'python',
                    'docspider/ocr.py',
                    self.directory or '',
                    self.subdirectory or '',
                    path,
                    page_count
            ]
            process = subprocess.run(process_args,capture_output=False)
            stdout  = process.stdout.read()
            stderr  = process.stderr.read()
            ex_code = process.returncode
            print(stdout,stderr,ex_code)
            # page_body , has_extra_text = self.process_PDF_page_with_OCR(path,page,page_count,ocr_reader)
            # if page_body:
            #    body += page_body + '\n'
            # found_extra_text = has_extra_text or found_extra_text
            page_count += 1
            
        if not found_extra_text:
            return default_body , False
        else:
            return body , False

    def process_response(self,path,response):
        parsed_url    = urlparse(response.url)
        domain_name   = parsed_url.netloc
        filename      = get_filename(parsed_url,response)
        doc_type      = get_doctype(response)
        title         = filename
        num_pages     = -1 
        body          = response.content
        needs_ocr     = False
        has_error     = False

        if doc_type == Document.DocumentType.PDF:
            try:
                with open(path, 'rb') as f:
                    pdf         = PdfReader(f) #PdfFileReader(f)
                    information = pdf.metadata #pdf.getDocumentInfo()
                    num_pages   = len(pdf.pages) #pdf.getNumPages()
                    title       = information.title or filename
                    body , needs_ocr = self.process_PDF_body(response.url,path,pdf)
                print("CLOSED FILE")
            except Exception as e:
                msg = str(e)
                if "EOF" in msg:
                    try:
                        pdf         = recover_PDF(path)
                        information = pdf.metadata #pdf.getDocumentInfo()
                        num_pages   = len(pdf.pages) #pdf.getNumPages()
                        title       = information.title or filename
                        body , needs_ocr = self.process_PDF_body(response.url,path,pdf)
                    except Exception as e2:
                        has_error = True
                        print(bcolors.FAIL,"ERROR recovering file",response.url,path,e2,bcolors.CEND)
                        #traceback.print_exc()

                else:
                    has_error = True
                    print(bcolors.FAIL,"ERROR processing file",path,e,bcolors.CEND)
                    traceback.print_exc()

        elif doc_type in [Document.DocumentType.DOC , Document.DocumentType.DOCX]:
            try:
                with open(path,'rb') as f:
                    worddoc  = Document(f)
                    body     = "\n".join([p.text for p in worddoc.paragraphs])
            except Exception as e:
                has_error = True
                print(bcolors.FAIL,"ERROR processing file",path,e,bcolors.CEND)
                #traceback.print_exc()

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
                #traceback.print_exc()
        
        elif doc_type == Document.DocumentType.RTF:
            body = rtf_to_text(body)

        elif doc_type == Document.DocumentType.HTML:
            try:
                soup  = BeautifulSoup(body,'html.parser')
                body  = soup.get_text()
                if soup.title:
                    title = soup.title.string
            except Exception as e:
                has_error = True
                print(bcolors.FAIL,"ERROR processing file",path,e,bcolors.CEND)
                #traceback.print_exc()        
        last_modified = get_header_http_last_modified(response)

        # cleanup extraneous spaces
        if body:
            if not isinstance(body,bytes) and not isinstance(body,bytearray):
                body = re.sub(r'([\s]{10,}|[\n]{3,})','\n\n',body)

        return domain_name , filename , doc_type , title , body , num_pages, needs_ocr , has_error , last_modified


    def handle(self, response, depth, previous_url, previous_id, *args, **kwargs):
        path , file_status , path_as_id = super().handle(response,*args,**kwargs)

        # the file already existed
        if file_status & FileStatus.EXISTING :
            try:
                # local_file path is unique
                the_doc = Document.objects.get(local_file=path)

                # let's also update the content to match the file (unless it's exactly the same file)
                if file_status & FileStatus.EXACT == 0:
                    domain_name , filename , doc_type , title , body , num_pages , needs_ocr , has_error , last_modified = self.process_response(path,response)
                    the_doc.body  = body 
                    the_doc.title = title
                    the_doc.num_pages = num_pages
                    the_doc.needs_ocr = needs_ocr
                    the_doc.has_error = has_error
                    the_doc.last_modified = last_modified
                    the_doc.save() 
                return path , file_status , the_doc.id
            except:
                print(bcolors.FAIL,"INTERNAL Error: an existing file is not registered in the database!",bcolors.CEND)
                return path , file_status , None

        domain_name , filename , doc_type , title , body , num_pages , needs_ocr , has_error , last_modified = self.process_response(path,response)


        doc = Document(
            domain      = domain_name , 
            url         = response.url , 
#            referer     = previous_url or '' ,
            depth       = depth ,
#            record_date = AUTO
            remote_name = filename ,
            http_length =  get_header_http_length(response),
            http_encoding = get_header_http_encoding(response),
            http_last_modified = get_header_http_last_modified(response) ,

            # Content: HTML/PDF + file
            doc_type    = doc_type ,
            title       = title or filename,
            body        = body ,
            size        = len(response.content) ,
            num_pages   = num_pages ,
            needs_ocr   = needs_ocr ,
            has_error   = has_error ,
            local_file  = path , 
            file_status = file_status
        )

        # save the new entry
        #print("saving new entry ...")
        doc.save()
        #print("done saving.")

        # add the referer
        added = None
        if previous_id is not None:
            added = False
            try:
                docreferer = Document.objects.get(pk=previous_id)
                if not doc.referers.contains(docreferer):
                    doc.referers.add(docreferer)
                    added = True
            except:
                pass
        elif previous_url is not None or added==False:
            try:
                docreferer = Document.objects.get(url=previous_url)
                if not doc.referers.contains(docreferer):
                    doc.referers.add(docreferer)
                    added = True
            except:
                pass

        # save the relationship
        if added:
            doc.save()

        return path , file_status , doc.id

class DBStatsHandler:

    def __init__(self,domain):
        self.domain = domain

    def get_handled_list(self,crawler_mode):
        list_handled = []
        
        if crawler_mode == CrawlerMode.CRAWL_FULL:
        
            pass

        elif crawler_mode == CrawlerMode.CRAWL_THRU:
            # we're gonna consider that really old non-html documents won't change anymore (2y+)
            # we can add those documents to the 'handled_list' and avoid head() or even get() requests
            # we have to discard HTML documents because we want to crawl them again
            # unless they are very very old as well (3 years+) ! 
            # this is all to minimize the footprint on the server....
            date_today = datetime.today()
            date_html  = make_aware( date_today - timedelta(days=3*365) ) # 3 years
            date_other = make_aware( date_today - timedelta(days=2*365) ) # 2 years 
            q_html  = Q(doc_type=Document.DocumentType.HTML)  & ~Q(http_last_modified__isnull=True) & Q(http_last_modified__lte=date_html)
            q_other = ~Q(doc_type=Document.DocumentType.HTML) & ~Q(http_last_modified__isnull=True) & Q(http_last_modified__lte=date_other)
            query   = Q(domain=self.domain) & (q_html | q_other)
            if self.domain:
                queryset = Document.objects.filter(query)
                #print(queryset.query)
                for doc in queryset:
                    list_handled.append(doc.url if isinstance(doc.url,str) else doc.url.name)

        elif crawler_mode == CrawlerMode.CRAWL_LIGHT:
            # we're gonna consider more documents as being done ...
            date_today = datetime.today()
            date_html  = make_aware( date_today - timedelta(days=1*365) ) # 2 years
            date_other = make_aware( date_today - timedelta(days=1*365) ) # 2 years
            q_html  = Q(doc_type=Document.DocumentType.HTML)  & ~Q(http_last_modified__isnull=True) & Q(http_last_modified__lte=date_html)
            q_other = ~Q(doc_type=Document.DocumentType.HTML) & ~Q(http_last_modified__isnull=True) & Q(http_last_modified__lte=date_other)
            query   = Q(domain=self.domain) & (q_html | q_other)
            if self.domain:
                queryset = Document.objects.filter(query)
                for doc in queryset:
                    list_handled.append(doc.url if isinstance(doc.url,str) else doc.url.name)

        return list_handled

    def handle(self, response, depth, previous_url, local_name, *args, **kwargs):
        # the job has already been done by the storage handler
        pass

    def get_filenames(self,response):
        result = []
        for doc in Document.objects.filter(url=response.url):
            result.append(doc.local_file.name)
        return result

    def find(self,response):
        http_length        = get_header_http_length(response)
        http_encoding      = get_header_http_encoding(response)
        http_last_modified = get_header_http_last_modified(response)
        try:
            if http_last_modified:
                result = Document.objects.get(url=response.url,http_last_modified=http_last_modified).only()
            else:
                result = Document.objects.get(url=response.url,http_length=http_length,http_encoding=http_encoding).only()
            return result.id
        except Document.DoesNotExist:
            # sometime some website will have http_last_modified to the latest time ... thats ok.
            # we're just gonna fetch the page then
            pass 
        except Document.MultipleObjectsReturned:
            try:
                results = Document.objects.find( url=response.url,
                                                http_last_modified=http_last_modified,
                                                http_length=http_length,
                                                http_encoding=http_encoding,
                                                ).order_by('-record_date').only()
                if results.count()>0:
                    return results[0].id
            except:
                pass
        except:
            pass
        return None




    def get_urls_by_referer(self,referer,objid=None):
        result = []

        if objid is None:
            referer_clean = clean_url(referer)
            if referer_clean != referer:
                queryset = Document.objects.filter(Q(referers__url=referer)|Q(referers__url=referer_clean))
            else:
                queryset = Document.objects.filter(referers__url=referer)
        else:
            queryset = Document.objects.get(pk=objid).links.all()

        for doc in queryset:
            result.append({"url": doc.url, "follow": True})
        return result
