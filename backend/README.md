# CV Tailor Backend API

Django REST API backend for CV Tailor - an AI-powered CV and cover letter generator with semantic artifact processing.

## Features

- **User Authentication**: JWT tokens with Google OAuth integration
- **Artifact Processing**: Multi-format document processing (PDF, GitHub repos, web profiles)
- **LLM Integration**: OpenAI/Anthropic APIs for content generation and semantic ranking
- **Vector Search**: PostgreSQL + pgvector for semantic similarity matching
- **Document Processing**: LangChain-powered content extraction and analysis
- **Background Tasks**: Celery workers for async artifact processing
- **Document Export**: PDF/DOCX generation with ReportLab and python-docx
- **Evidence Validation**: Link verification and GitHub repository analysis
- **Bullet Generation** (ft-006): Three-bullet-per-artifact with quality validation
  - Structured hierarchy (achievement → technical → impact)
  - Multi-criteria validation (length, action verbs, metrics, keywords, similarity)
  - Auto-regeneration with retry logic (up to 3 attempts)
  - ATS keyword optimization

## Architecture

- **Database**: PostgreSQL 15+ with pgvector extension for vector similarity search
- **Cache/Broker**: Redis for caching and Celery task queue
- **Document Processing**: LangChain for multi-format content extraction
- **LLM Providers**: Dual-provider strategy (OpenAI primary, Anthropic fallback)
- **Background Tasks**: Celery workers for artifact enhancement and processing

## Environment Configuration

### Multi-Environment Settings (ADR-029)

The backend uses environment-specific Django settings:

```
backend/cv_tailor/settings/
├── __init__.py          # Auto-detects DJANGO_ENV
├── base.py              # Shared configuration
├── development.py       # Local dev (default)
├── production.py        # AWS production
├── staging.py           # AWS staging
└── test.py              # Test environment
```

### Getting Started

**For local development (default):**
```bash
# No configuration needed - defaults to development environment
docker-compose up -d
```

**Environment variable:**
```bash
# Optional: Explicitly set environment
export DJANGO_ENV=development  # or: staging, production, test
```

### Environment-Specific Features

| Environment | Database | Cache | Storage | Secrets |
|-------------|----------|-------|---------|---------|
| `development` | PostgreSQL (Docker) | Redis (Docker) | Local filesystem | `.env` file |
| `test` | SQLite (in-memory) | DummyCache | Local filesystem | Mock values |
| `staging` | RDS PostgreSQL | ElastiCache | S3 | AWS Secrets Manager |
| `production` | RDS PostgreSQL (Multi-AZ) | ElastiCache | S3 | AWS Secrets Manager |

### Configuration Files

- **`.env`** - Local development secrets (git-ignored)
- **`.env.example`** - Template with all available variables
- **`pyproject.toml`** - Python dependencies (managed with `uv`)

### Required Environment Variables

See `.env.example` for complete list. Key variables:

```bash
# Django
DJANGO_ENV=development
SECRET_KEY=your-secret-key
DEBUG=True

# Database
DB_ENGINE=postgresql
DB_NAME=cv_tailor
DB_USER=cv_tailor_user
DB_PASSWORD=your-password
DB_HOST=db
DB_PORT=5432

# OpenAI (required)
OPENAI_API_KEY=sk-your-openai-key

# Optional
GITHUB_TOKEN=ghp_your-token
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-secret
```

### Deployment

**Local Development:**
- See: [../docs/deployment/local-development.md](../docs/deployment/local-development.md)
- Uses: `docker-compose.yml`
- Runs on: http://localhost:8000

**AWS Staging:**
- See: [../docs/deployment/staging-deployment.md](../docs/deployment/staging-deployment.md)
- Uses: Terraform + ECS Fargate
- Cost: ~$60-80/month

**AWS Production:**
- See: [../docs/deployment/production-deployment.md](../docs/deployment/production-deployment.md)
- Uses: Terraform + ECS Fargate
- Cost: ~$120-150/month (scales to $500-800/month)

**Architecture Details:**
- See: [../docs/specs/spec-deployment-v1.0.md](../docs/specs/spec-deployment-v1.0.md) (18,000 words)

## API Endpoints

### Authentication
- `POST /api/v1/auth/login/` - JWT token login
- `POST /api/v1/auth/register/` - User registration
- `POST /api/v1/auth/google/` - Google OAuth login

### Artifacts
- `GET /api/v1/artifacts/` - List user artifacts
- `POST /api/v1/artifacts/` - Create new artifact
- `GET /api/v1/artifacts/{id}/` - Retrieve artifact details
- `POST /api/v1/artifacts/{id}/enhance/` - Process artifact with LLM

### Generation
- `POST /api/v1/generate/cv/` - Generate CV from job description
- `GET /api/v1/generation/{id}/status/` - Check generation status
- `GET /api/v1/templates/` - List available CV templates

### Bullet Generation (ft-006)
- `POST /api/v1/cv/artifacts/{id}/generate-bullets/` - Generate 3 bullets for artifact
- `GET /api/v1/cv/artifacts/{id}/bullets/preview/` - Preview bullets with quality metrics
- `POST /api/v1/cv/artifacts/{id}/bullets/approve/` - Approve/reject/edit bullets
- `POST /api/v1/cv/bullets/validate/` - Validate bullet quality without saving

### Export
- `POST /api/v1/export/pdf/` - Export document as PDF
- `POST /api/v1/export/docx/` - Export document as DOCX

## Project Structure

```
backend/
├── cv_tailor/          # Django project settings
├── accounts/           # User authentication and OAuth
├── artifacts/          # Artifact storage and processing
├── generation/         # CV/cover letter + bullet generation (ft-006)
│   ├── services/       # Extracted service layer (ADR-20251001)
│   │   ├── bullet_generation_service.py  # Bullet orchestration (613 lines)
│   │   └── bullet_validation_service.py  # Multi-criteria validation (495 lines)
│   ├── models.py       # BulletPoint, BulletGenerationJob models
│   ├── views.py        # 5 new bullet API endpoints
│   └── serializers.py  # 9 bullet-specific serializers
├── export/             # Document export functionality
├── llm_services/       # Unified LLM integration with layered architecture
├── db_init/            # PostgreSQL initialization scripts
├── media/              # Uploaded files
├── manage.py           # Django management script
├── ARCHITECTURE.md     # Detailed architecture documentation
└── README.md           # This file
```