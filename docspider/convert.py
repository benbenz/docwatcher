import os
import argparse
import fnmatch
import pickle
from urllib.parse import urlparse
from crawler.core import CrawlerMode
import logging
logger = logging.getLogger("DocCrawler")


def convert_files():
    filesOfDirectory = os.listdir('.')
    pattern = "state.*"
    for file in filesOfDirectory:
        if fnmatch.fnmatch(file, pattern):
            with open(file,'rb') as f:
                print("Converting {0}".format(file))
                crawler = pickle.load(f)
                head_handler = crawler.get_one_head_handler()
                if head_handler and isinstance(crawler.urls_to_recover,set):
                    new_utr = dict()
                    for url in crawler.urls_to_recover:
                        match_id , content_type = head_handler.find_recent(url)
                        new_utr[url] = match_id , content_type
                    crawler.urls_to_recover = new_utr
            crawler.sitemap = None
            with open(file,'wb') as f:
                pickle.dump(crawler,f)    

if __name__ == '__main__':
    convert_files()
