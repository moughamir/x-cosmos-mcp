# MCP Admin Usage Guide & Troubleshooting

## Quick Start

### Accessing the Application

1. **Start the application:**
   ```bash
   # Development
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

   # Or using Docker
   docker compose up -d
   ```

2. **Open in browser:** http://localhost:8000

3. **API access:** http://localhost:8000/api/*

---

## Daily Usage Workflow

### 1. Product Management

#### Browse Products
- Navigate to **Products** section
- View all products in a table format
- Click **View** button to see product details

#### Edit Products
- Open product detail view (`/products/{id}`)
- Modify fields inline (title, description, category)
- Click **Save Changes** to update
- Changes are automatically logged in the audit trail

#### Review Low-Confidence Products
- Use **Products for Review** endpoint or section
- Products with confidence < 0.7 need manual attention
- Review and correct AI-generated content

### 2. Model Management

#### View Installed Models
- Navigate to **Models** section
- See all installed Ollama models
- Check model sizes and installation dates

#### Install New Models
- Enter model name (e.g., `llama3.2:1b`)
- Click **Pull Model**
- Monitor download progress
- Refresh list to see new model

### 3. Monitor Operations

#### Check Change Log
- Navigate to **Changes** section
- Review all modifications made to products
- Filter by date, product, or field
- Mark changes as reviewed

#### Pipeline Monitoring
- Check **Pipeline Progress** for real-time updates
- View **Pipeline Runs** for execution history
- Monitor success/failure rates

---

The following tasks are available:

*   `meta`: Optimize meta title and description.
*   `content`: Rewrite product content for better SEO.
*   `keywords`: Perform comprehensive keyword analysis.
*   `tags`: Analyze and optimize product tags.
*   `schema_analysis`: Analyze product data against a schema.

### Via API

You can also run the pipeline via the API by sending a POST request to `/api/pipeline/run` with the following JSON payload:

```json
{
  "task_type": "meta",
  "product_ids": [1, 2, 3]
}
```

## API Usage Examples

### Using cURL

#### Get All Products
```bash
curl -s http://localhost:8000/api/products | python3 -m json.tool
```

#### Get Specific Product
```bash
curl -s http://localhost:8000/api/products/172840065 | python3 -m json.tool
```

#### Update Product
```bash
curl -X POST http://localhost:8000/api/products/172840065/update \
  -H "Content-Type: application/json" \
  -d '{"title": "Updated Title", "category": "New Category"}'
```

#### Get Products for Review
```bash
curl -s "http://localhost:8000/api/products/review?limit=20" | python3 -m json.tool
```

#### Pull Ollama Model
```bash
curl -X POST http://localhost:8000/api/ollama/pull \
  -H "Content-Type: application/json" \
  -d '{"model_name": "qwen2:1.5b"}'
```

### Using Python

```python
import requests
import json

# Get products
response = requests.get('http://localhost:8000/api/products')
products = response.json()['products']

# Update product
update_data = {
    'title': 'Updated Product Title',
    'category': 'Electronics > Audio'
}
response = requests.post(
    'http://localhost:8000/api/products/172840065/update',
    json=update_data
)

# Check response
if response.status_code == 200:
    print('✅ Product updated successfully')
else:
    print('❌ Update failed:', response.text)
```

### Using JavaScript (Frontend Integration)

```javascript
// Fetch products
const response = await fetch('/api/products');
const data = await response.json();
const products = data.products;

// Update product
const updateResponse = await fetch('/api/products/172840065/update', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    title: 'New Title',
    category: 'New Category'
  })
});

if (updateResponse.ok) {
  console.log('✅ Product updated');
} else {
  console.error('❌ Update failed');
}
```

---

## Advanced Features

### 1. Batch Processing

#### Process Multiple Products
```bash
# Get products for batch processing
curl -s "http://localhost:8000/api/products/batch?limit=50" | \
  python3 -c "
import json, sys
data = json.load(sys.stdin)
products = data['products']
print(f'Processing {len(products)} products')
for product in products[:5]:
    print(f'ID: {product[\"id\"]}, Title: {product[\"title\"][:50]}...')
"
```

#### Monitor Batch Operations
- Use **Pipeline Progress** section for real-time updates
- Check **Pipeline Runs** for completion status
- Review **Changes** log for processing results

### 2. Data Quality Management

#### Review AI-Generated Content
```bash
# Get products with low confidence scores
curl -s "http://localhost:8000/api/products/review?limit=10" | \
  python3 -m json.tool | head -20
```

#### Manual Content Correction
1. Identify products needing review
2. Navigate to product detail view
3. Edit title, description, or category
4. Verify changes in the audit trail

### 3. Performance Monitoring

#### API Response Times
```bash
# Test endpoint performance
time curl -s http://localhost:8000/api/products >/dev/null
echo "API response time measured above"
```

