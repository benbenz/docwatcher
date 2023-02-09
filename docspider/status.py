import os
import argparse
import fnmatch
import pickle
from docspider.log import logger
from urllib.parse import urlparse
from crawler.core import CrawlerMode


def get_status(links_to_check=None):
    filesOfDirectory = os.listdir('.')
    pattern_state = "state.*"
    pattern_sitemap = "sitemap.*"
    for file in filesOfDirectory:
        if fnmatch.fnmatch(file, pattern_state):
            with open(file,'rb') as f:
                crawler = pickle.load(f)
                crawler_mode = CrawlerMode( crawler.crawler_mode & (CrawlerMode.CRAWL_ALL - CrawlerMode.CRAWL_RECOVER) )
                if crawler.crawler_mode & CrawlerMode.CRAWL_RECOVER:
                    crawler_mode_rec = CrawlerMode.CRAWL_RECOVER
                else:
                    crawler_mode_rec = None
                domain = crawler.get_domain()
                if not domain:
                    domain = file
                logger.info("CRAWLER {0}:".format(domain))
                if crawler_mode_rec:
                    logger.info("mode = {0} | {1}".format(crawler_mode.name,CrawlerMode.CRAWL_RECOVER.name))
                else:
                    logger.info("mode = {0}".format(crawler_mode.name))
                logger.info("has_finished = {0}".format(crawler.has_finished))
                logger.info("safe = {0}".format(crawler.safe))
                logger.info("sleep_time = {0}".format(crawler.sleep_time))
                logger.info("num urls_to_recover = {0}".format(len(crawler.urls_to_recover)))

    for file in filesOfDirectory:
        if fnmatch.fnmatch(file, pattern_sitemap) and links_to_check:
            print("Processing sitemap {0}".format(file))
            with open(file,'rb') as f:
                sitemap = pickle.load(f)
                for url , links in sitemap.items():
                    print(url,links)
                    for link in links:
                        if link in links_to_check:
                            print("{0} is included in {1} links ({2})".format(link,url,file))

if __name__ == '__main__':

    parser = argparse.ArgumentParser(prog = 'DocWatcher Status',description = 'Retrieve status',epilog = '=)')
    parser.add_argument('-l','--links',help="check if urls are linked in sitemap")
    args = parser.parse_args()    

    if args.links is not None:
        links = args.links.split(',')
    else:
        links = None

    get_status(links)
