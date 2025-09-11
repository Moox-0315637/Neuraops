# ==================================================================================
# NeuraOps Agent - Docker Multi-Stage Build  
# Agent optimisé pour monitoring système avec accès host contrôlé
# ==================================================================================

# Build stage avec UV pour performance
FROM python:3.11-slim AS builder

# Install system dependencies et UV
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && mv /root/.local/bin/uv /usr/local/bin/uv

WORKDIR /app

# Copy dependencies files from neuraops-agent directory (context is project root)
COPY neuraops-agent/pyproject.toml ./pyproject.toml
COPY neuraops-agent/uv.lock ./uv.lock

# Install dependencies with UV
RUN uv pip install --system --no-cache-dir .

# ==================================================================================
# Production stage - Agent runtime optimisé
# ==================================================================================
FROM python:3.11-slim AS agent

# Install runtime dependencies pour system monitoring
RUN apt-get update && apt-get install -y \
    procps \
    net-tools \
    iproute2 \
    lsof \
    htop \
    iotop \
    curl \
    wget \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

WORKDIR /app

# Copy agent source code from neuraops-agent directory (context is project root)
COPY neuraops-agent/src/ ./src/

# Create non-root user but with system access
RUN groupadd -r neuraops && useradd -r -g neuraops -m -d /home/neuraops neuraops \
    && mkdir -p /app/data /app/logs /app/config /home/neuraops/.neuraops \
    && chown -R neuraops:neuraops /app /home/neuraops

# Environment variables
ENV PYTHONPATH=/app/src
ENV NEURAOPS_ENV=docker
ENV NEURAOPS_LOG_LEVEL=INFO

# Default configuration
ENV NEURAOPS_CORE_URL=http://neuraops-core:8000
ENV NEURAOPS_AGENT_NAME=docker-agent
ENV NEURAOPS_METRICS_INTERVAL=30

# Volumes for persistent data
VOLUME ["/app/data", "/app/logs", "/app/config"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "from src.agent import is_agent_running; exit(0 if is_agent_running() else 1)" || exit 1

# Default user (can be overridden for privileged mode)
USER neuraops

# Default command
CMD ["python", "-m", "src.main", "start"]
