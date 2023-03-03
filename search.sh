#!/bin/bash
source ./env.sh
rm -rf www/docwatcher/whoosh_index/
python www/manage.py rebuild_index --noinput
python docspider/search.py
