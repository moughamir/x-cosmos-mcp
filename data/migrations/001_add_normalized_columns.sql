ALTER TABLE products ADD COLUMN normalized_title TEXT;
ALTER TABLE products ADD COLUMN normalized_body_html TEXT;
ALTER TABLE products ADD COLUMN normalized_tags_json TEXT;
ALTER TABLE products ADD COLUMN gmc_category_label TEXT;
ALTER TABLE products ADD COLUMN llm_model TEXT;
ALTER TABLE products ADD COLUMN llm_confidence REAL;
