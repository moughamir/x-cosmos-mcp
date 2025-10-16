#!/bin/bash
set -e

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
until python scripts/healthcheck.py; do
  echo "PostgreSQL is not ready yet. Waiting..."
  sleep 2
done

# Run database migrations
echo "Running database migrations..."
python scripts/migrations/migrate_to_postgres.py

# Start the main application
echo "Starting application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
