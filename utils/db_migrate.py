"""
Database schema migration for MCP.
"""
import aiosqlite

async def migrate_schema(db_path: str):
    """Applies all necessary schema migrations to the database."""
    async with aiosqlite.connect(db_path) as conn:
        cur = await conn.cursor()

        # Version 1: Add normalized columns to products table
        await cur.execute("PRAGMA table_info(products)")
        existing_columns = {row[1] for row in await cur.fetchall()}
        
        columns_to_add = [
            ("normalized_title", "TEXT"),
            ("normalized_body_html", "TEXT"),
            ("normalized_tags_json", "TEXT"),
            ("gmc_category_label", "TEXT"),
            ("llm_model", "TEXT"),
            ("llm_confidence", "REAL"),
            ("normalized_category", "TEXT"),
            ("category_confidence", "REAL"),
        ]

        for col_name, col_type in columns_to_add:
            if col_name not in existing_columns:
                print(f"Adding column {col_name} to products table.")
                await cur.execute(f"ALTER TABLE products ADD COLUMN {col_name} {col_type}")
            else:
                print(f"Column {col_name} already exists in products table.")

        # Version 2: Create changes_log table
        """
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
        """
        )

        # Version 3: Create pipeline_runs table
        print("Ensuring pipeline_runs table exists.")
        await cur.execute("""
            CREATE TABLE IF NOT EXISTS pipeline_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_type TEXT NOT NULL,
                status TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                total_products INTEGER,
                processed_products INTEGER DEFAULT 0,
                failed_products INTEGER DEFAULT 0
            );
        """)

        await conn.commit()
        print("Database migration check complete.")
