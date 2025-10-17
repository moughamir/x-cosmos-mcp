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
