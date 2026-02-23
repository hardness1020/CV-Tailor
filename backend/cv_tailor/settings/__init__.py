"""
Django settings module with environment-based configuration.

Auto-detects environment from DJANGO_ENV and imports appropriate settings.

Environments:
    - development: Local development (default)
    - production: AWS production environment
    - test: Test environment (used by pytest)

Usage:
    Set DJANGO_ENV environment variable to select configuration:
        export DJANGO_ENV=production

    If DJANGO_ENV is not set, defaults to 'development'.

Related ADRs:
    - ADR-029: Multi-Environment Settings Architecture

Related Features:
    - FT-020: Production Environment Configuration
"""

import os
import sys


def get_environment():
    """
    Get current environment from DJANGO_ENV variable.

    Returns:
        str: Environment name ('development', 'production', or 'test')

    Defaults:
        - 'test' if running under pytest or Django test runner
        - 'development' otherwise
    """
    # Auto-detect test environment
    # Check for pytest
    if 'pytest' in sys.modules or (sys.argv and 'pytest' in sys.argv[0]):
        return 'test'

    # Check for Django test runner (manage.py test)
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        return 'test'

    # Otherwise use DJANGO_ENV or default to development
    return os.environ.get('DJANGO_ENV', 'development').lower()


def validate_environment(env):
    """
    Validate that environment is supported.

    Args:
        env: Environment name to validate

    Raises:
        ValueError: If environment is not supported
    """
    valid_environments = {'development', 'production', 'test'}
    if env not in valid_environments:
        raise ValueError(
            f"Invalid DJANGO_ENV '{env}'. "
            f"Must be one of: {', '.join(sorted(valid_environments))}"
        )


# Get and validate environment
DJANGO_ENV = get_environment()
validate_environment(DJANGO_ENV)

# Import appropriate settings module based on environment
if DJANGO_ENV == 'production':
    from .production import *
elif DJANGO_ENV == 'test':
    from .test import *
else:  # development
    from .development import *

# Make environment accessible to other modules
__all__ = ['DJANGO_ENV']
