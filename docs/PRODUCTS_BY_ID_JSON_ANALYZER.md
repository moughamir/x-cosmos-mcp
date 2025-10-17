# Complete Guide: JSON to PostgreSQL with FTS (Low-End Hardware Optimized)

This guide provides a complete workflow for analyzing JSON product data, normalizing it, and importing it into PostgreSQL with Full-Text Search capabilities. Optimized for low-end hardware running Arch Linux.

---

## 1. Data Analysis Commands (jq)

### Quick Structure Analysis
```bash
# Get all top-level keys across all files (streaming)
find . -name "*.json" -type f -exec jq -c 'keys' {} \; | jq -s 'add | unique'

# Check data types for each field
jq -r 'to_entries | .[] | "\(.key): \(.value | type)"' your_file.json

# Count total records (without loading all into memory)
find . -name "*.json" -type f | wc -l

# Get the total number of JSON files
find data/json/products_by_id -type f -name "*.json" | wc -l

# Check total file size before processing
du -sh *.json

# Sample unique values for specific fields
jq -r '.tags[]' *.json | sort -u | head -20
jq -r '.vendor' *.json | sort -u
```

### Array Size Analysis
```bash
# Find max/min array sizes for variants, images, options, tags
find . -name "*.json" -exec jq -c '{
  variants: (.variants | length),
  images: (.images | length),
  options: (.options | length),
  tags: (.tags | length)
}' {} \; | jq -s 'group_by(keys[0]) | map({(.[0] | keys[0]): (map(.[keys[0]]) | {min: min, max: max, avg: (add/length)})})'
```

### Data Quality Checks
```bash
# Sample data structure from first 5 files
find . -name "*.json" | head -5 | xargs jq -c '{
  id, title, vendor,
  variant_count: (.variants | length),
  image_count: (.images | length),
  tag_count: (.tags | length)
}'

# Find data anomalies (products with no variants)
find . -name "*.json" -exec jq -r 'select((.variants | length) == 0) | .id' {} \;

# Check for missing required fields
find . -name "*.json" -exec jq -r 'select(.title == null or .handle == null) | .id' {} \;
```

---

## 2. PostgreSQL Schema (schema.sql)

```sql
-- Main products table
CREATE TABLE products (
    id BIGINT PRIMARY KEY,
    title TEXT NOT NULL,
    handle TEXT UNIQUE NOT NULL,
    body_html TEXT,
    published_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE,
    vendor_id INTEGER REFERENCES vendors(id),
    product_type_id INTEGER REFERENCES product_types(id),

    -- FTS vector column
    search_vector tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(body_html, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(handle, '')), 'C')
    ) STORED
);

-- Vendors (normalized)
CREATE TABLE vendors (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

-- Product types (normalized)
CREATE TABLE product_types (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

-- Tags (normalized many-to-many)
CREATE TABLE tags (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE product_tags (
    product_id BIGINT REFERENCES products(id) ON DELETE CASCADE,
    tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (product_id, tag_id)
);

-- Variants
CREATE TABLE variants (
    id BIGINT PRIMARY KEY,
    product_id BIGINT REFERENCES products(id) ON DELETE CASCADE,
    title TEXT,
    option1 TEXT,
    option2 TEXT,
    option3 TEXT,
    sku TEXT,
    requires_shipping BOOLEAN,
    taxable BOOLEAN,
    featured_image_id BIGINT,
    available BOOLEAN,
    price NUMERIC(10, 2),
    compare_at_price NUMERIC(10, 2),
    grams INTEGER,
    position INTEGER,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Images
CREATE TABLE images (
    id BIGINT PRIMARY KEY,
    product_id BIGINT REFERENCES products(id) ON DELETE CASCADE,
    position INTEGER,
    src TEXT NOT NULL,
    width INTEGER,
    height INTEGER,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Variant images (many-to-many)
CREATE TABLE variant_images (
    variant_id BIGINT REFERENCES variants(id) ON DELETE CASCADE,
    image_id BIGINT REFERENCES images(id) ON DELETE CASCADE,
    PRIMARY KEY (variant_id, image_id)
);

-- Options
CREATE TABLE options (
    id SERIAL PRIMARY KEY,
    product_id BIGINT REFERENCES products(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    position INTEGER
);

CREATE TABLE option_values (
    id SERIAL PRIMARY KEY,
    option_id INTEGER REFERENCES options(id) ON DELETE CASCADE,
    value TEXT NOT NULL
);

-- Indexes for performance
CREATE INDEX idx_products_vendor ON products(vendor_id);
CREATE INDEX idx_products_type ON products(product_type_id);
CREATE INDEX idx_products_search ON products USING GIN(search_vector);
CREATE INDEX idx_products_handle ON products(handle);
CREATE INDEX idx_variants_product ON variants(product_id);
CREATE INDEX idx_variants_sku ON variants(sku);
CREATE INDEX idx_images_product ON images(product_id);
CREATE INDEX idx_product_tags_tag ON product_tags(tag_id);
CREATE INDEX idx_product_tags_product ON product_tags(product_id);

-- FTS search function
CREATE OR REPLACE FUNCTION search_products(search_query TEXT)
RETURNS TABLE (
    id BIGINT,
    title TEXT,
    rank REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id,
        p.title,
        ts_rank(p.search_vector, websearch_to_tsquery('english', search_query)) AS rank
    FROM products p
    WHERE p.search_vector @@ websearch_to_tsquery('english', search_query)
    ORDER BY rank DESC;
END;
$$ LANGUAGE plpgsql;
```

