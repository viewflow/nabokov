"""WSGI entry point. Run with:

    gunicorn nabokov_web.wsgi:application --preload --workers 2

The spaCy pipeline is warmed at import time, so with ``--preload`` the model
loads once in the gunicorn master and forked workers share it copy-on-write.
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nabokov_web.settings")

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()

from nabokov_web.views import get_nlp

get_nlp()
