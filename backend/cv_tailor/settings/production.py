"""
Production settings for cv_tailor project.

Extends base.py with AWS production configuration.

Features:
    - AWS Secrets Manager for secret management
    - S3 for static and media files
    - RDS PostgreSQL with SSL
    - ElastiCache Redis
    - CloudWatch logging
    - Full security hardening (HTTPS, HSTS, secure cookies)
    - Rate limiting enabled

Environment Variables Required:
    - AWS_REGION: AWS region (default: us-west-1)
    - AWS_SECRETS_NAME: Name of secrets in Secrets Manager
    - ALLOWED_HOSTS: Comma-separated list of allowed hosts

Secrets Manager JSON Structure:
    {
        "DJANGO_SECRET_KEY": "your-secret-key",
        "OPENAI_API_KEY": "sk-your-openai-key",
        "DB_NAME": "cv_tailor_prod",
        "DB_USER": "cv_tailor_user",
        "DB_PASSWORD": "secure-db-password",
        "DB_HOST": "cv-tailor-prod-db.xxxxx.us-west-1.rds.amazonaws.com",
        "DB_PORT": "5432",
        "REDIS_HOST": "cv-tailor-prod-redis.xxxxx.cache.amazonaws.com",
        "REDIS_PORT": "6379",
        "AWS_STORAGE_BUCKET_NAME": "cv-tailor-prod-media",
        "AWS_STATIC_BUCKET_NAME": "cv-tailor-prod-static",
        "GOOGLE_CLIENT_ID": "your-google-client-id",
        "GOOGLE_CLIENT_SECRET": "your-google-client-secret",
        "GITHUB_TOKEN": "your-github-token"
    }

Related ADRs:
    - ADR-029: Multi-Environment Settings Architecture
    - ADR-030: AWS Deployment Architecture
    - ADR-031: Secrets Management Strategy
"""

import os
import json
import boto3
from botocore.exceptions import ClientError
from .base import *

# Environment variables
AWS_REGION = os.environ.get('AWS_REGION', 'us-west-1')
AWS_SECRETS_NAME = os.environ.get('AWS_SECRETS_NAME', 'cv-tailor/production')


def get_secret(secret_name=AWS_SECRETS_NAME, region_name=AWS_REGION):
    """
    Fetch secrets from AWS Secrets Manager.

    Args:
        secret_name: Name of the secret in Secrets Manager
        region_name: AWS region where secret is stored

    Returns:
        dict: Parsed JSON secrets

    Raises:
        RuntimeError: If secrets cannot be fetched

    Related:
        - ADR-031: Secrets Management Strategy
        - FT-020: Production Environment Configuration
    """
    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'DecryptionFailureException':
            raise RuntimeError(
                "Secrets Manager can't decrypt the protected secret text using the provided KMS key."
            ) from e
        elif error_code == 'InternalServiceErrorException':
            raise RuntimeError(
                "An error occurred on the server side."
            ) from e
        elif error_code == 'InvalidParameterException':
            raise RuntimeError(
                "You provided an invalid value for a parameter."
            ) from e
        elif error_code == 'InvalidRequestException':
            raise RuntimeError(
                "You provided a parameter value that is not valid for the current state of the resource."
            ) from e
        elif error_code == 'ResourceNotFoundException':
            raise RuntimeError(
                f"The requested secret {secret_name} was not found in {region_name}"
            ) from e
        else:
            raise RuntimeError(f"Unknown error fetching secrets: {error_code}") from e

    # Parse and return secret
    if 'SecretString' in get_secret_value_response:
        return json.loads(get_secret_value_response['SecretString'])
    else:
        raise RuntimeError("Secret is not a string (binary secrets not supported)")


# Fetch all secrets from AWS Secrets Manager
# Skip if running tests (tests will mock the secrets)
import sys
TESTING = 'test' in sys.argv or 'pytest' in sys.modules

if not TESTING:
    try:
        secrets = get_secret()
    except Exception as e:
        # In production, we MUST have secrets - fail fast
        raise RuntimeError(
            f"Failed to load secrets from AWS Secrets Manager: {e}\n"
            "Production deployment requires valid AWS Secrets Manager configuration."
        ) from e
else:
    # Provide minimal mock secrets for testing.
    # These use clearly-marked 'test-' prefixes and are never used in real deployments.
    # For comprehensive test fixtures, see conftest.py in each app.
    secrets = {
        'DJANGO_SECRET_KEY': 'test-only-not-a-real-secret-key',
        'OPENAI_API_KEY': 'test-fake-openai-key',
        'DB_NAME': 'test_cv_tailor',
        'DB_USER': 'test_user',
        'DB_PASSWORD': 'test_password',
        'DB_HOST': 'localhost',
        'DB_PORT': '5432',
        'REDIS_HOST': 'localhost',
        'REDIS_PORT': '6379',
        'AWS_STORAGE_BUCKET_NAME': 'test-media-bucket',
        'AWS_STATIC_BUCKET_NAME': 'test-static-bucket',
        'GOOGLE_CLIENT_ID': 'test-client-id',
        'GOOGLE_CLIENT_SECRET': 'test-client-secret',
        'GITHUB_TOKEN': 'test-github-token'
    }

