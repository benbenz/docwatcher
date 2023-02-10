import csv
import os
import uuid
import re
import sys
from urllib.parse import urlparse
import psutil       
from crawler.helper import get_content_type , clean_url
from crawler.core import CrawlerMode, bcolors , FileStatus
from enum import IntEnum
import difflib
from bs4 import BeautifulSoup
from lxml import etree
import traceback
import logging
logger = logging.getLogger("DocCrawler")

class LocalStorageHandler:

    def __init__(self, directory, subdirectory):
        self.directory = directory
        self.subdirectory = subdirectory
        self.do_stop = False

    def stop(self):
        self.do_stop = True

    def get_url_config(self,config,response):
        if not config:
            return None
        resp_domain = urlparse(response.url).netloc
        for url_cfg in config.get('urls'):
            url_domain = urlparse(url_cfg.get('url')).netloc
            if url_domain == resp_domain:
                return url_cfg
        return None

    def handle(self, response, *args, **kwargs):
        parsed = urlparse(response.url)
        ext = get_extension(response)
        filename = str(uuid.uuid4()) + ext
        subdirectory = self.subdirectory or parsed.netloc
        directory = os.path.join(self.directory, subdirectory)
        os.makedirs(directory, exist_ok=True)
        file_status = FileStatus.NEW

        config = kwargs.get('config') or dict()
        urlcfg = self.get_url_config(config,response)
        ignore_patterns = None
        if urlcfg:
            more_ignore_patterns = urlcfg.get('ignore_patterns')
            if more_ignore_patterns:
                if not ignore_patterns:
                    ignore_patterns = []
                for patt in more_ignore_patterns:
                    if not patt in ignore_patterns:
                        ignore_patterns.append(re.compile(patt))

        ignore_elements = None
        if urlcfg:
            more_ignore_elements = urlcfg.get('ignore_elements')
            if more_ignore_elements:
                ignore_elements = []
                for ele in more_ignore_elements:
                    if not ele in ignore_elements:
                        ignore_elements.append(ele)                        

        path = None

        if kwargs.get('old_files'):
            has_similar_file = False
            similar_file = None
            exact_file = False
            for old_file in kwargs.get('old_files'):
                if not os.path.isfile(old_file):
                    continue
                try:
                    with open(old_file,'rb') as old_fp:
                        old_content = old_fp.read()
                        if old_content == response.content:
                            has_similar_file = True
                            similar_file = old_file
                            exact_file = True
                            break
                        elif ignore_patterns is not None or ignore_elements is not None:
                            try:
                                old_soup = BeautifulSoup(old_content,'html.parser')
                                new_soup = BeautifulSoup(response.content,'html.parser')
                                old_html = old_soup.prettify().strip()
                                new_html = new_soup.prettify().strip()
                                if ignore_elements is not None:
                                    old_dom = etree.HTML(old_html)
                                    new_dom = etree.HTML(new_html)
                                    for xpath in ignore_elements:
                                        old_ele = old_dom.xpath(xpath)
                                        new_ele = new_dom.xpath(xpath)
                                        if old_ele is not None:
                                            for e in old_ele:
                                                e.getparent().remove(e)
                                        if new_ele is not None:
                                            for e in new_ele:
                                                e.getparent().remove(e)
                                    old_html = etree.tostring(old_dom, pretty_print=True, xml_declaration=True)
                                    new_html = etree.tostring(new_dom, pretty_print=True, xml_declaration=True)
                                for pattern in (ignore_patterns or []):
                                    if isinstance(old_html,bytes) or isinstance(old_html,bytearray):
                                        old_html = old_html.decode()
                                    if isinstance(new_html,bytes) or isinstance(new_html,bytearray):
                                        new_html = new_html.decode()
                                    old_html = re.sub(pattern,"",old_html)
                                    new_html = re.sub(pattern,"",new_html)
                                if old_html == new_html:
                                    has_similar_file = True
                                    similar_file = old_file
                                    break
                                elif config.get('debug')==True:
                                    if isinstance(old_html,bytes) or isinstance(old_html,bytearray):
                                        old_html = old_html.decode()
                                    if isinstance(new_html,bytes) or isinstance(new_html,bytearray):
                                        new_html = new_html.decode()
                                    # try maybe this ...
                                    #https://stackoverflow.com/questions/17904097/python-difference-between-two-strings
                                    with open(old_file+'.diff.html','wb') as diff_file:
                                        htmldiff = difflib.HtmlDiff()
                                        diff_file.write( htmldiff.make_file(old_html.splitlines(),new_html.splitlines(),context=True).encode() )
                            except Exception as e:
                                logger.error("Error while comparing files {0}".format(e))
                                logger.exception(e,exc_info=True)
                                #traceback.print_exc()
                        elif config.get('debug')==True:
                            with open(old_file+'.diff.html','wb') as diff_file:
                                htmldiff = difflib.HtmlDiff()
                                if isinstance(old_content,bytes) or isinstance(old_content,bytearray):
                                    old_content = old_content.decode()
                                if isinstance(response.content,bytes) or isinstance(response.content,bytearray):
                                    resp_content = response.content.decode()
                                else:
                                    resp_content = response.content
                                diff_file.write( htmldiff.make_file(old_content.splitlines(),resp_content.splitlines(),context=True).encode() )
                except:
                    logger.error("Error opening file {0}".format(old_file))
            if has_similar_file:
                #logger.debug("skipping recording of file {0} because it has already a version of it: {1}".format(response.url,similar_file))
                #return similar_file , FileStatus.EXISTING
                # lets overwrite
                path = similar_file
                file_status = FileStatus.EXISTING
                if exact_file:
                    file_status |= FileStatus.EXACT
                    return path , file_status , path # we're done here - let's save ourselves some I/O
                else:
                    logger.debug("overwriting file for url {0} because it has non-relevant changes: {1}".format(response.url,similar_file))

            else:
                logger.warning("we found a new version for the url {0}".format(response.url))
                file_status = FileStatus.MODIFIED
        
        if path is None:
            path = os.path.join(directory, filename)
            path = _ensure_unique(path)
        with open(path, 'wb') as f:
            f.write(response.content)

        return path , file_status , path # id is path

