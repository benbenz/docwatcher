if [[ $# < 1 ]];then
    echo "Usage: run.sh DOCWATCHER_PATH"
    exit
fi
deactivate
root=$1
shift # keep all the rest of the arguments under $@
cd $root
export PYTHONPATH=$root:$root/www:$PYTHONPATH
source .venv/bin/activate
source email_settings.sh
python docspider/run.py $@
python www/manage.py rebuild_index --noinput
python docspider/search.py