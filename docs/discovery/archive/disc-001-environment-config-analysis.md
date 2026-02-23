# Discovery: Environment Configuration Analysis

**File:** `docs/discovery/disc-001-environment-config-analysis.md`
**Date:** 2025-10-20
**Purpose:** Analyze current configuration patterns to inform production deployment architecture
**Related FEATURE:** ft-020-production-environment-config.md (to be created)

---

## Executive Summary

Current CV-Tailor configuration uses a **single-file settings** approach with `python-decouple` for environment variables. No AWS integration exists. Static/media files stored locally. **Ready for environment split and cloud deployment.**

**Key Finding:** The `llm_services/services/base/settings_manager.py` pattern provides an excellent abstraction layer that can be extended for environment-specific configuration management.

---

## Current Configuration Architecture

### 1. Settings Structure

**File:** `backend/cv_tailor/settings.py` (319 lines, monolithic)

**Pattern:**
```python
from decouple import config

SECRET_KEY = config('SECRET_KEY', default='django-insecure-placeholder-key-for-development')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=lambda v: [s.strip() for s in v.split(',')])
```

**Strengths:**
- ✅ Consistent use of `decouple.config()` for env vars
- ✅ Sensible defaults for development
- ✅ Type casting (bool, int, float) handled
- ✅ Security-conscious (checks DEBUG flag in custom commands)

**Limitations:**
- ❌ No environment separation (dev/staging/prod in same file)
- ❌ Production security settings mixed with dev defaults
- ❌ No validation for required production env vars
- ❌ Cannot override settings based on DJANGO_ENV

### 2. Environment Variable Management

**Current Approach:** `python-decouple` library

**Usage Pattern Found (38 files with `config()` or `environ`):**
```python
# Settings that use config()
- SECRET_KEY
- DEBUG
- ALLOWED_HOSTS
- DB_ENGINE, DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
- CELERY_BROKER_URL, CELERY_RESULT_BACKEND
- OPENAI_API_KEY
- GITHUB_TOKEN
- GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
- MODEL_SELECTION_STRATEGY
- MODEL_BUDGETS (daily/monthly limits)
- LANGCHAIN_SETTINGS
- CIRCUIT_BREAKER_SETTINGS
```

**Environment Variable Files:**
- `backend/.env` (git-ignored)
- `backend/.env.example` (checked in, 45 lines)

**Docker Integration:**
```yaml
# docker-compose.yml
env_file:
  - ./backend/.env
environment:
  - DB_HOST=db  # Override for containers
  - CELERY_BROKER_URL=redis://redis:6379/0
```

### 3. Secrets Management

**Current State:**
- **Storage:** Plain text in `.env` files
- **Protection:** `.gitignore` prevents commit
- **Rotation:** Manual (no automation)
- **Scope:** All environments use same pattern

**Sensitive Secrets Identified:**
1. `DJANGO_SECRET_KEY` - Session signing
2. `OPENAI_API_KEY` - LLM API access ($$ cost risk)
3. `DB_PASSWORD` - Database access
4. `GOOGLE_CLIENT_SECRET` - OAuth credentials
5. `GITHUB_TOKEN` - API access for repo analysis

**Security Gaps:**
- No secrets rotation strategy
- No audit logging for secret access
- No differentiation between dev/prod secrets
- API keys in environment variables (accessible via `/proc/`)

### 4. Static and Media Files

**Current Implementation:**

**Static Files (CSS, JS, frontend assets):**
```python
# settings.py:126-129
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
```
- **Storage:** Local filesystem (`/app/staticfiles/`)
- **Serving:** WhiteNoise middleware (in-process)
- **CDN:** None (direct from Django)
- **Compression:** Enabled (WhiteNoise gzip/brotli)

**Media Files (user uploads, artifacts, generated PDFs):**
```python
# settings.py:132-133
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
```
- **Storage:** Local filesystem (`/app/media/`)
- **Serving:** Django (via MEDIA_URL)
- **Backup:** Docker volumes only (vulnerable to data loss)
- **Scaling:** Not shared across multiple backend instances

**File Upload Settings:**
```python
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
```

**Docker Volume Configuration:**
```yaml
# docker-compose.yml (implicit)
volumes:
  - ./backend:/app  # Includes media/ directory
```

**Gaps for Production:**
- ❌ Local storage doesn't scale across multiple ECS tasks
- ❌ No CDN for static file delivery (latency for global users)
- ❌ No backup strategy for user uploads
- ❌ No encryption at rest for sensitive documents

