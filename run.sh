thisdir=$(pwd)
export PYTHONPATH=$thisdir:$thisdir/www:$PYTHONPATH
python docspider/run.py
cd www
python manage.py rebuild_index --noinput
cd $thisdir
python docspider/search.py