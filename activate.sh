export PYTHONPATH=$(pwd):$(pwd)/www:$PYTHONPATH
source .venv/bin/activate
git pull origin master
rm www/db.sqlite3
python www/manage.py migrate
