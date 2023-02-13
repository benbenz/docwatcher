#!/bin/bash
source ./env.sh
python www/manage.py update_index
python docspider/search.py
