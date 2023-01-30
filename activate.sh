deactivate
source .venv/bin/activate
export PYTHONPATH=$(pwd):$(pwd)/www:$PYTHONPATH
git pull origin master
rm www/db.sqlite3
python www/manage.py migrate
python docspider/run.py