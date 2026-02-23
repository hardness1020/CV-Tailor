"""
Test settings for cv_tailor project.

Extends base.py with test-specific configuration.

Optimized for:
    - Fast test execution
    - Isolated test environment
    - No external service dependencies
    - In-memory database
    - Mocked external APIs

Usage:
    Automatically detected when running pytest
    Or explicitly set: export DJANGO_ENV=test

Related ADRs:
    - ADR-029: Multi-Environment Settings Architecture
"""

import os
import warnings
from decouple import config
from .base import *

# Enable debug for better test error messages
DEBUG = True

# Security settings (relaxed for testing)
SECRET_KEY = 'test-secret-key-not-for-production'
ALLOWED_HOSTS = ['*']

# Use PostgreSQL test database (faster with --keepdb, avoids SQLite limitations)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='cv_tailor'),
        'USER': config('DB_USER', default='cv_tailor_user'),
        'PASSWORD': config('DB_PASSWORD', default='test-password'),
        'HOST': config('DB_HOST', default='db'),
        'PORT': config('DB_PORT', default='5432'),
        'ATOMIC_REQUESTS': True,
        'TEST': {
            'NAME': 'test_cv_tailor',  # Separate test database
        },
        'CONN_MAX_AGE': 0,  # Don't persist connections in tests
    }
}

# Disable migrations for faster tests (use --nomigrations flag in pytest)
# Tests should use Django's test database creation

# Static files (in-memory for tests)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'test_staticfiles')
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Ensure static files directory exists to suppress WhiteNoise warning
os.makedirs(STATIC_ROOT, exist_ok=True)

# Media files (temporary directory for tests)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'test_media')
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'

# CORS Configuration (allow all for tests)
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
CORS_ALLOW_CREDENTIALS = True

# Cache Configuration (use Redis like development - required by django-ratelimit)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://redis:6379/1'),
        'KEY_PREFIX': 'test',  # Separate namespace for tests
    }
}

# Celery Configuration (eager execution for synchronous tests)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = 'memory://'
CELERY_RESULT_BACKEND = 'cache+memory://'

# Password hashers (fast hashers for tests)
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# AI/LLM Settings (mocked in tests)
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', 'sk-test-key-for-testing')

# Set API key in environment for tests
os.environ['OPENAI_API_KEY'] = OPENAI_API_KEY

# GitHub API Settings (mocked in tests)
GITHUB_TOKEN = 'test-github-token'

# Google OAuth credentials (mocked in tests)
GOOGLE_CLIENT_ID = 'test-google-client-id'
GOOGLE_CLIENT_SECRET = 'test-google-client-secret'

# Test Model Strategy (use cost-optimized for faster mocked tests)
MODEL_SELECTION_STRATEGY = 'cost_optimized'
TRACK_MODEL_PERFORMANCE = False  # Disable performance tracking in tests
OPTIMIZE_FOR_COST = True
OPTIMIZE_FOR_QUALITY = False

# Test budgets (unlimited for tests)
MODEL_BUDGETS = {
    'daily_budget_usd': 99999.0,
    'monthly_budget_usd': 99999.0,
    'max_cost_per_user_daily': 99999.0,
    'cost_alert_threshold': 1.0  # Never alert in tests
}

# LangChain Settings (minimal for tests)
LANGCHAIN_SETTINGS = {
    'chunk_size': 100,  # Smaller chunks for faster tests
    'chunk_overlap': 20,
    'max_chunks_per_document': 10,  # Fewer chunks
    'semantic_chunking_threshold': 0.8
}

# Circuit Breaker Settings (lenient for tests)
CIRCUIT_BREAKER_SETTINGS = {
    'failure_threshold': 100,  # High threshold to not interfere with tests
    'timeout': 1,  # Short timeout
    'retry_attempts': 1  # Minimal retries
}

# Logging (minimal for tests - only errors)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'console': {
            'level': 'ERROR',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'ERROR',
    },
}

# Email backend (console for tests)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Rate Limiting (disabled for tests)
RATELIMIT_ENABLE = False

# Security settings (disabled for tests)
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Test-specific settings
TESTING = True

# Django REST Framework (add test-specific overrides if needed)
REST_FRAMEWORK['TEST_REQUEST_DEFAULT_FORMAT'] = 'json'

# Disable template caching for tests
for template_engine in TEMPLATES:
    template_engine['OPTIONS']['debug'] = True
    if 'loaders' in template_engine['OPTIONS']:
        # Disable template caching
        template_engine['OPTIONS']['loaders'] = [
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader',
        ]

# Suppress warnings from third-party libraries
warnings.filterwarnings(
    'ignore',
    message='coroutine .* was never awaited',
    category=RuntimeWarning,
    module='litellm.*'
)
