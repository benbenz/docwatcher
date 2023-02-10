from enum import IntEnum

class CrawlerMode(IntEnum):
    # crawl everything, everytime 
    CRAWL_FULL  = 1
    # smart crawl: go through the HTML website and decides if it needs to download files
    # old HTML and non-HTML files are also considered handled after a certain time (3years)
    CRAWL_THRU  = 2
    # smart crawl: skip the page if it's already been handled (dont go through)
    # old HTML and non-HTML files are also considered handled after a certain time (2years)
    CRAWL_LIGHT = 4
    # ultra light crawl: only crawl the already-marked 'of interest' pages AND their referrers
    # old HTML and non-HTML files are also considered handled after a certain time (1year)
    CRAWL_ULTRA_LIGHT = 8

    # MASK for recover mode (when an expiration time is used on the runtime - useful for shared VPS)
    CRAWL_RECOVER = 32

    CRAWL_ALL = CRAWL_RECOVER + CRAWL_ULTRA_LIGHT + CRAWL_LIGHT + CRAWL_THRU + CRAWL_FULL

class FileStatus(IntEnum):
    UNKNOWN  = 0
    NEW      = 1
    MODIFIED = 2
    EXISTING = 4
    EXACT    = 8 

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


DEFAULT_SLEEP_TIME = 7