---

## Reusable Patterns Discovered

### 1. SettingsManager Pattern (EXCELLENT - Reuse This!)

**File:** `backend/llm_services/services/base/settings_manager.py` (80 lines)

**Pattern:**
```python
class SettingsManager:
    """Centralized configuration management for LLM services"""

    @classmethod
    def get_llm_config(cls) -> Dict[str, Any]:
        return getattr(settings, 'LLM_SERVICE_SETTINGS', {
            'default_timeout': 30,
            'retry_attempts': 3,
            'fallback_enabled': True
        })

    @classmethod
    def get_circuit_breaker_config(cls) -> Dict[str, Any]:
        return getattr(settings, 'CIRCUIT_BREAKER_SETTINGS', {...})
```

**Why This Is Excellent:**
- ✅ **Centralized:** Single source of truth for service config
- ✅ **Type-safe:** Returns typed dictionaries
- ✅ **Fallback defaults:** Never crashes if setting missing
- ✅ **Testable:** Easy to mock in tests
- ✅ **Layer separation:** Services don't import settings directly

**Reuse Strategy:**
Extend this pattern for environment-specific settings:
```python
# New: EnvironmentSettingsManager
@classmethod
def get_storage_backend(cls) -> str:
    """Returns 's3' for prod, 'local' for dev"""
    if cls.is_production():
        return 's3'
    return 'local'

@classmethod
def get_secrets_backend(cls) -> str:
    """Returns 'aws_secrets' for prod, 'env_file' for dev"""
    ...
```

### 2. Environment-Aware Security Pattern

**File:** `backend/accounts/management/commands/create_dev_superuser.py:27-34`

**Pattern:**
```python
# SECURITY: Refuse to run in production
if not settings.DEBUG:
    self.stdout.write(
        self.style.ERROR(
            '❌ SECURITY: create_dev_superuser refused to run '
            '(DEBUG=False). This command is for development only!'
        )
    )
    return
```

**Why This Works:**
- ✅ **Fail-safe:** Production can't accidentally create insecure users
- ✅ **Explicit:** Clear error message
- ✅ **Idempotent:** Checks if user exists before creating

**Reuse Strategy:**
Apply this pattern to:
- Development-only middleware (debug toolbar)
- Test data seeding commands
- Unsafe configuration combinations

### 3. Environment Variable Validation Pattern

**File:** `backend/llm_services/tests/unit/services/base/test_settings_manager.py:68-73`

**Pattern:**
```python
with self.assertRaises(ValueError):
    # Test that missing required config raises error
    ...
```

**Gap Identified:**
- Current code doesn't validate required env vars at startup
- Django starts even with missing OPENAI_API_KEY
- Errors only appear when LLM calls happen (runtime failure)

**Improvement Needed:**
Add startup validation in `settings/__init__.py`:
```python
REQUIRED_VARS = {
    'production': ['SECRET_KEY', 'OPENAI_API_KEY', 'DB_PASSWORD'],
    'staging': ['SECRET_KEY', 'OPENAI_API_KEY'],
    'development': []  # Lenient for local dev
}

def validate_environment():
    env = os.environ.get('DJANGO_ENV', 'development')
    for var in REQUIRED_VARS[env]:
        if not os.environ.get(var):
            raise ImproperlyConfigured(f"Missing required env var: {var}")
```

---

## AWS Integration Analysis

### Current State: ZERO AWS Usage

**Search Results:**
- `boto3` references: **11 files** (all test files, not production)
- `aws` references: **11 files** (same test files)
- Production code: **NO AWS SDK usage**

**Test File Examples:**
```python
# llm_services/tests/integration/test_real_pdf_enrichment.py
# Uses "aws" in test names, but mocks S3
```

**Conclusion:** Clean slate for AWS integration, no refactoring needed.

### Recommended AWS Services (10-30 users)

Based on current architecture analysis:

1. **Secrets Manager** (replaces .env for prod)
   - Store: SECRET_KEY, OPENAI_API_KEY, DB_PASSWORD, GOOGLE_CLIENT_SECRET
   - Cost: $0.40/secret/month = ~$2/month for 5 secrets

2. **S3** (replaces local media storage)
   - Static files bucket (CloudFront later)
   - Media files bucket (user uploads)
   - Cost: ~$5-10/month for 5-10GB storage

3. **RDS PostgreSQL** (replaces Docker PostgreSQL)
   - Instance: db.t4g.micro (2 vCPU, 1GB RAM)
   - Current config supports this (already using PostgreSQL)
   - Cost: ~$15-20/month