class CSVStatsHandler:
    _FIELDNAMES = ['filename', 'local_name', 'url', 'linking_page_url', 'size', 'depth']

    def __init__(self, directory, name):
        self.directory = directory
        self.name = name
        os.makedirs(directory, exist_ok=True)

    def get_handled_list(self,crawler_mode):
        list_handled = []

        if crawler_mode & CrawlerMode.CRAWL_FULL or crawler_mode & CrawlerMode.CRAWL_THRU :
            pass
        else:
            # this will cause already crawled urls to not be crawled again !
            if self.name:
                file_name = os.path.join(self.directory, self.name + '.csv')
                if os.path.isfile(file_name):
                    with open(file_name, newline='') as csvfile:
                        reader = csv.reader(csvfile)
                        for k, row in enumerate(reader):
                            if k > 0:
                                list_handled.append(row[2])
        return list_handled

    def handle(self, response, depth, previous_url, local_name, *args, **kwargs):
        parsed_url = urlparse(response.url)
        name = self.name or parsed_url.netloc
        output = os.path.join(self.directory, name + '.csv')
        if not os.path.isfile(output):
            with open(output, 'w', newline='') as file:
                csv.writer(file).writerow(self._FIELDNAMES)

        with open(output, newline='') as csvfile:
            reader = csv.reader(csvfile)
            for k, row in enumerate(reader):
                if k > 0:
                    if row[1] == local_name and row[2] == response.url:
                        logger.warning("CSVStatsHandler: this entry is already saved! {0} {1}".format(local_name,response.url))
                        return

        with open(output, 'a', newline='') as file:
            writer = csv.DictWriter(file, self._FIELDNAMES)
            filename = get_filename(parsed_url,response)
            row = {
                'filename': filename,
                'local_name': local_name,
                'url': response.url,
                'linking_page_url': previous_url or '',
                'size': response.headers.get('Content-Length') or '',
                'depth': depth,
            }
            writer.writerow(row)

    def get_filenames(self,url,final_url=None):
        parsed_url = urlparse(url)
        name = self.name or parsed_url.netloc
        output = os.path.join(self.directory, name + '.csv')
        if not os.path.isfile(output):
            return None
        result = []
        with open(output, newline='') as csvfile:
            reader = csv.reader(csvfile)
            for k, row in enumerate(reader):
                if k > 0:
                    if row[2] == url or (final_url and row[2] == final_url):
                        result.append(row[1]) # local_name
        return result

    def get_urls_by_referer(self,referer,objid=None):
        parsed_url = urlparse(referer)
        name = self.name or parsed_url.netloc
        output = os.path.join(self.directory, name + '.csv')
        if not os.path.isfile(output):
            return None
        result = []
        with open(output, newline='') as csvfile:
            reader = csv.reader(csvfile)
            for k, row in enumerate(reader):
                if k > 0:
                    if row[3] == referer:
                        result.append({"url": row[2], "follow": True}) # url
        return result           

    def find(self,url,response):
        final_url = clean_url(response.url)
        res = self.get_filenames(url,final_url)
        if res and len(res)>0:
            return res[0]
        return None

    def find_latest(self,url,):
        res = self.get_filenames(url,None)
        if res and len(res)>0:
            return res[0] , None , None , None
        return None

    def find_recent(self,url):
        return None , None  

    def get_urls_of_interest(self):
        # not implemented
        return None

    def pre_record_document(self, previous_id , url):
        return

        parsed_url = urlparse(url)
        name = self.name or parsed_url.netloc
        output = os.path.join(self.directory, name + '.csv')
        if not os.path.isfile(output):
            with open(output, 'w', newline='') as file:
                csv.writer(file).writerow(self._FIELDNAMES)

        with open(output, newline='') as csvfile:
            reader = csv.reader(csvfile)
            for k, row in enumerate(reader):
                if k > 0:
                    if row[2] == url:
                        logger.warning("CSVStatsHandler: this entry is already saved! {0}".format(url))
                        return

        with open(output, 'a', newline='') as file:
            writer = csv.DictWriter(file, self._FIELDNAMES)
            filename = get_filename(parsed_url,response)
            row = {
                'filename': '',
                'local_name': '',
                'url': url,
                'linking_page_url': '',
                'size': -1,
                'depth': -1,
            }
            writer.writerow(row)        

