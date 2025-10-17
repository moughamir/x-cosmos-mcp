# MCP Workflow CLI Guide

## Overview
The MCP CLI provides a powerful command-line interface for running AI-powered SEO optimization tasks on your product catalog.

## Installation
```bash
# Ensure you're in the project directory
cd /home/odin/Documents/Vaults/x-cosmos-ws/mcp/openai

# Install dependencies (if not already done)
pip install -r requirements.txt
```

## Basic Usage

### Single Task Execution
```bash
python cli.py <task_name> [options]
```

### Available Tasks
- `meta_optimization` - Optimize meta titles and descriptions
- `content_rewriting` - Rewrite product content for better SEO
- `keyword_analysis` - Analyze and suggest keywords
- `tag_optimization` - Optimize product tags
- `category_normalization` - Normalize categories using Google taxonomy

### Workflow Mode (Multiple Tasks)
```bash
python cli.py workflow --tasks <task1> <task2> <task3> [options]
```

---

## Command Options

### Product Selection

#### Process Specific Products
```bash
python cli.py category_normalization --product-ids 123 456 789
```

#### Process All Products
```bash
python cli.py tag_optimization --all
```

#### Process Sample (Default: 10 products)
```bash
python cli.py keyword_analysis
```

#### Process Custom Sample Size
```bash
python cli.py meta_optimization --limit 50
```

### Performance Options

#### Use Quantized Models (Faster)
```bash
python cli.py content_rewriting --all --quantize
```

### Dry Run (Preview Without Changes)
```bash
python cli.py workflow --tasks category_normalization tag_optimization --all --dry-run
```

---

## Examples

### Example 1: Normalize Categories for All Products
```bash
python cli.py category_normalization --all
```
**Output:**
```
🔧 Initializing database pool...
Fetching all product IDs...
🚀 Starting workflow for 100 products
Tasks: category_normalization
============================================================

Product 5856071680150: 'Balances & Scales' -> 'Hardware > Tools > Measuring Tools & Sensors > Measuring Scales' (confidence: 0.34)
✅ Category normalization batch complete.
...

============================================================
📊 WORKFLOW SUMMARY
============================================================
  category_normalization: ✅ 98 succeeded, ❌ 2 failed
============================================================
TOTAL: ✅ 98 succeeded, ❌ 2 failed
============================================================
```

### Example 2: Optimize Tags for Specific Products
```bash
python cli.py tag_optimization --product-ids 1926707413055 2016844251234 4115702251598
```

### Example 3: Run Complete SEO Workflow
```bash
python cli.py workflow \
  --tasks category_normalization tag_optimization meta_optimization \
  --all \
  --quantize
```
**What it does:**
1. Normalizes all product categories
2. Optimizes all product tags
3. Optimizes all meta titles and descriptions
4. Uses quantized models for faster processing

### Example 4: Test Workflow on Sample
```bash
python cli.py workflow \
  --tasks category_normalization tag_optimization \
  --limit 5 \
  --dry-run
```
**Output:**
```
============================================================
🔍 DRY RUN MODE - No changes will be made
============================================================
Tasks to run: category_normalization, tag_optimization
Products to process: 5
Product IDs: [1926707413055, 2016844251234, 4115702251598, 4808014331938, 4814237171790]
Quantized models: No
============================================================
```

### Example 5: Rewrite Content with Quantized Models
```bash
python cli.py content_rewriting --limit 20 --quantize
```

---

## Workflow Patterns

### Full Product Optimization Pipeline
```bash
# Step 1: Normalize categories
python cli.py category_normalization --all

# Step 2: Optimize tags
python cli.py tag_optimization --all

# Step 3: Optimize meta data
python cli.py meta_optimization --all

# Step 4: Rewrite content
python cli.py content_rewriting --all
```

### Or run as a single workflow:
```bash
python cli.py workflow \
  --tasks category_normalization tag_optimization meta_optimization content_rewriting \
  --all
```

### Incremental Processing
```bash
# Process in batches of 50
python cli.py tag_optimization --limit 50
# Run again to process next batch
python cli.py tag_optimization --limit 50
# Repeat as needed
```

---

## Output and Logging

### Log Levels
The CLI uses Python's logging module with INFO level by default.

### Progress Tracking
- Real-time progress updates for each product
- Batch completion notifications
- Final summary with success/failure counts

### Example Output:
```
2025-10-17 21:25:31,581 - INFO - Product 5856071680150: 'Balances & Scales' -> 'Hardware > Tools > Measuring Tools & Sensors > Measuring Scales' (confidence: 0.34)
2025-10-17 21:25:31,583 - INFO - ✅ Category normalization batch complete.
2025-10-17 21:25:31,591 - INFO - Updated product 5856071680150 with fields: ['normalized_category', 'category_confidence']
```

---

## Error Handling

