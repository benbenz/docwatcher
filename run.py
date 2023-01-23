import os
from shutil import rmtree
import csv
import json

import crawler


# change this to your geckodriver path
gecko_path = "./geckodriver"
output_dir = "download"


def crawl_rendered_all():

    #if os.path.isdir(output_dir):
    #    rmtree(output_dir)

    with open('config.json','r') as jsonfile:
        cfg = json.load(jsonfile)

    for url_config in cfg.get('urls'):
        method = url_config.get('method') or "rendered-all"
        url = url_config.get("url")
        crawler.crawl(url=url,sleep_time=5,depth=1,output_dir=output_dir,method=method,gecko_path=gecko_path)

if __name__ == '__main__':
    crawl_rendered_all()