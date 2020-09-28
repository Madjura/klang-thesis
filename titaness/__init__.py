from __future__ import absolute_import, unicode_literals

# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
from .celery import app as celery_app

__all__ = ('celery_app',)


import os


def setup():
    """
    This method must be called every time anything related to Django is imported in modules
    that are not necessarily used only when Django is running.
    :return:
    """
    _module = os.path.split(os.path.dirname(__file__))[-1]
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "{}.settings".format(_module))
    import django
    django.setup()
