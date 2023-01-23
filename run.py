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

    urls = cfg.get('urls').keys()

    for url,url_config in cfg.get('urls').items():
        method = url_config.get('method') or "rendered-all"
        crawler.crawl(url=url,sleep_time=5,depth=1,output_dir=output_dir,method=method,gecko_path=gecko_path)

if __name__ == '__main__':
    crawl_rendered_all()