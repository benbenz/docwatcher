import os
import argparse
import fnmatch
import pickle
from docspider.log import logger
from urllib.parse import urlparse
from crawler.core import CrawlerMode


def get_status():
    filesOfDirectory = os.listdir('.')
    pattern = "state.*"
    for file in filesOfDirectory:
        if fnmatch.fnmatch(file, pattern):
            with open(file,'rb') as f:
                crawler = pickle.load(f)
                crawler_mode = CrawlerMode( crawler.crawler_mode & (CrawlerMode.CRAWL_ALL - CrawlerMode.CRAWL_RECOVER) )
                if crawler.crawler_mode & CrawlerMode.CRAWL_RECOVER:
                    crawler_mode_rec = CrawlerMode.CRAWL_RECOVER
                else:
                    crawler_mode_rec = None
                logger.info("CRAWLER {0}:")
                if crawler_mode_rec:
                    logger.info("mode = {0} | {1}".format(crawler_mode.name,CrawlerMode.CRAWL_RECOVER.name))
                else:
                    logger.info("mode = {0}".format(crawler_mode.name))
                logger.info("has_finished = {0}".format(crawler.has_finished))
                logger.info("safe = {0}".format(crawler.safe))
                logger.info("sleep_time = {0}".format(crawler.sleep_time))
                logger.info("num urls_to_recover = {0}".format(len(crawler.urls_to_recover)))

if __name__ == '__main__':
    get_status()
