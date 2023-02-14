import os
import argparse
import fnmatch
import pickle
from urllib.parse import urlparse
from crawler.core import CrawlerMode
from crawler.helper import clean_url
import logging
logger = logging.getLogger("DocCrawler")


def convert_files(urls,has_finished):
    filesOfDirectory = os.listdir('.')
    pattern = "state.*"
    if urls is not None:
        urls = urls.split(',')
        urls = [ clean_url(url) for url in urls ]

    for file in filesOfDirectory:
        if fnmatch.fnmatch(file, pattern):
            with open(file,'rb') as f:
                crawler = pickle.load(f)
                if urls:
                    crawler_url = getattr(crawler,'orig_url',None)
                    if crawler_url:
                        crawler_url = clean_url(crawler_url)
                    if crawler_url and crawler_url not in urls:
                        print("skipping {0}:{1} because it is not matching urls {2}".format(file,crawler_url,urls))
                        continue
                    elif crawler_url is None:
                        print("[!] crawler has not URL {0}".format(file))

                print("Converting {0}".format(file))
                head_handler = crawler.get_one_head_handler()
                if head_handler and isinstance(crawler.urls_to_recover,set):
                    new_utr = dict()
                    for url in crawler.urls_to_recover:
                        match_id , content_type , last_modified , record_date = head_handler.find_latest(url)
                        new_utr[url] = match_id , content_type
                    crawler.urls_to_recover = new_utr
                
                if has_finished is not None:
                    print("has_finished > {0}".format(has_finished))
                    crawler.has_finished = has_finished
            crawler.sitemap = None
            with open(file,'wb') as f:
                pickle.dump(crawler,f)    

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog = 'python -m docspider.convert',description = 'Fix state files',epilog = '=)')
    parser.add_argument('-f','--finished',type=bool,help="This option set the has_finished attribute to the boolean value provided.")
    parser.add_argument('-u','--urls',type=str,help="Filters the URLs to apply the conversion to")
    args = parser.parse_args()
    convert_files(args.urls,args.finished)
