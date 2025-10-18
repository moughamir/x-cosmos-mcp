--
-- OptimusV3 Supabase Schema
--

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "vector";

-- 1. Function to automatically update 'updated_at' timestamps
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 2. Products Table (Main table)
CREATE TABLE IF NOT EXISTS public.products (
    id BIGSERIAL PRIMARY KEY,
    product_id TEXT UNIQUE NOT NULL,
    handle TEXT,
    title TEXT,
    description TEXT,
    product_type TEXT,
    tags TEXT[],
    meta JSONB,
    seo_keywords JSONB,
    primary_keywords JSONB,
    long_tail_keywords JSONB,
    competitor_terms JSONB,
    keyword_difficulty TEXT,
    content_score NUMERIC(5, 2),
    embedding vector(768),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    published_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Trigger for products.updated_at
DROP TRIGGER IF EXISTS on_products_update ON public.products;
CREATE TRIGGER on_products_update
BEFORE UPDATE ON public.products
FOR EACH ROW
EXECUTE PROCEDURE public.handle_updated_at();

-- 4. Product Variants Table
CREATE TABLE IF NOT EXISTS public.product_variants (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL REFERENCES public.products(id) ON DELETE CASCADE,
    source_variant_id TEXT,
    title TEXT,
    sku TEXT,
    price NUMERIC(10, 2),
    compare_at_price NUMERIC(10, 2),
    inventory_quantity INT,
    available BOOLEAN,
    grams INT,
    options JSONB,
    metadata JSONB,
    created_at TIMESTAMPTZ
);
-- Add constraint for UPSERT
ALTER TABLE public.product_variants
ADD CONSTRAINT product_variants_product_id_source_variant_id_key UNIQUE (product_id, source_variant_id);

-- 5. Product Images Table
CREATE TABLE IF NOT EXISTS public.product_images (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL REFERENCES public.products(id) ON DELETE CASCADE,
    source_image_id TEXT,
    url TEXT,
    alt_text TEXT,
    position INT,
    metadata JSONB,
    created_at TIMESTAMPTZ
);
-- Add constraint for UPSERT
ALTER TABLE public.product_images
ADD CONSTRAINT product_images_product_id_source_image_id_key UNIQUE (product_id, source_image_id);

-- 6. Product Options Table
CREATE TABLE IF NOT EXISTS public.product_options (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL REFERENCES public.products(id) ON DELETE CASCADE,
    name TEXT,
    position INT,
    "values" TEXT[]
);
-- Add constraint for UPSERT (already created, but included for completeness)
ALTER TABLE public.product_options
ADD CONSTRAINT product_options_product_id_name_key UNIQUE (product_id, name);

-- Add Indexes for performance
CREATE INDEX IF NOT EXISTS idx_products_product_id ON public.products(product_id);
CREATE INDEX IF NOT EXISTS idx_variants_product_id ON public.product_variants(product_id);
CREATE INDEX IF NOT EXISTS idx_images_product_id ON public.product_images(product_id);
CREATE INDEX IF NOT EXISTS idx_options_product_id ON public.product_options(product_id);
