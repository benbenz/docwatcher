import logging
import sys
from urllib.parse import urlparse
import signal

from crawler.crawler import Crawler
from crawler.core import CrawlerMode , bcolors
from crawler.downloaders import RequestsDownloader
from crawler.handlers import (
    LocalStorageHandler,
    CSVStatsHandler,
    ProcessHandler,
    get_filename
)

logging.basicConfig(
    format='[%(asctime)s] %(message)s',
    level=logging.INFO,
    stream=sys.stdout,
)

requests_downloader = RequestsDownloader()
crawlers = []

def crawl(url, output_dir, depth=2, sleep_time=5, method="normal", gecko_path="geckodriver", page_name=None, custom_get_handler=None, custom_stats_handler=None, custom_process_handler=None, safe=False,crawler_mode=CrawlerMode.CRAWL_THRU,domain=None):
    head_handlers = {}
    get_handlers = {}

    # get name of page for sub-directories etc. if not custom name given
    if page_name is None:
        page_name = urlparse(url).netloc

    if custom_get_handler is None:
        get_handlers['application/pdf'] = LocalStorageHandler(
            directory=output_dir, subdirectory=page_name)

        get_handlers['text/html'] = LocalStorageHandler(
            directory=output_dir, subdirectory=page_name)
    else:
        for content_type, Handler in custom_get_handler.items():
            get_handlers[content_type] = Handler

    if custom_stats_handler is None:
        defhandler = CSVStatsHandler(directory=output_dir, name=page_name)
        head_handlers['application/pdf'] = defhandler
        head_handlers['text/html'] = defhandler
    else:
        for content_type, Handler in custom_stats_handler.items():
            head_handlers[content_type] = Handler

    if custom_process_handler is None:
        process_handler = ProcessHandler()
    else:
        process_handler = custom_process_handler

    if not get_handlers and not head_handlers:
        raise ValueError('You did not specify any output')

    crawler = Crawler(
        downloader=requests_downloader,
        head_handlers=head_handlers,
        get_handlers=get_handlers,
        follow_foreign_hosts=False,
        crawl_method=method,
        gecko_path=gecko_path,
        process_handler=process_handler,
        sleep_time=sleep_time,
        safe=safe,
        crawler_mode=crawler_mode
    )

    crawlers.append(crawler)

    print(bcolors.OKCYAN,"Crawler created with mode '{0}' for domain {1}. We have {2} urls that are already handled".format(crawler.get_mode().name,domain,crawler.get_handled_len()),bcolors.CEND)

    try:

        crawler.crawl(url, depth)
        
        print(bcolors.OKCYAN,"DONE CRAWLING",url,bcolors.CEND)

    except KeyboardInterrupt:

        print("KeyboardInterrupt: cancelling task")

    crawler.close()

def exit_gracefully(signum,frame):
    for crawler in crawlers:
        crawler.close()


def register_signals():
    signal.signal(signal.SIGINT , exit_gracefully)
    signal.signal(signal.SIGTERM, exit_gracefully)        

