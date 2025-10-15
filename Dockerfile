# Stage 1: Frontend builder
FROM node:20-alpine AS frontend-builder
WORKDIR /app/views/admin

# Copy root package files
COPY package.json pnpm-lock.yaml ./

# Install pnpm and dependencies
RUN npm install -g pnpm && pnpm install --frozen-lockfile

# Copy frontend source and build
COPY views/admin/ .
RUN pnpm run build

# Stage 2: Build with dependencies
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies for building wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir=/wheels -r requirements.txt

# Stage 2: Final image
FROM python:3.11-slim

WORKDIR /app

# Copy wheels from builder stage
COPY --from=builder /wheels /wheels

# Install Python dependencies from wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/*

# Copy frontend assets
COPY --from=frontend-builder /app/views/admin/dist /app/static

# Copy application code
COPY app /app/app

# Ensure the database directory exists
RUN mkdir -p /data

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Default command (can be overridden in docker-compose)
CMD ["tail", "-f", "/dev/null"]