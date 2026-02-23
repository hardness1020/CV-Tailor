# ADR-029: Multi-Environment Django Settings Architecture

**File:** `docs/adrs/adr-029-multi-environment-settings.md`
**Status:** Accepted
**Date:** 2025-10-20
**Deciders:** DevOps Team, Backend Team
**Related Documents:**
- Discovery: `disc-001-environment-config-analysis.md`
- TECH SPEC: `spec-deployment-v1.0.md`
- FEATURE: `ft-020-production-environment-config.md` (to be created)

---

## Context

Currently, CV-Tailor uses a single `backend/cv_tailor/settings.py` file (319 lines) for all environments (development, staging, production). This creates several problems:

**Current Issues:**
1. **Security Risk:** Production security settings (SECURE_SSL_REDIRECT, CSRF_COOKIE_SECURE, etc.) are set to False by default, requiring manual changes before deployment
2. **Configuration Drift:** No clear separation between dev and prod settings, leading to accidental misconfigurations
3. **Debugging Difficulty:** Production runs with `DEBUG=True` if `.env` is misconfigured
4. **Secrets Management:** All environments use the same secret loading pattern (`.env` files), not suitable for production
5. **Testing Issues:** Tests reference `cv_tailor.settings.test` in `pyproject.toml` but the file doesn't exist

**Discovered Patterns:**
- Good: `llm_services/services/base/settings_manager.py` shows clean abstraction pattern
- Good: `accounts/management/commands/create_dev_superuser.py` checks `settings.DEBUG` to refuse running in production
- Gap: No environment-specific settings modules
- Gap: No validation for required production environment variables

**Trigger:**
Preparing for AWS production deployment requires clear environment separation with different:
- Database configurations (local PostgreSQL vs RDS)
- Static/media storage (local filesystem vs S3)
- Secrets management (`.env` files vs AWS Secrets Manager)
- Security settings (permissive dev vs strict production)
- Logging configuration (console vs CloudWatch)

---

## Decision

**Adopt a modular Django settings architecture with environment-specific modules:**

```
backend/cv_tailor/settings/
├── __init__.py          # Environment detection and auto-import
├── base.py              # Shared configuration (all environments)
├── development.py       # Local development overrides
├── staging.py           # AWS staging environment
├── production.py        # AWS production environment
└── test.py              # Test environment (isolated)
```

**Key Principles:**

1. **Environment Detection via `DJANGO_ENV` Environment Variable:**
   ```python
   # settings/__init__.py
   import os
   DJANGO_ENV = os.environ.get('DJANGO_ENV', 'development')

   if DJANGO_ENV == 'production':
       from .production import *
   elif DJANGO_ENV == 'staging':
       from .staging import *
   elif DJANGO_ENV == 'test':
       from .test import *
   else:
       from .development import *
   ```

2. **Base Settings (Shared Across All Environments):**
   - `INSTALLED_APPS`, `MIDDLEWARE`, `TEMPLATES`
   - `AUTH_USER_MODEL`, `REST_FRAMEWORK`, `SIMPLE_JWT`
   - Database configuration templates (using `config()`)
   - Celery configuration templates
   - LLM settings (`MODEL_STRATEGIES`, `MODEL_BUDGETS`)
   - Circuit breaker settings

3. **Environment-Specific Overrides:**

   **development.py:**
   - `DEBUG = True`
   - `ALLOWED_HOSTS = ['localhost', '127.0.0.1']`
   - Local database (Docker PostgreSQL)
   - Local Redis
   - Local static/media files (WhiteNoise + filesystem)
   - Console logging
   - No rate limiting (for ease of development)

   **staging.py:**
   - `DEBUG = False` (but with verbose logging)
   - AWS RDS PostgreSQL
   - AWS ElastiCache Redis
   - AWS S3 for static/media files
   - AWS Secrets Manager for secrets
   - CloudWatch logging
   - Production-like security settings
   - Rate limiting enabled (same as production)

   **production.py:**
   - `DEBUG = False`
   - All security middleware enabled
   - AWS Secrets Manager (with retry logic)
   - Strict CORS policy
   - Rate limiting enforced
   - CloudWatch structured logging
   - Performance monitoring enabled

   **test.py:**
   - In-memory SQLite database (fast)
   - Synchronous Celery (no Redis)
   - Mocked external APIs
   - Fast password hashing
   - No rate limiting

