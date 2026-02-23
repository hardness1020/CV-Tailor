# Local Development Guide

**Complete guide for developing CV-Tailor on your local machine**

## Overview

This guide covers:
- Setting up your local development environment
- Running the application with Docker Compose
- Understanding the `development` environment
- Common development workflows
- Troubleshooting

## Prerequisites

- **Docker Desktop**: Version 20.10+ (includes Docker Compose v2)
- **Git**: For cloning the repository
- **Code Editor**: VS Code recommended (with Python extension)
- **Terminal**: bash/zsh (macOS/Linux) or Git Bash (Windows)

## Quick Setup (5 Minutes)

### 1. Clone and Navigate

```bash
git clone https://github.com/your-org/cv-tailor.git
cd cv-tailor
```

### 2. Create Environment Files

#### Backend Environment

```bash
# Copy the example file
cp backend/.env.example backend/.env

# Edit with your API keys
nano backend/.env  # or use your preferred editor
```

**Required API Keys** (in `backend/.env`):
```bash
# OpenAI API Key (required for CV generation)
OPENAI_API_KEY=sk-your-actual-openai-key-here

# GitHub Token (optional, for GitHub profile parsing)
GITHUB_TOKEN=ghp_your-github-token

# Google OAuth (optional, for social login)
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

#### Frontend Environment

⚠️ **Required for Google OAuth to work in development**

```bash
# Create frontend .env file
cat > frontend/.env <<EOF
# Development environment variables for frontend

# Backend API URL (uses Vite proxy - see vite.config.ts)
VITE_API_BASE_URL=http://localhost:8000

# Google OAuth Client ID (same as backend)
VITE_GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
EOF
```

**Note**: Frontend uses Vite environment variables with `VITE_` prefix. These are embedded in the frontend bundle at build time.

### 3. Start Services

```bash
# Start all services (PostgreSQL, Redis, Backend, Celery, Frontend)
docker-compose up -d

# Check logs
docker-compose logs backend --tail=50
```

### 4. Verify Setup

```bash
# Backend should be running
curl http://localhost:8000/admin/

# Frontend should be running
curl http://localhost:3000/
```

**You're done!** 🎉

## Development Environment

### What is `development` Environment?

The **development** environment (`backend/cv_tailor/settings/development.py`) is configured for:

✅ **Local development** on your machine
✅ **Hot reload** for code changes
✅ **Debug mode** enabled (`DEBUG=True`)
✅ **Verbose logging** to console
✅ **Local file storage** (not S3)
✅ **PostgreSQL** via Docker Compose
✅ **Redis** via Docker Compose
✅ **Relaxed security** (no HTTPS required)

### Environment Detection

The system **automatically** uses `development` settings:

```bash
# Option 1: Default (DJANGO_ENV not set)
docker-compose up -d
# → Uses development settings

# Option 2: Explicit (same result)
export DJANGO_ENV=development
docker-compose up -d
# → Uses development settings
```

You can verify:
```bash
docker-compose exec backend uv run python -c "from cv_tailor import settings; print(f'Environment: {settings.DJANGO_ENV}, DEBUG: {settings.DEBUG}')"
# Output: Environment: development, DEBUG: True
```

## Docker Compose Services

### Services Overview

```bash
docker-compose ps
```

| Service | Container Name | Port | Purpose |
|---------|---------------|------|---------|
| **db** | cv_tailor_db | 5432 | PostgreSQL 15 database |
| **redis** | cv_tailor_redis | 6379 | Cache & Celery broker |
| **backend** | cv-tailor-backend | 8000 | Django API server |
| **celery** | cv_tailor_celery | - | Background task worker |
| **frontend** | cv_tailor_frontend | 3000 | React development server |

### Starting/Stopping Services

```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d backend

# Stop all services
docker-compose down

# Stop and remove volumes (⚠️ deletes database)
docker-compose down -v

# Restart a service
docker-compose restart backend

