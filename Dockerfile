# Multi-stage Docker build for SCDL - SoundCloud Downloader
FROM python:3.12-slim as builder

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY pyproject.toml uv.lock* ./

# Install dependencies
RUN uv sync --frozen

# Production stage
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . .

# Install scdl
RUN uv pip install -e .

# Create downloads directory
RUN mkdir -p /downloads && chown scdl:scdl /downloads

# Switch to non-root user
USER scdl

# Set default download directory
VOLUME ["/downloads"]
WORKDIR /downloads

# Default command
ENTRYPOINT ["scdl"]
CMD ["--help"]
