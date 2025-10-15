# Multi-stage Dockerfile for MCP Admin application with PostgreSQL
# Stage 1: Frontend build
FROM node:20-alpine AS frontend-builder

# Set working directory for frontend build
WORKDIR /app

# Copy package files for better layer caching
COPY package.json pnpm-lock.yaml ./

# Install pnpm and dependencies
RUN npm install -g pnpm && pnpm install --frozen-lockfile

# Copy frontend source files to the correct location
COPY views/admin ./views/admin

# Build frontend assets (build script expects to run from project root)
RUN pnpm run build

# Stage 2: Python dependencies
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

# Stage 3: Final application image
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

# Copy frontend assets from frontend builder
COPY --from=frontend-builder /app/views/admin/static ./views/admin/static

# Copy application source code
COPY app ./app
COPY config.yaml ./
COPY .env* ./

# Copy migration scripts
COPY migrate_sqlite_to_postgres.py ./
COPY migrate_to_postgres.py ./

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
    CMD python -c "
import asyncio
import asyncpg
async def test():
    try:
        conn = await asyncpg.connect(
            user='${POSTGRES_USER:-mcp_user}',
            password='${POSTGRES_PASSWORD:-mcp_password}',
            host='${POSTGRES_HOST:-postgres}',
            port=${POSTGRES_PORT:-5432},
            database='${POSTGRES_DB:-mcp_db}'
        )
        await conn.fetchval('SELECT 1')
        await conn.close()
        print('PostgreSQL connection successful')
        return True
    except Exception as e:
        print(f'PostgreSQL connection failed: {e}')
        return False
asyncio.run(test())
" || exit 1

# Start the application using uvicorn
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]