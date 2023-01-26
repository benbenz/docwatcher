from crawler.helper import get_content_type, call, call_head , clean_url
from crawler.core import CrawlerMode, bcolors
from crawler.crawl_methods import get_hrefs_html, get_hrefs_js_simple, ClickCrawler
from crawler.handlers import FileStatus 
import time
from urllib.parse import urlparse
import json
import re


K_DOMAINS_SKIP = 'domains_skip'
K_URLS         = 'urls'

class Crawler:
    def __init__(self, downloader, get_handlers=None, head_handlers=None, follow_foreign_hosts=False, crawl_method="normal", gecko_path="geckodriver", sleep_time=1, process_handler=None,safe=False,crawler_mode=CrawlerMode.CRAWL_THRU):

        # Crawler internals
        self.downloader = downloader
        self.get_handlers = get_handlers or {}
        self.head_handlers = head_handlers or {}
        self.session = self.downloader.session(safe)
        self.process_handler = process_handler
        self.sleep_time = sleep_time
        self.do_stop = False
        self.click_crawler = None
        self.crawler_mode = crawler_mode

        try:
            with open('config.json','r') as jsonfile:
                self.config = json.load(jsonfile)
            #self.config = __import__('config').config
        except Exception as e:
            print(e)
            self.config = dict()

        # Crawler information
        self.handled = set()
        self.follow_foreign = follow_foreign_hosts
        self.executable_path_gecko = gecko_path
        # these file endings are excluded to speed up the crawling (assumed that urls ending with these strings are actual files)
        self.file_endings_exclude = [".mp3", ".wav", ".mkv", ".flv", ".vob", ".ogv", ".ogg", ".gif", ".avi", ".mov", ".wmv", ".mp4", ".mp3", ".mpg"]

        # 3 possible values:
        # "normal" (default) => simple html crawling (no js),
        # "rendered" => renders page,
        # "rendered-all" => renders page and clicks all buttons/other elements to collect all links that only appear when something is clicked (javascript pagination etc.)
        self.crawl_method = crawl_method

        # # load already handled files from folder if available
        for k, Handler in self.head_handlers.items():
            handled_list = Handler.get_handled_list(self.crawler_mode)
            for handled_entry in handled_list:
                handled_entry['url'] = clean_url(handled_entry['url'])
                self.handled.add(handled_entry)

    def get_handled_len(self):
        return len(self.handled)

    def get_mode(self):
        return self.crawler_mode

    def close(self):
        if self.session:
            try:
                self.do_stop = True
                self.session.close()
                print("closed session")
            except Exception as e:
                print("error while closing session",e)
        if self.click_crawler is not None:
            self.click_crawler.close()
            
    def get_url_config(self,url):
        if not self.config:
            return dict()
        resp_domain = urlparse(url).netloc
        for url_cfg in self.config.get('urls'):
            url_domain = urlparse(url_cfg.get('url')).netloc
            if url_domain == resp_domain:
                return url_cfg
        return dict()        

    def has_document(self,url):
        # we are crawling/downloading everything no matter what
        if self.crawler_mode == CrawlerMode.CRAWL_FULL:
            return False , None , None
        
        # we are crawling only stuff that changed but go through all HTML
        elif self.crawler_mode == CrawlerMode.CRAWL_THRU:
            response     = call_head(self.session, url, use_proxy=self.config.get('use_proxy'))
            content_type = get_content_type(response)
            if content_type == 'text/html':
                return False , content_type , None # we still want to parkour the website...
            
            head_handler = self.head_handlers.get(content_type)
            if head_handler:
                match_id = head_handler.find(response)
                if match_id is not None:
                    print(bcolors.OKCYAN,"skipping fetching of document because we already have it",url,bcolors.CEND)
                    return True , content_type , match_id
                else:
                    return False , content_type , None
            else:
                return False , content_type , None

        # we are crawling only stuff that changed 
        elif self.crawler_mode == CrawlerMode.CRAWL_LIGHT:
            response     = call_head(self.session, url, use_proxy=self.config.get('use_proxy'))
            content_type = get_content_type(response)
            head_handler = self.head_handlers.get(content_type)
            if head_handler:
                match_id = head_handler.find(response)
                if match_id is not None:
                    print(bcolors.OKCYAN,"skipping fetching of document because we already have it",url,bcolors.CEND)
                    return True , content_type , match_id
                else:
                    return False , content_type , None
            else:
                return False , content_type , None         

    def should_crawl(self,url):
        # file types that are ignored
        if url[-4:] in self.file_endings_exclude:
            return False , None , None

        # url is handled within this crawl session
        # this set can be initiated with old/non-changing documents at startup (in has_document)
        # this avoid the head() request triggered below...
        if url in self.handled:
            return False , None , None

        urlcfg = self.get_url_config(url)
        for iurl in urlcfg.get('ignore_urls') or []:
            if re.match(iurl,url.strip(),flags=re.IGNORECASE):
                return False , None , None

        # domain has to be skipped
        urlinfo = urlparse(url)
        if self.config.get(K_DOMAINS_SKIP):
            for kdomain in self.config.get(K_DOMAINS_SKIP):
                if kdomain == urlinfo.netloc or urlinfo.netloc.endswith(".{0}".format(kdomain)):
                    #print("skipping domain {0} for url {1} because of configuration".format(urlinfo.netloc,url))
                    return False , None , None

        # url is handled by persistence/records
        has_doc , content_type , objid = self.has_document(url)
        if has_doc:
            self.handled.add(url) # also had it to the crawled urls
            return False , content_type , objid

        return True , content_type , None

    def crawl(self, url, depth, previous_url=None, previous_id=None, follow=True, orig_url=None):

        if self.do_stop:
            return

        objid = None

        url = clean_url(url)

        # we're entering crawl() ...
        if orig_url is None:
            orig_url = url

        # sleep now before any kind of request
        time.sleep(self.sleep_time)

        should_crawl , content_type , objid = self.should_crawl(url) # HEAD request potentially
        if not should_crawl:
            # we may be in light mode
            # we shouldnt stop here because we want to check the potential sub pages of the already-downloaded page
            if self.crawler_mode == CrawlerMode.CRAWL_LIGHT and content_type == 'text/html':
                urls = self.get_urls_by_referer(url,objid) 
                if urls is None: # we dont have a handler to help with LIGHT mode ...
                    print(bcolors.WARNING,"!!! Switching to ",CrawlerMode.CRAWL_THRU.name,"!!!")
                    self.crawler_mode = CrawlerMode.CRAWL_THRU
                else:
                    self.handled.add(url)
                    for next_url in urls:
                        if self.do_stop:
                            return
                        if depth and follow:
                            self.crawl(next_url['url'], depth-1, previous_url=url, previous_id=objid, follow=next_url['follow'],orig_url=orig_url)
                    return
            else:
                return

        response = call(self.session, url, use_proxy=self.config.get('use_proxy')) # GET request
        # Type of content on page at url
        content_type = get_content_type(response)
        
        if not response:
            print(bcolors.FAIL,"No response received for",url,bcolors.CEND)
            return

        final_url = clean_url(response.url)

        should_crawl , content_type , objid = self.should_crawl(final_url)
        if not should_crawl:
            return

        print(final_url,"...") 

        # Name of pdf
        local_name = None

        get_handler  = self.get_handlers.get(content_type)
        head_handler = self.head_handlers.get(content_type)
        file_status = FileStatus.UNKNOWN
        if get_handler:
            old_files = head_handler.get_filenames(response) if head_handler else None
            local_name , file_status , nu_objid = get_handler.handle(response,depth, previous_url, previous_id, old_files=old_files,orig_url=orig_url,config=self.config)
        if head_handler and file_status!=FileStatus.EXISTING and file_status!=FileStatus.SKIPPED:
            head_handler.handle(response, depth, previous_url, local_name)

        if nu_objid is not None:
            objid = nu_objid

        if content_type == "text/html":
            self.handled.add(final_url)
            self.handled.add(url)
            if depth and follow:
                depth -= 1
                if self.do_stop:
                    return
                urls = self.get_urls(response)
                #self.handled.add(final_url)
                for next_url in urls:
                    if self.do_stop:
                        return
                    self.crawl(next_url['url'], depth, previous_url=url, previous_id=objid , follow=next_url['follow'],orig_url=orig_url)
        else:
            self.handled.add(final_url)

    def get_urls(self, response):

        if self.crawl_method == "rendered":
            urls = get_hrefs_js_simple(response, self.follow_foreign)
        elif self.crawl_method == "rendered-all":
            self.click_crawler = ClickCrawler(self.process_handler, self.executable_path_gecko, response, self.follow_foreign)
            urls = self.click_crawler.get_hrefs_js_complex()
        else:
            # plain html
            if self.crawl_method is not None and self.crawl_method != "normal":
                print("Invalid crawl method specified, default used (normal)")
            urls = get_hrefs_html(response, self.follow_foreign)

        return urls


    def get_urls_by_referer(self,referer,objid):

        html_handler = self.head_handlers.get('text/html')        

        if not html_handler:
            return None

        return html_handler.get_urls_by_referer(referer,objid)
