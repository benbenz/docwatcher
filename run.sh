thisdir=$(pwd)
export PYTHONPATH=$thisdir:$thisdir/www:$PYTHONPATH
python docspider/run.py
#
# THIS IS NOW DONE thanks to the HAYSTACK_SIGNAL_PROCESSOR = 'haystack.signals.RealtimeSignalProcessor'
#
#cd www
#python manage.py rebuild_index --noinput
#cd $thisdir
python docspider/search.py