import logging
import sys
from urllib.parse import urlparse

from crawler.crawler import Crawler
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


def crawl(url, output_dir, depth=2, sleep_time=1, method="normal", gecko_path="geckodriver", page_name=None, custom_get_handler=None, custom_stats_handler=None, custom_process_handler=None, ignore_patterns=None,config=None):
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
        sleep_time=sleep_time
    )
    crawler.crawl(url, depth, ignore_patterns=ignore_patterns,config=config)