---

## 3. ETL Extraction Script (extract_data.py)

```python
#!/usr/bin/env python3
"""
extract_data.py
----------------------------------------
Multithreaded ETL script to extract data from JSON files and transform it into a
PostgreSQL-friendly TSV format.

Optimized for low-end hardware with features like:
- Multithreading
- Batch processing
- Caching for incremental runs
"""

import json
import hashlib
import concurrent.futures
from pathlib import Path
from tqdm import tqdm
import csv

# -------------------------------------
# Configuration
# -------------------------------------
JSON_DIR = Path("../data/json/products_by_id")
OUTPUT_DIR = Path("./psql_import")
CACHE_FILE = Path("processed_files.jsonl")
MAX_WORKERS = 4
BATCH_SIZE = 1000

# -------------------------------------
# Helper Functions
# -------------------------------------
def file_hash(path: Path) -> str:
    """Return a short, consistent hash of a file path."""
    return hashlib.md5(str(path).encode()).hexdigest()[:10]


def safe_load_json(file_path: Path):
    """Safely load a JSON file and return its content or None."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def load_cached_hashes() -> set:
    """Load cached file hashes from the cache file."""
    if not CACHE_FILE.exists():
        return set()
    with CACHE_FILE.open("r", encoding="utf-8") as f:
        return {json.loads(line).get("hash") for line in f}


def append_to_cache(path: Path):
    """Append a file's hash to the cache."""
    with CACHE_FILE.open("a", encoding="utf-8") as f:
        json.dump({"path": str(path), "hash": file_hash(path)}, f)
        f.write("\\n")


def process_file(file_path: Path):
    """
    Processes a single JSON file and extracts all relevant information.
    Returns a dictionary containing extracted data for different tables.
    """
    data = safe_load_json(file_path)
    if not data:
        return None

    product_id = data.get("id")

    # Product data
    product_data = {
        "id": product_id,
        "title": data.get("title"),
        "handle": data.get("handle"),
        "body_html": data.get("body_html", ""),
        "published_at": data.get("published_at"),
        "created_at": data.get("created_at"),
        "updated_at": data.get("updated_at"),
        "vendor": data.get("vendor"),
        "product_type": data.get("product_type"),
    }

    # Variants data
    variants_data = [
        {
            "id": v.get("id"),
            "product_id": product_id,
            "title": v.get("title"),
            "option1": v.get("option1"),
            "option2": v.get("option2"),
            "option3": v.get("option3"),
            "sku": v.get("sku"),
            "requires_shipping": v.get("requires_shipping"),
            "taxable": v.get("taxable"),
            "featured_image_id": v.get("featured_image", {}).get("id") if v.get("featured_image") else None,
            "available": v.get("available"),
            "price": v.get("price"),
            "compare_at_price": v.get("compare_at_price"),
            "grams": v.get("grams"),
            "position": v.get("position"),
            "created_at": v.get("created_at"),
            "updated_at": v.get("updated_at"),
        }
        for v in data.get("variants", [])
    ]

    # Images data
    images_data = [
        {
            "id": img.get("id"),
            "product_id": product_id,
            "position": img.get("position"),
            "src": img.get("src"),
            "width": img.get("width"),
            "height": img.get("height"),
            "created_at": img.get("created_at"),
            "updated_at": img.get("updated_at"),
        }
        for img in data.get("images", [])
    ]

    # Variant-Image relationships
    variant_images_data = [
        {"variant_id": variant_id, "image_id": image["id"]}
        for image in data.get("images", [])
        for variant_id in image.get("variant_ids", [])
    ]

    # Tags
    tags_data = data.get("tags", [])

    # Product-Tag relationships
    product_tags_data = [{"product_id": product_id, "tag": tag} for tag in tags_data]

    # Options
    options_data = [
        {
            "product_id": product_id,
            "name": opt.get("name"),
            "position": opt.get("position"),
        }
        for opt in data.get("options", [])
    ]

    # Option Values
    option_values_data = [
        {
            "product_id": product_id,
            "option_position": opt.get("position"),
            "option_name": opt.get("name"),
            "value": value,
        }
        for opt in data.get("options", [])
        for value in opt.get("values", [])
    ]


    return {
        "products": [product_data],
        "variants": variants_data,
        "images": images_data,
        "variant_images": variant_images_data,
        "tags": tags_data,
        "product_tags": product_tags_data,
        "vendors": [data.get("vendor")] if data.get("vendor") else [],
        "product_types": [data.get("product_type")] if data.get("product_type") else [],
        "options": options_data,
        "option_values": option_values_data,
    }


def write_batch_to_tsv(output_dir: Path, batch_data: dict):
    """Writes a batch of data to the corresponding TSV files."""
    for key, data in batch_data.items():
        if not data:
            continue

        file_path = output_dir / f"{key}.tsv"
        # Use 'a' mode to append to the file
        with file_path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter="\\t")
            for item in data:
                if isinstance(item, dict):
                    writer.writerow(item.values())
                else:
                    writer.writerow([item])


# -------------------------------------
# Main Processing Logic
# -------------------------------------
def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    json_files = list(JSON_DIR.rglob("*.json"))
    if not json_files:
        print(f"❌ No JSON files found in {JSON_DIR}")
        return

    cached_hashes = load_cached_hashes()
    to_process = [f for f in json_files if file_hash(f) not in cached_hashes]

    print(f"✅ Loaded {len(cached_hashes)} cached file hashes.")
    print(f"🔍 Found {len(to_process)} new files to process.")

    batch_data = {
        "products": [],
        "variants": [],
        "images": [],
        "variant_images": [],
        "tags": set(),
        "product_tags": [],
        "vendors": set(),
        "product_types": set(),
        "options": [],
        "option_values": [],
    }

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_file, path): path for path in to_process}

        for future in tqdm(
            concurrent.futures.as_completed(futures),
            total=len(futures),
            desc="Processing Files",
            unit="file",
        ):
            path = futures[future]
            try:
                result = future.result()
                if result:
                    for key, data in result.items():
                        if isinstance(batch_data[key], list):
                            batch_data[key].extend(data)
                        elif isinstance(batch_data[key], set):
                            batch_data[key].update(data)

                    if len(batch_data["products"]) >= BATCH_SIZE:
                        write_batch_to_tsv(OUTPUT_DIR, batch_data)
                        # Clear lists after writing
                        for key in batch_data:
                            if isinstance(batch_data[key], list):
                                batch_data[key].clear()

                    append_to_cache(path)

            except Exception as e:
                print(f"⚠️ Error processing {path}: {e}")

    # Write any remaining data in the batch
    write_batch_to_tsv(OUTPUT_DIR, batch_data)

    # Process unique sets (vendors, product_types, tags) and write to TSV
    for key in ["vendors", "product_types", "tags"]:
        with (OUTPUT_DIR / f"{key}.tsv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter="\\t")
            for i, item in enumerate(sorted(list(batch_data[key])), 1):
                writer.writerow([i, item])


    print("\\n✅ ETL process completed successfully!")
    print(f"💾 Data extracted to: {OUTPUT_DIR}")


# -------------------------------------
# Entry Point
# -------------------------------------
if __name__ == "__main__":
    main()

```

