from crawler.helper import get_content_type, call, call_head , clean_url
from crawler.core import CrawlerMode, bcolors , DEFAULT_SLEEP_TIME , FileStatus
from crawler.crawl_methods import get_hrefs_html, get_hrefs_js_simple, ClickCrawler
import time
from urllib.parse import urlparse
from http import HTTPStatus
import json
import os
import re
import pickle
from datetime import datetime, timedelta


K_DOMAINS_SKIP = 'domains_skip'
K_URLS         = 'urls'

class Crawler:
    def __init__(self, downloader, get_handlers=None, head_handlers=None, follow_foreign_hosts=False, crawl_method="normal", gecko_path="geckodriver", sleep_time=DEFAULT_SLEEP_TIME, process_handler=None,safe=False,crawler_mode=CrawlerMode.CRAWL_THRU,expiration=None):

        # Crawler internals
        self.downloader = downloader
        self.get_handlers = get_handlers or {}
        self.head_handlers = head_handlers or {}
        self.safe = safe
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

        self.has_finished = False

        if expiration:
            self.time0            = datetime.now()
            self.expiration_delta = timedelta(minutes=expiration)
            self.urls_to_recover  = set()
            self.sitemap          = dict()
        else:
            self.time0            = None
            self.expiration_delta = None
            self.urls_to_recover  = None
            self.sitemap          = None
        self.expired = False

        # Crawler information
        self.handled = set()
        self.fetched = dict()
        self.follow_foreign = follow_foreign_hosts
        self.executable_path_gecko = gecko_path
        # these file endings are excluded to speed up the crawling (assumed that urls ending with these strings are actual files)
        self.file_endings_exclude = [".mp3", ".wav", ".mkv", ".flv", ".vob", ".ogv", ".ogg", ".gif", ".avi", ".mov", ".wmv", ".mp4", ".mp3", ".mpg" , ".jpg" , ".png"]

        # 3 possible values:
        # "normal" (default) => simple html crawling (no js),
        # "rendered" => renders page,
        # "rendered-all" => renders page and clicks all buttons/other elements to collect all links that only appear when something is clicked (javascript pagination etc.)
        self.crawl_method = crawl_method

        # # load already handled files from folder if available
        for k, Handler in self.head_handlers.items():
            handled_list = Handler.get_handled_list(self.crawler_mode)
            for handled_entry in handled_list:
                handled_entry = clean_url(handled_entry)
                self.handled.add(handled_entry)

    def get_handled_len(self):
        return len(self.handled)

    def get_mode(self):
        return self.crawler_mode

    def get_config(self):
        return self.config

    def close(self):
        for k, Handler in self.get_handlers.items():
            Handler.stop()

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

    def get_one_head_handler(self):     
        one_handler_k = next(iter(self.head_handlers))
        return self.head_handlers.get(one_handler_k)

    def get_one_get_handler(self):     
        one_handler_k = next(iter(self.head_handlers))
        return self.get_handlers.get(one_handler_k)

    def has_document(self,url):

        if self.crawler_mode & CrawlerMode.CRAWL_RECOVER :
            # + if it is in 'urls_to_recover' >> we get the recent one (no matter what the crawl mode is)
            if url in self.urls_to_recover : 
                head_handler = self.get_one_head_handler()
                if head_handler:
                    match_id , content_type = head_handler.find_recent(url)
                    if match_id is not None:
                        print(bcolors.OKCYAN,"skipping fetching of document because of its recovery:",url,bcolors.CEND)
                        return True , content_type , match_id

        # we are crawling/downloading everything no matter what
        if self.crawler_mode & CrawlerMode.CRAWL_FULL:
            return False , None , None
        
        # we are crawling only stuff that changed but go through all HTML
        elif self.crawler_mode & CrawlerMode.CRAWL_THRU:
            if self.safe: # website may detact head requests as bots
                return False , None , None
            response     = call_head(self.session, url, use_proxy=self.config.get('use_proxy'),sleep_time=self.sleep_time)
            content_type = get_content_type(response)
            if content_type == 'text/html':
                return False , content_type , None # we still want to parkour the website...
            
            head_handler = self.head_handlers.get(content_type)
            if head_handler:
                match_id = head_handler.find(url,response)
                if match_id is not None:
                    print(bcolors.OKCYAN,"skipping fetching of document because we already have it",url,bcolors.CEND)
                    return True , content_type , match_id
                else:
                    return False , content_type , None
            else:
                return False , content_type , None

        # we are crawling only stuff that changed 
        elif self.crawler_mode & CrawlerMode.CRAWL_LIGHT or self.crawler_mode & CrawlerMode.CRAWL_ULTRA_LIGHT :

            # website may detect head requests as bots
            # compromise - we're in safe mode so we dont really want to do a head request
            # but we are also in a *LIGHT mode so we dont want to trigger as many full requests
            # which would happen if we were just returning False , None , None
            # >>> let's not fetch if the document is relatively recent ...
            if self.safe: 
                one_handler_k = next(iter(self.head_handlers))
                if one_handler_k:
                    head_handler = self.head_handlers[one_handler_k]
                    match_id , content_type = head_handler.find_recent(url)
                    if match_id is not None:
                        print(bcolors.OKCYAN,"skipping fetching of document because it is recent",url,bcolors.CEND)
                        return True , content_type , match_id
                return False , None , None

            response     = call_head(self.session, url, use_proxy=self.config.get('use_proxy'),sleep_time=self.sleep_time)
            content_type = get_content_type(response)
            head_handler = self.head_handlers.get(content_type)
            final_url = clean_url(response.url)
            if head_handler:
                match_id = head_handler.find(url,response)
                if match_id is not None:
                    print(bcolors.OKCYAN,"skipping fetching of document because we already have it",url,bcolors.CEND)
                    return True , content_type , match_id
                else:
                    return False , content_type , None
            else:
                return False , content_type , None  
            

    def should_crawl(self,url):
        # file types that are ignored
        if url[-4:].lower() in self.file_endings_exclude:
            return False 

        # url is handled within this crawl session
        # this set can be initiated with old/non-changing documents at startup (in has_document)
        # this avoid the head() request triggered below...
        if url in self.handled:
            return False 

        urlcfg = self.get_url_config(url)
        for iurl in urlcfg.get('ignore_urls') or []:
            if re.fullmatch(iurl,url.strip(),flags=re.IGNORECASE):
                return False 

        # domain has to be skipped
        urlinfo = urlparse(url)
        if self.config.get(K_DOMAINS_SKIP):
            for kdomain in self.config.get(K_DOMAINS_SKIP):
                if kdomain == urlinfo.netloc or urlinfo.netloc.endswith(".{0}".format(kdomain)):
                    #print("skipping domain {0} for url {1} because of configuration".format(urlinfo.netloc,url))
                    return False 

        return True 

    def handle_local(self,depth,url,orig_url,is_entry):

        # ultra light mode will only look at HTML page linked to 'of-interest' documents
        if is_entry and self.crawler_mode & CrawlerMode.CRAWL_ULTRA_LIGHT:
            one_handler_k = next(iter(self.head_handlers))
            if not one_handler_k:
                return False , None
            urls = self.head_handlers[one_handler_k].get_urls_of_interest()
            if urls is None:
                print(bcolors.WARNING,"!!! Switching to ",CrawlerMode.CRAWL_LIGHT.name,"!!!")
                self.crawler_mode = CrawlerMode.CRAWL_LIGHT | (self.crawler_mode & CrawlerMode.CRAWL_RECOVER)
                return False , None
            for next_url in urls:
                if self.do_stop:
                    return
                self.crawl(next_url,1, previous_url=None,follow=False,orig_url=orig_url)

            return True , None

        # url is handled by persistence/records (and hasnt changed)
        has_doc , content_type , objid = self.has_document(url) # HEAD request potentially
        if has_doc:
            if self.crawler_mode & CrawlerMode.CRAWL_RECOVER and content_type == 'text/html':
                urls , follow = self.sitemap.get(url) 
                if urls is not None:
                    for next_url in urls:
                        if self.do_stop:
                            return
                        if depth and follow:
                            self.handled.add(url)
                            self.fetched.pop(url,None) # remove the cache ('handled' will now make sure we dont process anything)
                            self.crawl(next_url['url'], depth-1, previous_url=url, previous_id=objid, follow=next_url['follow'],orig_url=orig_url)
                    return True , objid

            # we may be in light mode
            # we shouldnt stop here because we want to check the potential sub pages of the already-downloaded page
            if self.crawler_mode & CrawlerMode.CRAWL_LIGHT and content_type == 'text/html':
                urls = self.get_urls_by_referer(url,objid) 
                if urls is None: # we dont have a handler to help with LIGHT mode ...
                    print(bcolors.WARNING,"!!! Switching to ",CrawlerMode.CRAWL_THRU.name,"!!!")
                    self.crawler_mode = CrawlerMode.CRAWL_THRU | (self.crawler_mode & CrawlerMode.CRAWL_RECOVER)
                    return False , objid
                else:
                    for next_url in urls:
                        if self.do_stop:
                            return
                        follow = next_url['follow']
                        if depth and follow:
                            self.handled.add(url)
                            self.fetched.pop(url,None) # remove the cache ('handled' will now make sure we dont process anything)
                            self.crawl(next_url['url'], depth-1, previous_url=url, previous_id=objid, follow=follow,orig_url=orig_url)
                    return True , objid
            else:
                return True , objid
        
        return False , objid

    def crawl(self, url, depth, previous_url=None, previous_id=None, follow=True, orig_url=None):

        if self.do_stop:
            return

        objid = None

        url = clean_url(url)

        # we're entering crawl() ...
        is_entry = orig_url is None
        if is_entry:
            orig_url = url
            continue_crawling = self.recover_state(url)
            if not continue_crawling:
                return

        if self.time0 is not None and not is_entry:
            datetime_now = datetime.today()
            if datetime_now - self.time0 > self.expiration_delta:
                if self.expired == False:
                    print(bcolors.WARNING,"expiring ...",bcolors.CEND)
                self.expired = True
                return

        # check if url should be skipped
        if not self.should_crawl(url):
            return 

        if url in self.fetched:

            response , httpcode , content_type , objid = self.fetched[url]

            if not response:
                return

        else:

            # sleep now before any kind of request
            #time.sleep(self.sleep_time)
            #if self.do_stop:
            #    return

            is_handled , objid = self.handle_local(depth,url,orig_url,is_entry)
            if is_handled:
                return

            # we may have slept
            if self.do_stop:
                return 

            response , httpcode , errmsg = call(self.session, url, use_proxy=self.config.get('use_proxy'),sleep_time=self.sleep_time) # GET request
            content_type        = get_content_type(response)

            # we may have slept
            if self.do_stop:
                return 
        
            if not response:
                if httpcode == HTTPStatus.NOT_FOUND:
                    print(bcolors.WARNING,"404 response received for {0}".format(url),bcolors.CEND)
                    self.handled.add(url)
                    self.fetched.pop(url,None)  # remove the cache ('handled' will now make sure we dont process anything)
                    return
                else:
                    print(bcolors.WARNING,"No response received for {0}. Errmsg={1}. Trying to clear the cookies".format(url,errmsg),bcolors.CEND)
                    self.session = self.downloader.session(self.safe)
                    print(bcolors.WARNING,"sleeping 5 minutes first ...",bcolors.CEND)
                    time.sleep(60*5)
                    # increasing sleep time too 
                    self.sleep_time += 5 
                    response , httpcode , errmsg = call(self.session, url, use_proxy=self.config.get('use_proxy'),sleep_time=self.sleep_time) # GET request
                    content_type = get_content_type(response)
                    # we may have slept
                    if self.do_stop:
                        return 
            
            if not response:
                if httpcode:
                    try:
                        httpcode_int = int(httpcode)
                    except:
                        httpcode_int = -1
                    print(bcolors.FAIL,"No response received for {0} (code {1} {2})".format(url,httpcode_int,httpcode),bcolors.CEND)
                else:
                    print(bcolors.FAIL,"No response received for {0}. Errmsg={1}".format(url,errmsg),bcolors.CEND)
                # add the url so we dont check again
                self.handled.add(url)
                self.fetched.pop(url,None)  # remove the cache ('handled' will now make sure we dont process anything)
                return

        final_url = clean_url(response.url)

        # check again
        if final_url != url:
            #print("final url is different from url:",final_url,"VS",url)

            # check if final_url should be skipped
            if not self.should_crawl(final_url):
                return 

            is_handled , objid = self.handle_local(depth,final_url,orig_url,is_entry)
            if is_handled:
                return

            # we may have slept
            if self.do_stop:
                return 


        print(final_url) 

        # Name of pdf
        local_name = None

        get_handler  = self.get_handlers.get(content_type)
        head_handler = self.head_handlers.get(content_type)
        file_status = FileStatus.UNKNOWN
        nu_objid = None
        if get_handler:
            old_files = head_handler.get_filenames(url,final_url) if head_handler else None
            local_name , file_status , nu_objid = get_handler.handle(response,depth, previous_url, previous_id, old_files=old_files,orig_url=orig_url,config=self.config,final_url=final_url)
            # we got this object
            # if there is an expiration coming
            # we want to make sure we mark this object as recently fetched...
            if self.urls_to_recover is not None:
                self.urls_to_recover.add(url)
                self.urls_to_recover.add(final_url)

        if head_handler and file_status&FileStatus.EXISTING == 0:
            head_handler.handle(response, depth, previous_url, local_name)

        if nu_objid is not None:
            objid = nu_objid

        if content_type == "text/html":
            if depth and follow:
                if self.do_stop:
                    return
                urls = self.get_urls(response)
                #print("ALL URLS from {0}:".format(final_url),[url['url'] for url in urls])
                # add the urls 
                self.handled.add(final_url)
                self.handled.add(url)
                self.fetched.pop(url,None)  # remove the cache ('handled' will now make sure we dont process anything)
                
                depth -= 1
                
                # memory sitemap
                if self.sitemap is not None:
                    self.sitemap[final_url] = urls , follow 
                    self.sitemap[url]       = urls , follow

                # persistent sitemap
                self.pre_record_clear(objid,depth)
                for next_url in urls:
                    if self.should_crawl(next_url['url']):
                        self.pre_record_document(objid,next_url['url'])

                for next_url in urls:
                    if self.do_stop:
                        return
                    self.crawl(next_url['url'], depth, previous_url=url, previous_id=objid , follow=next_url['follow'],orig_url=orig_url)
            else:
                # lets save the work
                # we may need it if we come back to this URL with depth != 0
                self.fetched[url] = response , httpcode , content_type , objid 
        else:
            # add both
            self.handled.add(url)            
            self.handled.add(final_url)

        if is_entry:
            domain = urlparse(url).netloc
            filename = 'state.'+domain
            # we expired
            if not self.expired:
                self.has_finished = True

            if self.time0 is not None: # state mode
                print(bcolors.WARNING,"Saving state because of expiration",bcolors.CEND)
                with open(filename,'wb') as f:
                    pickle.dump(self,f)

    def pre_record_document(self,previous_id,url):
        head_handler = self.get_one_head_handler()
        if not head_handler:
            return None
        return head_handler.pre_record_document(previous_id,url)
        
    def pre_record_clear(self,previous_id,depth):
        head_handler = self.get_one_head_handler()
        if not head_handler:
            return None
        return head_handler.pre_record_clear(previous_id,depth)

    def recover_state(self,url):
        # recover only when in expiration mode
        if self.time0 is None:
            return True # continue crawl

        domain = urlparse(url).netloc
        filename = 'state.'+domain
        if os.path.isfile(filename):
            with open(filename,'rb') as f:
                obj = pickle.load(f)
                #lets not do that so the recursion can take its course
                #self.handled = obj.handled
                # let's restore the cache
                self.fetched = obj.fetched
                # let's restore the fetched urls list
                self.urls_to_recover = obj.urls_to_recover
                # let's restore the partial site map too
                self.sitemap = obj.sitemap
                # let's switch to RECOVER mode
                self.crawler_mode |= CrawlerMode.CRAWL_RECOVER
                # make sure we're not expired
                self.expired = False
                # has finished?
                self.has_finished = obj.has_finished

                if self.has_finished:
                    print(bcolors.WARNING,"This crawler has finished working. Delete the state file {0} if you want to restart a job".format(filename),bcolors.CEND)
                    return False # stop crawling
                
        return True # continue crawl

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


    def get_urls_by_referer(self,referer_url,objid):

        html_handler = self.head_handlers.get('text/html')        

        if not html_handler:
            return None

        return html_handler.get_urls_by_referer(referer_url,objid)

