#!/bin/bash
set -e

# The docker-compose file's `depends_on` condition is now the sole mechanism
# for ensuring the database is ready.

# Start the main application
echo "Starting application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
