deactivate
ps -ef | grep 'docspider/run.py' | grep -v grep | awk '{print $2}' | xargs -r kill -9
ps -ef | grep 'docspider/ocr.py' | grep -v grep | awk '{print $2}' | xargs -r kill -9
export PYTHONPATH=$(pwd):$(pwd)/www:$PYTHONPATH
source .venv/bin/activate
source email_settings.sh
git pull origin master
rm www/db.sqlite3
rm -rf download
rm -rf www/docs/migrations
rm -rf www/docwatcher/whoosh_index
rm state.*
rm sitemap.*
rm *.log
python www/manage.py makemigrations docs
python www/manage.py migrate
python docspider/init.py
# python docspider/run.py