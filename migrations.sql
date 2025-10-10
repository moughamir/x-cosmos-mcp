ALTER TABLE products
ADD COLUMN normalized_category TEXT;

ALTER TABLE products
ADD COLUMN category_confidence REAL;

