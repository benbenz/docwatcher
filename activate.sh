deactivate
export PYTHONPATH=$(pwd):$(pwd)/www:$PYTHONPATH
source .venv/bin/activate
source email_settings.sh
git pull origin master
rm www/db.sqlite3
rm -rf download
rm -rf www/docs/migrations
python www/manage.py makemigrations docs
python www/manage.py migrate
python docspider/init.py
# python docspider/run.py