class ProcessHandler:

    def __init__(self):
        self.process_list = []

    def register_new_process(self, pid):
        self.process_list.append(int(pid))

    def kill_all(self):

        # kill all current processes in list as well as child processes
        for pid in self.process_list:

            try:
                parent_process = psutil.Process(int(pid))
            except psutil._exceptions.NoSuchProcess:
                continue
            children = parent_process.children(recursive=True)

            for c in children:
                c.terminate()

            parent_process.terminate()

        self.process_list = []

def get_extension(response):
    content_type = get_content_type(response)
    ext = ""
    if content_type=="application/pdf" :
        ext = ".pdf"
    elif content_type=="text/html":
        ext = ".html"
    elif content_type=="text/plain":
        ext = ".txt"
    elif content_type=="application/rtf":
        ext = ".rtf"
    elif content_type=="application/msword":
        ext = ".doc"
    elif content_type=="application/vnd.openxmlformats" or content_type=="officedocument.wordprocessingml.document":
        ext = ".docx"
    elif content_type=="application/vnd.ms-powerpoint":
        ext = ".ppt"
    elif content_type=="application/vnd.openxmlformats-officedocument.presentationml.presentation":
        ext = ".pptx"
    elif content_type=="application/vnd.ms-powerpoint.presentation.macroEnabled.12":
        ext = ".pptm"

    if ext == "":
        try:
            content = response.text.strip()
            if "<!doctype html>" in content[:64]:
                ext = ".html"
            elif "%PDF-" in content[:32]:
                ext = ".pdf"
            elif "word/" in content[:32]:
                ext = ".docx"
        except:
            pass
    if ext == "":
        try:
            last_part = response.url.rsplit('/', 1)[-1]
            file_name, file_extension = os.path.splitext(last_part)
            if file_extension:
                ext = file_extension
        except:
            pass
    
    return ext  

def get_filename(parsed_url,response):
    filename = parsed_url.path.split('/')[-1]
    if parsed_url.query:
        filename += f'_{parsed_url.query}'
    ext = get_extension(response)
    if filename and not filename.lower().endswith(ext):
        filename += ext

    filename = filename.replace('%20', '_')

    if len(filename) >= 255:
        filename = str(uuid.uuid4())[:8] + ext

    return filename


def _ensure_unique(path):
    if os.path.isfile(path):
        filename,ext = os.path.splitext(path)
        short_uuid = str(uuid.uuid4())[:8]
        path = path.replace(ext, f'-{short_uuid}{ext}')
        return _ensure_unique(path)
    return path
