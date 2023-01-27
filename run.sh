thisdir=$(pwd)
export PYTHONPATH=$thisdir:$thisdir/www:$thisdir/easyocr:$PYTHONPATH
python docspider/run.py
python www/manage.py rebuild_index --noinput
python docspider/search.py