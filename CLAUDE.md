# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Always create docs for new/edit/fix features before implement code. Follow the rules in @rules/ directory.

## Project Overview

**CV Tailor** is a full-stack application that auto-generates tailored CVs and cover letters from uploaded work artifacts using LLM processing. Built with Django REST API backend and React frontend.

## Architecture

**Backend (Django):** `/backend/`
- **Framework:** Django 4.2+ with Django REST Framework
- **Database:** PostgreSQL 15+ for relational storage
- **LLM Integration:** OpenAI API (GPT-5 series) for content generation
- **Document Processing:** LangChain for multi-format processing (PDF, GitHub, web)
- **Authentication:** JWT tokens with Google OAuth via django-allauth
- **Background Tasks:** Celery with Redis broker
- **Document Generation:** PDF/DOCX generation with ReportLab and python-docx
- **Dependency Management:** uv for Python dependency management (see pyproject.toml)

**Django Apps Structure:**
- **accounts/** - User authentication, registration, profile management (JWT + Google OAuth)
- **artifacts/** - Work artifact storage, enhancement, and management
- **generation/** - CV/cover letter + bullet generation (MODERNIZED with service layer, ft-006)
  - **services/** - Extracted business logic following llm_services pattern
    - `bullet_generation_service.py` - Orchestration with retry logic (613 lines)
    - `bullet_validation_service.py` - Multi-criteria quality validation (495 lines)
  - **models/** - BulletPoint, BulletGenerationJob (structured hierarchy)
  - **API:** 5 bullet endpoints (generate, preview, approve, batch, validate)
- **export/** - Document export to PDF/DOCX formats
- **llm_services/** - Unified LLM integration with reliability patterns (circuit breaker, model selection, performance tracking)

**Key Architectural Patterns:**
- **Circuit Breaker:** Fault tolerance for external LLM API calls (llm_services/services/reliability/)
- **Service Layer:** Extracted and well-architected
  - llm_services: base → core → infrastructure → reliability layers
  - generation/services: Following same pattern (ADR-20251001, ft-006)
- **Async Processing:** Celery tasks for long-running operations (document generation, artifact processing)
- **Artifact Selection:** Manual user selection with keyword-based ranking suggestions (ADR-028)
- **TDD Workflow:** Write failing tests → Implement → Refactor (89.6% test coverage in generation/)

**Frontend (React):** `/frontend/`
- **Framework:** React 18 with TypeScript and Vite
- **Routing:** React Router DOM
- **Styling:** Tailwind CSS with Radix UI components
- **State Management:** Zustand
- **Forms:** React Hook Form with Zod validation
- **HTTP Client:** Axios

## Environment Configuration

**Multi-Environment Settings Architecture** (ADR-029)

The backend uses environment-based Django settings for different deployment contexts:

```
backend/cv_tailor/settings/
├── __init__.py          # Auto-detects DJANGO_ENV and imports appropriate module
├── base.py              # Shared configuration (REST, JWT, Auth, LLM)
├── development.py       # Local development (default) ✅ YOUR CURRENT ENV
├── production.py        # AWS production with Secrets Manager
└── test.py              # Test environment (in-memory DB, optimized for speed)
```

### Environments

| Environment | Use Case | Infrastructure | Secrets |
|-------------|----------|----------------|---------|
| **development** | Local Docker development | docker-compose.yml | `.env` file |
| **test** | Automated testing | In-memory SQLite | Mock values |
| **production** | AWS live deployment | Terraform + ECS | AWS Secrets Manager |

### Environment Selection

```bash
# Development (default - no need to set)
docker-compose up -d
# → Uses development settings automatically

# Explicit environment selection
export DJANGO_ENV=development  # or: production, test
docker-compose up -d

# Verify current environment
docker-compose exec backend uv run python -c "from cv_tailor import settings; print(f'Environment: {settings.DJANGO_ENV}, DEBUG: {settings.DEBUG}')"
```

### Key Configuration Differences

| Setting | Development | Test | Production |
|---------|-------------|------|------------|
| `DEBUG` | `True` | `True` | `False` |
| Database | PostgreSQL (Docker) | SQLite (in-memory) | RDS PostgreSQL |
| Cache | Redis (Docker) | DummyCache | ElastiCache Redis |
| File Storage | Local filesystem | Local filesystem | S3 |
| Secrets | `.env` file | Mock values | AWS Secrets Manager |
| HTTPS | Not required | Not required | Enforced |
| Logging | Console (verbose) | Minimal (ERROR only) | CloudWatch |
| Rate Limiting | Disabled | Disabled | Enabled |

### Deployment Documentation

- **[Deployment Guide](docs/deployment/README.md)** - Quick start and decision tree
- **[Local Development](docs/deployment/local-development.md)** - Day-to-day development guide
- **[Testing Environments](docs/deployment/testing-environments.md)** - How to test settings
- **[Deployment Pipeline](docs/deployment/deployment-pipeline.md)** - How to deploy frontend/backend updates
- **[Architecture](docs/deployment/architecture.md)** - Infrastructure overview and diagrams

### Production Infrastructure (AWS)

**Production Infrastructure (AWS):**

The application was deployed to AWS using the following services:
- **ECS Fargate**: Serverless container platform
- **RDS PostgreSQL**: Managed database
- **ElastiCache Redis**: Managed cache/broker
- **S3 + CloudFront**: Frontend hosting with global CDN
- **ALB**: Application load balancer with HTTPS
- **Secrets Manager**: Production secrets management

**Terraform** configuration exists in `terraform/` directory. Deploy scripts are in `scripts/`.

See `docs/deployment/` for deployment pipeline and architecture documentation.

## Visual Development & Testing

### Design System

The project follows S-Tier SaaS design standards inspired by Stripe, Airbnb, and Linear. All UI development must adhere to:

- **Design Principles**: `rules/design-principles.md` - S-Tier SaaS design checklist inspired by Stripe, Airbnb, Linear
- **Component Library**: Radix UI with custom Tailwind configuration


## Development Commands

### Docker Development Environment
```bash
# Start all services (PostgreSQL, Redis, Backend, Celery)
docker-compose up -d

# Stop all services
docker-compose down
```

### Backend Testing

**Testing Philosophy:** This project follows **Test-Driven Development (TDD)** with proper mocking for fast feedback.

**📖 TESTING DOCUMENTATION:**
- **Quick Start:** [`docs/testing/README.md`](docs/testing/README.md) - Navigation index and architecture overview
- **TDD Policy:** [`rules/06-tdd/policy.md`](rules/06-tdd/policy.md) - Framework-agnostic TDD requirements and quality gates
- **TDD Workflow:** [`rules/06-tdd/guide.md`](rules/06-tdd/guide.md) - Conceptual TDD workflow and decision-making guidance
- **Django Decorators:** [`docs/testing/test-decorators.md`](docs/testing/test-decorators.md) - Django @tag syntax and categorization
- **Test Execution:** [`docs/testing/test-execution.md`](docs/testing/test-execution.md) - Docker + uv commands, mocking patterns, execution guide

**⚠️ CRITICAL: Unit tests MUST use proper mocking to avoid slow execution!**
- This project uses **docker-compose** and **uv** for backend testing
- **Do not run all tests directly** - Use tags for faster feedback
- **Always mock external API calls** in unit tests (see guides for examples)
- ✅ **Proper mocking guide** (critical - prevents 30+ min test runs!)
- ✅ Step-by-step test execution guide
- ✅ Recommended test order (fast → medium → slow)
- ✅ Expected outcomes and timing benchmarks (158 tests in ~1 min)
- ✅ Common mocking patterns and pitfalls to avoid
- ✅ Troubleshooting common issues
- ✅ CI/CD integration examples

**Performance Impact of Proper Mocking:**
- ⚡ With mocking: 158 tests in 63s (~1 minute)
- 🐌 Without mocking: 30+ minutes (real API calls, retries, failures)
- **30x faster with proper mocking!**

**Quick Commands:**
```bash
# Fast unit tests (recommended for pre-commit, ~1 minute with proper mocking)
docker-compose exec backend uv run python manage.py test --tag=fast --tag=unit --keepdb

# All tests excluding slow real API tests (recommended for CI/CD)
docker-compose exec backend uv run python manage.py test --exclude-tag=slow --exclude-tag=real_api --keepdb

# All tests with database persistence
docker-compose exec backend uv run python manage.py test --keepdb

# Real API tests (requires API keys, costs money)
docker-compose exec -e FORCE_REAL_API_TESTS=true backend uv run python manage.py test --tag=real_api --keepdb -v 2
```

### Backend Database Management

```bash
# Create migrations after model changes
docker-compose exec backend uv run python manage.py makemigrations

# Apply migrations
docker-compose exec backend uv run python manage.py migrate

# Access database shell
docker-compose exec db psql -U cv_tailor_user -d cv_tailor
```

### Frontend Development

This project uses **Vite** for frontend development:

```bash
# Install dependencies
cd frontend && npm install

# Run development server (http://localhost:3000)
npm run dev

# Type checking
npm run typecheck

# Linting
npm run lint

# Build for production
npm run build

# Run tests (when implemented)
npm test
```

**Note**: Frontend is typically run outside Docker for faster hot-reload during development. Use `docker-compose` for backend services only.

### Development Workflow

**Typical Development Setup:**
1. Start backend services: `docker-compose up -d` (PostgreSQL, Redis, Backend, Celery)
2. Start frontend separately: `cd frontend && npm run dev`

**Service Endpoints:**
- **Backend API:** http://localhost:8000
- **Frontend:** http://localhost:3000 (Vite dev server)
- **PostgreSQL:** localhost:5432
- **Redis:** localhost:6379
- **Celery:** Background task worker for artifact processing

**CORS Configuration:** Frontend origins (http://localhost:3000, http://localhost:8000) are configured in Django settings

## Security

### Security Documentation

- **[Backend Security](docs/security/backend-security.md)** - Django security configurations, HTTPS, CORS, authentication
- **[Frontend Security](docs/security/frontend-security.md)** - React security best practices, XSS prevention, CSP headers
- **[CloudFront Security Headers](docs/deployment/cloudfront-security-headers.md)** - CDN security configuration

### Key Security Features

**Backend:**
- HTTPS-only in production (SECURE_SSL_REDIRECT, SECURE_HSTS_SECONDS)
- Secure session/CSRF cookies (SECURE, HTTPONLY, SAMESITE)
- CORS whitelist for allowed origins
- JWT authentication with token expiry
- Secrets stored in AWS Secrets Manager (production)

**Frontend:**
- HTTPS delivery via CloudFront
- Content Security Policy (CSP) headers
- XSS protection headers
- Input validation with Zod schemas
- Secure token storage (httpOnly cookies for sensitive data)

**Infrastructure:**
- Private subnets for database and cache
- Security groups with least-privilege access
- VPC isolation for production resources
- SSL/TLS certificates from AWS ACM
- Secrets Manager for credential rotation

## Development Workflow and Governance

This project follows a **docs-first, TDD-driven development pipeline** with mandatory stage gating.

### Quick Workflow Selector

Not all changes require the full pipeline. Choose your workflow track based on change scope:

| **Track** | **Scope** | **Required Stages** | **Example** |
|-----------|-----------|---------------------|-------------|
| **Micro** | Bug fix, typo, small refactor | F → G (TDD only) | Fix typo in error message, update config value |
| **Small** | Single feature, no contracts | E → F → G → H | Add field to existing form, UI polish |
| **Medium** | Multi-component, no new services | B → C → D → E → F → G → H → I | New API endpoint using existing services |
| **Large** | System change, new contracts/services | Full A → L | New LLM integration, new auth system |

**See `rules/00-workflow.md` for:**
- Complete stage-by-stage guidance (lines 45-204)
- Review checkpoint strategy (6 grouped checkpoints vs. individual stops)
- Size-based track definitions and decision criteria

### Core Principles
- **Docs-First Mandate:** Generate or update required docs BEFORE generating code
- **TDD Workflow:** Write failing tests BEFORE implementation code
- **Stage Gating:** Each stage requires human review/approval before proceeding to next stage
- **Rule Compliance:** Follow rules in `rules/` directory for each document type

### Rule Reference Matrix

Each stage has a corresponding rule file with detailed requirements:

| **Stage** | **Output** | **Rule File** |
|-----------|------------|---------------|
| A (Initiate) | PRD | `rules/01-prd.md` |
| B (Discovery) | Discovery document | `rules/02-discovery/policy.md` |
| C (Specify) | TECH SPEC | `rules/03-tech_spec.md` |
| D (Decide) | ADR | `rules/04-adr.md` |
| E (Plan) | FEATURE spec | `rules/05-feature.md` |
| F-H (Implement) | Tests + Code | `rules/06-tdd/policy.md` |
| I (Reconciliation) | Updated specs | See `rules/00-workflow.md` lines 154-187 |
| J (Release Prep) | OP-NOTE | `rules/07-op_note.md` |
| K (Deploy) | Deployed system | Follow OP-NOTE |
| L (Close Loop) | Updated docs, tags | See `rules/00-workflow.md` lines 200-203 |

**Note:** Stage numbering corrected to match `rules/00-workflow.md` (Stage I = Spec Reconciliation, Stage J = Release Prep)

### Change-Control Triggers

Increment SPEC version when changing **contracts, topology, framework roles, or SLOs**. See `rules/00-workflow.md` lines 214-220 for complete trigger definitions and versioning guidance.

### Git Conventions (User-Driven)

Recommended conventions for traceability:
- **Branch Naming:** `feat/<ID>-<slug>`, `fix/<ID>-<slug>`, `chore/<ID>-<slug>`
- **Commit Format:** `<type>(scope): subject (#<ID>)` (Conventional Commits)
- **Traceability:** Reference IDs in branches, commits, PRs, and code comments

See `rules/00-workflow.md` lines 222-249 for detailed conventions and commit timing recommendations.

### Enforcement

The workflow includes automatic blockers for violations (e.g., code before docs, missing tests, contract changes without SPEC updates). See `rules/00-workflow.md` lines 252-273 for the complete enforcement matrix and recovery guidance.

## Architecture Patterns

For detailed architectural patterns and best practices, see **[Architecture Patterns](docs/architecture/patterns.md)** - Reusable design standards for the codebase.

### LLM Services Architecture Pattern (Best Practice Reference)

The `llm_services/` app demonstrates the target architecture for service layers:

```
llm_services/services/
├── base/                              # Foundation abstractions
│   ├── base_service.py               # Base service class with common functionality
│   ├── client_manager.py             # API client lifecycle management
│   ├── task_executor.py              # Unified execution patterns with retries
│   ├── exception_handler.py          # Centralized error handling
│   └── settings_manager.py           # Configuration management
├── core/                              # Business services
│   ├── tailored_content_service.py   # Job-tailored application generation
│   ├── document_loader_service.py    # Pure I/O document loading
│   ├── artifact_enrichment_service.py # Multi-source preprocessing orchestrator
│   ├── artifact_ranking_service.py   # Keyword-based relevance ranking
│   └── evidence_content_extractor.py # LLM-based content extraction
├── infrastructure/                    # Supporting components
│   ├── model_registry.py             # Model configurations and metadata
│   └── model_selector.py             # Intelligent model selection with fallbacks
└── reliability/                      # Fault tolerance
    ├── circuit_breaker.py            # Failure detection and recovery
    └── performance_tracker.py        # Metrics, cost tracking, monitoring
```

**Key Patterns to Replicate:**
- **Layered separation:** base → core → infrastructure → reliability
- **Circuit Breaker:** Automatic failure detection and recovery for external APIs
- **Task Executor:** Unified retry logic, timeout handling, and error reporting
- **Model Registry:** Centralized configuration for all LLM models
- **Performance Tracking:** Built-in cost monitoring and latency tracking
- **Separation of Concerns:** Pure I/O (document_loader_service) separate from LLM operations (evidence_content_extractor)
- **Pipeline Orchestration:** High-level coordinators (artifact_enrichment_service) compose lower-level services

## Shell Tools Usage Guidelines

⚠️ **IMPORTANT**: Use the following specialized tools instead of traditional Unix commands: (Install if missing)

| Task Type | Must Use | Do Not Use |
|-----------|----------|------------|
| Find Files | `fd` | `find`, `ls -R` |
| Search Text | `rg` (ripgrep) | `grep`, `ag` |
| Analyze Code Structure | `ast-grep` | `grep`, `sed` |
| Interactive Selection | `fzf` | Manual filtering |
| Process JSON | `jq` | `python -m json.tool` |
| Process YAML/XML | `yq` | Manual parsing |