#### Database Query Performance
```bash
# Enable SQLite query timing
sqlite3 data/sqlite/products.sqlite ".timer on"

# Run test queries
sqlite3 data/sqlite/products.sqlite "SELECT COUNT(*) FROM products;"
sqlite3 data/sqlite/products.sqlite "SELECT * FROM products WHERE id = 172840065;"
```

---

## Troubleshooting Guide

### 1. Application Won't Start

**Symptoms:** Server fails to start, port not accessible

**Solutions:**
```bash
# Check if port 8000 is in use
netstat -tlnp | grep :8000

# Kill conflicting processes
sudo lsof -ti:8000 | xargs sudo kill -9

# Check Python environment
python3 -c "import fastapi, uvicorn; print('Dependencies OK')"

# Verify configuration file
python3 -c "from app.config import settings; print('Config loaded successfully')"
```

### 2. Database Connection Issues

**Symptoms:** API returns 500 errors, database operations fail

**Solutions:**
```bash
# Check database file exists and is readable
ls -la data/sqlite/products.sqlite

# Test database connectivity
sqlite3 data/sqlite/products.sqlite "SELECT COUNT(*) FROM products;"

# Check file permissions
chmod 644 data/sqlite/products.sqlite

# Verify database schema
sqlite3 data/sqlite/products.sqlite ".schema products" | head -10
```

### 3. Ollama Connection Problems

**Symptoms:** Model endpoints fail, models not accessible

**Solutions:**
```bash
# Check Ollama service status
systemctl status ollama

# Restart Ollama if needed
sudo systemctl restart ollama

# Test Ollama API directly
curl http://localhost:11434/api/version

# Check model storage
du -sh ~/.ollama/models/

# Verify model installation
ollama list
```

### 4. Frontend Issues

**Symptoms:** CSS/JS not loading, build errors, blank pages

**Solutions:**
```bash
# Clear build cache and rebuild
rm -rf node_modules/.cache
rm -rf views/admin/static/*
pnpm install
pnpm run build

# Check file permissions
chmod -R 755 views/admin/static/

# Verify Nginx configuration (if using)
sudo nginx -t
sudo systemctl reload nginx
```

### 5. Docker Issues

**Symptoms:** Containers fail to start, services unavailable

**Solutions:**
```bash
# Check Docker service
sudo systemctl status docker

# Clean up Docker resources
docker compose down
docker system prune -f

# Rebuild images
docker compose build --no-cache

# Check container logs
docker compose logs backend
docker compose logs ollama
```

### 6. Performance Issues

**Symptoms:** Slow API responses, high memory usage, timeouts

**Solutions:**
```bash
# Monitor system resources
htop
docker stats

# Check database performance
sqlite3 data/sqlite/products.sqlite "ANALYZE;"

# Optimize configuration
# Edit config.yaml to reduce batch sizes or worker counts

# Check for memory leaks
# Monitor application logs for error patterns
```

### 7. Data Issues

**Symptoms:** Missing products, corrupted data, import failures

**Solutions:**
```bash
# Backup current database first
cp data/sqlite/products.sqlite data/sqlite/backup_$(date +%Y%m%d_%H%M%S).sqlite

# Verify data integrity
sqlite3 data/sqlite/products.sqlite "PRAGMA integrity_check;"

# Check for orphaned records
sqlite3 data/sqlite/products.sqlite "
SELECT COUNT(*) FROM changes_log
WHERE product_id NOT IN (SELECT id FROM products);"

# Recreate indexes if needed
sqlite3 data/sqlite/products.sqlite "REINDEX;"
```

---

## API Error Handling

### Understanding HTTP Status Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| `200` | Success | Operation completed successfully |
| `400` | Bad Request | Invalid input parameters |
| `404` | Not Found | Resource doesn't exist |
| `500` | Server Error | Internal application error |

### Common Error Messages

#### Product Not Found
```json
{
  "detail": "Product not found"
}
```

#### Invalid Model Name
```json
{
  "detail": "model_name is required"
}
```

#### Database Connection Error
```json
{
  "detail": "Internal server error"
}
```

### Debugging API Issues

1. **Check server logs:**
   ```bash
   tail -f app.log backend.log
   ```

2. **Test with simple requests:**
   ```bash
   curl -v http://localhost:8000/api/products
   ```

3. **Verify database connectivity:**
   ```bash
   python3 -c "
   import asyncio
   import aiosqlite
   async def test():
       async with aiosqlite.connect('data/sqlite/products.sqlite') as conn:
           await conn.execute('SELECT 1')
           print('Database OK')
   asyncio.run(test())
   "
   ```

---

## Maintenance Tasks

### Daily Checks

- [ ] Verify all API endpoints respond correctly
- [ ] Check database contains expected number of products
- [ ] Confirm Ollama models are accessible
- [ ] Review recent changes in audit log

### Weekly Maintenance

- [ ] Review application logs for errors or warnings
- [ ] Check disk space usage
- [ ] Verify backup creation
- [ ] Test full workflow from frontend to backend