# SECURITY WARNING: Never set DEBUG=True in production!
DEBUG = False

# Security Settings
SECRET_KEY = secrets['DJANGO_SECRET_KEY']

# ALLOWED_HOSTS configuration
# For production, allow custom domain and ALB DNS
# SECURITY FIX: Removed wildcard '*' to prevent Host header injection attacks
# ALB health checks are handled by HealthCheckMiddleware (cv_tailor.middleware)
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get('ALLOWED_HOSTS', '').split(',')
    if host.strip()
]

# HTTPS and Security Headers
# HTTPS is now enabled with ACM certificate on ALB (port 443)
# HTTP requests (port 80) are redirected to HTTPS by ALB
SECURE_SSL_REDIRECT = False  # Keep False: ALB handles redirect (HTTP→HTTPS)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')  # Trust ALB headers
SESSION_COOKIE_SECURE = True  # Only send session cookies over HTTPS
CSRF_COOKIE_SECURE = True  # Only send CSRF tokens over HTTPS
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# HSTS (HTTP Strict Transport Security)
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# CSRF trusted origins (for API requests)
CSRF_TRUSTED_ORIGINS = [
    f"https://{host}" for host in ALLOWED_HOSTS if host
]

# Database Configuration (RDS PostgreSQL with SSL)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': secrets['DB_NAME'],
        'USER': secrets['DB_USER'],
        'PASSWORD': secrets['DB_PASSWORD'],
        'HOST': secrets['DB_HOST'],
        'PORT': secrets.get('DB_PORT', '5432'),
        'OPTIONS': {
            'connect_timeout': 10,
            'sslmode': 'require',  # Require SSL for RDS
        },
        'CONN_MAX_AGE': 600,  # Connection pooling (10 minutes)
    }
}

# AWS S3 Configuration for Static Files
AWS_S3_REGION_NAME = AWS_REGION
AWS_STATIC_BUCKET_NAME = secrets.get('AWS_STATIC_BUCKET_NAME', f'cv-tailor-prod-static')
AWS_STORAGE_BUCKET_NAME = secrets.get('AWS_STORAGE_BUCKET_NAME', f'cv-tailor-prod-media')

# Static files (S3)
AWS_S3_CUSTOM_DOMAIN = f'{AWS_STATIC_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com'
STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'
STATICFILES_STORAGE = 'storages.backends.s3boto3.S3StaticStorage'

# Media files (S3) - Private by default
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
MEDIA_URL = f'https://{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com/'

# S3 Settings
AWS_DEFAULT_ACL = 'private'  # Media files are private
AWS_QUERYSTRING_AUTH = True  # Use signed URLs for media files
AWS_QUERYSTRING_EXPIRE = 3600  # Signed URLs expire in 1 hour
AWS_S3_FILE_OVERWRITE = False  # Don't overwrite files with same name
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',  # Cache for 1 day
}

# Static files location in S3
AWS_STATIC_LOCATION = 'static'
AWS_MEDIA_LOCATION = 'media'

# CORS Configuration (production domains only)
# Allow frontend domains (CloudFront custom domains)
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',')
    if origin.strip()
]
CORS_ALLOW_CREDENTIALS = True

# Cache Configuration (ElastiCache Redis)
REDIS_HOST = secrets['REDIS_HOST']
REDIS_PORT = secrets.get('REDIS_PORT', '6379')
REDIS_PASSWORD = secrets.get('REDIS_PASSWORD', '')

# Redis URL with authentication (ElastiCache requires AUTH)
if REDIS_PASSWORD:
    from urllib.parse import quote_plus
    REDIS_URL = f'redis://:{quote_plus(REDIS_PASSWORD)}@{REDIS_HOST}:{REDIS_PORT}'
else:
    REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': f'{REDIS_URL}/0',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'cv_tailor_prod',
        'TIMEOUT': 300,  # 5 minutes default
    }
}

# Celery Configuration (ElastiCache Redis)
CELERY_BROKER_URL = f'{REDIS_URL}/1'
CELERY_RESULT_BACKEND = f'{REDIS_URL}/1'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# NEW (ft-023): Task reliability and distribution settings
CELERY_TASK_ACKS_LATE = True  # Acknowledge task after completion (prevents loss on worker crash)
CELERY_TASK_REJECT_ON_WORKER_LOST = True  # Requeue task if worker dies during execution
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # Fetch one task at a time (better distribution)

# AI/LLM Settings
OPENAI_API_KEY = secrets.get('OPENAI_API_KEY', '')

