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
import copy
from requests import Response
from datetime import datetime, timedelta
from docspider.log import logger


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
        self.orig_url = None

        try:
            with open('config.json','r') as jsonfile:
                self.config = json.load(jsonfile)
            #self.config = __import__('config').config
        except Exception as e:
            logger.error(e)
            self.config = dict()

        self.sitemap = dict()
        self.sitemap_name = None

        self.has_finished = False

        if expiration:
            self.time0            = datetime.now()
            self.expiration_delta = timedelta(minutes=expiration)
            self.urls_to_recover  = dict()
        else:
            self.time0            = None
            self.expiration_delta = None
            self.urls_to_recover  = None

        self.expired = False

        # Crawler information
        self.handled = set()
        self.avoid   = set()
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
                #lets not add anything for now
                #self.handled.add(handled_entry)

    def get_handled_len(self):
        return len(self.handled)

    def get_mode(self):
        return self.crawler_mode

    def get_config(self):
        return self.config

    def get_domain(self):
        if not getattr(self,"orig_url",None):
            return None
        else:
            return urlparse(self.orig_url).netloc

    def close(self):
        for k, Handler in self.get_handlers.items():
            Handler.stop()

        if self.session:
            try:
                self.do_stop = True
                self.session.close()
                logger.info("closed session")
            except Exception as e:
                logger.error("error while closing session {0}".format(e))
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
                # head_handler = self.get_one_head_handler()
                # if head_handler:
                #     match_id , content_type = head_handler.find_recent(url)
                #     if match_id is not None:
                #         logger.debug("skipping fetching of document because of its recovery: {0}".format(url))
                #         return True , content_type , match_id
                logger.debug("skipping fetching of document because of its recovery: {0}".format(url))
                match_id , content_type = self.urls_to_recover[url]
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
                    logger.debug("skipping fetching of document because we already have it {0}".format(url))
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
                        logger.debug("skipping fetching of document because it is recent {0}".format(url))
                        return True , content_type , match_id
                return False , None , None

            response     = call_head(self.session, url, use_proxy=self.config.get('use_proxy'),sleep_time=self.sleep_time)
            content_type = get_content_type(response)
            head_handler = self.head_handlers.get(content_type)
            final_url = clean_url(response.url)
            if head_handler:
                match_id = head_handler.find(url,response)
                if match_id is not None:
                    logger.debug("skipping fetching of document because we already have it {0}".format(url))
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

        # url has been marked as an avoid
        if url in self.avoid:
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
                    #logger.debug("skipping domain {0} for url {1} because of configuration".format(urlinfo.netloc,url))
                    return False 

        return True 

    def handle_local(self,depth,follow,url,orig_url,is_entry):

        # ultra light mode will only look at HTML page linked to 'of-interest' documents
        if is_entry and self.crawler_mode & CrawlerMode.CRAWL_ULTRA_LIGHT:
            one_handler_k = next(iter(self.head_handlers))
            if not one_handler_k:
                return False , None
            urls = self.head_handlers[one_handler_k].get_urls_of_interest()
            if urls is None:
                logger.warning("!!! Switching to {0} !!!".format(CrawlerMode.CRAWL_LIGHT.name))
                self.crawler_mode = CrawlerMode.CRAWL_LIGHT | (self.crawler_mode & CrawlerMode.CRAWL_RECOVER)
                return False , None

            if depth and follow:
                # mark the URL as handled now
                self.handled.add(url)
                for next_url in urls:
                    if self.do_stop:
                        return False , None
                    self.crawl(next_url,1, previous_url=None,follow=False,orig_url=orig_url)

            return True , None

        # url is handled by persistence/records (and hasnt changed)
        has_doc , content_type , objid = self.has_document(url) # HEAD request potentially
        if has_doc:
            if self.crawler_mode & CrawlerMode.CRAWL_RECOVER and content_type == 'text/html':
                urls = self.sitemap.get(url) 
                if urls is not None:
                    if depth and follow:
                        self.handled.add(url)
                        self.fetched.pop(url,None) # remove the cache ('handled' will now make sure we dont process anything)
                        for next_url in urls:
                            if self.do_stop:
                                return False , None
                            self.crawl(next_url['url'], depth-1, previous_url=url, previous_id=objid, follow=next_url['follow'],orig_url=orig_url)
                        return True , objid

            # we may be in light mode
            # we shouldnt stop here because we want to check the potential sub pages of the already-downloaded page
            if self.crawler_mode & CrawlerMode.CRAWL_LIGHT and content_type == 'text/html':
                urls = self.sitemap.get(url) 
                if urls is None: # try through the DB 
                    urls = self.get_urls_by_referer(url,objid) 
                if urls is None: # we dont have a handler to help with LIGHT mode ...
                    logger.warning("!!! Switching to {0} !!!".format(CrawlerMode.CRAWL_THRU.name))
                    self.crawler_mode = CrawlerMode.CRAWL_THRU | (self.crawler_mode & CrawlerMode.CRAWL_RECOVER)
                    return False , objid
                else:
                    if depth and follow:
                        self.handled.add(url)
                        self.fetched.pop(url,None) # remove the cache ('handled' will now make sure we dont process anything)
                        for next_url in urls:
                            if self.do_stop:
                                return False , None
                            urlfollow = next_url['follow']
                            self.crawl(next_url['url'], depth-1, previous_url=url, previous_id=objid, follow=urlfollow,orig_url=orig_url)
                    return True , objid
            else:
                return True , objid
        
        return False , objid

    def crawl(self, url, depth, previous_url=None, previous_id=None, follow=True, orig_url=None):

        if self.do_stop:
            return

        if url is None:
            return

        objid = None

        url = clean_url(url)

        # we're entering crawl() ...
        is_entry = orig_url is None
        if is_entry:
            orig_url = url
            self.orig_url = orig_url
            continue_crawling = self.recover_state(url)
            if not continue_crawling:
                return
            self.sitemap_name = 'sitemap.'+urlparse(url).netloc+'.pickle'
            self.load_sitemap()

        if self.time0 is not None and not is_entry:
            datetime_now = datetime.today()
            if datetime_now - self.time0 > self.expiration_delta:
                if self.expired == False:
                    thedomain = urlparse(orig_url).netloc if orig_url else None
                    logger.warning("expiring {0} ...".format(thedomain or ""))
                self.expired = True
                # to accelerate the expiration
                self.do_stop = True
                return

        # check if url should be skipped
        if not self.should_crawl(url):
            return 

        if url in self.fetched:

            response , httpcode , content_type , objid = self.fetched[url]

            if not response:
                return

            logger.debug("recovered cached url {0}".format(url))

        else:

            is_handled , objid = self.handle_local(depth,follow,url,orig_url,is_entry)
            if is_handled:
                return

            # we may have slept
            if self.do_stop:
                return 

            logger.info("GET {0} (depth={1})".format(url,depth))

            response , httpcode , errmsg = call(self.session, url, use_proxy=self.config.get('use_proxy'),sleep_time=self.sleep_time) # GET request
            content_type        = get_content_type(response)

            # we may have slept
            if self.do_stop:
                return 
        
            if not response:
                if httpcode == HTTPStatus.NOT_FOUND:
                    logger.warning("404 response received for {0}".format(url))
                    self.handled.add(url)
                    self.fetched.pop(url,None)  # remove the cache ('handled' will now make sure we dont process anything)
                    return
                else:
                    logger.warning("No response received for {0}. Errmsg={1}. Trying to clear the cookies".format(url,errmsg))
                    self.session = self.downloader.session(self.safe)
                    if urlparse(url).netloc == urlparse(orig_url).netloc:
                        logger.warning("sleeping 5 minutes first ...")
                        time.sleep(60*5)
                        # increasing sleep time too 
                        self.sleep_time += 2
                    else:
                        logger.warning("sleeping 30 seconds  first ...")
                        time.sleep(30)

                    if self.do_stop:
                        return
                        
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
                    logger.error("No response received for {0} (code {1} {2})".format(url,httpcode_int,httpcode))
                else:
                    logger.error("No response received for {0}. Errmsg={1}".format(url,errmsg))
                # add the url so we dont check again
                self.handled.add(url)
                self.fetched.pop(url,None)  # remove the cache ('handled' will now make sure we dont process anything)
                # this is a particularly problematic URL ... lets mark it as avoid
                self.avoid.add(url) # mark as avoid (will be saved in the state and recovered)
                return

        final_url = clean_url(response.url)

        # check again
        if final_url != url:
            # check if final_url should be skipped
            if not self.should_crawl(final_url):
                return 

            is_handled , objid = self.handle_local(depth,follow,final_url,orig_url,is_entry)
            if is_handled:
                return

            # we may have slept
            if self.do_stop:
                return 


        #logger.info(final_url) 

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
                #self.urls_to_recover.add(url)
                #self.urls_to_recover.add(final_url)
                self.urls_to_recover[url]       = nu_objid , content_type
                self.urls_to_recover[final_url] = nu_objid , content_type

        if head_handler and file_status&FileStatus.EXISTING == 0:
            head_handler.handle(response, depth, previous_url, local_name)

        if nu_objid is not None:
            objid = nu_objid

        if content_type == "text/html":
            if depth and follow:
                if self.do_stop:
                    return
                urls = self.get_urls(response)

                # add the urls 
                self.handled.add(final_url)
                self.handled.add(url)
                self.fetched.pop(url,None)  # remove the cache ('handled' will now make sure we dont process anything)
                
                depth -= 1
                
                # memory sitemap
                if self.sitemap is not None:
                    self.sitemap[url]       = urls
                    self.sitemap[final_url] = urls
                    self.save_sitemap()

                for next_url in urls:
                    if self.do_stop:
                        return
                    self.crawl(next_url['url'], depth, previous_url=url, previous_id=objid , follow=next_url['follow'],orig_url=orig_url)
            else:
                # lets save the work
                # we may need it if we come back to this URL with depth != 0
                if url not in self.fetched:
                    self.fetched[url] = response , httpcode , content_type , objid 
        else:
            # add both
            self.handled.add(url)            
            self.handled.add(final_url)

        if is_entry:
            self.finish(url)
    
    def finish(self,url):
        domain = urlparse(url).netloc
        filename = 'state.'+domain
        # we expired
        if not self.expired:
            self.has_finished = True

        if self.time0 is not None: # state mode
            if not self.has_finished:
                logger.warning("Saving state because of expiration option")
            with open(filename,'wb') as f:
                pickle.dump(self,f)    

    # used by pickle
    def __getstate__(self):
        state = self.__dict__.copy()
        # Don't pickle baz
        state.pop("sitemap",None)
        return state   
    
    #used by pickle
    def __setstate__(self, state):
        self.__dict__.update(state)
        # load separate sitemap
        self.load_sitemap()

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

    def load_sitemap(self):
        if not self.sitemap_name:
            return
        try:
            with open(self.sitemap_name,'rb') as f:
                self.sitemap = pickle.load(f)
        except:
            pass

    def save_sitemap(self):
        if not self.sitemap_name:
            return
        with open(self.sitemap_name,'wb') as f:
            pickle.dump(self.sitemap,f)

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
                # let's restore the avoid urls
                self.avoid = obj.avoid #getattr(obj,"avoid",set())
                # let's restore the cache
                self.fetched = obj.fetched
                # let's restore the fetched urls list
                self.urls_to_recover = obj.urls_to_recover
                # let's restore the partial site map too
                #self.sitemap = obj.sitemap
                # let's switch to RECOVER mode
                self.crawler_mode |= CrawlerMode.CRAWL_RECOVER
                # make sure we're not expired
                self.expired = False
                # has finished?
                self.has_finished = obj.has_finished

                if self.has_finished:
                    logger.info_plus("This crawler has finished working. Delete the state file {0} if you want to restart a job".format(filename))
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
                logger.warning("Invalid crawl method specified, default used (normal)")
            urls = get_hrefs_html(response, self.follow_foreign)

        return urls


    def get_urls_by_referer(self,referer_url,objid):

        html_handler = self.head_handlers.get('text/html')        

        if not html_handler:
            return None

        return html_handler.get_urls_by_referer(referer_url,objid)

