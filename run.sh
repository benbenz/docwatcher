deactivate
export PYTHONPATH=$(pwd):$(pwd)/www:$PYTHONPATH
source .venv/bin/activate
source email_settings.sh
python docspider/run.py
python www/manage.py rebuild_index --noinput
python docspider/search.py