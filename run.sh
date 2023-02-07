deactivate
export PYTHONPATH=$(pwd):$(pwd)/www:$PYTHONPATH
source .venv/bin/activate
source email_settings.sh
python docspider/run.py $@
if [[ -z "${SKIP_SEARCH}" ]]; then
    python www/manage.py update_index --noinput
    python docspider/search.py
fi