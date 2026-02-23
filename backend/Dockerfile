# =============================================================================
# BUILDER STAGE - Compile dependencies and build artifacts
# =============================================================================
FROM python:3.11-slim-bookworm AS builder

# Set build-time environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install ONLY build-time system dependencies
# These will NOT be in the final image
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libpq-dev \
    libmagic-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast Python package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy dependency files first (better layer caching)
COPY pyproject.toml README.md /app/

# Install Python dependencies with uv
# --frozen: Use existing lock file without updating
# --extra prod: Install production extras (sentry, health-check, etc.)
# --no-dev: Skip dev dependencies
RUN uv lock && \
    uv sync --frozen --extra prod --no-dev && \
    uv cache clean

# =============================================================================
# RUNTIME STAGE - Minimal production image
# =============================================================================
FROM python:3.11-slim-bookworm AS runtime

# Set runtime environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app

WORKDIR /app

# Install ONLY runtime system dependencies (much smaller than builder)
# - libpq5: PostgreSQL client library (runtime only, not dev)
# - postgresql-client: psql command line tool
# - libmagic1: File type detection (runtime only, not dev)
# - poppler-utils: PDF manipulation utilities
# - curl: Health checks and debugging
# - libgl1-mesa-glx: OpenGL library for computer vision (needed by unstructured[pdf])
# - libglib2.0-0: GLib library (needed by OpenCV)
# - tesseract-ocr: OCR engine for text extraction from PDFs (needed by unstructured[pdf])
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    postgresql-client \
    libmagic1 \
    poppler-utils \
    poppler-data \
    curl \
    libgl1-mesa-glx \
    libglib2.0-0 \
    tesseract-ocr \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && rm -rf /tmp/* /var/tmp/*

# Copy uv binary from builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy Python virtual environment from builder (includes all compiled packages)
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY . /app/

# Create necessary directories with appropriate permissions
RUN mkdir -p /app/media /app/logs /app/staticfiles && \
    chmod +x /app/manage.py && \
    # Remove Python cache files and unnecessary artifacts
    find /app -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true && \
    find /app -type f -name "*.pyc" -delete && \
    find /app -type f -name "*.pyo" -delete && \
    find /app -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true && \
    find /app -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Default command (overridden in docker-compose.yml)
# Use gunicorn for production (faster startup, production-ready)
CMD ["gunicorn", "cv_tailor.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "60"]
