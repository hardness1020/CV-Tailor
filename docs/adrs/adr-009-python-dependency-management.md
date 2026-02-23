# ADR: Choose uv over pip/poetry for Python Dependency Management

**File:** docs/adrs/adr-009-python-dependency-management.md
**Status:** Draft

## Context

The CV Auto-Tailor system requires robust Python dependency management for:
- Backend API development with Django DRF and numerous packages
- Machine learning dependencies (OpenAI, Anthropic, transformers libraries)
- Document processing libraries (ReportLab, python-docx, PyPDF2)
- Data processing and async libraries (pandas, asyncio, aiohttp)
- Development and testing tools (pytest, black, mypy, pre-commit)

Key requirements:
- **Fast Installation**: Quick dependency resolution and installation for development and CI/CD
- **Reproducible Builds**: Lockfiles ensuring consistent environments across dev/staging/production
- **Dependency Resolution**: Conflict detection and resolution for complex ML dependencies
- **Virtual Environment Management**: Isolated environments for different components
- **Security**: Vulnerability scanning and secure package installation
- **Team Workflow**: Easy onboarding and consistent developer experience

The main candidates are:
1. **pip + pip-tools**: Traditional Python package management
2. **Poetry**: Modern dependency management with packaging features
3. **uv**: Ultra-fast Python package installer and resolver
4. **Pipenv**: Environment management with pip and virtualenv

## Decision

Adopt **uv** as the primary Python dependency management tool for all backend components (API, LLM services, workers, and scripts).

Rationale:
1. **Performance**: uv is 10-100x faster than pip for dependency resolution and installation
2. **Modern Lockfiles**: Uses `uv.lock` format with precise dependency pinning and checksums
3. **Universal Compatibility**: Drop-in replacement for pip with existing requirements.txt support
4. **Virtual Environment Integration**: Built-in venv management without additional tools
5. **Security**: Built-in vulnerability scanning and secure package verification
6. **Rust-based**: Memory-safe implementation with excellent performance characteristics
7. **CI/CD Optimization**: Dramatically reduces build times in Docker and GitHub Actions

## Consequences

### Positive
+ **Dramatically Faster Builds**: Development environment setup from minutes to seconds
+ **Improved CI/CD Performance**: Docker builds and GitHub Actions 5-10x faster
+ **Better Developer Experience**: Instant dependency installation encourages experimentation
+ **Reliable Lockfiles**: uv.lock format prevents dependency drift between environments
+ **Security by Default**: Automatic vulnerability scanning and secure package verification
+ **Future-Proof**: Active development with backing from Astral (ruff creators)
+ **Memory Efficiency**: Lower memory usage during large dependency installations

### Negative
- **Newer Tool**: Less mature ecosystem compared to pip/poetry (though rapidly evolving)
- **Learning Curve**: Team needs to learn uv-specific commands and workflows
- **Integration Uncertainty**: Some CI/CD systems may not have native uv support yet
- **Community Adoption**: Smaller community compared to established tools
- **Documentation**: Less extensive third-party documentation and tutorials

## Alternatives

### Poetry
**Pros**: Mature ecosystem, excellent dependency resolution, built-in packaging, wide adoption
**Cons**: Slower than uv, complex for simple use cases, opinionated project structure
**Verdict**: Poetry's features don't outweigh uv's performance advantages for our backend-focused use case

### pip + pip-tools
**Pros**: Standard Python tooling, universal compatibility, extensive documentation
**Cons**: Slow dependency resolution, manual lockfile management, no built-in security scanning
**Verdict**: Traditional approach but lacks modern features and performance

### Pipenv
**Pros**: Good environment management, Pipfile format, security scanning
**Cons**: Performance issues, abandoned by maintainers, complex dependency resolution
**Verdict**: Not recommended due to maintenance concerns

## Implementation Details

### Project Structure
```
├── pyproject.toml          # Project metadata and uv configuration
├── uv.lock                 # Lockfile with exact dependency versions
├── requirements/
│   ├── base.txt           # Core dependencies
│   ├── dev.txt            # Development dependencies
│   ├── prod.txt           # Production-only dependencies
│   └── ml.txt             # ML/AI specific dependencies
└── scripts/
    ├── setup-dev.sh       # Development environment setup
    └── install-deps.sh    # Production dependency installation
```

