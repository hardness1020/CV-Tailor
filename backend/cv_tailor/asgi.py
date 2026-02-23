"""
ASGI config for cv_tailor project.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cv_tailor.settings')

application = get_asgi_application()