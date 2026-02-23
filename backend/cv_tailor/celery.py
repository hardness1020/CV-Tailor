"""
Celery configuration for CV Tailor project.
"""

import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cv_tailor.settings')

app = Celery('cv_tailor')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat schedule for periodic tasks
# NOTE: Abandonment detection disabled - users can resume incomplete wizards anytime
# app.conf.beat_schedule = {
#     'mark-abandoned-artifacts': {
#         'task': 'artifacts.tasks.mark_abandoned_artifacts',
#         'schedule': crontab(hour='*/6'),  # Run every 6 hours
#     },
# }
app.conf.beat_schedule = {}


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')