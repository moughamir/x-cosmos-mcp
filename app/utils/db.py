import datetime
import json
import logging

import aiosqlite

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


async def get_products_batch(db_path: str, limit=10):
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.cursor()
        await cur.execute(
            "SELECT id, title, body_html, tags, category FROM products WHERE normalized_title IS NULL LIMIT ?",
            (limit,),
        )
        return await cur.fetchall()


async def get_products_for_review(db_path: str, limit=10):
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.cursor()
        await cur.execute(
            "SELECT id, title, normalized_title, body_html, normalized_body_html, llm_confidence FROM products WHERE llm_confidence < 0.7 LIMIT ?",
            (limit,),
        )
        return await cur.fetchall()


async def get_all_products(db_path: str):
    try:
        async with aiosqlite.connect(db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cur = await conn.cursor()
            await cur.execute(
                "SELECT id, title, llm_confidence, gmc_category_label FROM products"
            )
            return await cur.fetchall()
    except Exception as e:
        logging.error(f"Error in get_all_products: {e}", exc_info=True)
        raise


async def get_product_details(db_path: str, product_id: int):
    try:
        async with aiosqlite.connect(db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cur = await conn.cursor()
            await cur.execute("SELECT * FROM products WHERE id = ?", (product_id,))
            product = await cur.fetchone()
            await cur.execute(
                "SELECT * FROM changes_log WHERE product_id = ? ORDER BY created_at DESC",
                (product_id,),
            )
            changes = await cur.fetchall()
            return {"product": product, "changes": changes}
    except Exception as e:
        logging.error(
            f"Error in get_product_details for product ID {product_id}: {e}",
            exc_info=True,
        )
        raise


async def update_product_details(db_path: str, product_id: int, **kwargs):
    async with aiosqlite.connect(db_path) as conn:
        cur = await conn.cursor()
        set_clauses = []
        values = []
        for key, value in kwargs.items():
            set_clauses.append(f"{key} = ?")
            values.append(value)

        if not set_clauses:
            return  # No fields to update

        # Use parameterized query instead of string formatting
        sql = f"UPDATE products SET {', '.join(set_clauses)} WHERE id = ?"
        values.append(product_id)

        await cur.execute(sql, tuple(values))
        await conn.commit()


async def get_change_log(db_path: str, limit=100):
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.cursor()
        await cur.execute(
            "SELECT id, product_id, field, old, new, created_at, reviewed FROM changes_log ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return await cur.fetchall()


async def get_db_schema(db_path: str) -> dict:
    try:
        async with aiosqlite.connect(db_path) as conn:
            cur = await conn.cursor()
            await cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in await cur.fetchall()]

            schema = []  # Changed to list to match frontend expectation
            for table_name in tables:
                await cur.execute(f"PRAGMA table_info({table_name});")
                columns = await cur.fetchall()
                schema.append(
                    {
                        "name": table_name,
                        "columns": [
                            {"name": col[1], "type": col[2]} for col in columns
                        ],
                    }
                )
            return schema
    except Exception as e:
        logging.error(f"Error in get_db_schema: {e}", exc_info=True)
        raise


async def mark_as_reviewed(db_path: str, product_id: int):
    async with aiosqlite.connect(db_path) as conn:
        cur = await conn.cursor()
        await cur.execute(
            "UPDATE changes_log SET reviewed = 1 WHERE product_id = ?",
            (product_id,),
        )
        await conn.commit()


async def log_change(db_path: str, pid, field, old, new, source):
    async with aiosqlite.connect(db_path) as conn:
        cur = await conn.cursor()
        await cur.execute(
            """
            INSERT INTO changes_log (product_id, field, old, new, source, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                pid,
                field,
                json.dumps(old),
                json.dumps(new),
                source,
                datetime.datetime.now().isoformat(),
            ),
        )
        await conn.commit()


async def update_database_schema(db_path: str):
    """Update the database schema to include required columns if they don't exist."""
    async with aiosqlite.connect(db_path) as conn:
        cur = await conn.cursor()

        # Check if products table exists
        await cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY,
                title TEXT,
                body_html TEXT,
                tags TEXT,
                category TEXT,
                normalized_title TEXT,
                normalized_body_html TEXT,
                llm_confidence REAL DEFAULT 0.0,
                gmc_category_label TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Add any missing columns to products table
        await cur.execute("PRAGMA table_info(products)")
        columns = [col[1] for col in await cur.fetchall()]

        if "normalized_title" not in columns:
            await cur.execute("ALTER TABLE products ADD COLUMN normalized_title TEXT")
        if "normalized_body_html" not in columns:
            await cur.execute(
                "ALTER TABLE products ADD COLUMN normalized_body_html TEXT"
            )
        if "llm_confidence" not in columns:
            await cur.execute(
                "ALTER TABLE products ADD COLUMN llm_confidence REAL DEFAULT 0.0"
            )
        if "gmc_category_label" not in columns:
            await cur.execute("ALTER TABLE products ADD COLUMN gmc_category_label TEXT")
        if "created_at" not in columns:
            await cur.execute(
                "ALTER TABLE products ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            )
        if "updated_at" not in columns:
            await cur.execute(
                "ALTER TABLE products ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            )

        # Create changes_log table if it doesn't exist
        await cur.execute("""
            CREATE TABLE IF NOT EXISTS changes_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                field TEXT,
                old TEXT,
                new TEXT,
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed BOOLEAN DEFAULT 0,
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        """)

        await conn.commit()


async def create_pipeline_run(db_path: str, task_type: str, total_products: int) -> int:
    async with aiosqlite.connect(db_path) as conn:
        cur = await conn.cursor()
        now = datetime.datetime.now().isoformat()
        await cur.execute(
            """
            INSERT INTO pipeline_runs (task_type, status, start_time, total_products)
            VALUES (?, ?, ?, ?)
            """,
            (task_type, "RUNNING", now, total_products),
        )
        await conn.commit()
        return cur.lastrowid


async def update_pipeline_run(
    db_path: str,
    run_id: int,
    processed_products: int = None,
    failed_products: int = None,
    status: str = None,
):
    async with aiosqlite.connect(db_path) as conn:
        cur = await conn.cursor()
        set_clauses = []
        values = []
        if processed_products is not None:
            set_clauses.append("processed_products = ?")
            values.append(processed_products)
        if failed_products is not None:
            set_clauses.append("failed_products = ?")
            values.append(failed_products)
        if status is not None:
            set_clauses.append("status = ?")
            values.append(status)

        if not set_clauses:
            return  # No fields to update

        sql = f"UPDATE pipeline_runs SET {', '.join(set_clauses)} WHERE id = ?"
        values.append(run_id)

        await cur.execute(sql, tuple(values))
        await conn.commit()


async def complete_pipeline_run(
    db_path: str,
    run_id: int,
    status: str,
    processed_products: int,
    failed_products: int,
):
    async with aiosqlite.connect(db_path) as conn:
        cur = await conn.cursor()
        now = datetime.datetime.now().isoformat()
        await cur.execute(
            "UPDATE pipeline_runs SET status = ?, end_time = ?, processed_products = ?, failed_products = ? WHERE id = ?",
            (status, now, processed_products, failed_products, run_id),
        )
        await conn.commit()


async def get_pipeline_runs(db_path: str, limit: int = 100):
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.cursor()
        await cur.execute(
            "SELECT id, task_type, status, start_time, end_time, total_products, processed_products, failed_products FROM pipeline_runs ORDER BY start_time DESC LIMIT ?",
            (limit,),
        )
        return await cur.fetchall()
