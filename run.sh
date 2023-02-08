#!/bin/bash
deactivate
export PYTHONPATH=$(pwd):$(pwd)/www:$(pwd)/easyocr:$PYTHONPATH
source .venv/bin/activate
source email_settings.sh
python docspider/run.py $@
if [[ -z "${SKIP_SEARCH}" ]]; then
    # python www/manage.py rebuild_index --noinput
    python www/manage.py update_index
    python docspider/search.py
else
    echo "run.sh: not performing search"
fi