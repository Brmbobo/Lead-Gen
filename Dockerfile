# Lead-Gen Dockerfile
# Multi-stage build for minimal, secure production image

# =============================================================================
# Stage 1: Builder
# =============================================================================
FROM python:3.12-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir build && \
    pip wheel --no-cache-dir --wheel-dir=/app/wheels -e .

# =============================================================================
# Stage 2: Production
# =============================================================================
FROM python:3.12-slim as production

# Security: Create non-root user
RUN groupadd --gid 1000 leadgen && \
    useradd --uid 1000 --gid leadgen --shell /bin/bash --create-home leadgen

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy wheels from builder
COPY --from=builder /app/wheels /app/wheels

# Install application
RUN pip install --no-cache-dir /app/wheels/* && \
    rm -rf /app/wheels

# Copy application code
COPY --chown=leadgen:leadgen src/ ./src/
COPY --chown=leadgen:leadgen workflows/ ./workflows/

# Security: Switch to non-root user
USER leadgen

# Environment defaults
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ENVIRONMENT=production \
    LOG_LEVEL=INFO \
    LOG_JSON=true

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from lead_gen.core.config import get_settings; get_settings()" || exit 1

# Default command
ENTRYPOINT ["python", "-m", "lead_gen.cli"]
CMD ["--help"]

# =============================================================================
# Stage 3: Development
# =============================================================================
FROM production as development

# Switch back to root to install dev dependencies
USER root

# Install dev dependencies
RUN pip install --no-cache-dir \
    pytest \
    pytest-asyncio \
    pytest-cov \
    mypy \
    ruff \
    black

# Switch back to non-root
USER leadgen

# Override for development
ENV ENVIRONMENT=development \
    LOG_LEVEL=DEBUG \
    LOG_JSON=false

CMD ["validate-env"]