4. **ElastiCache Redis** (replaces Docker Redis)
   - Instance: cache.t4g.micro
   - Already configured (Celery broker + cache)
   - Cost: ~$12/month

5. **ECS Fargate** (replaces Docker Compose)
   - Backend task: 0.5 vCPU, 1GB RAM
   - Celery task: 0.25 vCPU, 0.5GB RAM
   - Cost: ~$25-35/month

---

## Database Configuration Analysis

**Current Setup:**
```python
# settings.py:78-102
DB_ENGINE = config('DB_ENGINE', default='sqlite')

if DB_ENGINE == 'postgresql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME', default='cv_tailor'),
            'USER': config('DB_USER', default='cv_tailor_user'),
            'PASSWORD': config('DB_PASSWORD', default='your-secure-password-here'),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432', cast=int),
            'OPTIONS': {
                'connect_timeout': 10,
            },
        }
    }
```

**Strengths:**
- ✅ Already supports PostgreSQL (production-ready)
- ✅ Environment variable driven
- ✅ Connection timeout configured

**Gaps for RDS:**
- ❌ No SSL/TLS configuration for encrypted connections
- ❌ No connection pooling (recommended for Fargate)
- ❌ No read replica support

**Recommended Additions for Production:**
```python
# Production database settings
'OPTIONS': {
    'connect_timeout': 10,
    'sslmode': 'require',  # Force SSL for RDS
    'options': '-c statement_timeout=30000',  # 30 second query timeout
},
'CONN_MAX_AGE': 60,  # Connection pooling (reuse for 60 seconds)
```

---

## Dependencies Analysis

**Current Dependencies (from `pyproject.toml`):**

**Web Framework:**
- `django>=4.2.24` ✅
- `djangorestframework>=3.16.1` ✅
- `gunicorn>=21.0,<22.0` ✅ (Production WSGI server)

**Auth:**
- `djangorestframework-simplejwt>=5.5.1` ✅
- `django-allauth>=65.11.2` ✅ (Google OAuth)

**Database:**
- `psycopg2-binary>=2.9.10` ✅ (PostgreSQL driver)

**Cache/Queue:**
- `celery>=5.5.3` ✅
- `redis>=6.4.0` ✅

**LLM:**
- `openai>=1.108.2` ✅
- `langchain>=0.1,<1.0` ✅

**Static Files:**
- `whitenoise>=6.11.0` ✅ (Current static file serving)

**Security:**
- `django-ratelimit>=4.1,<5.0` ⚠️ (Listed but commented out in INSTALLED_APPS)
- `cryptography>=46.0.1` ✅

**Missing for Production:**
- ❌ `boto3` - AWS SDK
- ❌ `django-storages` - S3 storage backend
- ❌ `sentry-sdk` - Error tracking (in optional-dependencies.prod)
- ❌ `django-health-check` - Health check endpoint (in optional-dependencies.prod)

---

## Security Analysis

### Current Security Settings

**Good Practices Found:**
```python
# Password validation enabled
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# CORS configured (but only for localhost)
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# JWT token expiry
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}
```

**Missing Production Security:**
```python
# These are NOT set (all default to False in dev)
SECURE_SSL_REDIRECT = False  # ❌ Should be True in prod
SESSION_COOKIE_SECURE = False  # ❌ Should be True in prod
CSRF_COOKIE_SECURE = False  # ❌ Should be True in prod
SECURE_HSTS_SECONDS = 0  # ❌ Should be 31536000 in prod
SECURE_HSTS_INCLUDE_SUBDOMAINS = False  # ❌ Should be True
SECURE_CONTENT_TYPE_NOSNIFF = False  # ❌ Should be True
X_FRAME_OPTIONS = 'DENY'  # ✅ Already set (good!)
```

**Rate Limiting:**
- `django-ratelimit` in dependencies but **NOT ACTIVE** (commented out in INSTALLED_APPS line 29)
- No rate limiting on API endpoints
- ⚠️ **RISK:** OpenAI API calls unthrottled (cost abuse possible)

### Cost Protection Analysis

**Current LLM Cost Controls:**
```python
# settings.py:238-243
MODEL_BUDGETS = {
    'daily_budget_usd': config('DAILY_LLM_BUDGET', default=50.0, cast=float),
    'monthly_budget_usd': config('MONTHLY_LLM_BUDGET', default=1000.0, cast=float),
    'max_cost_per_user_daily': config('MAX_USER_DAILY_COST', default=5.0, cast=float),
    'cost_alert_threshold': 0.8  # Alert at 80% of budget
}
```

