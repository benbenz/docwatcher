from enum import IntEnum

class CrawlerMode(IntEnum):
    # crawl everything, everytime 
    CRAWL_FULL  = 1
    # smart crawl: go through the HTML website and decides if it needs to download files
    # old HTML and non-HTML files are also considered handled after a certain time (>2/3years)
    CRAWL_THRU  = 2
    # smart crawl: skip the page if it's already been handled (dont go through)
    # old HTML and non-HTML files are also considered handled after a certain time (>2 years)
    CRAWL_LIGHT = 3


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    CEND      = '\33[0m'        
