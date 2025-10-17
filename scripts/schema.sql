-- This is the single, unified schema for the project.

-- Vendors (normalized)
CREATE TABLE IF NOT EXISTS vendors (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

-- Product types (normalized)
CREATE TABLE IF NOT EXISTS product_types (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

-- Tags (normalized many-to-many)
CREATE TABLE IF NOT EXISTS tags (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

-- Main products table
CREATE TABLE IF NOT EXISTS products (
    id BIGINT PRIMARY KEY,
    title TEXT,
    handle TEXT UNIQUE NOT NULL,
    body_html TEXT,
    published_at TIMESTAMP WITH TIME ZONE,
    vendor_id INTEGER REFERENCES vendors(id),
    product_type_id INTEGER REFERENCES product_types(id),
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE,

    -- Columns from the application schema
    category TEXT,
    normalized_title TEXT,
    normalized_body_html TEXT,
    normalized_tags_json TEXT,
    gmc_category_label TEXT,
    llm_model TEXT,
    llm_confidence DECIMAL(3,2) DEFAULT 0.0,
    normalized_category TEXT,
    category_confidence DECIMAL(3,2),

    -- FTS vector column for search
    search_vector tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(body_html, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(handle, '')), 'C')
    ) STORED
);

-- Junction table for product-tag many-to-many relationship
CREATE TABLE IF NOT EXISTS product_tags (
    product_id BIGINT REFERENCES products(id) ON DELETE CASCADE,
    tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (product_id, tag_id)
);

-- Variants table
CREATE TABLE IF NOT EXISTS variants (
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

-- Images table
CREATE TABLE IF NOT EXISTS images (
    id BIGINT PRIMARY KEY,
    product_id BIGINT REFERENCES products(id) ON DELETE CASCADE,
    position INTEGER,
    src TEXT NOT NULL,
    width INTEGER,
    height INTEGER,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Junction table for variant-image many-to-many relationship
CREATE TABLE IF NOT EXISTS variant_images (
    variant_id BIGINT REFERENCES variants(id) ON DELETE CASCADE,
    image_id BIGINT REFERENCES images(id) ON DELETE CASCADE,
    PRIMARY KEY (variant_id, image_id)
);

-- Options table
CREATE TABLE IF NOT EXISTS options (
    id SERIAL PRIMARY KEY,
    product_id BIGINT REFERENCES products(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    position INTEGER
);

-- Option values table
CREATE TABLE IF NOT EXISTS option_values (
    id SERIAL PRIMARY KEY,
    option_id INTEGER REFERENCES options(id) ON DELETE CASCADE,
    value TEXT NOT NULL
);

-- Application table for logging changes
CREATE TABLE IF NOT EXISTS changes_log (
    id SERIAL PRIMARY KEY,
    product_id BIGINT REFERENCES products(id) ON DELETE CASCADE,
    field TEXT,
    old TEXT,
    new TEXT,
    source TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed BOOLEAN DEFAULT FALSE
);

-- Application table for tracking pipeline runs
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id SERIAL PRIMARY KEY,
    task_type TEXT,
    status TEXT,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    total_products INTEGER,
    processed_products INTEGER DEFAULT 0,
    failed_products INTEGER DEFAULT 0
);


-- === INDEXES ===

-- Indexes for performance on foreign keys and common lookups
CREATE INDEX IF NOT EXISTS idx_products_vendor ON products(vendor_id);
CREATE INDEX IF NOT EXISTS idx_products_type ON products(product_type_id);
CREATE INDEX IF NOT EXISTS idx_products_handle ON products(handle);
CREATE INDEX IF NOT EXISTS idx_variants_product ON variants(product_id);
CREATE INDEX IF NOT EXISTS idx_variants_sku ON variants(sku);
CREATE INDEX IF NOT EXISTS idx_images_product ON images(product_id);
CREATE INDEX IF NOT EXISTS idx_product_tags_tag ON product_tags(tag_id);
CREATE INDEX IF NOT EXISTS idx_product_tags_product ON product_tags(product_id);

-- Indexes for application-specific queries
CREATE INDEX IF NOT EXISTS idx_products_llm_confidence ON products(llm_confidence);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_changes_log_product_id ON changes_log(product_id);
CREATE INDEX IF NOT EXISTS idx_changes_log_created_at ON changes_log(created_at);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status ON pipeline_runs(status);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_start_time ON pipeline_runs(start_time);

-- Full-text search index
CREATE INDEX IF NOT EXISTS idx_products_fts ON products USING GIN (search_vector);


-- === FUNCTIONS ===

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