# View logs
docker-compose logs -f backend  # Follow logs
docker-compose logs --tail=100 backend  # Last 100 lines
```

## Common Development Tasks

### Running Migrations

```bash
# Create migration files (after model changes)
docker-compose exec backend uv run python manage.py makemigrations

# Apply migrations
docker-compose exec backend uv run python manage.py migrate

# Check migration status
docker-compose exec backend uv run python manage.py showmigrations
```

### Running Tests

```bash
# Fast unit tests (recommended for pre-commit)
docker-compose exec backend uv run python manage.py test --tag=fast --tag=unit --keepdb

# All tests except slow ones
docker-compose exec backend uv run python manage.py test --exclude-tag=slow --keepdb

# All tests
docker-compose exec backend uv run python manage.py test --keepdb

# Specific app tests
docker-compose exec backend uv run python manage.py test accounts --keepdb

# Specific test file
docker-compose exec backend uv run python manage.py test generation.tests.test_services --keepdb
```

### Accessing Django Shell

```bash
# Django shell
docker-compose exec backend uv run python manage.py shell

# Django shell with enhanced features
docker-compose exec backend uv run python manage.py shell_plus
```

### Accessing Database

```bash
# PostgreSQL shell
docker-compose exec db psql -U cv_tailor_user -d cv_tailor

# Run SQL query
docker-compose exec db psql -U cv_tailor_user -d cv_tailor -c "SELECT * FROM accounts_user LIMIT 5;"
```

### Creating Superuser

```bash
# Option 1: Auto-create (if configured in .env)
# See backend/.env.example for DJANGO_SUPERUSER_* variables

# Option 2: Manual creation
docker-compose exec backend uv run python manage.py createsuperuser
```

### Collecting Static Files

```bash
docker-compose exec backend uv run python manage.py collectstatic --noinput
```

### Viewing Logs

```bash
# All services
docker-compose logs

# Specific service
docker-compose logs backend
docker-compose logs celery
docker-compose logs db

# Follow logs (live tail)
docker-compose logs -f backend

# Last N lines
docker-compose logs --tail=50 backend
```

## File Structure

### Local Development Files

```
CV-Tailor/
├── backend/
│   ├── .env                          # Your local secrets (git-ignored)
│   ├── .env.example                  # Template
│   ├── cv_tailor/
│   │   └── settings/
│   │       ├── __init__.py           # Auto-detects environment
│   │       ├── base.py               # Shared config
│   │       ├── development.py        # 👈 YOU ARE HERE
│   │       ├── production.py         # AWS production
│   │       ├── staging.py            # AWS staging
│   │       └── test.py               # Test environment
│   ├── manage.py
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   └── package.json
├── docker-compose.yml                # 👈 Development config
├── docker-compose.override.yml       # Your local overrides (git-ignored)
└── README.md
```

### Development Settings Module

**File**: `backend/cv_tailor/settings/development.py`

**Key Configuration**:
```python
# Debug mode (enabled)
DEBUG = True

# Database (PostgreSQL via Docker)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'cv_tailor',
        'USER': 'cv_tailor_user',
        'HOST': 'db',  # Docker service name
        'PORT': '5432',
    }
}

# Cache (Redis via Docker)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://redis:6379/0',
    }
}

# File storage (local filesystem)
MEDIA_ROOT = '/app/media'
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'

# CORS (allow local frontend)
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Rate limiting (disabled for dev convenience)
RATELIMIT_ENABLE = False

# Security (relaxed for local dev)
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
```

## Development Workflows

### Making Code Changes

**Backend** (Django):
```bash
# 1. Make code changes in your editor
# 2. Changes auto-reload (runserver watches for changes)
# 3. Check logs for errors
docker-compose logs -f backend
```

**Frontend** (React):
```bash
# 1. Make code changes in your editor
# 2. Vite auto-reloads (HMR enabled)
# 3. Check browser console
```

### Adding Dependencies

**Backend** (Python with uv):
```bash
# Edit pyproject.toml manually
nano backend/pyproject.toml

