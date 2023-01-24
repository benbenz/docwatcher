from crawler.helper import get_content_type, call, clean_url
from crawler.crawl_methods import get_hrefs_html, get_hrefs_js_simple, ClickCrawler
from crawler.handlers import FileStatus
import time
from urllib.parse import urlparse
import json

K_DOMAINS_SKIP = 'domains_skip'
K_URLS         = 'urls'

class Crawler:
    def __init__(self, downloader, get_handlers=None, head_handlers=None, follow_foreign_hosts=False, crawl_method="normal", gecko_path="geckodriver", sleep_time=1, process_handler=None):

        # Crawler internals
        self.downloader = downloader
        self.get_handlers = get_handlers or {}
        self.head_handlers = head_handlers or {}
        self.session = self.downloader.session()
        self.process_handler = process_handler
        self.sleep_time = sleep_time

        try:
            with open('config.json','r') as jsonfile:
                self.config = json.load(jsonfile)
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

        # load already handled files from folder if available
        for k, Handler in self.head_handlers.items():
            handled_list = Handler.get_handled_list()
            for handled_entry in handled_list:
                self.handled.add(clean_url(handled_entry))

    def crawl(self, url, depth, previous_url=None, follow=True):

        url = clean_url(url)

        if url in self.handled or url[-4:] in self.file_endings_exclude:
            print("url already handled: {0}".format(url))
            return

        urlinfo = urlparse(url)

        if self.config.get(K_DOMAINS_SKIP) and urlinfo.netloc in self.config.get(K_DOMAINS_SKIP):
            print("skipping domain {0} for url {1} because of configuration".format(urlinfo.netloc,url))
            return

        response = call(self.session, url)
        if not response:
            return

        final_url = clean_url(response.url)

        if final_url in self.handled or final_url[-4:] in self.file_endings_exclude:
            return

        print(final_url)

        print("sleeping {0}s ...".format(self.sleep_time))
        time.sleep(self.sleep_time)

        # Type of content on page at url
        content_type = get_content_type(response)

        # Name of pdf
        local_name = None

        get_handler  = self.get_handlers.get(content_type)
        head_handler = self.head_handlers.get(content_type)
        file_status = FileStatus.UNKNOWN
        if get_handler:
            old_files = head_handler.get_filenames(response) if head_handler else None
            local_name , file_status = get_handler.handle(response,depth, previous_url,old_files=old_files)
        if head_handler and file_status!=FileStatus.EXISTING:
            head_handler.handle(response, depth, previous_url, local_name)

        if content_type == "text/html":
            self.handled.add(final_url)
            if depth and follow:
                depth -= 1
                urls = self.get_urls(response)
                #self.handled.add(final_url)
                for next_url in urls:
                    self.crawl(next_url['url'], depth, previous_url=url, follow=next_url['follow'])
        else:
            self.handled.add(final_url)

    def get_urls(self, response):

        if self.crawl_method == "rendered":
            urls = get_hrefs_js_simple(response, self.follow_foreign)
        elif self.crawl_method == "rendered-all":
            click_crawler = ClickCrawler(self.process_handler, self.executable_path_gecko, response, self.follow_foreign)
            urls = click_crawler.get_hrefs_js_complex()
        else:
            # plain html
            if self.crawl_method is not None and self.crawl_method != "normal":
                print("Invalid crawl method specified, default used (normal)")
            urls = get_hrefs_html(response, self.follow_foreign)

        return urls
