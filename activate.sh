deactivate
source .venv/bin/activate
export PYTHONPATH=$(pwd):$(pwd)/www:$PYTHONPATH
git pull origin master
rm www/db.sqlite3
rm -rf www/docs/migrations
python www/manage.py makemigrations docs
python www/manage.py migrate
python docspider/run.py