# Sync dependencies
docker-compose exec backend uv sync

# Restart backend to load new packages
docker-compose restart backend
```

**Frontend** (npm):
```bash
# Add package
docker-compose exec frontend npm install package-name

# Restart frontend
docker-compose restart frontend
```

### Database Reset

```bash
# ⚠️ WARNING: This deletes all data

# Stop services
docker-compose down

# Remove database volume
docker volume rm cv-tailor_postgres_data

# Start fresh
docker-compose up -d

# Run migrations
docker-compose exec backend uv run python manage.py migrate
```

## Troubleshooting

### Backend Won't Start

**Problem**: "django_ratelimit.E003 cache backend is not a real cache"
```bash
# Solution: Ensure Redis is running
docker-compose up -d redis
docker-compose restart backend
```

**Problem**: "FATAL: database \"cv_tailor\" does not exist"
```bash
# Solution: Initialize database
docker-compose exec db psql -U cv_tailor_user -c "CREATE DATABASE cv_tailor;"
docker-compose exec backend uv run python manage.py migrate
```

**Problem**: "ModuleNotFoundError: No module named 'X'"
```bash
# Solution: Sync dependencies
docker-compose exec backend uv sync
docker-compose restart backend
```

### Port Already in Use

**Problem**: "port is already allocated"
```bash
# Find process using port
lsof -i :8000  # or :3000, :5432, :6379

# Kill process
kill -9 <PID>

# Or change port in docker-compose.yml
```

### Database Connection Issues

**Problem**: "could not connect to server"
```bash
# Check if database is healthy
docker-compose ps db

# Wait for healthcheck
docker-compose up -d db
sleep 5
docker-compose logs db
```

### Permission Issues

**Problem**: Permission denied on volumes
```bash
# Fix ownership (macOS/Linux)
sudo chown -R $(whoami):$(whoami) backend/media
sudo chown -R $(whoami):$(whoami) backend/staticfiles
```

### Slow Performance

**Problem**: Docker is slow
- **Solution 1**: Increase Docker Desktop resources (Settings → Resources)
- **Solution 2**: Use Docker's VirtioFS (faster file sharing on macOS)
- **Solution 3**: Exclude large directories from volume mounts (already done for `.venv`)

## Environment Variables Reference

See `backend/.env.example` for complete list. Key variables:

```bash
# Django
SECRET_KEY=django-insecure-placeholder-key-for-development
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_ENV=development  # Optional, defaults to development

# Database (PostgreSQL)
DB_ENGINE=postgresql
DB_NAME=cv_tailor
DB_USER=cv_tailor_user
DB_PASSWORD=your-secure-password-here
DB_HOST=db
DB_PORT=5432

# Redis/Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# OpenAI (required)
OPENAI_API_KEY=sk-your-openai-key-here

# GitHub (optional)
GITHUB_TOKEN=ghp_your-github-token

# Google OAuth (optional)
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret

# LLM Model Strategy (optional)
MODEL_SELECTION_STRATEGY=balanced  # or: cost_optimized, quality_optimized
```

## Next Steps

- **Testing**: See [Testing Environments Guide](./testing-environments.md)
- **Staging**: See [Staging Deployment Guide](./staging-deployment.md)
- **Production**: See [Production Deployment Guide](./production-deployment.md)
- **Architecture**: Read [Deployment Spec](../specs/spec-deployment-v1.0.md)

## Related Documentation

- [Deployment README](./README.md) - Quick start guide
- [ADR-029](../adrs/adr-029-multi-environment-settings.md) - Multi-environment decision
- [FT-020](../features/ft-020-production-environment-config.md) - Environment config feature
- [Testing Guide](../testing/test-backend-guide.md) - Comprehensive testing guide

---

**Last Updated**: 2025-10-20
**Environment**: `development`
**Docker Compose**: `docker-compose.yml`
