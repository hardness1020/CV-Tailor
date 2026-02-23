"""
Custom management command to auto-create a development superuser.

Security Features:
- Only runs when DEBUG=True (refuses in production)
- Uses environment variables (no hardcoded credentials)
- Idempotent (checks if user exists before creating)
- Optional (only runs if env vars are set)

Usage:
    python manage.py create_dev_superuser
"""

import os
from django.conf import settings
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Create a development superuser from environment variables (DEV ONLY)'

    def handle(self, *args, **options):
        """Create superuser if it doesn't exist and we're in development mode."""

        # SECURITY: Refuse to run in production
        if not settings.DEBUG:
            self.stdout.write(
                self.style.ERROR(
                    '❌ SECURITY: create_dev_superuser refused to run '
                    '(DEBUG=False). This command is for development only!'
                )
            )
            return

        # Get credentials from environment variables
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

        # Check if env vars are set
        if not all([username, email, password]):
            self.stdout.write(
                self.style.WARNING(
                    '⚠️  Skipping superuser creation: '
                    'DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL, '
                    'or DJANGO_SUPERUSER_PASSWORD not set'
                )
            )
            return

        User = get_user_model()

        # Check if superuser already exists (idempotent)
        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(
                    f'⚠️  Superuser "{username}" already exists, skipping creation'
                )
            )
            return

        # Create the superuser
        try:
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Development superuser "{username}" created successfully!\n'
                    f'   Email: {email}\n'
                    f'   ⚠️  WARNING: This is for DEVELOPMENT ONLY'
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f'❌ Failed to create superuser: {str(e)}'
                )
            )