# Set API key in environment for services that check os.environ directly
if OPENAI_API_KEY:
    os.environ['OPENAI_API_KEY'] = OPENAI_API_KEY

# GitHub API Settings
GITHUB_TOKEN = secrets.get('GITHUB_TOKEN', '')

# Google OAuth credentials
GOOGLE_CLIENT_ID = secrets.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = secrets.get('GOOGLE_CLIENT_SECRET', '')

# Production Model Strategy (cost-optimized by default)
MODEL_SELECTION_STRATEGY = os.environ.get('MODEL_SELECTION_STRATEGY', 'balanced')
TRACK_MODEL_PERFORMANCE = True
OPTIMIZE_FOR_COST = os.environ.get('OPTIMIZE_FOR_COST', 'false').lower() == 'true'

# Production budgets (more conservative)
MODEL_BUDGETS = {
    'daily_budget_usd': float(os.environ.get('DAILY_LLM_BUDGET', '100.0')),
    'monthly_budget_usd': float(os.environ.get('MONTHLY_LLM_BUDGET', '2000.0')),
    'max_cost_per_user_daily': float(os.environ.get('MAX_USER_DAILY_COST', '10.0')),
    'cost_alert_threshold': 0.8
}

# ft-030: Anti-Hallucination Improvements Settings
# Feature flag to enable/disable verification service
FT030_VERIFICATION_ENABLED = os.environ.get('FT030_VERIFICATION_ENABLED', 'true').lower() == 'true'

# GPT-5 Configuration (ADR-045)
FT030_GPT5_ENABLED = os.environ.get('FT030_GPT5_ENABLED', 'true').lower() == 'true'

# Reasoning effort levels by task type
FT030_REASONING_LEVELS = {
    'extraction': os.environ.get('FT030_REASONING_EXTRACTION', 'high'),
    'verification': os.environ.get('FT030_REASONING_VERIFICATION', 'high'),
    'generation': os.environ.get('FT030_REASONING_GENERATION', 'medium'),
    'ranking': os.environ.get('FT030_REASONING_RANKING', 'low')
}

# Confidence Threshold Overrides (ADR-043)
FT030_THRESHOLDS = {
    'high': float(os.environ.get('FT030_THRESHOLD_HIGH', '0.85')),
    'medium': float(os.environ.get('FT030_THRESHOLD_MEDIUM', '0.70')),
    'low': float(os.environ.get('FT030_THRESHOLD_LOW', '0.50'))
}

# Inferred item ratio threshold (trigger penalty if exceeded)
FT030_INFERRED_RATIO_THRESHOLD = float(os.environ.get('FT030_INFERRED_RATIO_THRESHOLD', '0.30'))

# Verification performance settings
FT030_VERIFICATION_SETTINGS = {
    'max_parallel_verifications': int(os.environ.get('FT030_MAX_PARALLEL_VERIFICATIONS', '5')),
    'verification_timeout': int(os.environ.get('FT030_VERIFICATION_TIMEOUT', '30'))
}

# CloudWatch Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'aws': {
            'format': '[%(levelname)s] %(asctime)s %(name)s: %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'aws',
        },
        # CloudWatch handler disabled - ECS already sends console logs to CloudWatch
        # 'cloudwatch': {
        #     'level': 'INFO',
        #     'class': 'watchtower.CloudWatchLogHandler',
        #     'boto3_client': boto3.client('logs', region_name=AWS_REGION),
        #     'log_group_name': '/aws/ecs/cv-tailor-prod',
        #     'log_stream_name': '{machine_name}/{logger_name}/{strftime:%Y-%m-%d}',
        #     'formatter': 'aws',
        # },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'google_auth': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'llm_services': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'generation': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'artifacts': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
}

# Rate Limiting (production only)
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'

# REST Framework Throttling (API rate limiting)
REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = [
    'rest_framework.throttling.AnonRateThrottle',
    'rest_framework.throttling.UserRateThrottle'
]
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'anon': '100/hour',  # Anonymous users: 100 requests per hour
    'user': '1000/hour'  # Authenticated users: 1000 requests per hour
}

# Email Configuration (optional - for error notifications)
if 'EMAIL_HOST' in secrets:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = secrets['EMAIL_HOST']
    EMAIL_PORT = int(secrets.get('EMAIL_PORT', '587'))
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = secrets.get('EMAIL_HOST_USER', '')
    EMAIL_HOST_PASSWORD = secrets.get('EMAIL_HOST_PASSWORD', '')
    DEFAULT_FROM_EMAIL = secrets.get('DEFAULT_FROM_EMAIL', 'noreply@cv-tailor.com')
    ADMINS = [('Admin', secrets.get('ADMIN_EMAIL', 'admin@cv-tailor.com'))]

# Admin email for error notifications
if 'ADMIN_EMAIL' in secrets:
    ADMINS = [('CV Tailor Admin', secrets['ADMIN_EMAIL'])]
    MANAGERS = ADMINS
