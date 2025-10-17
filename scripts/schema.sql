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