---

## 4. PostgreSQL Import Script (import_to_postgres.sh)

```bash
#!/bin/bash
# Import TSV files into PostgreSQL
# Usage: ./import_to_postgres.sh [database_name]

set -e

DB_NAME="${1:-your_database}"
IMPORT_DIR="./psql_import"

echo "Importing data into PostgreSQL database: $DB_NAME"

# Function to execute SQL
psql_exec() {
    psql -d "$DB_NAME" -c "$1"
}

# 1. Import vendors
echo "Importing vendors..."
psql_exec "COPY vendors(id, name) FROM STDIN WITH (FORMAT csv, DELIMITER E'\t', NULL '')" < "$IMPORT_DIR/vendors.tsv"

# 2. Import product types
echo "Importing product types..."
psql_exec "COPY product_types(id, name) FROM STDIN WITH (FORMAT csv, DELIMITER E'\t', NULL '')" < "$IMPORT_DIR/product_types.tsv"

# 3. Import tags
echo "Importing tags..."
psql_exec "COPY tags(id, name) FROM STDIN WITH (FORMAT csv, DELIMITER E'\t', NULL '')" < "$IMPORT_DIR/tags.tsv"

# 4. Import products (with vendor_id and product_type_id lookup)
echo "Importing products..."
psql -d "$DB_NAME" <<EOF
CREATE TEMP TABLE products_staging (
    id BIGINT,
    title TEXT,
    handle TEXT,
    body_html TEXT,
    published_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE,
    vendor_name TEXT,
    product_type_name TEXT
);

\COPY products_staging FROM '$IMPORT_DIR/products.tsv' WITH (FORMAT csv, DELIMITER E'\t', NULL '');

INSERT INTO products (id, title, handle, body_html, published_at, created_at, updated_at, vendor_id, product_type_id)
SELECT
    ps.id,
    ps.title,
    ps.handle,
    ps.body_html,
    ps.published_at,
    ps.created_at,
    ps.updated_at,
    v.id,
    pt.id
FROM products_staging ps
LEFT JOIN vendors v ON v.name = ps.vendor_name
LEFT JOIN product_types pt ON pt.name = ps.product_type_name
ON CONFLICT (id) DO NOTHING;

DROP TABLE products_staging;
EOF

# 5. Import variants
echo "Importing variants..."
psql -d "$DB_NAME" <<EOF
\COPY variants(id, product_id, title, option1, option2, option3, sku, requires_shipping, taxable, featured_image_id, available, price, compare_at_price, grams, position, created_at, updated_at) FROM '$IMPORT_DIR/variants.tsv' WITH (FORMAT csv, DELIMITER E'\t', NULL '');
EOF

# 6. Import images
echo "Importing images..."
psql -d "$DB_NAME" <<EOF
\COPY images(id, product_id, position, src, width, height, created_at, updated_at) FROM '$IMPORT_DIR/images.tsv' WITH (FORMAT csv, DELIMITER E'\t', NULL '');
EOF

# 7. Import variant-image relationships
echo "Importing variant-image relationships..."
if [ -s "$IMPORT_DIR/variant_images.tsv" ]; then
    psql -d "$DB_NAME" <<EOF
\COPY variant_images(variant_id, image_id) FROM '$IMPORT_DIR/variant_images.tsv' WITH (FORMAT csv, DELIMITER E'\t', NULL '');
EOF
fi

# 8. Import product-tag relationships
echo "Importing product-tag relationships..."
psql -d "$DB_NAME" <<EOF
CREATE TEMP TABLE product_tags_staging (
    product_id BIGINT,
    tag_name TEXT
);

\COPY product_tags_staging FROM '$IMPORT_DIR/product_tags.tsv' WITH (FORMAT csv, DELIMITER E'\t', NULL '');

INSERT INTO product_tags (product_id, tag_id)
SELECT DISTINCT pts.product_id, t.id
FROM product_tags_staging pts
INNER JOIN tags t ON t.name = pts.tag_name
ON CONFLICT DO NOTHING;

DROP TABLE product_tags_staging;
EOF

# 9. Import options and values
echo "Importing options..."
psql -d "$DB_NAME" <<EOF
CREATE TEMP TABLE options_staging (
    product_id BIGINT,
    name TEXT,
    position INTEGER
);

CREATE TEMP TABLE option_values_staging (
    product_id BIGINT,
    option_position INTEGER,
    option_name TEXT,
    value TEXT
);

\COPY options_staging FROM '$IMPORT_DIR/options.tsv' WITH (FORMAT csv, DELIMITER E'\t', NULL '');
\COPY option_values_staging FROM '$IMPORT_DIR/option_values.tsv' WITH (FORMAT csv, DELIMITER E'\t', NULL '');

-- Insert options
INSERT INTO options (product_id, name, position)
SELECT DISTINCT product_id, name, position
FROM options_staging
ON CONFLICT DO NOTHING;

-- Insert option values
INSERT INTO option_values (option_id, value)
SELECT DISTINCT o.id, ovs.value
FROM option_values_staging ovs
INNER JOIN options o ON o.product_id = ovs.product_id AND o.position = ovs.option_position
ON CONFLICT DO NOTHING;

DROP TABLE options_staging;
DROP TABLE option_values_staging;
EOF

# 10. Update sequences
echo "Updating sequences..."
psql -d "$DB_NAME" <<EOF
SELECT setval('vendors_id_seq', (SELECT MAX(id) FROM vendors));
SELECT setval('product_types_id_seq', (SELECT MAX(id) FROM product_types));
SELECT setval('tags_id_seq', (SELECT MAX(id) FROM tags));
SELECT setval('options_id_seq', (SELECT MAX(id) FROM options));
SELECT setval('option_values_id_seq', (SELECT MAX(id) FROM option_values));
EOF

# 11. Analyze tables for query optimization
echo "Analyzing tables..."
psql_exec "ANALYZE products; ANALYZE variants; ANALYZE images; ANALYZE tags; ANALYZE product_tags;"

echo ""
echo "Import complete!"
echo "Run some test queries:"
echo "  psql -d $DB_NAME -c \"SELECT COUNT(*) FROM products;\""
echo "  psql -d $DB_NAME -c \"SELECT * FROM search_products('sideboard');\""
```