### uv Configuration (pyproject.toml)
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "cv-auto-tailor"
version = "0.1.0"
description = "CV & Cover-Letter Auto-Tailor Backend"
dependencies = [
    "django>=4.2,<5.0",
    "djangorestframework>=3.14",
    "celery>=5.3",
    "redis>=5.0",
    "psycopg2-binary>=2.9",
    "openai>=1.0",
    "anthropic>=0.7",
    "reportlab>=4.0",
    "python-docx>=1.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-django>=4.5",
    "black>=23.0",
    "isort>=5.12",
    "mypy>=1.0",
    "pre-commit>=3.0",
    "django-debug-toolbar>=4.0",
]
ml = [
    "transformers>=4.30",
    "torch>=2.0",
    "numpy>=1.24",
    "pandas>=2.0",
    "scikit-learn>=1.3",
]
prod = [
    "gunicorn>=21.0",
    "whitenoise>=6.5",
    "sentry-sdk>=1.30",
]

[tool.uv]
dev-dependencies = [
    "pytest>=7.0",
    "black>=23.0",
    "mypy>=1.0",
]

[tool.uv.sources]
# Pin specific versions for critical dependencies
django = { version = ">=4.2,<4.3" }
openai = { version = ">=1.0,<2.0" }
```

### Development Workflow Commands
```bash
# Initial setup
uv sync                     # Install all dependencies including dev
uv sync --frozen           # Install from lockfile only (CI/production)
uv sync --group prod       # Install production dependencies only

# Dependency management
uv add django>=4.2         # Add new dependency
uv add --dev pytest        # Add development dependency
uv add --group ml torch     # Add to specific group
uv remove package-name     # Remove dependency
uv lock                    # Update lockfile

# Environment management
uv venv                    # Create virtual environment
uv pip install -e .       # Install project in development mode
uv run python manage.py runserver  # Run commands in uv environment
uv run pytest             # Run tests
```

### CI/CD Integration
```yaml
# GitHub Actions example
- name: Set up Python
  uses: actions/setup-python@v4
  with:
    python-version: '3.11'

- name: Install uv
  run: pip install uv

- name: Install dependencies
  run: uv sync --frozen

- name: Run tests
  run: uv run pytest
```

### Docker Integration
```dockerfile
FROM python:3.11-slim

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

# Run application
CMD ["uv", "run", "gunicorn", "config.wsgi:application"]
```

## Rollback Plan

If uv proves inadequate or problematic:

1. **Phase 1**: Convert uv.lock to requirements.txt format using `uv export`
2. **Phase 2**: Switch to Poetry with existing pyproject.toml (minimal changes needed)
3. **Phase 3**: Fall back to pip + pip-tools with generated requirements files

**Migration Strategy**: uv's compatibility with pip and pyproject.toml standards makes rollback straightforward

**Trigger Criteria**:
- uv installation failures >5% in CI/CD
- Team productivity significantly impacted by uv learning curve
- Critical dependency resolution bugs affecting development
- Lack of support in required deployment platforms

## Integration with Existing Tools

### Pre-commit Hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: uv-lock-check
        name: Check uv lockfile is up to date
        entry: uv lock --check
        language: system
        files: '^(pyproject\.toml|uv\.lock)$'
```

### IDE Integration
- **VS Code**: Configure Python interpreter to use uv-managed environment
- **PyCharm**: Set project interpreter to `.venv/bin/python`
- **Vim/Neovim**: Use uv run for executing Python commands

### Development Scripts
```bash
#!/bin/bash
# scripts/setup-dev.sh
set -e

echo "Setting up development environment with uv..."

# Install uv if not present
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    pip install uv
fi

# Create and sync environment
uv sync

# Install pre-commit hooks
uv run pre-commit install

echo "Development environment ready!"
echo "Activate with: source .venv/bin/activate"
echo "Or run commands with: uv run <command>"
```

## Links

- **PRD**: `prd-20250923.md` - Development velocity and deployment requirements
- **TECH-SPECs**: `spec-20250923-api.md`, `spec-20250923-llm.md` - Python dependency requirements
- **Related ADRs**: `adr-005-backend-framework.md` - Django framework choice affects dependency management strategy