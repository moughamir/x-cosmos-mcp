# MCP Database Schema Documentation

## Overview

The MCP application uses **PostgreSQL** as its primary database, with automatic schema management and migration capabilities.

## Database Location

**Development/Production:** Configured via `config.yaml` or environment variables. See `app/config.py`.

## Core Tables

---

### 1. Products Table

**Primary table for product data storage and management. Created by `migrate_to_postgres.py`.**

```sql
CREATE TABLE IF NOT EXISTS products (
    id BIGINT PRIMARY KEY,
    title TEXT,
    body_html TEXT,
    tags TEXT,
    category TEXT,
    normalized_title TEXT,
    normalized_body_html TEXT,
    normalized_tags_json TEXT,
    gmc_category_label TEXT,
    llm_model TEXT,
    llm_confidence DECIMAL(3,2) DEFAULT 0.0,
    normalized_category TEXT,
    category_confidence DECIMAL(3,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Columns:**

| Column                 | Type         | Description                          | Example                            |
| ---------------------- | ------------ | ------------------------------------ | ---------------------------------- |
| `id`                   | BIGINT       | Primary key, product ID              | `172840065`                        |
| `title`                | TEXT         | Original product title               | `"Mangas Mini Caramelo Rug"`       |
| `body_html`            | TEXT         | Product description                  | `"<p>The Mangas Mini..."`          |
| `tags`                 | TEXT         | Comma-separated tags                 | `"Brand: GAN, Collection: Mangas"` |
| `category`             | TEXT         | Original product category            | `"Home & Garden > Rugs"`           |
| `normalized_title`     | TEXT         | AI-processed title                   | `"Modern Wool Area Rug"`           |
| `normalized_body_html` | TEXT         | AI-processed description             | `"<p>Beautiful handcrafted..."`    |
| `normalized_tags_json` | TEXT         | AI-processed tags as a JSON string   | `["GAN", "Mangas Collection"]`     |
| `gmc_category_label`   | TEXT         | Google Merchant Center category      | `"Home & Garden > Decor > Rugs"`   |
| `llm_model`            | TEXT         | The LLM used for the last update     | `llama3`                           |
| `llm_confidence`       | DECIMAL(3,2) | AI confidence score (0-1)            | `0.85`                             |
| `normalized_category`  | TEXT         | AI-normalized category               | `"Rugs"`                           |
| `category_confidence`  | DECIMAL(3,2) | Confidence of category normalization | `0.95`                             |
| `created_at`           | TIMESTAMP    | Record creation time                 | `"2023-01-01T00:00:00"`            |
| `updated_at`           | TIMESTAMP    | Last modification time               | `"2023-01-01T00:00:00"`            |

**Indexes:**

- `idx_products_llm_confidence` on `llm_confidence`
- `idx_products_category` on `category`
- `idx_products_fts` for full-text search on `title` and `body_html`

---

### 2. Changes Log Table

**Audit trail for all product modifications.**

```sql
CREATE TABLE IF NOT EXISTS changes_log (
    id SERIAL PRIMARY KEY,
    product_id BIGINT REFERENCES products(id),
    field TEXT,
    old TEXT,
    new_value TEXT,
    source TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed BOOLEAN DEFAULT FALSE
);
```

**Columns:**

| Column       | Type      | Description            | Example                 |
| ------------ | --------- | ---------------------- | ----------------------- |
| `id`         | INTEGER   | Primary key, change ID | `1`                     |
| `product_id` | INTEGER   | Related product ID     | `172840065`             |
| `field`      | TEXT      | Field that was changed | `"title"`               |
| `old`        | TEXT      | Previous value (JSON)  | `"Old Title"`           |
| `new`        | TEXT      | New value (JSON)       | `"New Title"`           |
| `source`     | TEXT      | Change source          | `"manual_edit"`         |
| `created_at` | TIMESTAMP | When change occurred   | `"2023-01-01T00:00:00"` |
| `reviewed`   | BOOLEAN   | Review status          | `0` (false)             |

**Possible `source` values:**

- `manual_edit` - User modified via frontend
- `api_update` - Modified via API call
- `pipeline_meta` - Changed by meta optimization pipeline
- `pipeline_content` - Changed by content rewriting pipeline
- `pipeline_category` - Changed by category normalization pipeline

---

### 3. Pipeline Runs Table

**Tracks execution history of AI processing pipelines.**

```sql
CREATE TABLE pipeline_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_type TEXT,
    status TEXT,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    total_products INTEGER,
    processed_products INTEGER,
    failed_products INTEGER
);
```

**Columns:**

| Column               | Type      | Description               | Example                 |
| -------------------- | --------- | ------------------------- | ----------------------- |
| `id`                 | INTEGER   | Primary key, run ID       | `1`                     |
| `task_type`          | TEXT      | Type of pipeline task     | `"meta_optimization"`   |
| `status`             | TEXT      | Current status            | `"COMPLETED"`           |
| `start_time`         | TIMESTAMP | When pipeline started     | `"2023-01-01T00:00:00"` |
| `end_time`           | TIMESTAMP | When pipeline finished    | `"2023-01-01T00:01:00"` |
| `total_products`     | INTEGER   | Total products to process | `100`                   |
| `processed_products` | INTEGER   | Successfully processed    | `95`                    |
| `failed_products`    | INTEGER   | Failed to process         | `5`                     |

**Possible `task_type` values:**

- `meta_optimization` - SEO meta tag optimization
- `content_rewriting` - Product description enhancement
- `keyword_analysis` - Keyword extraction and analysis
- `category_normalization` - Category standardization
- `tag_optimization` - Tag optimization and cleanup

**Possible `status` values:**

- `RUNNING` - Currently executing
- `COMPLETED` - Finished successfully
- `FAILED` - Encountered errors
- `CANCELLED` - Manually stopped

---

## Supporting Tables

### 4. Collections Table

**Product collections and groupings.**

```sql
CREATE TABLE collections (
    id INTEGER PRIMARY KEY,
    title TEXT,
    handle TEXT,
    body_html TEXT,
    image_url TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### 5. Categories Table

**Product category taxonomy.**

```sql
CREATE TABLE categories (
    id INTEGER PRIMARY KEY,
    name TEXT,
    parent_id INTEGER,
    gmc_id TEXT,
    created_at TIMESTAMP
);
```

### 6. Product-Category Relations

**Many-to-many relationship between products and categories.**

```sql
CREATE TABLE product_categories (
    id INTEGER PRIMARY KEY,
    product_id INTEGER,
    category_id INTEGER,
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (category_id) REFERENCES categories(id)
);
```

### 7. Tags Table

**Individual tag definitions.**

```sql
CREATE TABLE tags (
    id INTEGER PRIMARY KEY,
    name TEXT,
    category TEXT,
    created_at TIMESTAMP
);
```

### 8. Product-Tag Relations

**Many-to-many relationship between products and tags.**

```sql
CREATE TABLE product_tags (
    id INTEGER PRIMARY KEY,
    product_id INTEGER,
    tag_id INTEGER,
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (tag_id) REFERENCES tags(id)
);
```

---

## Full-Text Search Indexes

### Products FTS Table

**Optimized for full-text search operations.**

```sql
CREATE VIRTUAL TABLE products_fts USING fts5(
    title, body_html, tags, category,
    content=products, content_rowid=id
);
```

**Usage:**

```sql
-- Search in title and description
SELECT * FROM products_fts WHERE products_fts MATCH 'modern rug';

-- Search with rankings
SELECT *, rank FROM products_fts WHERE products_fts MATCH 'wool'
ORDER BY rank;
```

---

## Data Types and Constraints

### SQLite Data Types Used

| Type        | Description       | Example                 |
| ----------- | ----------------- | ----------------------- |
| `INTEGER`   | Whole numbers     | `172840065`             |
| `TEXT`      | Strings/JSON      | `"Product Title"`       |
| `REAL`      | Decimal numbers   | `0.85`                  |
| `TIMESTAMP` | ISO datetime      | `"2023-01-01T00:00:00"` |
| `BOOLEAN`   | True/false values | `0` or `1`              |

### Foreign Key Constraints

- `changes_log.product_id` → `products.id`
- `product_categories.product_id` → `products.id`
- `product_categories.category_id` → `categories.id`
- `product_tags.product_id` → `products.id`
- `product_tags.tag_id` → `tags.id`

### Check Constraints

```sql
-- LLM confidence must be between 0 and 1
CHECK (llm_confidence >= 0 AND llm_confidence <= 1)

-- Status must be valid enum value
CHECK (status IN ('RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED'))
```

---

## Database Relationships

### Entity Relationship Diagram

```
products (1) ──── (N) changes_log
products (N) ──── (N) categories (via product_categories)
products (N) ──── (N) tags (via product_tags)
categories (1) ──── (N) product_categories
tags (1) ──── (N) product_tags
```

### Cardinality

- **One product** can have **multiple categories**
- **One product** can have **multiple tags**
- **One product** can have **multiple changes**
- **One category** can have **multiple products**
- **One tag** can be assigned to **multiple products**

---

## Performance Considerations

### Indexing Strategy

1. **Primary Keys:** All tables have INTEGER PRIMARY KEY (fast lookups)
2. **Foreign Keys:** Indexed for join performance
3. **Search Columns:** Full-text search index on searchable content
4. **Timestamps:** Indexes on date columns for time-based queries

### Query Optimization

**Efficient Queries:**

```sql
-- Use indexed columns
SELECT * FROM products WHERE id = ?;

-- Use FTS for text search
SELECT * FROM products_fts WHERE products_fts MATCH ?;

-- Limit results appropriately
SELECT * FROM products ORDER BY created_at DESC LIMIT 100;
```

**Avoid:**

```sql
-- No indexes on these columns
SELECT * FROM products WHERE category = ?;

-- Large result sets
SELECT * FROM changes_log; -- Use LIMIT or WHERE clauses
```

---

## Data Migration

### Automatic Migrations

The application automatically handles schema updates:

1. **Column Addition:** New columns added with ALTER TABLE
2. **Table Creation:** New tables created if missing
3. **Index Creation:** Search indexes created as needed
4. **Data Transformation:** Existing data migrated to new formats

### Manual Migration (Advanced)

For complex schema changes:

```sql
-- Add new column
ALTER TABLE products ADD COLUMN new_field TEXT;

-- Create new index
CREATE INDEX idx_products_category ON products(category);

-- Update existing data
UPDATE products SET new_field = 'default_value';
```

---

## Backup and Recovery

### Backup Contents

A complete backup should include:

- `products.sqlite` - Main database file
- `config.yaml` - Application configuration
- Model files in `~/.ollama/models/` - AI models

### Recovery Process

1. **Restore database file**
2. **Verify schema compatibility**
3. **Test API endpoints**
4. **Check data integrity**

---

## Monitoring and Analytics

### Key Metrics

- **Product Count:** `SELECT COUNT(*) FROM products`
- **Review Queue Size:** `SELECT COUNT(*) FROM products WHERE llm_confidence < 0.7`
- **Recent Changes:** `SELECT COUNT(*) FROM changes_log WHERE created_at > datetime('now', '-24 hours')`
- **Pipeline Success Rate:** `SELECT COUNT(*) FROM pipeline_runs WHERE status = 'COMPLETED'`

### Performance Queries

```sql
-- Slow queries (for optimization)
SELECT sql FROM sqlite_master WHERE type = 'table';

-- Table sizes
SELECT name, COUNT(*) as rows FROM products GROUP BY name;

-- Index usage statistics
SELECT * FROM sqlite_stat1;
```

---

## Data Quality

### Validation Rules

1. **Product IDs:** Must be unique positive integers
2. **LLM Confidence:** Must be between 0.0 and 1.0
3. **Timestamps:** Must be valid ISO format
4. **JSON Fields:** Must be valid JSON strings
5. **Required Fields:** Title and body_html cannot be empty

### Data Cleaning

**Regular maintenance queries:**

```sql
-- Remove orphaned records
DELETE FROM changes_log WHERE product_id NOT IN (SELECT id FROM products);

-- Update timestamps
UPDATE products SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL;

-- Validate JSON fields
SELECT id FROM products WHERE json_valid(normalized_title) = 0;
```

---

## Future Enhancements

### Planned Schema Changes

1. **User Management:** Add users and permissions tables
2. **API Keys:** Secure API access with key management
3. **Analytics:** Usage tracking and performance metrics
4. **Caching:** Redis integration for high-performance scenarios
5. **Multi-tenancy:** Support for multiple data sources

### Scalability Considerations

For datasets larger than 100K products:

1. **Database Migration:** Consider PostgreSQL for better performance
2. **Read Replicas:** Separate read/write databases
3. **Caching Layer:** Redis for frequently accessed data
4. **Search Engine:** Elasticsearch for advanced search capabilities
5. **Archiving:** Move old data to cold storage
