"""
Development settings for cv_tailor project.

Extends base.py with local development configuration.

Usage:
    export DJANGO_ENV=development  (or don't set it - development is default)
    Create .env file in backend/ directory with:
        SECRET_KEY=your-dev-secret-key
        OPENAI_API_KEY=sk-your-openai-key
        DB_ENGINE=postgresql
        DB_NAME=cv_tailor
        DB_USER=cv_tailor_user
        DB_PASSWORD=your-secure-password
        DB_HOST=db
        DB_PORT=5432
        GITHUB_TOKEN=your-github-token
        GOOGLE_CLIENT_ID=your-google-client-id
        GOOGLE_CLIENT_SECRET=your-google-client-secret

Related ADRs:
    - ADR-029: Multi-Environment Settings Architecture
    - ADR-031: Secrets Management Strategy
"""

import os
from decouple import config
from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

# Security settings (relaxed for development)
# SECURITY FIX: Removed default SECRET_KEY to prevent accidental production deployment
SECRET_KEY = config('SECRET_KEY')
ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    default='localhost,127.0.0.1',
    cast=lambda v: [s.strip() for s in v.split(',')]
)

# Database Configuration
DB_ENGINE = config('DB_ENGINE', default='postgresql')

if DB_ENGINE == 'postgresql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME', default='cv_tailor'),
            'USER': config('DB_USER', default='cv_tailor_user'),
            'PASSWORD': config('DB_PASSWORD'),
            'HOST': config('DB_HOST', default='db'),
            'PORT': config('DB_PORT', default='5432', cast=int),
            'OPTIONS': {
                'connect_timeout': 10,
            },
        }
    }
else:
    # Fallback to SQLite for simple development
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files (local filesystem for development)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'

# CORS Configuration (allow local frontend)
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]
CORS_ALLOW_CREDENTIALS = True

# Cache Configuration (Redis for development - required by django-ratelimit)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://redis:6379/0'),
        'KEY_PREFIX': 'cv_tailor_dev',
        'TIMEOUT': 300,
    }
}

# Celery Configuration (local Redis)
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://redis:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://redis:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

# NEW (ft-023): Task reliability and distribution settings
CELERY_TASK_ACKS_LATE = True  # Acknowledge task after completion (prevents loss on worker crash)
CELERY_TASK_REJECT_ON_WORKER_LOST = True  # Requeue task if worker dies during execution
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # Fetch one task at a time (better distribution)

# AI/LLM Settings
OPENAI_API_KEY = config('OPENAI_API_KEY', default='')

# Set API key in environment for tests and services that check os.environ directly
if OPENAI_API_KEY:
    os.environ['OPENAI_API_KEY'] = OPENAI_API_KEY

# GitHub API Settings
GITHUB_TOKEN = config('GITHUB_TOKEN', default='')

# Google OAuth credentials
GOOGLE_CLIENT_ID = config('GOOGLE_CLIENT_ID', default='')
GOOGLE_CLIENT_SECRET = config('GOOGLE_CLIENT_SECRET', default='')

# Development-specific LLM settings (override base if needed)
MODEL_SELECTION_STRATEGY = config('MODEL_SELECTION_STRATEGY', default='balanced')
TRACK_MODEL_PERFORMANCE = config('TRACK_MODEL_PERFORMANCE', default=True, cast=bool)
OPTIMIZE_FOR_COST = config('OPTIMIZE_FOR_COST', default=False, cast=bool)
OPTIMIZE_FOR_QUALITY = config('OPTIMIZE_FOR_QUALITY', default=False, cast=bool)

# Development budgets (override base if needed)
MODEL_BUDGETS = {
    'daily_budget_usd': config('DAILY_LLM_BUDGET', default=50.0, cast=float),
    'monthly_budget_usd': config('MONTHLY_LLM_BUDGET', default=1000.0, cast=float),
    'max_cost_per_user_daily': config('MAX_USER_DAILY_COST', default=5.0, cast=float),
    'cost_alert_threshold': 0.8
}

# LangChain Settings (can be overridden via .env)
LANGCHAIN_SETTINGS = {
    'chunk_size': config('LANGCHAIN_CHUNK_SIZE', default=1000, cast=int),
    'chunk_overlap': config('LANGCHAIN_CHUNK_OVERLAP', default=200, cast=int),
    'max_chunks_per_document': config('MAX_CHUNKS_PER_DOCUMENT', default=50, cast=int),
    'semantic_chunking_threshold': config('SEMANTIC_CHUNKING_THRESHOLD', default=0.8, cast=float)
}

# ft-030: Anti-Hallucination Improvements Settings
# Feature flag to enable/disable verification service
FT030_VERIFICATION_ENABLED = config('FT030_VERIFICATION_ENABLED', default=True, cast=bool)

# GPT-5 Configuration (ADR-045)
FT030_GPT5_ENABLED = config('FT030_GPT5_ENABLED', default=True, cast=bool)

# Reasoning effort levels by task type
FT030_REASONING_LEVELS = {
    'extraction': config('FT030_REASONING_EXTRACTION', default='high'),
    'verification': config('FT030_REASONING_VERIFICATION', default='high'),
    'generation': config('FT030_REASONING_GENERATION', default='medium'),
    'ranking': config('FT030_REASONING_RANKING', default='low')
}

# Confidence Threshold Overrides (ADR-043)
FT030_THRESHOLDS = {
    'high': config('FT030_THRESHOLD_HIGH', default=0.85, cast=float),
    'medium': config('FT030_THRESHOLD_MEDIUM', default=0.70, cast=float),
    'low': config('FT030_THRESHOLD_LOW', default=0.50, cast=float)
}

# Inferred item ratio threshold (trigger penalty if exceeded)
FT030_INFERRED_RATIO_THRESHOLD = config('FT030_INFERRED_RATIO_THRESHOLD', default=0.30, cast=float)

# Verification performance settings
FT030_VERIFICATION_SETTINGS = {
    'max_parallel_verifications': config('FT030_MAX_PARALLEL_VERIFICATIONS', default=5, cast=int),
    'verification_timeout': config('FT030_VERIFICATION_TIMEOUT', default=30, cast=int)
}

# Logging (file + console for development)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'cv_tailor.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'google_auth': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'llm_services': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'generation': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# Rate Limiting (enabled for development to prevent API abuse and match production behavior)
# SECURITY FIX: Enable rate limiting in development (High Security Issue #2)
# Use higher limits than production for development convenience
RATELIMIT_ENABLE = True

# REST Framework Throttling (much higher limits for development testing - 100x production)
REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = [
    'rest_framework.throttling.AnonRateThrottle',
    'rest_framework.throttling.UserRateThrottle',
]
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'anon': '10000/hour',    # Much higher than production for development testing
    'user': '10000/hour',    # Much higher than production for development testing
}

# Security settings (relaxed for development)
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Debug toolbar (optional, add to INSTALLED_APPS if needed)
if DEBUG:
    try:
        import debug_toolbar
        INSTALLED_APPS += ['debug_toolbar']
        MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE
        INTERNAL_IPS = ['127.0.0.1', 'localhost']
    except ImportError:
        pass