---

## 5. Complete Workflow

```bash
# Step 1: Analyze your data first (optional but recommended)
./scripts/analyze_json_keys.py

# Step 2: Make scripts executable
chmod +x scripts/extract_data.py scripts/import_to_postgres.sh

# Step 3: Run ETL extraction (memory-efficient, processes one file at a time)
./scripts/extract_data.py

# Step 4: Create database and apply schema
createdb products_db
psql -d products_db -f scripts/schema.sql

# Step 5: Import data
./scripts/import_to_postgres.sh products_db

# Step 6: Test the database
psql -d products_db -c "SELECT COUNT(*) FROM products;"
psql -d products_db -c "SELECT * FROM search_products('natural sideboard');"
```

---

## 6. Performance Optimization for Low-End Hardware

### Process Large Datasets in Batches
```bash
# Split files into batches of 1000
ls *.json | split -l 1000 - batch_

# Process each batch
for batch in batch_*; do
    cat $batch | xargs -I {} jq '...' {} >> output.tsv
done
```

### Disable Indexes During Import (Faster)
```sql
-- Before import
DROP INDEX idx_products_search;
DROP INDEX idx_products_vendor;
DROP INDEX idx_variants_product;

-- ... do imports ...

-- After import
CREATE INDEX idx_products_search ON products USING GIN(search_vector);
CREATE INDEX idx_products_vendor ON products(vendor_id);
CREATE INDEX idx_variants_product ON variants(product_id);
```

