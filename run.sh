#!/bin/bash
# deactivate
# export PYTHONPATH=$(pwd):$(pwd)/www:$(pwd)/easyocr:$PYTHONPATH
# source .venv/bin/activate
# source email_settings.sh
source ./env.sh
python docspider/run.py $@
if [[ -z "${SKIP_SEARCH}" ]]; then
    rm -rf www/docwatcher/whoosh_index/
    nice +15 python www/manage.py rebuild_index --noinput
    nice +15 python docspider/search.py
else
    echo "run.sh: not performing search"
fi