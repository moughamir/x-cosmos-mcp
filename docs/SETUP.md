# MCP Admin Setup & Deployment Guide

## Overview

This guide covers the complete setup, configuration, and deployment process for the MCP Admin application.

## System Requirements

### Minimum Requirements

- **Operating System:** Linux (Ubuntu 20.04+, CentOS 8+, or similar)
- **Memory:** 8GB RAM minimum, 16GB recommended
- **Storage:** 20GB free space for application + data
- **Network:** Internet connection for Ollama model downloads

### Recommended Specifications

- **CPU:** 4+ cores for parallel processing
- **RAM:** 32GB for large datasets (10K+ products)
- **Storage:** SSD for faster database operations
- **Network:** 100Mbps+ for model downloads

---

## Local Development Setup

### 1. Prerequisites

#### Install Node.js and pnpm

```bash
# Using Node Version Manager (recommended)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.bashrc
nvm install 18
nvm use 18

# Install pnpm
npm install -g pnpm
```

#### Install Python 3.11+

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev

# Or using pyenv
curl https://pyenv.run | bash
pyenv install 3.11
pyenv global 3.11
```

#### Install Ollama

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama service
systemctl enable ollama
systemctl start ollama

# Verify installation
ollama --version
```

### 2. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd mcp-openai

# Install Python dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Install Node.js dependencies
pnpm install

# Build frontend assets
pnpm run build
```

### 3. Configuration

#### Database Setup

```bash
# Create data directory
mkdir -p data/sqlite

# The database will be automatically created on first run
# with the correct schema and sample data
```

#### Configuration Files

**config.yaml** - Main application configuration:

```yaml
# Model settings
models:
  title_model: llama3.2:1b-instruct-q4_K_M
  description_model: qwen2:1.5b
  provider: ollama
  temperature: 0.4
  max_output_tokens: 512
  concurrency: 1
  batch_size: 10
  timeout: 150

# Database paths
paths:
  database: data/sqlite/products.sqlite
  log_table: changes_log
  prompt_dir: ./prompts

# Worker configuration
workers:
  max_workers: 4
  queue_size: 100
  timeout: 300
  retry_attempts: 3
  batch_size: 10
```

**Environment Variables** (optional):

```bash
# Ollama configuration
export OLLAMA_HOST=http://localhost:11434

# Application settings
export MCP_LOG_LEVEL=INFO
export MCP_DEBUG=true
```

### 4. Start Development Server

```bash
# Start the backend server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Or using npm script
npm run python:run
```

The application will be available at:
- **Frontend:** http://localhost:8000
- **API:** http://localhost:8000/api/*
- **API Documentation:** Available through frontend interface

---

## Docker Deployment

### Production Docker Setup

#### 1. Build Images

```bash
# Build all services
docker compose build

# Or build specific services
docker compose build backend
docker compose build frontend
```

#### 2. Start Services

```bash
# Start all services
docker compose up -d

# Start with logs
docker compose up

# Start specific services
docker compose up backend ollama
```

#### 3. Verify Deployment

```bash
# Check running containers
docker compose ps

# Check logs
docker compose logs backend
docker compose logs ollama