### Use UNLOGGED Tables (Faster, Less Safe)
```sql
-- Before import
ALTER TABLE products SET UNLOGGED;
ALTER TABLE variants SET UNLOGGED;
ALTER TABLE images SET UNLOGGED;

-- ... do imports ...

-- After import (make durable again)
ALTER TABLE products SET LOGGED;
ALTER TABLE variants SET LOGGED;
ALTER TABLE images SET LOGGED;
```

### PostgreSQL Configuration for Import
Add to `postgresql.conf` during import:
```
maintenance_work_mem = 256MB
shared_buffers = 512MB
work_mem = 16MB
checkpoint_timeout = 30min
max_wal_size = 2GB
```

---

## 7. Full-Text Search Examples

### Simple Search
```sql
SELECT * FROM search_products('wooden sideboard');
```

### Advanced Search with Filters
```sql
SELECT p.*, ts_rank(p.search_vector, query) as rank
FROM products p, websearch_to_tsquery('english', 'modern furniture') query
WHERE p.search_vector @@ query
  AND p.vendor_id = 1
ORDER BY rank DESC
LIMIT 10;
```

### Search with Highlighting
```sql
SELECT
    p.title,
    ts_headline('english', p.body_html, query, 'MaxWords=50') as snippet
FROM products p,
     websearch_to_tsquery('english', 'natural wood') query
WHERE p.search_vector @@ query
ORDER BY ts_rank(p.search_vector, query) DESC;
```