**Performance Tracking:**
```python
# llm_services/services/reliability/performance_tracker.py
# Tracks: latency, cost, tokens, errors
# Gap: No enforcement of MODEL_BUDGETS (tracking only, no blocking)
```

**Recommendation:**
Add budget enforcement in production:
```python
# In API views
@ratelimit(key='user', rate='50/h', method='POST', block=True)
def generate_bullets(request):
    daily_spend = PerformanceTracker.get_user_daily_spend(request.user.id)
    if daily_spend > settings.MODEL_BUDGETS['max_cost_per_user_daily']:
        return Response({'error': 'Daily budget exceeded'}, status=429)
    ...
```

---

## CORS Configuration Analysis

**Current:**
```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # Local frontend dev
    "http://127.0.0.1:3000",
    "http://localhost:3001",  # Alternative port
    "http://127.0.0.1:3001",
]
```

**Gap:** Hardcoded localhost origins, no production domain

**Recommendation:**
```python
# base.py
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGIN_REGEXES = []

# production.py
CORS_ALLOWED_ORIGINS = [
    'https://cv-tailor.com',
    'https://www.cv-tailor.com',
    'https://app.cv-tailor.com',
]

# development.py
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://localhost:3001',
]
```

---

## Test Environment Configuration

**Found:** Reference to separate test settings

```python
# pyproject.toml:129
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "cv_tailor.settings.test"
```

**Gap:** File `cv_tailor/settings/test.py` **DOES NOT EXIST**

**Directory Check:**
```bash
ls -la backend/cv_tailor/settings/
# total 0
# drwxr-xr-x  2  64 Oct 16 22:06 .
# drwxr-xr-x  9 288 Oct 17 22:00 ..
```

**Impact:** Tests likely using main settings.py (not isolated)

**Recommendation:**
Create `settings/test.py` with:
- In-memory database (SQLite)
- Disabled Celery (synchronous tasks)
- Mocked external APIs
- Fast password hashing

---

## Logging Configuration Analysis

**Current:**
```python
# settings.py:293-319
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'cv_tailor.log',  # ❌ Local file
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {...},
        'google_auth': {...},
    },
}
```

**Gaps for Production:**
- ❌ Local file logging doesn't work in ephemeral containers (ECS Fargate)
- ❌ No structured logging (JSON format for CloudWatch parsing)
- ❌ No log aggregation
- ❌ Missing loggers for `llm_services`, `generation`, `artifacts`

**Recommendation:**
```python
# production.py
import watchtower  # CloudWatch handler

LOGGING['handlers']['cloudwatch'] = {
    'class': 'watchtower.CloudWatchLogHandler',
    'log_group': 'cv-tailor-prod',
    'stream_name': '{machine_name}/{logger_name}',
}
```

---

## Celery Configuration Analysis

**Current:**
```python
# settings.py:189-193
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
```

**Strengths:**
- ✅ Already configured
- ✅ JSON serialization (secure, no pickle)
- ✅ Environment variable driven

**Gaps for Production:**
- ❌ No task routing (all tasks in one queue)
- ❌ No rate limiting per task type
- ❌ No task result expiry (Redis fills up)
- ❌ No task timeouts

**Tasks Found:**
```python
# artifacts/tasks.py
# generation/tasks.py
```

**Recommendation:**
```python
# production.py
CELERY_TASK_ROUTES = {
    'artifacts.tasks.*': {'queue': 'artifact_processing'},
    'generation.tasks.*': {'queue': 'cv_generation'},
}
CELERY_RESULT_EXPIRES = 3600  # 1 hour
CELERY_TASK_TIME_LIMIT = 300  # 5 minutes max
CELERY_TASK_SOFT_TIME_LIMIT = 240  # Warning at 4 minutes
```

---

## Scaling Considerations

**Current Architecture:**
- Single backend container (docker-compose)
- Single Celery worker
- Shared volume for media files

**Scaling Blockers for Multiple Instances:**

1. **Media Files (Critical)**
   - Local `/app/media/` not shared across containers
   - Two ECS tasks can't access same artifacts
   - **Solution:** S3 storage backend

2. **Static Files (Minor)**
   - WhiteNoise works per-container (each builds staticfiles)
   - **Solution:** S3 + CloudFront (lazy optimization)

