import os
from shutil import rmtree
import json
import crawler
import signal 
import argparse
import docspider.handlers as handlers
from urllib.parse import urlparse
from crawler.core import DEFAULT_SLEEP_TIME
from concurrent.futures import ThreadPoolExecutor , ProcessPoolExecutor , as_completed

# change this to your geckodriver path
gecko_path = "./geckodriver"
output_dir = "download"

executor = None
futures  = []

def crawl_rendered_all(crawler_mode0):
    global executor

    #if os.path.isdir(output_dir):
    #    rmtree(output_dir)

    with open('config.json','r') as jsonfile:
        cfg = json.load(jsonfile)
    # cfg = __import__('config').config    

    # issue with html.render() in requests_html >> use ProcessPoolExecutor
    executor = ProcessPoolExecutor(max_workers=10)
    #executor = ThreadPoolExecutor(max_workers=10)

    solo = cfg.get("solo",None) 

    #futures = []
    if crawler_mode0 is not None: 
        crawler_mode0 = crawler.CrawlerMode[crawler_mode0]

    for url_config in cfg.get('urls'):

        url    = url_config.get("url")
        method = url_config.get("method") or "rendered-all"
        depth  = url_config.get("depth") or 4
        sleep  = url_config.get("sleep") or DEFAULT_SLEEP_TIME
        safe   = url_config.get("safe",False)
        c_mode = url_config.get("crawler_mode")

        crawler_mode = crawler.CrawlerMode[c_mode] if c_mode else crawler.CrawlerMode.CRAWL_THRU

        # use the least agressive crawler?
        if crawler_mode0 is not None: #>crawler_mode:        
            crawler_mode = crawler_mode0

        if solo is not None and solo != url:
            continue 

        domain_name = urlparse(url).netloc

        handled_types = [
            'text/html',
            'text/plain',
            'application/rtf',
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats',
            'officedocument.wordprocessingml.document',
            'application/vnd.ms-powerpoint',
            'application/vnd.ms-powerpoint.presentation.macroEnabled.12',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'application/vnd.ms-powerpoint.presentation.macroEnabled.12'
        ]

        get_handlers = dict()
        get_handler  = handlers.AllInOneHandler(directory=output_dir, subdirectory=domain_name)
        for handled_type in handled_types:
            get_handlers[handled_type] = get_handler

        head_handlers = dict()
        head_handler  = handlers.DBStatsHandler(domain_name)
        for handled_type in handled_types:
            head_handlers[handled_type] = head_handler

        if not url:
            print("skipping config entry: no URL found")
            continue

        future = executor.submit(
                crawler.crawl, 
                url=url,
                sleep_time=sleep,
                custom_get_handler=get_handlers,
                custom_stats_handler=head_handlers,
                depth=depth,
                output_dir=output_dir,
                method=method,
                gecko_path=gecko_path,
                safe=safe,
                crawler_mode=crawler_mode,
                domain=domain_name
        )

        futures.append(future)

    try:
        for _ in as_completed(futures):
            pass   
    except KeyboardInterrupt:
        for future in futures:
            try:
                future.cancel()
            except:
                pass
        if executor:
            #executor.shutdown(wait=True,cancel_futures=True)
            executor.shutdown(wait=True)

def exit_gracefully(signum,frame):
    print("RECEIVED SIGNAL",signum)
    signame = signal.Signals(signum).name
    print(f'exit_gracefully() called with signal {signame} ({signum})')  
    for future in futures:
        try:
            future.cancel()
        except:
            pass
    if executor is not None:  
        #executor.shutdown(wait=True,cancel_futures=True)
        executor.shutdown(wait=True)


if __name__ == '__main__':
    signal.signal(signal.SIGINT , exit_gracefully)
    signal.signal(signal.SIGTERM, exit_gracefully)     
    crawler.register_signals()

    parser = argparse.ArgumentParser(prog = 'DocWatcher',description = 'Watch for new docs',epilog = '=)')
    parser.add_argument('-m','--mode',choices=['CRAWL_FULL','CRAWL_THRU','CRAWL_LIGHT','CRAWL_ULTRA_LIGHT'],help="This option forces the crawlers to use the provided mode.")
    args = parser.parse_args()    
    crawl_rendered_all(args.mode)
