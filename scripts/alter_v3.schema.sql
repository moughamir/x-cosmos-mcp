--
-- OptimusV3: ALTER Schema Script (v3)
-- This script is idempotent and can be run safely on an existing database.
-- Fixes default value casting during `tags` column conversion.
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

-- 2. Alter Products Table
DO $$
DECLARE
    col_type TEXT;
BEGIN
    -- Add columns if they don't exist
    ALTER TABLE public.products ADD COLUMN IF NOT EXISTS handle TEXT;
    ALTER TABLE public.products ADD COLUMN IF NOT EXISTS meta JSONB;
    ALTER TABLE public.products ADD COLUMN IF NOT EXISTS seo_keywords JSONB;
    ALTER TABLE public.products ADD COLUMN IF NOT EXISTS primary_keywords JSONB;
    ALTER TABLE public.products ADD COLUMN IF NOT EXISTS long_tail_keywords JSONB;
    ALTER TABLE public.products ADD COLUMN IF NOT EXISTS competitor_terms JSONB;
    ALTER TABLE public.products ADD COLUMN IF NOT EXISTS keyword_difficulty TEXT;
    ALTER TABLE public.products ADD COLUMN IF NOT EXISTS content_score NUMERIC(5, 2);
    ALTER TABLE public.products ADD COLUMN IF NOT EXISTS embedding vector(768);
    ALTER TABLE public.products ADD COLUMN IF NOT EXISTS published_at TIMESTAMPTZ;

    -- Check current data type of the 'tags' column
    SELECT pg_catalog.format_type(atttypid, atttypmod) INTO col_type
    FROM pg_catalog.pg_attribute
    WHERE attrelid = 'public.products'::regclass
    AND attname = 'tags' AND attnum > 0 AND NOT attisdropped;

    -- If the type is not already text[], alter it carefully.
    IF col_type IS NOT NULL AND col_type != 'text[]' THEN
        -- 1. Drop the old default value if it exists.
        ALTER TABLE public.products ALTER COLUMN tags DROP DEFAULT;
        -- 2. Alter the column type using a conversion.
        ALTER TABLE public.products ALTER COLUMN tags TYPE TEXT[] USING string_to_array(tags::text, ',');
        -- 3. Set a new, correct default for the array type.
        ALTER TABLE public.products ALTER COLUMN tags SET DEFAULT '{}';
    ELSIF col_type IS NULL THEN
        -- If column doesn't exist at all, add it with the correct type and default.
        ALTER TABLE public.products ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{}';
    END IF;

    -- Ensure other types are correct
    ALTER TABLE public.products ALTER COLUMN updated_at TYPE TIMESTAMPTZ;
    ALTER TABLE public.products ALTER COLUMN created_at TYPE TIMESTAMPTZ;

    -- Ensure product_id is unique for ON CONFLICT
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'products_product_id_key' AND conrelid = 'public.products'::regclass) THEN
        ALTER TABLE public.products ADD CONSTRAINT products_product_id_key UNIQUE (product_id);
    END IF;
END;
$$;

-- 3. Attach Trigger for products.updated_at
DROP TRIGGER IF EXISTS on_products_update ON public.products;
CREATE TRIGGER on_products_update
BEFORE UPDATE ON public.products
FOR EACH ROW
EXECUTE PROCEDURE public.handle_updated_at();

-- 4. Create and Alter Product Variants Table
CREATE TABLE IF NOT EXISTS public.product_variants (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT, -- Will add constraint below
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
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_variants_to_products' AND conrelid = 'public.product_variants'::regclass) THEN
        ALTER TABLE public.product_variants ADD CONSTRAINT fk_variants_to_products FOREIGN KEY (product_id) REFERENCES public.products(id) ON DELETE CASCADE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'product_variants_product_id_source_variant_id_key' AND conrelid = 'public.product_variants'::regclass) THEN
        ALTER TABLE public.product_variants ADD CONSTRAINT product_variants_product_id_source_variant_id_key UNIQUE (product_id, source_variant_id);
    END IF;
END;
$$;

-- 5. Create and Alter Product Images Table
CREATE TABLE IF NOT EXISTS public.product_images (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT, -- Will add constraint below
    source_image_id TEXT,
    url TEXT,
    alt_text TEXT,
    position INT,
    metadata JSONB,
    created_at TIMESTAMPTZ
);
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_images_to_products' AND conrelid = 'public.product_images'::regclass) THEN
        ALTER TABLE public.product_images ADD CONSTRAINT fk_images_to_products FOREIGN KEY (product_id) REFERENCES public.products(id) ON DELETE CASCADE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'product_images_product_id_source_image_id_key' AND conrelid = 'public.product_images'::regclass) THEN
        ALTER TABLE public.product_images ADD CONSTRAINT product_images_product_id_source_image_id_key UNIQUE (product_id, source_image_id);
    END IF;
END;
$$;

-- 6. Create and Alter Product Options Table
CREATE TABLE IF NOT EXISTS public.product_options (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT, -- Will add constraint below
    name TEXT,
    position INT,
    "values" TEXT[]
);
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_options_to_products' AND conrelid = 'public.product_options'::regclass) THEN
        ALTER TABLE public.product_options ADD CONSTRAINT fk_options_to_products FOREIGN KEY (product_id) REFERENCES public.products(id) ON DELETE CASCADE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'product_options_product_id_name_key' AND conrelid = 'public.product_options'::regclass) THEN
        ALTER TABLE public.product_options ADD CONSTRAINT product_options_product_id_name_key UNIQUE (product_id, name);
    END IF;
END;
$$;

-- 7. Add Indexes for performance
CREATE INDEX IF NOT EXISTS idx_products_product_id ON public.products(product_id);
CREATE INDEX IF NOT EXISTS idx_variants_product_id ON public.product_variants(product_id);
CREATE INDEX IF NOT EXISTS idx_images_product_id ON public.product_images(product_id);
CREATE INDEX IF NOT EXISTS idx_options_product_id ON public.product_options(product_id);
