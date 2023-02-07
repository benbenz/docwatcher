#!/usr/bin/bash
deactivate
export PYTHONPATH=$(pwd):$(pwd)/www:$PYTHONPATH
source .venv/bin/activate
source email_settings.sh
python docspider/run_ocr.py $@
python www/manage.py update_index --noinput
python docspider/search.py