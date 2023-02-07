deactivate
export PYTHONPATH=$(pwd):$(pwd)/www:$PYTHONPATH
. .venv/bin/activate
. email_settings.sh
python docspider/run_ocr.py $@
python www/manage.py update_index --noinput
python docspider/search.py