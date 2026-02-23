"""
WSGI config for cv_tailor project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cv_tailor.settings')

application = get_wsgi_application()