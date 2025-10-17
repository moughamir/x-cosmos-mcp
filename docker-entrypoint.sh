#!/bin/bash
set -e

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
until python scripts/setup/03_healthcheck.py; do
  echo "PostgreSQL is not ready yet. Waiting..."
  sleep 2
done

# Run database migrations
echo "Running database migrations..."
python scripts/migrations/01_import_products_from_json.py

# Start the main application
echo "Starting application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
