deactivate
export PYTHONPATH=$(pwd):$(pwd)/www:$PYTHONPATH
source .venv/bin/activate
source email_settings.sh
python docspider/run.py $@
python www/manage.py update_index --noinput
if [[ -z "${SKIP_SEARCH}" ]]; then
    python docspider/search.py
fi