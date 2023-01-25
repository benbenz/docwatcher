import csv
import os
import uuid
import re
from urllib.parse import urlparse
import psutil       
from crawler.helper import get_content_type
from enum import IntEnum
import difflib
from bs4 import BeautifulSoup

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    CEND      = '\33[0m'        


class FileStatus(IntEnum):
    UNKNOWN  = 0
    NEW      = 1
    MODIFIED = 2
    EXISTING = 4
    SKIPPED  = 5

class LocalStorageHandler:

    def __init__(self, directory, subdirectory):
        self.directory = directory
        self.subdirectory = subdirectory

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

        ignore_patterns = None
        urlcfg = self.get_url_config(kwargs.get('config'),response)
        if urlcfg:
            more_ignore_patterns = urlcfg.get('ignore_patterns')
            if more_ignore_patterns:
                if not ignore_patterns:
                    ignore_patterns = []
                for patt in more_ignore_patterns:
                    if not patt in ignore_patterns:
                        ignore_patterns.append(patt)

        if kwargs.get('orig_url'):
            orig_domain = urlparse(kwargs.get('orig_url')).netloc
            if ext == ".html" and orig_domain not in parsed.netloc:
                print("skipping HTML content that is out of domain",parsed.netloc,"vs",orig_domain)
                return None , FileStatus.SKIPPED

        if kwargs.get('old_files'):
            has_similar_file = False
            similar_file = None
            for old_file in kwargs.get('old_files'):
                if not os.path.isfile(old_file):
                    continue
                try:
                    with open(old_file,'rb') as old_fp:
                        old_content = old_fp.read()
                        if old_content == response.content:
                            has_similar_file = True
                            similar_file = old_file
                            break
                        elif ignore_patterns is not None:
                            try:
                                #https://stackoverflow.com/questions/17904097/python-difference-between-two-strings
                                old_html = BeautifulSoup(old_content,'html.parser').prettify()
                                new_html = BeautifulSoup(response.content,'html.parser').prettify()
                                for pattern in ignore_patterns:
                                    old_html = re.sub(pattern,"",old_html)
                                    new_html = re.sub(pattern,"",new_html)
                                if old_html == new_html:
                                    has_similar_file = True
                                    similar_file = old_file
                                    break
                            except Exception as e:
                                print(bcolors.FAIL,"Error while comparing files",e,bcolors.CEND)
                except:
                    print(bcolors.FAIL,"Error opening file",old_file,bcolors.CEND)
            if has_similar_file:
                print(bcolors.OKCYAN,"Skipping recording of file {0} because it has already a version of it: {1}".format(response.url,similar_file),bcolors.CEND)
                return similar_file , FileStatus.EXISTING
            else:
                print(bcolors.WARNING,"We found a new version of the file",response.url,bcolors.CEND)
                file_status = FileStatus.MODIFIED

        path = os.path.join(directory, filename)
        path = _ensure_unique(path)
        with open(path, 'wb') as f:
            f.write(response.content)

        return path , file_status  

class CSVStatsHandler:
    _FIELDNAMES = ['filename', 'local_name', 'url', 'linking_page_url', 'size', 'depth']

    def __init__(self, directory, name):
        self.directory = directory
        self.name = name
        os.makedirs(directory, exist_ok=True)

    def get_handled_list(self):
        list_handled = []
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
                        print("CSVStatsHandler: this entry is already saved! {0} {1}".format(local_name,response.url))
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

    def get_filenames(self,response):
        parsed_url = urlparse(response.url)
        name = self.name or parsed_url.netloc
        output = os.path.join(self.directory, name + '.csv')
        if not os.path.isfile(output):
            return None
        result = []
        with open(output, newline='') as csvfile:
            reader = csv.reader(csvfile)
            for k, row in enumerate(reader):
                if k > 0:
                    if row[2] == response.url:
                        result.append(row[1]) # local_name
        return result

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
    if not filename.lower().endswith(ext):
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
