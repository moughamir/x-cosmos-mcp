CREATE TABLE IF NOT EXISTS changes_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    field TEXT,
    old TEXT,
    new TEXT,
    created_at TEXT,
    source TEXT,
    reviewed INTEGER DEFAULT 0
);
