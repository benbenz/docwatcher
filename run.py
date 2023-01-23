import os
from shutil import rmtree
import csv
import json

import crawler


# change this to your geckodriver path
gecko_path = "./geckodriver"
output_dir = "download"


def crawl_rendered_all():

    if os.path.isdir(output_dir):
        rmtree(output_dir)

    cfg = json.load('config.json')
    
    crawler.crawl(url=cfg["url_run"],sleep_time=5,depth=1,output_dir=output_dir,method="rendered-all",gecko_path=gecko_path)

if __name__ == '__main__':
    crawl_rendered_all()