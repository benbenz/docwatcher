import os
# load django stuff
# MAKE SURE ROOT/www is also in the PYTHONPATH !!!
os.environ['DJANGO_SETTINGS_MODULE'] = 'docwatcher.settings'
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
# now we can load the model :)
# note that we don't have www.docs.models (because of PYTHONPATH)

from django.contrib.auth.models import User

user = User.objects.create_user('obs', 'observer@docwatcher.com', '1234')
user.save()