4. **Validation at Import Time:**
   ```python
   # settings/__init__.py
   if DJANGO_ENV in ['production', 'staging']:
       required_vars = ['SECRET_KEY', 'OPENAI_API_KEY', 'DB_HOST']
       missing = [var for var in required_vars if not globals().get(var)]
       if missing:
           raise ImproperlyConfigured(f"Missing required settings: {missing}")
   ```

5. **Backward Compatibility:**
   - Keep existing `settings.py` as `settings/base.py` (with modifications)
   - Update `manage.py`, `wsgi.py`, `asgi.py` to point to `cv_tailor.settings` (no change needed, imports `settings/__init__.py`)
   - Update `.env.example` to include `DJANGO_ENV` variable

---

## Consequences

### Positive

1. **✅ Security by Default:**
   - Production settings enforce SSL, secure cookies, HSTS without manual changes
   - No risk of deploying with `DEBUG=True`
   - Clear separation of development and production secrets

2. **✅ Configuration Clarity:**
   - Easy to see environment-specific differences
   - Reduced risk of configuration drift
   - New developers can't accidentally break production settings

3. **✅ Testing Isolation:**
   - Test environment uses fast in-memory database
   - No interference with development database
   - Mocked external services prevent flaky tests

4. **✅ Deployment Simplicity:**
   - Single environment variable (`DJANGO_ENV`) controls all settings
   - No manual settings changes before deployment
   - CI/CD pipeline can test staging settings before production

5. **✅ Maintainability:**
   - Shared settings in `base.py` reduce duplication
   - Environment-specific changes are localized
   - Following Django best practices (widely documented)

6. **✅ Extends Existing Patterns:**
   - Builds on `SettingsManager` abstraction in `llm_services`
   - Compatible with existing `python-decouple` usage
   - Leverages existing environment-aware code (e.g., `create_dev_superuser.py`)

### Negative

1. **❌ Migration Effort:**
   - Need to split existing `settings.py` into modules
   - Update all environments to set `DJANGO_ENV` variable
   - Update Docker Compose, Terraform, GitHub Actions

2. **❌ Slightly More Complex:**
   - New developers need to understand settings module structure
   - More files to navigate (5 instead of 1)
   - Need to know which environment they're running

3. **❌ Import Order Matters:**
   - Settings modules must maintain correct import order (base → environment)
   - Risk of circular imports if not careful
   - Some settings can't be overridden after import

4. **❌ Testing Overhead:**
   - Need tests for settings loading in each environment
   - Need to verify environment detection logic
   - More settings files to maintain

### Mitigation

- **Documentation:** Add clear README in `settings/` directory explaining structure
- **Validation:** Comprehensive tests for settings loading (`test_settings.py`)
- **Defaults:** Sensible defaults in `base.py` minimize environment-specific overrides
- **Examples:** Update `.env.example` with all environment variable options

---

## Alternatives Considered

### Alternative 1: Single settings.py with if/else blocks

```python
# settings.py
if os.environ.get('DJANGO_ENV') == 'production':
    DEBUG = False
    SECURE_SSL_REDIRECT = True
    # ... 50 lines of production settings
else:
    DEBUG = True
    # ... dev settings
```

**Rejected because:**
- ❌ Single file becomes 500+ lines (hard to maintain)
- ❌ Nested if/else blocks reduce readability
- ❌ Easy to forget a condition (security risk)
- ❌ Not idiomatic Django (most projects use modules)

### Alternative 2: python-decouple only (no modules)

```python
# settings.py
DEBUG = config('DEBUG', default=True, cast=bool)
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=False, cast=bool)
# ... 100+ config() calls
```

**Rejected because:**
- ❌ Requires 100+ environment variables
- ❌ `.env` files become 200+ lines
- ❌ Easy to forget to set a variable
- ❌ No type safety (all strings)
- ❌ Complex settings (dicts, lists) hard to express in env vars

### Alternative 3: django-environ library

```python
# settings.py
import environ
env = environ.Env()
DEBUG = env.bool('DEBUG', default=True)
```

**Rejected because:**
- ❌ Adds new dependency (we already use `python-decouple`)
- ❌ Doesn't solve the core problem (still need environment separation)
- ❌ Migration effort without clear benefit
- ✅ Could reconsider in future if `decouple` becomes limiting

### Alternative 4: External configuration service (Consul, etcd)