### Complex Query with Joins
```sql
SELECT
    p.id,
    p.title,
    v.name as vendor,
    array_agg(DISTINCT t.name) as tags,
    COUNT(DISTINCT var.id) as variant_count,
    ts_rank(p.search_vector, query) as rank
FROM products p
CROSS JOIN websearch_to_tsquery('english', 'sideboard natural') query
LEFT JOIN vendors v ON v.id = p.vendor_id
LEFT JOIN product_tags pt ON pt.product_id = p.id
LEFT JOIN tags t ON t.id = pt.tag_id
LEFT JOIN variants var ON var.product_id = p.id
WHERE p.search_vector @@ query
GROUP BY p.id, p.title, v.name, query
ORDER BY rank DESC
LIMIT 20;
```

### Phrase Search
```sql
-- Search for exact phrase
SELECT * FROM products
WHERE search_vector @@ phraseto_tsquery('english', 'natural sideboard');
```

### Boolean Search
```sql
-- Must have 'wood', might have 'natural', must not have 'plastic'
SELECT * FROM products
WHERE search_vector @@ to_tsquery('english', 'wood & natural & !plastic');
```

---

## 8. Useful Queries

### Get Product with All Relations
```sql
SELECT
    p.*,
    v.name as vendor,
    pt.name as product_type,
    json_agg(DISTINCT jsonb_build_object('id', var.id, 'price', var.price)) as variants,
    json_agg(DISTINCT jsonb_build_object('id', img.id, 'src', img.src)) as images,
    array_agg(DISTINCT t.name) as tags
FROM products p
LEFT JOIN vendors v ON v.id = p.vendor_id
LEFT JOIN product_types pt ON pt.id = p.product_type_id
LEFT JOIN variants var ON var.product_id = p.id
LEFT JOIN images img ON img.product_id = p.id
LEFT JOIN product_tags ptag ON ptag.product_id = p.id
LEFT JOIN tags t ON t.id = ptag.tag_id
WHERE p.id = 9598585110775
GROUP BY p.id, v.name, pt.name;
```

### Products by Price Range
```sql
SELECT p.title, MIN(v.price) as min_price, MAX(v.price) as max_price
FROM products p
JOIN variants v ON v.product_id = p.id
GROUP BY p.id, p.title
HAVING MIN(v.price) >= 1000 AND MAX(v.price) <= 2000
ORDER BY min_price;
```

### Most Popular Tags
```sql
SELECT t.name, COUNT(*) as product_count
FROM tags t
JOIN product_tags pt ON pt.tag_id = t.id
GROUP BY t.id, t.name
ORDER BY product_count DESC
LIMIT 20;
```

---

## 9. Troubleshooting

### Memory Issues During jq Processing
```bash
# Process even smaller batches
find . -name "*.json" | head -100 | xargs ...

# Use streaming parser
jq -c '.' large_file.json | while read -r line; do
    echo "$line" | jq -r '...'
done
```

### Import Fails on Large Text Fields
```sql
-- Increase client encoding buffer
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
```

### Slow FTS Queries
```sql
-- Check if index is being used
EXPLAIN ANALYZE
SELECT * FROM search_products('test');

-- Update statistics
ANALYZE products;

-- Consider using different FTS configuration
ALTER TABLE products
ALTER COLUMN search_vector TYPE tsvector
USING to_tsvector('simple', coalesce(title, ''));
```

---

## 10. Data Validation Queries

```sql
-- Products without variants
SELECT COUNT(*) FROM products p
WHERE NOT EXISTS (SELECT 1 FROM variants v WHERE v.product_id = p.id);

-- Products without images
SELECT COUNT(*) FROM products p
WHERE NOT EXISTS (SELECT 1 FROM images i WHERE i.product_id = p.id);

-- Orphaned variants
SELECT COUNT(*) FROM variants v
WHERE NOT EXISTS (SELECT 1 FROM products p WHERE p.id = v.product_id);

-- Products with duplicate handles
SELECT handle, COUNT(*)
FROM products
GROUP BY handle
HAVING COUNT(*) > 1;
```

---

This complete guide provides everything needed to transform JSON product data into a normalized, searchable PostgreSQL database optimized for low-resource environments.
