# Multi-stage Dockerfile for MCP Admin application with PostgreSQL
# Stage 1: Python dependencies
FROM python:3.11-slim AS python-builder

WORKDIR /app

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy Python requirements
COPY requirements.txt .

# Upgrade pip and create wheels for faster installs
RUN pip install --no-cache-dir --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir=/wheels -r requirements.txt

# Stage 2: Final application image
FROM python:3.11-slim

# Install PostgreSQL client for health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Copy Python wheels from builder stage
COPY --from=python-builder /wheels /wheels

# Install Python dependencies from wheels (faster than source)
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/*

# Copy application source code
COPY app ./app
COPY config.yaml ./
COPY .env* ./
COPY scripts ./scripts

# Create data directory for any file storage
RUN mkdir -p data && chown -R appuser:appuser /app

# Set proper ownership
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PATH="/home/appuser/.local/bin:${PATH}"

# Expose port
EXPOSE 8000

# Health check with PostgreSQL connectivity
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python scripts/healthcheck.py || exit 1

# Start the application using uvicorn (will be overridden by entrypoint script in docker-compose)