**Rejected because:**
- ❌ Massive overkill for project size (10-30 users initially)
- ❌ Adds operational complexity (need to run Consul cluster)
- ❌ Not needed until multi-region deployment
- ✅ Consider for Phase 2 (1000+ users)

---

## Rollback Plan

If the settings refactoring causes issues:

**Immediate Rollback (within 1 hour):**
1. Revert commits that created `settings/` module
2. Restore original `settings.py` from git history
3. Remove `DJANGO_ENV` environment variable
4. Restart services

**Partial Rollback (keep some changes):**
1. Keep `settings/base.py` as single settings file
2. Remove `DJANGO_ENV` detection logic
3. Manually change production settings before deployment (old workflow)

**Data Impact:**
- ✅ **No database migrations** (settings only)
- ✅ **No data loss risk** (configuration change only)
- ✅ **Zero downtime** (can deploy settings change without restart)

**Testing Before Production:**
1. Test locally with `DJANGO_ENV=development`
2. Deploy to staging with `DJANGO_ENV=staging`
3. Run full test suite on staging
4. Manual QA on staging (login, upload, generate CV)
5. Only then deploy to production

---

## Implementation Checklist

**Phase 1: Preparation**
- [x] Document current settings in discovery doc
- [x] Create TECH SPEC with target architecture
- [ ] Create FEATURE spec with implementation plan
- [ ] Write failing tests for settings module loading

**Phase 2: Implementation**
- [ ] Create `settings/` directory
- [ ] Split `settings.py` into `base.py`
- [ ] Create `development.py` with dev overrides
- [ ] Create `staging.py` with AWS staging overrides
- [ ] Create `production.py` with AWS production overrides
- [ ] Create `test.py` for test environment
- [ ] Create `__init__.py` with environment detection
- [ ] Add README in `settings/` directory

**Phase 3: Testing**
- [ ] Write tests for settings loading (all environments)
- [ ] Write tests for environment variable validation
- [ ] Run test suite (verify nothing breaks)
- [ ] Test locally with `DJANGO_ENV=development`
- [ ] Test in Docker with `DJANGO_ENV=staging`

**Phase 4: Deployment**
- [ ] Update `.env.example` with `DJANGO_ENV`
- [ ] Update `docker-compose.yml` to set `DJANGO_ENV=development`
- [ ] Update Terraform to set `DJANGO_ENV` in ECS tasks
- [ ] Update GitHub Actions to set `DJANGO_ENV` for CI/CD
- [ ] Deploy to staging
- [ ] Manual QA on staging
- [ ] Deploy to production
- [ ] Monitor for 24 hours

**Phase 5: Cleanup**
- [ ] Remove old `settings.py` (after confirming everything works)
- [ ] Update documentation (README, deployment guide)
- [ ] Close related issues

---

## Related Decisions

**Upstream Decisions:**
- **ADR-005:** Backend Framework (chose Django)
- **ADR-009:** Python Dependency Management (chose uv)

**Related Decisions (being made concurrently):**
- **ADR-030:** AWS Deployment Architecture (requires environment separation)
- **ADR-031:** Secrets Management Strategy (different for dev vs prod)

**Future Decisions:**
- **ADR-0XX:** Multi-region deployment (will extend this pattern)
- **ADR-0XX:** Configuration as Code (may adopt external config service)

---

## References

**Django Documentation:**
- [Settings Best Practices](https://docs.djangoproject.com/en/4.2/topics/settings/)
- [Deployment Checklist](https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/)

**Industry Patterns:**
- [12-Factor App: Config](https://12factor.net/config)
- [django-environ](https://github.com/joke2k/django-environ)
- [cookiecutter-django settings](https://github.com/cookiecutter/cookiecutter-django/tree/master/%7B%7Bcookiecutter.project_slug%7D%7D/config/settings)

**Internal References:**
- Discovery: `docs/discovery/disc-001-environment-config-analysis.md`
- TECH SPEC: `docs/specs/spec-deployment-v1.0.md`
- SettingsManager pattern: `backend/llm_services/services/base/settings_manager.py`

---

## Approval

**Reviewed by:**
- [x] Backend Team Lead - Approved
- [x] DevOps Team - Approved
- [ ] Security Team - Pending review

**Approved for implementation:** Yes

**Implementation Owner:** Backend Team

**Target Completion:** Week 1 of deployment project (Day 5-6)
