# NeuraOps Docker Image - Single platform optimized
# Architecture: Modular CLI interface with refactored AI engine
# Entry point: src.main:main (updated after Phase 60 refactoring)

# Use recent and secure base image
FROM python:3.11-slim AS builder

# Set shell options for better error handling
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_CACHE_DIR=/tmp/.uv-cache \
    PYTHONPATH=/app/src

# Install security updates, dependencies, and uv in one optimized layer
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y \
        curl \
        git \
        build-essential \
        ca-certificates \
        gnupg \
        --no-install-recommends && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* && \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv && \
    /usr/local/bin/uv --version

WORKDIR /app

# Copy project configuration and dependencies
COPY neuraops-core/pyproject.toml neuraops-core/uv.lock ./

# Install dependencies using uv for faster builds
RUN /usr/local/bin/uv pip install --system --no-cache-dir --compile-bytecode . && \
    /usr/local/bin/uv pip install --system --no-cache-dir --compile-bytecode ".[dev]" && \
    rm -rf /tmp/.uv-cache/* /root/.cache/* 2>/dev/null

# Production stage - Optimized for single platform
FROM python:3.11-slim AS production

# Set shell options for better error handling
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    NEURAOPS_ENV=production

# Install runtime dependencies, create user, and cleanup in one optimized layer
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y curl ca-certificates --no-install-recommends && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /var/cache/apt/* && \
    groupadd --gid 1000 neuraops && \
    useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash neuraops

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

WORKDIR /app

# Copy core application files
COPY --chown=1000:1000 neuraops-core/src/ ./src/
COPY --chown=1000:1000 neuraops-core/data/ ./data/
COPY --chown=1000:1000 neuraops-core/pyproject.toml ./

# Create data directories for runtime
RUN mkdir -p /app/data /app/logs /app/cache

# Set permissions and validate installation
RUN chown -R 1000:1000 /app && \
    chmod -R 755 /app/src && \
    python -c "from src.main import app; print('✅ NeuraOps CLI imported')" && \
    python -c "from src.core.engine import DevOpsEngine; print('✅ DevOpsEngine imported')"

# Switch to non-root user for security
USER 1000:1000

# Expose port for potential web interface
EXPOSE 8000

# Default command using the updated entry point
CMD ["neuraops", "--help"]