import os
from shutil import rmtree
import csv
import json
import crawler
import docspider.handlers as handlers
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
        method = url_config.get("method") or "rendered-all"
        depth  = url_config.get("depth") or 4
        sleep  = url_config.get("sleep") or 5
        ignore = url_config.get("ignore_patterns")

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
                        gecko_path=gecko_path,
                        ignore_patterns=ignore
                    )

if __name__ == '__main__':
    crawl_rendered_all()