"""
Base Django settings for cv_tailor project.

Contains environment-agnostic configuration.
Environment-specific overrides are in:
    - development.py: Local development
    - production.py: AWS production environment
    - test.py: Test environment

Related ADRs:
    - ADR-029: Multi-Environment Settings Architecture
"""

import os
from pathlib import Path
from datetime import timedelta

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_ratelimit',  # Enabled for production rate limiting
    'django_extensions',
    # Django-allauth
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    # Project apps
    'accounts',
    'artifacts',
    'generation',
    'export',
    # Enhanced LLM services
    'llm_services',
]

MIDDLEWARE = [
    'cv_tailor.middleware.HealthCheckMiddleware',  # SECURITY: Bypass ALLOWED_HOSTS for ALB health checks
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# SECURITY: Validate SECRET_KEY is not using default insecure value
# This prevents accidental production deployment with hardcoded secrets
def validate_secret_key():
    """Validate SECRET_KEY is not using default insecure value."""
    import sys
    # Get SECRET_KEY from the current settings module
    # Skip validation during import (SECRET_KEY may not be set yet)
    if hasattr(sys.modules[__name__], 'SECRET_KEY'):
        secret = getattr(sys.modules[__name__], 'SECRET_KEY', None)
        if secret and 'django-insecure-placeholder' in secret:
            from django.core.exceptions import ImproperlyConfigured
            raise ImproperlyConfigured(
                "SECURITY ERROR: Default SECRET_KEY detected!\n\n"
                "The SECRET_KEY 'django-insecure-placeholder-key-for-development-only' "
                "is hardcoded and insecure.\n\n"
                "Action required:\n"
                "1. Generate a new SECRET_KEY:\n"
                "   python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'\n"
                "2. Add it to your .env file:\n"
                "   SECRET_KEY=<generated-key>\n"
                "3. Never commit .env file to version control\n\n"
                "Related: Critical Security Issue #3 (CVSS 7.3) - Hardcoded SECRET_KEY"
            )

ROOT_URLCONF = 'cv_tailor.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'cv_tailor.wsgi.application'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom user model
AUTH_USER_MODEL = 'accounts.User'

# REST Framework configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': [
        'djangorestframework_camel_case.render.CamelCaseJSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'djangorestframework_camel_case.parser.CamelCaseJSONParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FileUploadParser',
    ],
    'JSON_UNDERSCOREIZE': {
        'no_underscore_before_number': True,
    },
}

# JWT Configuration
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

# File Upload Settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB

# Model Selection Strategy (can be overridden per environment)
MODEL_SELECTION_STRATEGY = 'balanced'
TRACK_MODEL_PERFORMANCE = True
OPTIMIZE_FOR_COST = False
OPTIMIZE_FOR_QUALITY = False

# Model Strategy Configurations
MODEL_STRATEGIES = {
    'cost_optimized': {
        'job_parsing_model': 'gpt-5-mini',
        'cv_generation_model': 'gpt-5-mini',
        'embedding_model': 'text-embedding-3-small',
        'embedding_dimensions': 1536,
        'max_cost_per_generation': 0.05,  # $0.05 per CV
    },
    'balanced': {
        'job_parsing_model': 'gpt-5',
        'cv_generation_model': 'gpt-5',
        'embedding_model': 'text-embedding-3-small',
        'embedding_dimensions': 1536,
        'max_cost_per_generation': 0.15,  # $0.15 per CV
    },
    'quality_optimized': {
        'job_parsing_model': 'gpt-5',
        'cv_generation_model': 'gpt-5',
        'embedding_model': 'text-embedding-3-small',
        'embedding_dimensions': 1536,
        'max_cost_per_generation': 0.50,  # $0.50 per CV
    }
}

# Model Performance & Cost Budgets (can be overridden per environment)
MODEL_BUDGETS = {
    'daily_budget_usd': 50.0,
    'monthly_budget_usd': 1000.0,
    'max_cost_per_user_daily': 5.0,
    'cost_alert_threshold': 0.8  # Alert at 80% of budget
}

# LangChain Document Processing
LANGCHAIN_SETTINGS = {
    'chunk_size': 1000,
    'chunk_overlap': 200,
    'max_chunks_per_document': 50,
    'semantic_chunking_threshold': 0.8
}

# Circuit Breaker Settings
CIRCUIT_BREAKER_SETTINGS = {
    'failure_threshold': 5,
    'timeout': 30,  # seconds
    'retry_attempts': 3
}

# Django-allauth configuration
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
        'OAUTH_PKCE_ENABLED': True,
        'FETCH_USERINFO': True,
    }
}

SOCIALACCOUNT_ADAPTER = 'accounts.adapters.CustomSocialAccountAdapter'
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_VERIFICATION = 'optional'
SOCIALACCOUNT_STORE_TOKENS = False
