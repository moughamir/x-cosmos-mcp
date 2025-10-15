#!/bin/bash
set -e

# Run database migrations
echo "Running database migrations..."
python migrate_to_postgres.py

# Start the main application
echo "Starting application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