3. **Database (Ready)**
   - PostgreSQL supports multiple connections ✅
   - RDS can handle 10-30 connections easily

4. **Redis (Ready)**
   - ElastiCache supports multiple clients ✅

**Right-Sizing for 10-30 Users:**
- **Backend:** 1-2 ECS tasks (auto-scale at 70% CPU)
- **Celery:** 1 task (most operations are synchronous)
- **Database:** db.t4g.micro (1GB RAM sufficient)
- **Redis:** cache.t4g.micro (0.5GB sufficient)

---

## Migration Path Assessment

### Low Risk Changes:
1. ✅ Split settings into base/dev/staging/prod (no code changes)
2. ✅ Add boto3 and django-storages (isolated dependencies)
3. ✅ Create Terraform modules (infrastructure only)

### Medium Risk Changes:
1. ⚠️ Switch to S3 storage (requires migration of existing media files)
2. ⚠️ Enable rate limiting (might affect legitimate users)
3. ⚠️ Add security middleware (test for CORS issues)

### High Risk Changes:
1. ⚠️⚠️ Database migration to RDS (requires backup and restore)
2. ⚠️⚠️ Secrets migration to AWS Secrets Manager (must not break existing deployments)

**Recommended Order:**
1. Settings refactoring (local dev still works)
2. Add tests for new settings module
3. Deploy Terraform to staging (new environment)
4. Test staging thoroughly
5. Migrate production (low traffic window)

---

## Key Findings Summary

### Strengths to Build Upon:
1. ✅ **SettingsManager pattern** in llm_services (excellent abstraction)
2. ✅ **Consistent env var usage** with python-decouple
3. ✅ **PostgreSQL ready** (already configured)
4. ✅ **Security-aware code** (DEBUG checks in management commands)
5. ✅ **Good test coverage** (89.6% in generation/)

### Critical Gaps:
1. ❌ **No environment separation** (dev/prod mixed)
2. ❌ **Local file storage** (doesn't scale)
3. ❌ **No secrets rotation**
4. ❌ **Missing production security settings**
5. ❌ **Rate limiting disabled**
6. ❌ **No cost enforcement** (budget tracking only)

### Reusable Components:
1. `llm_services/services/base/settings_manager.py` - Extend for environment config
2. `accounts/management/commands/create_dev_superuser.py` - Environment-aware pattern
3. `llm_services/services/reliability/performance_tracker.py` - Cost tracking foundation

### Anti-Patterns to Avoid:
1. ❌ Don't create separate settings.py files (use module)
2. ❌ Don't duplicate env var loading logic (centralize in base.py)
3. ❌ Don't hardcode environment detection (use DJANGO_ENV var)

---

## Recommendations for Next Steps

### Immediate (Phase 2-3):
1. Create TECH SPEC with architecture diagram
2. Create ADRs for key decisions (settings split, AWS services, secrets)
3. Create FEATURE spec with implementation plan

### Implementation Priority (Phase 4-5):
1. **Week 1:** Settings refactoring + tests (TDD)
2. **Week 2:** Terraform infrastructure + dependencies
3. **Week 3:** Security hardening + CI/CD
4. **Week 4:** Staging deployment + documentation

### Testing Strategy:
- Write tests BEFORE implementation (TDD)
- Test settings loading for all environments
- Mock AWS SDK calls (don't hit real services in tests)
- Integration test with staging environment

---

## Files Analyzed

**Settings:**
- ✅ `backend/cv_tailor/settings.py` (319 lines)
- ✅ `backend/llm_services/services/base/settings_manager.py` (80 lines)
- ✅ `backend/.env.example` (45 lines)

**Docker:**
- ✅ `docker-compose.yml` (116 lines)
- ✅ `backend/Dockerfile` (51 lines)

**Tests:**
- ✅ `backend/llm_services/tests/unit/services/base/test_settings_manager.py`
- ✅ `backend/pyproject.toml` (test configuration)

**Security:**
- ✅ `backend/accounts/management/commands/create_dev_superuser.py` (83 lines)

**Grep Searches:**
- ✅ AWS/boto3 references (11 test files)
- ✅ Environment variable usage (38 files, 149 occurrences)
- ✅ DEBUG checks (1 production usage)
- ✅ Secrets usage (15 files)

---

## Next Document

**TECH SPEC:** `docs/specs/spec-deployment-v1.0.md`
- Full architecture diagram
- AWS service specifications
- Cost estimates
- Scaling thresholds
