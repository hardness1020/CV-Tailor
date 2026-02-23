"""
Utility functions for real API testing.

This module provides centralized utilities for checking API key availability
and managing real API test configurations.
"""

import os
from django.conf import settings
from django.test import override_settings


def has_openai_api_key():
    """
    Check if OpenAI API key is available for testing.

    Checks both Django settings and environment variables to ensure
    the API key is properly loaded.

    Returns:
        bool: True if OpenAI API key is available and valid
    """
    # Check Django settings first
    django_key = getattr(settings, 'OPENAI_API_KEY', '')
    if django_key and django_key.strip():
        return True

    # Fallback to environment variable
    env_key = os.environ.get('OPENAI_API_KEY', '')
    if env_key and env_key.strip():
        return True

    return False


def has_anthropic_api_key():
    """
    Check if Anthropic API key is available for testing.

    Checks both Django settings and environment variables to ensure
    the API key is properly loaded.

    Returns:
        bool: True if Anthropic API key is available and valid
    """
    # Check Django settings first
    django_key = getattr(settings, 'ANTHROPIC_API_KEY', '')
    if django_key and django_key.strip():
        return True

    # Fallback to environment variable
    env_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if env_key and env_key.strip():
        return True

    return False


def get_openai_api_key():
    """
    Get the OpenAI API key from Django settings or environment.

    Returns:
        str: The OpenAI API key, or empty string if not available
    """
    # Check Django settings first
    django_key = getattr(settings, 'OPENAI_API_KEY', '')
    if django_key and django_key.strip():
        return django_key

    # Fallback to environment variable
    return os.environ.get('OPENAI_API_KEY', '')


def get_anthropic_api_key():
    """
    Get the Anthropic API key from Django settings or environment.

    Returns:
        str: The Anthropic API key, or empty string if not available
    """
    # Check Django settings first
    django_key = getattr(settings, 'ANTHROPIC_API_KEY', '')
    if django_key and django_key.strip():
        return django_key

    # Fallback to environment variable
    return os.environ.get('ANTHROPIC_API_KEY', '')


def ensure_api_keys_in_environment():
    """
    Ensure API keys from Django settings are available in os.environ.

    This is needed for libraries that check os.environ directly instead
    of using Django settings.
    """
    openai_key = get_openai_api_key()
    anthropic_key = get_anthropic_api_key()

    if openai_key and not os.environ.get('OPENAI_API_KEY'):
        os.environ['OPENAI_API_KEY'] = openai_key

    if anthropic_key and not os.environ.get('ANTHROPIC_API_KEY'):
        os.environ['ANTHROPIC_API_KEY'] = anthropic_key


def should_run_real_api_tests():
    """
    Check if real API testing should be performed.

    Returns:
        bool: True if real API tests should be run (requires explicit flag)
    """
    # Check if explicitly enabled via environment variable
    return os.environ.get('FORCE_REAL_API_TESTS', '').lower() in ('true', '1', 'yes')


def require_real_api_keys():
    """
    Check if real API testing should be performed.

    Returns:
        bool: True if real API tests should be run (based on API key availability)
    """
    # Check if API keys are available
    return has_openai_api_key() or has_anthropic_api_key()


def get_real_api_test_settings():
    """
    Get Django settings overrides for real API testing.

    Returns:
        dict: Settings to override for real API tests
    """
    return {
        'CELERY_TASK_ALWAYS_EAGER': True,
        'CELERY_TASK_EAGER_PROPAGATES': True,
        'CACHES': {
            'default': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            }
        },
        # Use real API keys if available
        'OPENAI_API_KEY': get_openai_api_key(),
        'ANTHROPIC_API_KEY': get_anthropic_api_key(),
        # Test model configuration
        'MODEL_SELECTION_STRATEGY': 'cost_optimized',
        'MODEL_BUDGETS': {
            'test_tier': {'daily_limit_usd': 0.50}  # 50 cents max for all tests
        }
    }


class RealAPITestMixin:
    """
    Mixin class to provide common functionality for real API testing.
    """

    @classmethod
    def setUpClass(cls):
        """Ensure API keys are properly set up for testing."""
        super().setUpClass()
        ensure_api_keys_in_environment()

    def setUp(self):
        """Common setup for real API tests."""
        super().setUp()