### Monthly Maintenance

- [ ] Update system packages and dependencies
- [ ] Review and optimize database indexes
- [ ] Check for outdated Ollama models
- [ ] Performance testing and optimization

---

## Monitoring Dashboard

### Key Metrics to Monitor

1. **API Response Times**
   - Average response time < 500ms
   - 95th percentile < 2s

2. **Database Performance**
   - Query execution times
   - Connection pool usage

3. **System Resources**
   - CPU usage < 70%
   - Memory usage < 80%
   - Disk I/O performance

4. **Error Rates**
   - API error rate < 1%
   - Failed pipeline runs < 5%

### Setting Up Monitoring

```bash
# Install monitoring tools
sudo apt install htop iotop nethogs prometheus-node-exporter

# Set up log aggregation
# Configure ELK stack or similar

# Create monitoring dashboard
# Use Grafana with Prometheus metrics
```

---

## Security Best Practices

### API Security

1. **Input Validation:** All inputs sanitized and validated
2. **Rate Limiting:** Implement request throttling (planned)
3. **Authentication:** JWT-based auth (planned for future)
4. **HTTPS:** Use SSL/TLS in production

### Data Security

1. **Backups:** Regular encrypted backups
2. **Access Control:** Database file permissions
3. **Audit Logging:** Complete change tracking
4. **Data Validation:** Schema constraints enforced

### Operational Security

1. **Updates:** Regular security patches
2. **Monitoring:** Log analysis for suspicious activity
3. **Network:** Firewall configuration
4. **Secrets:** Environment variable management

---

## Performance Optimization

### Database Optimization

```bash
# Analyze database performance
sqlite3 data/sqlite/products.sqlite "ANALYZE;"

# Check query execution plans
sqlite3 data/sqlite/products.sqlite "EXPLAIN QUERY PLAN SELECT * FROM products WHERE id = 172840065;"

# Optimize indexes
sqlite3 data/sqlite/products.sqlite "CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);"

# Vacuum database periodically
sqlite3 data/sqlite/products.sqlite "VACUUM;"
```

### Application Tuning

**config.yaml optimizations:**
```yaml
# Reduce batch sizes for slower systems
workers:
  max_workers: 2  # Reduce from 4
  batch_size: 5   # Reduce from 10

# Adjust model settings
models:
  concurrency: 1  # Reduce for limited resources
  timeout: 300    # Increase for complex operations
```

### Caching Strategies

1. **API Response Caching:** Cache frequently requested data
2. **Database Query Caching:** Cache expensive query results
3. **Static Asset Caching:** Long-term browser caching
4. **Model Result Caching:** Cache AI processing results

---

## Support Resources

### Documentation

- **[API Documentation](./API.md)** - Complete API reference
- **[Frontend Guide](./FRONTEND.md)** - Frontend features and usage
- **[Setup Guide](./SETUP.md)** - Installation and deployment
- **[Database Schema](./DATABASE.md)** - Database structure and relationships

### Getting Help

1. **Check Logs:** Review application and system logs
2. **Test Endpoints:** Use curl or browser developer tools
3. **Database Inspection:** Use SQLite Browser for data examination
4. **Community Support:** GitHub issues and discussions

### Emergency Contacts

For critical issues requiring immediate attention:
- Check system resource usage (`htop`)
- Review recent log entries
- Test basic connectivity
- Escalate to system administrator if needed

---

## Version History

### Current Version: v1.0.0

**Features:**
- ✅ Product CRUD operations
- ✅ AI model management via Ollama
- ✅ Database schema management
- ✅ Audit trail and change logging
- ✅ Real-time pipeline monitoring
- ✅ Responsive web interface

**Known Issues:**
- Schema endpoint occasionally returns 500 errors
- Pipeline runs endpoint needs debugging
- TypeScript decorator warnings in frontend (non-critical)

### Future Releases

**v1.1.0 (Planned):**
- Advanced search functionality
- Bulk product operations
- User authentication and authorization
- API rate limiting
- Enhanced error reporting

**v1.2.0 (Planned):**
- Multi-language support
- Advanced analytics dashboard
- Plugin system for custom processors
- Mobile application
- REST API documentation interface

---

## Contributing

### Development Workflow

1. **Create Feature Branch:** `git checkout -b feature/new-feature`
2. **Make Changes:** Implement and test thoroughly
3. **Run Tests:** Ensure all functionality works
4. **Update Documentation:** Update relevant docs
5. **Submit PR:** Create pull request with description

### Code Standards

- **Python:** Follow PEP 8 style guidelines
- **TypeScript:** Use strict type checking
- **Documentation:** Update docs for any API changes
- **Testing:** Add tests for new functionality
- **Commits:** Use conventional commit format

### Quality Assurance

- [ ] Code review completed
- [ ] Documentation updated
- [ ] Tests passing
- [ ] Manual testing completed
- [ ] Performance verified
- [ ] Security considerations addressed