### Graceful Interruption
Press `Ctrl+C` to stop the workflow gracefully:
```
⚠️  Workflow interrupted by user
🛑 Shutting down worker pool...
🛑 Closing database pool...
```

### Error Recovery
- Failed products are logged but don't stop the workflow
- Summary shows which products succeeded/failed
- Check logs for detailed error messages

---

## Performance Tips

### 1. Use Quantized Models
```bash
--quantize
```
- Faster inference
- Lower memory usage
- Slightly reduced accuracy (usually negligible)

### 2. Adjust Worker Pool Size
Edit `app/config.py`:
```python
workers:
  max_workers: 4  # Increase for more parallelism
```

### 3. Process in Batches
```bash
# Instead of --all, use --limit
python cli.py tag_optimization --limit 100
```

### 4. Run During Off-Peak Hours
- Less database contention
- Better API response times

---

## Integration with Frontend

The CLI shares the same backend as the web interface:
- Changes made via CLI are visible in the frontend
- Real-time progress can be monitored at `/admin/pipeline-progress`
- Both use the same worker pool and database

### Monitor CLI Progress in Browser
1. Start the backend server:
   ```bash
   uvicorn app.api:app --reload --host 0.0.0.0 --port 8000
   ```

2. Open browser to:
   ```
   http://localhost:3000/admin/pipeline-progress
   ```

3. Run CLI command:
   ```bash
   python cli.py category_normalization --all
   ```

4. Watch real-time progress in the browser! 🎉

---

## Troubleshooting

### Issue: "No product IDs to process"
**Solution**: Check that products exist in the database
```bash
# Verify products exist
psql -d your_database -c "SELECT COUNT(*) FROM products;"
```

### Issue: "Model not available"
**Solution**: Pull the required Ollama model
```bash
ollama pull llama3.2:1b-instruct-q4_K_M
```

### Issue: Database connection errors
**Solution**: Check PostgreSQL is running and credentials are correct
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Verify connection
psql -d your_database -U your_user
```

### Issue: Worker pool timeout
**Solution**: Increase timeout in `app/config.py`
```python
workers:
  timeout: 300  # Increase from default
```

---

## Advanced Usage

### Custom Task Handlers
You can extend the CLI by adding custom task handlers in `app/pipeline.py`:

```python
async def custom_task(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
    # Your custom logic here
    return {"status": "success", "data": result}
```

Then register it in `cli.py`:
```python
task_handlers = {
    # ... existing handlers ...
    "custom_task": manager.custom_task,
}
```

### Programmatic Usage
```python
from app.pipeline import MultiModelSEOManager
from app.config import TaskType

async def run_custom_workflow():
    manager = MultiModelSEOManager()
    product_ids = [123, 456, 789]

    results = await manager.batch_process_products(
        product_ids,
        TaskType.TAG_OPTIMIZATION,
        quantize=True
    )

    return results
```

---

## Help and Support

### Get Help
```bash
python cli.py --help
```

### View Available Tasks
```bash
python cli.py --help | grep -A 20 "choices:"
```

### Check Version
```bash
python cli.py --version  # If implemented
```

---

## Best Practices

1. **Always test with --dry-run first**
   ```bash
   python cli.py workflow --tasks ... --dry-run
   ```

2. **Start with small batches**
   ```bash
   python cli.py tag_optimization --limit 10
   ```

3. **Monitor logs for errors**
   ```bash
   python cli.py category_normalization --all 2>&1 | tee workflow.log
   ```

4. **Use workflows for consistency**
   ```bash
   # Better than running tasks individually
   python cli.py workflow --tasks category_normalization tag_optimization
   ```

5. **Schedule regular runs**
   ```bash
   # Add to crontab for daily execution
   0 2 * * * cd /path/to/project && python cli.py category_normalization --all
   ```

---

## Summary of All Commands

```bash
# Single task on all products
python cli.py <task> --all

# Single task on specific products
python cli.py <task> --product-ids 123 456 789

# Single task on sample
python cli.py <task> --limit 50

# Workflow on all products
python cli.py workflow --tasks <task1> <task2> --all

# Workflow with quantized models
python cli.py workflow --tasks <task1> <task2> --all --quantize

# Dry run
python cli.py workflow --tasks <task1> <task2> --dry-run

# Get help
python cli.py --help
```

---

## Quick Reference

| Option | Description | Example |
|--------|-------------|---------|
| `--product-ids` | Specific product IDs | `--product-ids 123 456` |
| `--all` | Process all products | `--all` |
| `--limit` | Sample size (default: 10) | `--limit 50` |
| `--quantize` | Use quantized models | `--quantize` |
| `--dry-run` | Preview without changes | `--dry-run` |
| `--tasks` | Tasks for workflow mode | `--tasks task1 task2` |

---

Happy optimizing! 🚀
