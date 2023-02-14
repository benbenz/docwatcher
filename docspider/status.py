import os
import argparse
import fnmatch
import pickle
from urllib.parse import urlparse
from crawler.core import CrawlerMode , bcolors
from crawler.helper import clean_url

def get_first_non_ready_crawl_node(crawler,crawl_node):
    if not crawl_node:
        return None , None
    # we skip the not-crawled urls as well...
    if crawl_node['ready'] == False and \
        crawler.should_crawl(clean_url(crawl_node['url'])) and \
        crawl_node.get('content_type') == "text/html" and \
        crawl_node.get('depth',-1) >= 0: 
            return crawl_node['url'] , crawl_node.get('depth')
    if 'children' in crawl_node and 'urls' in crawl_node:
        # we gotta get them in the right order
        for url_next in crawl_node['urls']:
        #for url,child in crawl_node['children'].items():
            child  = crawl_node['children'].get(url_next['url'],None)
            if child:
                result , depth = get_first_non_ready_crawl_node(crawler,child)
                if result is not None:
                    return result , depth
            elif crawler.should_crawl(clean_url(url_next['url'])):
                # this maybe wrong (depending on handle_local ... :/)
                return url_next['url'] # not been created yet - this is the next one !
    return None , None

def get_status(links_to_check=None):
    filesOfDirectory = os.listdir('.')
    pattern_state = "state.*"
    pattern_sitemap = "sitemap.*"
    ljustsize = 20
    for file in filesOfDirectory:
        if fnmatch.fnmatch(file, pattern_state):
            try:
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
                    print(bcolors.HEADER+"\n{0}:".format(domain)+bcolors.CEND)
                    if crawler.has_finished:
                        print("has_finished".ljust(ljustsize),":",bcolors.BOLD+bcolors.OKCYAN+"{0}".format(crawler.has_finished)+bcolors.CEND)
                    else:
                        print("has_finished".ljust(ljustsize),":","{0}".format(crawler.has_finished))
                    if crawler_mode_rec:
                        print("mode".ljust(ljustsize),":","{0} | {1}".format(crawler_mode.name,CrawlerMode.CRAWL_RECOVER.name))
                    else:
                        print("mode".ljust(ljustsize),":","{0}".format(crawler_mode.name))
                    print("safe".ljust(ljustsize),":","{0}".format(crawler.safe))
                    print("sleep_time".ljust(ljustsize),":","{0}".format(crawler.sleep_time))
                    print("num urls_to_recover".ljust(ljustsize),":","{0}".format(len(crawler.urls_to_recover)))

                    crawl_tree = getattr(crawler,'crawl_tree',None)
                    current_url , depth = get_first_non_ready_crawl_node(crawler,crawl_tree)
                    print("current URL".ljust(ljustsize),":","{0} (depth={1})".format(current_url,depth))
            except Exception as e:
                print(bcolors.FAIL+"error while loading {0}: {1}".format(file,e)+bcolors.CEND)

    for file in filesOfDirectory:
        if fnmatch.fnmatch(file, pattern_sitemap) and links_to_check:
            print("Processing sitemap {0}".format(file))
            with open(file,'rb') as f:
                sitemap = pickle.load(f)
                for url , links in sitemap.items():
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
