#!/bin/bash
source ./env.sh
rm -rf www/docwatcher/whoosh_index/
nice +15 python www/manage.py rebuild_index --noinput
nice +15 python docspider/search.py
