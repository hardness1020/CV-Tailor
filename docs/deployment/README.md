# CV-Tailor Deployment Guide

**Quick navigation for deploying CV-Tailor in different environments**

## 🚀 Production Deployment (Live System)

**CV Tailor is live on AWS!** Deployed: October 23, 2025 | Custom Domain: October 24, 2025

### Quick Access
- **[Deployment Pipeline](./deployment-pipeline.md)** - How to deploy frontend/backend updates
- **[Architecture](./architecture.md)** - Infrastructure overview and diagrams

### Production URLs
- **Frontend**: https://<YOUR_DOMAIN> (CloudFront + S3)
- **Backend API**: https://api.<YOUR_DOMAIN> (ECS Fargate + ALB)

### Quick Deploy Commands
```bash
# Deploy Frontend
cd frontend && npm run build
aws s3 sync dist/ s3://<YOUR_S3_BUCKET>/ --delete --region <AWS_REGION>
aws cloudfront create-invalidation --distribution-id <CLOUDFRONT_DISTRIBUTION_ID> --paths "/*"

# Deploy Backend
docker buildx build --platform linux/amd64 -t cv-tailor-backend:latest -f backend/Dockerfile backend --load
docker tag cv-tailor-backend:latest <AWS_ACCOUNT_ID>.dkr.ecr.<AWS_REGION>.amazonaws.com/cv-tailor/production:latest
aws ecr get-login-password --region <AWS_REGION> | docker login --username AWS --password-stdin <AWS_ACCOUNT_ID>.dkr.ecr.<AWS_REGION>.amazonaws.com
docker push <AWS_ACCOUNT_ID>.dkr.ecr.<AWS_REGION>.amazonaws.com/cv-tailor/production:latest
aws ecs update-service --cluster <YOUR_ECS_CLUSTER> --service <YOUR_ECS_SERVICE> --force-new-deployment --region <AWS_REGION>
```

---

## 📋 Table of Contents