# Test API endpoints
curl http://localhost:8000/api/products | head -5
```

### Docker Services

#### Backend Service

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Features:**
- Multi-stage build for smaller images
- Production-optimized Python environment
- Proper signal handling for graceful shutdowns

#### Frontend Service (Nginx)

**nginx.conf:**
```nginx
server {
    listen 80;
    server_name localhost;

    root /usr/share/nginx/html;
    index index.html;

    # API proxy
    location /api/ {
        proxy_pass http://backend:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Static files
    location /static/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Frontend fallback
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

#### Ollama Service

**Dockerfile:**
```dockerfile
FROM ollama/ollama:latest

# Pre-install common models
RUN ollama pull llama3.2:1b
RUN ollama pull nomic-embed-text
```

---

## Environment Configuration

### Development Environment

**.env (Development):**
```bash
# Database
DATABASE_URL=sqlite:///data/products.db

# Ollama
OLLAMA_HOST=http://localhost:11434

# Application
DEBUG=true
LOG_LEVEL=DEBUG

# Frontend
VITE_API_URL=http://localhost:8000/api
```

### Production Environment

**.env (Production):**
```bash
# Database
DATABASE_URL=sqlite:////data/products.db

# Ollama (internal network)
OLLAMA_HOST=http://ollama:11434

# Application
DEBUG=false
LOG_LEVEL=INFO

# Security
SECRET_KEY=your-secret-key-here

# Frontend
VITE_API_URL=/api
```

---

## Database Management

### Initial Setup

The database is automatically initialized on first startup with:
- **Products table:** Main product data storage
- **Changes log:** Audit trail for all modifications
- **Pipeline runs:** Execution history tracking

### Migrations

```bash
# Run database migrations
curl -X POST http://localhost:8000/api/db/migrate

# Check current schema
curl http://localhost:8000/api/schema
```

### Backup and Restore

```bash
# Create backup
cp data/sqlite/products.sqlite data/sqlite/products.backup.$(date +%Y%m%d_%H%M%S).sqlite

# Restore from backup
cp data/sqlite/products.backup.YYYYMMDD_HHMMSS.sqlite data/sqlite/products.sqlite

# Restart application after restore
docker compose restart backend
```

---

## Ollama Model Management

### Installing Models

#### Via API
```bash
# Pull a model
curl -X POST http://localhost:8000/api/ollama/pull \
  -H "Content-Type: application/json" \
  -d '{"model_name": "llama3.2:1b"}'

# List installed models
curl http://localhost:8000/api/ollama/models
```

#### Via Ollama CLI
```bash
# Pull model directly
ollama pull llama3.2:1b

# List models
ollama list

# Remove model
ollama rm llama3.2:1b
```

### Model Storage

Models are stored in:
- **Docker:** `/root/.ollama/models/`
- **Host:** `~/.ollama/models/`

### Recommended Models

For the MCP application:
- **llama3.2:1b-instruct-q4_K_M** - Title optimization (4GB)
- **qwen2:1.5b** - Content rewriting (3GB)
- **nomic-embed-text:latest** - Text embeddings (274MB)

---

## Monitoring and Logging

### Application Logs

```bash
# View all logs
docker compose logs

# Follow logs
docker compose logs -f

# Specific service logs
docker compose logs backend
docker compose logs ollama

# Save logs
docker compose logs > mcp_logs_$(date +%Y%m%d).txt
```

### Log Files

- **Application logs:** `app.log` and `backend.log`
- **Ollama logs:** Docker container logs
- **System logs:** `/var/log/syslog` or journalctl

### Health Checks

```bash
# API health
curl -f http://localhost:8000/api/products

# Database health
python3 -c "
import asyncio
import aiosqlite
async def test():
    async with aiosqlite.connect('data/sqlite/products.sqlite') as conn:
        await conn.execute('SELECT 1')
        print('Database OK')
asyncio.run(test())
"

# Ollama health
curl http://localhost:11434/api/version
```

---

## Troubleshooting

### Common Issues

#### 1. Backend Won't Start

**Symptoms:** Server fails to start, port 8000 not accessible

**Solutions:**
```bash
# Check if port is in use
netstat -tlnp | grep :8000

# Kill conflicting process
kill -9 <PID>

# Check Python environment
python3 -c "import fastapi, uvicorn; print('Dependencies OK')"

# Check configuration
python3 -c "from app.config import settings; print('Config OK')"
```

#### 2. Database Connection Issues

**Symptoms:** API returns 500 errors, database operations fail

**Solutions:**
```bash
# Check database file
ls -la data/sqlite/products.sqlite

# Test database connectivity
sqlite3 data/sqlite/products.sqlite "SELECT COUNT(*) FROM products;"

# Check file permissions
chmod 644 data/sqlite/products.sqlite

# Recreate database if corrupted
rm data/sqlite/products.sqlite
# Application will recreate on restart
```

#### 3. Ollama Connection Issues

**Symptoms:** Model endpoints return errors, models not accessible

**Solutions:**
```bash
# Check Ollama status
systemctl status ollama

# Restart Ollama service
systemctl restart ollama

# Test Ollama API
curl http://localhost:11434/api/version

# Check model storage
du -sh ~/.ollama/models/
```

#### 4. Frontend Build Issues

**Symptoms:** CSS/JS not loading, build errors

**Solutions:**
```bash
# Clear build cache
rm -rf node_modules/.cache
rm -rf views/admin/static/*

# Reinstall dependencies
pnpm install

# Rebuild assets
pnpm run build

# Check file permissions
chmod -R 755 views/admin/static/
```

#### 5. Docker Issues

**Symptoms:** Containers fail to start, services unavailable

**Solutions:**
```bash
# Check Docker status
systemctl status docker

# Clean up containers
docker compose down
docker system prune -f

# Rebuild images
docker compose build --no-cache

# Check resource usage
docker system df
```

### Performance Issues

#### High Memory Usage

```bash
# Monitor memory usage
docker stats

# Adjust worker count
# Edit config.yaml workers.max_workers

# Restart services
docker compose restart
```

#### Slow API Responses

```bash
# Check database performance
sqlite3 data/sqlite/products.sqlite "ANALYZE;"

# Monitor query performance
# Add logging to identify slow endpoints

# Optimize batch sizes
# Reduce workers.batch_size in config
```

---

## Scaling and Performance

### Horizontal Scaling

For high-traffic deployments:

1. **Load Balancer:** Use nginx or HAProxy for API distribution
2. **Database:** Consider PostgreSQL for better concurrency
3. **Caching:** Implement Redis for session and API caching
4. **CDN:** Use CloudFlare or similar for static assets

### Vertical Scaling

For single-server deployments:

1. **CPU:** Increase worker processes
2. **RAM:** Allocate more memory for larger datasets
3. **Storage:** Use faster SSD storage
4. **Network:** Ensure adequate bandwidth for model downloads

### Monitoring Setup

```bash
# Install monitoring tools
sudo apt install htop iotop nethogs

# Set up log aggregation
# Configure centralized logging (ELK stack)

# Performance monitoring
# Use New Relic, DataDog, or similar
```

---

## Security Considerations

### Production Security

1. **HTTPS:** Configure SSL/TLS certificates
2. **Authentication:** Implement JWT or OAuth2
3. **Rate Limiting:** Add request throttling
4. **Input Validation:** Sanitize all user inputs
5. **CORS:** Configure appropriate CORS policies

### Docker Security

```dockerfile
# Use non-root user
RUN useradd -m appuser
USER appuser

# Minimal base image
FROM python:3.11-slim

# Security updates
RUN apt update && apt upgrade -y
```

### Network Security

- Use internal Docker networks
- Firewall configuration
- API gateway implementation
- DDoS protection

---

## Backup Strategy

### Automated Backups

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backup/mcp"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
cp data/sqlite/products.sqlite $BACKUP_DIR/products_$TIMESTAMP.sqlite

# Backup configuration
cp config.yaml $BACKUP_DIR/
cp .env $BACKUP_DIR/

# Cleanup old backups (keep 7 days)
find $BACKUP_DIR -name "*.sqlite" -type f -mtime +7 -delete

echo "Backup completed: $TIMESTAMP"
```

### Recovery Procedures

1. **Stop services:** `docker compose down`
2. **Restore database:** Replace database file
3. **Restore config:** Copy configuration files
4. **Restart services:** `docker compose up -d`
5. **Verify:** Test API endpoints and functionality

---

## Support and Maintenance

### Regular Maintenance

- **Weekly:** Review logs and performance metrics
- **Monthly:** Update dependencies and security patches
- **Quarterly:** Full backup and system review
- **Annually:** Major version updates and architecture review

### Getting Help

1. **Documentation:** Check this guide and API documentation
2. **Logs:** Review application and system logs
3. **Community:** GitHub issues and discussions
4. **Monitoring:** Check system health and performance

### Update Procedures

```bash
# Backup before updates
./backup.sh

# Update application
git pull origin main

# Update dependencies
pip install -r requirements.txt --upgrade
pnpm update

# Rebuild and restart
pnpm run build
docker compose build
docker compose up -d
```

---

## API Versioning

Current API version: **v1**

**Version Header:** `X-API-Version: v1`

**Breaking Changes:** Will be released as new major versions with advance notice.

**Deprecation Policy:** Old endpoints will be supported for 6 months after deprecation announcement.
