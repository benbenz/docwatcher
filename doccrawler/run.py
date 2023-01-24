import os
from shutil import rmtree
import csv
import json
import crawler
import doccrawler.handlers as handlers
from urllib.parse import urlparse

# change this to your geckodriver path
gecko_path = "./geckodriver"
output_dir = "download"

def crawl_rendered_all():

    #if os.path.isdir(output_dir):
    #    rmtree(output_dir)

    with open('config.json','r') as jsonfile:
        cfg = json.load(jsonfile)

    for url_config in cfg.get('urls'):
        
        url    = url_config.get("url")
        method = url_config.get('method') or "rendered-all"
        depth  = url_config.get("depth") or 1
        sleep  = url_config.get("sleep") or 5

        domain_name = urlparse(url).netloc

        get_handlers = dict()
        get_handler  = handlers.AllInOneHandler(directory=output_dir, subdirectory=domain_name)
        get_handlers['application/pdf'] = get_handler
        get_handlers['text/html']       = get_handler

        head_handlers = dict()
        head_handler  = handlers.DBStatsHandler(domain_name)
        head_handlers['application/pdf'] = head_handler
        head_handlers['text/html']       = head_handler

        if not url:
            print("Skipping config entry: no URL found")
            continue

        crawler.crawl(
                        url=url,
                        sleep_time=sleep,
                        custom_get_handler=get_handlers,
                        custom_stats_handler=head_handlers,
                        depth=depth,
                        output_dir=output_dir,
                        method=method,
                        gecko_path=gecko_path
                    )

if __name__ == '__main__':
    crawl_rendered_all()