- [Production Deployment](#-production-deployment-live-system)
- [Overview](#overview)
- [Environments](#environments)
- [Quick Start](#quick-start)
- [Environment Selection Decision Tree](#environment-selection-decision-tree)
- [Documentation Map](#documentation-map)
- [Common Tasks](#common-tasks)

## Overview

CV-Tailor uses a **multi-environment settings architecture** that allows the same codebase to run in different contexts with appropriate configuration.

**Key Concepts:**
- **Settings Modules**: Environment-specific configuration in `backend/cv_tailor/settings/`
- **Environment Variable**: `DJANGO_ENV` controls which settings load
- **Secrets Management**: `.env` files (dev) or AWS Secrets Manager (production)
- **Docker Compose**: Different compose files for different environments

## Environments

| Environment | Purpose | Infrastructure | Secrets | Testing |
|-------------|---------|----------------|---------|---------|
| **development** | Local development on your machine | Docker Compose | `.env` file | Manual, full test suite |
| **test** | Automated testing (CI/CD) | In-memory SQLite | Mock values | Automated tests only |
| **production** | Live production deployment | AWS (RDS, S3, ElastiCache) | AWS Secrets Manager | Automated monitoring |

## Quick Start

### For Local Development (Most Common)

```bash
# 1. Navigate to project root
cd /path/to/CV-Tailor

# 2. Start services (DJANGO_ENV defaults to 'development')
docker-compose up -d

# 3. Check logs
docker-compose logs backend --tail=50

# 4. Access application
open http://localhost:8000
```

**That's it!** No need to set `DJANGO_ENV` - it defaults to `development`.

👉 **Detailed Guide**: [Local Development](./local-development.md)

### For Running Tests

```bash
# Run fast unit tests (no AWS required)
docker-compose exec backend uv run python manage.py test --tag=fast --tag=unit --keepdb

# Run all tests
docker-compose exec backend uv run python manage.py test --keepdb
```

👉 **Testing Guide**: [Testing Environments](./testing-environments.md)

### For AWS Production Deployment

```bash
# 1. Set environment
export DJANGO_ENV=production
export AWS_SECRETS_NAME=cv-tailor/production

# 2. Deploy via ECS (see production guide)
# ... AWS ECS deployment steps
```

👉 **Production Guide**: [Production Deployment](./production-deployment.md)

## Environment Selection Decision Tree

```
┌─────────────────────────────────────────┐
│  What do you want to do?                │
└─────────────────────────────────────────┘
                  │
                  ├─→ 💻 Develop locally?
                  │   → Use: development (default)
                  │   → File: docker-compose.yml
                  │   → Guide: local-development.md
                  │
                  ├─→ 🧪 Run automated tests?
                  │   → Use: test (automatic in pytest)
                  │   → File: N/A (uses test settings)
                  │   → Guide: testing-environments.md
                  │
                  └─→ 🚀 Deploy to production users?
                      → Use: production
                      → File: ECS task definitions
                      → Guide: production-deployment.md
```

## Documentation Map

### Getting Started
- **[Local Development](./local-development.md)** - Start here for day-to-day development
- **[Testing Environments](./testing-environments.md)** - How to test settings and environments

### AWS Deployment
- **[Production Deployment](./production-deployment.md)** - Deploy to AWS production

### Architecture & Decisions
- **[Deployment Spec](../specs/spec-deployment-v1.0.md)** - Complete AWS architecture (18,000 words)
- **[ADR-029](../adrs/adr-029-multi-environment-settings.md)** - Multi-environment settings decision
- **[ADR-030](../adrs/adr-030-aws-deployment-architecture.md)** - AWS architecture decision
- **[ADR-031](../adrs/adr-031-secrets-management-strategy.md)** - Secrets management decision

### Implementation Details
- **[FT-020](../features/ft-020-production-environment-config.md)** - Production environment feature spec (11,000 words)
- **[Discovery Doc](../discovery/disc-001-environment-config-analysis.md)** - Codebase analysis (9,000 words)

## Common Tasks

### Switching Environments Locally

```bash
# Development (default)
export DJANGO_ENV=development
docker-compose up -d

# Test settings (for testing only)
export DJANGO_ENV=test
uv run python manage.py test

# Production (deploy to AWS ECS, not local)
export DJANGO_ENV=production
# ... use ECS deployment instead of docker-compose
```

### Checking Current Environment

```bash
# From within backend container
docker-compose exec backend uv run python -c "from cv_tailor import settings; print(f'Environment: {settings.DJANGO_ENV}')"

# Check DEBUG status
docker-compose exec backend uv run python -c "from cv_tailor import settings; print(f'DEBUG: {settings.DEBUG}')"

# Check database backend
docker-compose exec backend uv run python -c "from cv_tailor import settings; print(f'Database: {settings.DATABASES[\"default\"][\"ENGINE\"]}')"
```

### Viewing Environment-Specific Settings

```bash
# Development settings
docker-compose exec backend uv run python -c "from cv_tailor.settings import development; print(development.DEBUG)"

# Production settings (in test mode, uses mock secrets)
docker-compose exec backend uv run python -c "from cv_tailor.settings import production; print(production.DEBUG)"

# Test settings
docker-compose exec backend uv run python -c "from cv_tailor.settings import test; print(test.DATABASES)"
```

### Troubleshooting

**Problem**: "ModuleNotFoundError: No module named 'cv_tailor.settings'"
- **Solution**: Make sure you're in the backend directory or use docker-compose exec

**Problem**: "Failed to load secrets from AWS Secrets Manager"
- **Solution**:
  - Check `AWS_SECRETS_NAME` is set correctly
  - Verify AWS credentials are configured
  - For testing, the settings provide mock secrets automatically

**Problem**: "django_ratelimit.E003 cache backend is not a real cache"
- **Solution**: Development now uses Redis cache (not DummyCache). Ensure Redis is running: `docker-compose up -d redis`

**Problem**: Settings changes not taking effect
- **Solution**: Restart the backend container: `docker-compose restart backend`

## Related Files

### Settings Modules
```
backend/cv_tailor/settings/
├── __init__.py         # Environment detection and auto-import
├── base.py             # Shared configuration (REST, JWT, Auth)
├── development.py      # Local development settings ✅ YOUR CURRENT
├── production.py       # AWS production settings
└── test.py             # Test environment settings
```

### Docker Compose Files
```
docker-compose.yml              # Base/development environment
docker-compose.override.yml     # Local developer overrides (git-ignored)
docker-compose.prod.yml         # Production reference (not used - ECS instead)
docker-compose.test.yml         # CI/CD testing (future)
```

### Environment Files
```
backend/.env                    # Your local environment variables (git-ignored)
backend/.env.example            # Template with all available variables
```

## Support

- **Questions**: Check the deployment guides above
- **Issues**: See [Troubleshooting](#troubleshooting) section
- **Architecture**: Read `docs/specs/spec-deployment-v1.0.md` for complete AWS design
- **Decisions**: Review ADRs in `docs/adrs/` for rationale behind choices

---

**Last Updated**: 2025-10-24
**Related ADRs**: ADR-029, ADR-030, ADR-031
**Related Features**: FT-020
