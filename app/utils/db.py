"""
PostgreSQL database utilities for MCP Admin
Uses asyncpg for high-performance async database operations
"""

import datetime
import json
import logging
import os
from typing import Any, Dict, List, Optional

import asyncpg
from functools import wraps

# Global connection pool for better performance
_pool: Optional[asyncpg.Pool] = None


def db_connection_decorator(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        conn = None
        try:
            conn = await get_db_connection()
            # Pass the connection as the first argument to the decorated function
            return await func(conn, *args, **kwargs)
        except Exception as e:
            logging.error(f"Error in {func.__name__}: {e}")
            raise
        finally:
            if conn:
                await release_db_connection(conn)
    return wrapper


async def init_db_pool():
    """Initialize PostgreSQL connection pool"""
    global _pool
    if _pool is None:
        logging.info("Initializing PostgreSQL connection pool...")
        _pool = await asyncpg.create_pool(
            user=os.getenv("POSTGRES_USER", "mcp_user"),
            password=os.getenv("POSTGRES_PASSWORD", "mcp_password"),
            host=os.getenv("POSTGRES_HOST", "postgres"),
            port=int(os.getenv("POSTGRES_PORT", 5432)),
            database=os.getenv("POSTGRES_DB", "mcp_db"),
            min_size=1,
            max_size=20,  # Increased for better concurrency
            timeout=60,
            command_timeout=60,
        )
        logging.info("PostgreSQL connection pool initialized.")
    if conn:
        await release_db_connection(conn)


async def close_db_pool():
    """Close PostgreSQL connection pool"""
    global _pool
    if _pool:
        logging.info("Closing PostgreSQL connection pool...")
        await _pool.close()
        _pool = None
        logging.info("PostgreSQL connection pool closed.")


async def get_db_connection():
    """Get database connection from pool"""
    if _pool is None:
        await init_db_pool()
    return await _pool.acquire()


async def release_db_connection(conn):
    """Release database connection back to pool"""
    if _pool:
        await _pool.release(conn)


@db_connection_decorator
async def get_all_products(conn):
    """Get all products for listing"""
    rows = await conn.fetch(
        "SELECT id, title, llm_confidence, gmc_category_label FROM products ORDER BY id"
    )
    return [dict(row) for row in rows]


@db_connection_decorator
async def get_product_details(conn, product_id: int):
    """Get detailed product information including change history"""
    # Get product details
    product_row = await conn.fetchrow(
        "SELECT * FROM products WHERE id = $1", product_id
    )

    if not product_row:
        return {"product": None, "changes": []}

    # Get change history
    changes_rows = await conn.fetch(
        "SELECT * FROM changes_log WHERE product_id = $1 ORDER BY created_at DESC",
        product_id,
    )

    return {
        "product": dict(product_row),
        "changes": [dict(change) for change in changes_rows],
    }


@db_connection_decorator
async def update_product_details(conn, product_id: int, **kwargs):
    """Update product details or create if it doesn't exist"""
    # Check if product exists
    existing_product = await conn.fetchrow(
        "SELECT id FROM products WHERE id = $1", product_id
    )

    if existing_product:
        # Update existing product
        set_clauses: List[str] = []
        values: List[Any] = []
        param_count = 1

        for field, value in kwargs.items():
            set_clauses.append(f"{field} = ${param_count}")
            values.append(value)
            param_count += 1

        if not set_clauses:
            return

        set_clauses.append(f"updated_at = ${param_count}")
        values.append(datetime.datetime.now())

        query = f"""
            UPDATE products
            SET {", ".join(set_clauses)}
            WHERE id = ${param_count + 1}
        """
        values.append(product_id)

        await conn.execute(query, *values)
        logging.info(
            f"Updated product {product_id} with fields: {list(kwargs.keys())}"
        )
    else:
        # Create new product
        insert_columns: List[str] = ["id"]
        insert_values: List[Any] = [product_id]
        value_placeholders: List[str] = ["$1"]
        param_count = 2

        for field, value in kwargs.items():
            insert_columns.append(field)
            insert_values.append(value)
            value_placeholders.append(f"${param_count}")
            param_count += 1

        insert_columns.append("created_at")
        insert_values.append(datetime.datetime.now())
        value_placeholders.append(f"${param_count}")

        insert_columns.append("updated_at")
        insert_values.append(datetime.datetime.now())
        value_placeholders.append(f"${param_count + 1}")

        query = f"""
            INSERT INTO products ({", ".join(insert_columns)})
            VALUES ({", ".join(value_placeholders)})
        """
        await conn.execute(query, *insert_values)
        logging.info(
            f"Created new product {product_id} with fields: {list(kwargs.keys())}"
        )


@db_connection_decorator
async def get_products_batch(conn, limit: int = 10):
    """Get products for batch processing (unprocessed items)"""
    rows = await conn.fetch(
        """
        SELECT id, title, body_html, tags, category
        FROM products
        WHERE normalized_title IS NULL
        LIMIT $1
        """,
        limit,
    )
    return [dict(row) for row in rows]


@db_connection_decorator
async def get_products_for_review(conn, limit: int = 20):
    """Get products for manual review"""
    rows = await conn.fetch(
        """
        SELECT id, title, llm_title, llm_body_html, llm_tags, llm_category
        FROM products
        WHERE status = 'review'
        ORDER BY updated_at DESC
        LIMIT $1
        """,
        limit,
    )
    return [dict(row) for row in rows]


@db_connection_decorator
async def log_product_change(
    conn,
    product_id: int,
    changed_fields: Dict[str, Any],
    model_name: Optional[str] = None,
):
    """Log changes made to a product"""
    await conn.execute(
        """
        INSERT INTO changes_log (product_id, changed_fields, model_name, created_at)
        VALUES ($1, $2, $3, $4)
        """,
        product_id,
        json.dumps(changed_fields),
        model_name,
        datetime.datetime.now(),
    )


@db_connection_decorator
async def get_product_count(conn) -> int:
    """Get total number of products"""
    count = await conn.fetchval("SELECT COUNT(*) FROM products")
    return count or 0


@db_connection_decorator
async def get_unprocessed_count(conn) -> int:
    """Get number of unprocessed products"""
    count = await conn.fetchval(
        "SELECT COUNT(*) FROM products WHERE normalized_title IS NULL"
    )
    return count or 0


@db_connection_decorator
async def get_review_queue_count(conn) -> int:
    """Get number of products in review queue"""
    count = await conn.fetchval("SELECT COUNT(*) FROM products WHERE status = 'review'")
    return count or 0


@db_connection_decorator
async def get_last_import_timestamp(conn) -> Optional[datetime.datetime]:
    """Get timestamp of the last imported product"""
    return await conn.fetchval("SELECT MAX(created_at) FROM products")


@db_connection_decorator
async def get_model_usage_stats(conn) -> List[Dict[str, Any]]:
    """Get statistics on model usage"""
    rows = await conn.fetch(
        """
        SELECT model_name, COUNT(*) as usage_count
        FROM changes_log
        WHERE model_name IS NOT NULL
        GROUP BY model_name
        ORDER BY usage_count DESC
        """
    )
    return [dict(row) for row in rows]


@db_connection_decorator
async def get_category_distribution(conn) -> List[Dict[str, Any]]:
    """Get distribution of products by category"""
    rows = await conn.fetch(
        """
        SELECT gmc_category_label, COUNT(*) as product_count
        FROM products
        WHERE gmc_category_label IS NOT NULL
        GROUP BY gmc_category_label
        ORDER BY product_count DESC
        """
    )
    return [dict(row) for row in rows]


@db_connection_decorator
async def get_confidence_score_distribution(conn) -> List[Dict[str, Any]]:
    """Get distribution of LLM confidence scores"""
    rows = await conn.fetch(
        """
        SELECT
            width_bucket(llm_confidence, 0, 1, 10) as bucket,
            MIN(llm_confidence) as min_score,
            MAX(llm_confidence) as max_score,
            COUNT(*) as product_count
        FROM products
        WHERE llm_confidence IS NOT NULL
        GROUP BY bucket
        ORDER BY bucket
        """
    )
    return [dict(row) for row in rows]


@db_connection_decorator
async def get_recent_changes(conn, limit: int = 20) -> List[Dict[str, Any]]:
    """Get recent changes from the log"""
    rows = await conn.fetch(
        """
        SELECT cl.id, cl.product_id, p.title, cl.changed_fields, cl.model_name, cl.created_at
        FROM changes_log cl
        JOIN products p ON cl.product_id = p.id
        ORDER BY cl.created_at DESC
        LIMIT $1
        """,
        limit,
    )
    return [dict(row) for row in rows]


@db_connection_decorator
async def get_product_by_id(conn, product_id: int) -> Optional[Dict[str, Any]]:
    """Fetch a single product by its ID."""
    row = await conn.fetchrow("SELECT * FROM products WHERE id = $1", product_id)
    return dict(row) if row else None
    """Get products for batch processing (unprocessed items)"""
    conn = None
    try:
        conn = await get_db_connection()
        rows = await conn.fetch(
            """
            SELECT id, title, body_html, tags, category
            FROM products
            WHERE normalized_title IS NULL
            LIMIT $1
            """,
            limit,
        )
        return [dict(row) for row in rows]
    except Exception as e:
        logging.error(f"Error fetching products batch: {e}")
        raise
    finally:
        if conn:
            await release_db_connection(conn)


async def get_products_for_review(limit: int = 10):
    """Get products that need review (low confidence scores)"""
    conn = None
    try:
        conn = await get_db_connection()
        rows = await conn.fetch(
            """
            SELECT id, title, normalized_title, body_html, normalized_body_html, llm_confidence
            FROM products
            WHERE llm_confidence < 0.7
            ORDER BY llm_confidence ASC
            LIMIT $1
            """,
            limit,
        )
        return [dict(row) for row in rows]
    except Exception as e:
        logging.error(f"Error fetching products for review: {e}")
        raise
    finally:
        if conn:
            await release_db_connection(conn)


async def get_db_schema() -> List[Dict[str, Any]]:
    """Get database schema information"""
    conn = None
    try:
        conn = await get_db_connection()

        # Get table names
        tables_result = await conn.fetch(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        """
        )

        schema = []
        for table_row in tables_result:
            table_name = table_row["table_name"]

            # Get column information
            columns_result = await conn.fetch(
                """
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = $1 AND table_schema = 'public'
                ORDER BY ordinal_position
            """,
                table_name,
            )

            columns = []
            for col_row in columns_result:
                columns.append(
                    {
                        "name": col_row["column_name"],
                        "type": col_row["data_type"],
                        "nullable": col_row["is_nullable"] == "YES",
                        "default": col_row["column_default"],
                    }
                )

            schema.append({"name": table_name, "columns": columns})

        return schema

    except Exception as e:
        logging.error(f"Error fetching database schema: {e}")
        raise
    finally:
        if conn:
            await release_db_connection(conn)


async def get_change_log(limit: int = 100):
    """Get change log entries"""
    conn = None
    try:
        conn = await get_db_connection()
        rows = await conn.fetch(
            """
            SELECT id, product_id, field, old, new, created_at, reviewed
            FROM changes_log
            ORDER BY id DESC
            LIMIT $1
            """,
            limit,
        )
        return [dict(row) for row in rows]
    except Exception as e:
        logging.error(f"Error fetching changes: {e}")
        raise
    finally:
        if conn:
            await release_db_connection(conn)


async def mark_as_reviewed(product_id: int):
    """Mark all changes for a product as reviewed"""
    conn = None
    try:
        conn = await get_db_connection()
        await conn.execute(
            "UPDATE changes_log SET reviewed = TRUE WHERE product_id = $1", product_id
        )
    except Exception as e:
        logging.error(
            f"Error marking changes as reviewed for product {product_id}: {e}"
        )
        raise
    finally:
        if conn:
            await release_db_connection(conn)


async def log_change(pid: int, field: str, old: Any, new: Any, source: str):
    """Log a change to the database"""
    conn = None
    try:
        conn = await get_db_connection()
        await conn.execute(
            """
            INSERT INTO changes_log (product_id, field, old, new, source, created_at)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            pid,
            field,
            json.dumps(old) if old is not None else None,
            json.dumps(new) if new is not None else None,
            source,
            datetime.datetime.now(),
        )
    except Exception as e:
        logging.error(f"Error logging change for product {pid}: {e}")
        raise
    finally:
        if conn:
            await release_db_connection(conn)


async def update_database_schema():
    """Update database schema for PostgreSQL compatibility"""
    conn = None
    try:
        conn = await get_db_connection()

        # Check if columns exist and add them if missing
        existing_columns = await conn.fetch(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'products'
        """
        )

        existing_column_names = {row["column_name"] for row in existing_columns}

        # Add missing columns
        columns_to_add = [
            ("normalized_title", "TEXT"),
            ("normalized_body_html", "TEXT"),
            ("normalized_tags_json", "TEXT"),
            ("gmc_category_label", "TEXT"),
            ("llm_model", "TEXT"),
            ("llm_confidence", "DECIMAL(3,2)"),
            ("normalized_category", "TEXT"),
            ("category_confidence", "DECIMAL(3,2)"),
        ]

        for column_name, column_type in columns_to_add:
            if column_name not in existing_column_names:
                await conn.execute(
                    f"ALTER TABLE products ADD COLUMN {column_name} {column_type}"
                )
                logging.info(f"Added column {column_name} to products table")

        # Ensure changes_log table exists
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS changes_log (
                id SERIAL PRIMARY KEY,
                product_id BIGINT REFERENCES products(id),
                field TEXT,
                old TEXT,
                new TEXT,
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed BOOLEAN DEFAULT FALSE
            )
        """
        )

        # Ensure pipeline_runs table exists
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pipeline_runs (
                id SERIAL PRIMARY KEY,
                task_type TEXT,
                status TEXT,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                total_products INTEGER,
                processed_products INTEGER DEFAULT 0,
                failed_products INTEGER DEFAULT 0
            )
        """
        )

        # Create indexes for better performance
        indexes_to_create = [
            ("idx_products_llm_confidence", "products(llm_confidence)"),
            ("idx_products_category", "products(category)"),
            ("idx_changes_log_product_id", "changes_log(product_id)"),
            ("idx_changes_log_created_at", "changes_log(created_at)"),
            ("idx_pipeline_runs_status", "pipeline_runs(status)"),
            ("idx_pipeline_runs_start_time", "pipeline_runs(start_time)"),
        ]

        for index_name, index_columns in indexes_to_create:
            try:
                await conn.execute(
                    f"CREATE INDEX IF NOT EXISTS {index_name} ON {index_columns}"
                )
                logging.info(f"Created index {index_name}")
            except Exception as e:
                logging.warning(f"Could not create index {index_name}: {e}")

        logging.info("Database schema updated successfully")

    except Exception as e:
        logging.error(f"Error updating database schema: {e}")
        raise
    finally:
        if conn:
            await release_db_connection(conn)


async def create_pipeline_run(task_type: str, total_products: int) -> int:
    """Create a new pipeline run record"""
    conn = None
    try:
        conn = await get_db_connection()
        now = datetime.datetime.now()

        run_id = await conn.fetchval(
            """
            INSERT INTO pipeline_runs (task_type, status, start_time, total_products)
            VALUES ($1, $2, $3, $4)
            RETURNING id
            """,
            task_type,
            "RUNNING",
            now,
            total_products,
        )

        return run_id
    except Exception as e:
        logging.error(f"Error creating pipeline run: {e}")
        raise
    finally:
        if conn:
            await release_db_connection(conn)


async def update_pipeline_run(
    run_id: int,
    processed_products: Optional[int] = None,
    failed_products: Optional[int] = None,
    status: Optional[str] = None,
):
    """Update pipeline run progress"""
    conn = None
    try:
        conn = await get_db_connection()

        set_clauses: List[str] = []
        values: List[Any] = []

        if processed_products is not None:
            set_clauses.append(f"processed_products = ${len(values) + 1}")
            values.append(processed_products)

        if failed_products is not None:
            set_clauses.append(f"failed_products = ${len(values) + 1}")
            values.append(failed_products)

        if status is not None:
            set_clauses.append(f"status = ${len(values) + 1}")
            values.append(status)

        if not set_clauses:
            return

        query = f"""
            UPDATE pipeline_runs
            SET {", ".join(set_clauses)}
            WHERE id = ${len(values) + 1}
        """
        values.append(run_id)

        await conn.execute(query, *values)

    except Exception as e:
        logging.error(f"Error updating pipeline run {run_id}: {e}")
        raise
    finally:
        if conn:
            await release_db_connection(conn)


async def complete_pipeline_run(
    run_id: int, status: str, processed_products: int, failed_products: int
):
    """Mark pipeline run as completed"""
    conn = None
    try:
        conn = await get_db_connection()
        now = datetime.datetime.now()

        await conn.execute(
            """
            UPDATE pipeline_runs
            SET status = $1, end_time = $2, processed_products = $3, failed_products = $4
            WHERE id = $5
            """,
            status,
            now,
            processed_products,
            failed_products,
            run_id,
        )

    except Exception as e:
        logging.error(f"Error completing pipeline run {run_id}: {e}")
        raise
    finally:
        if conn:
            await release_db_connection(conn)


async def get_pipeline_runs(limit: int = 100):
    """Get pipeline run history"""
    conn = None
    try:
        conn = await get_db_connection()
        rows = await conn.fetch(
            """
            SELECT id, task_type, status, start_time, end_time, total_products, processed_products, failed_products
            FROM pipeline_runs
            ORDER BY start_time DESC
            LIMIT $1
            """,
            limit,
        )
        return [dict(row) for row in rows]
    except Exception as e:
        logging.error(f"Error fetching pipeline runs: {e}")
        raise
    finally:
        if conn:
            await release_db_connection(conn)


# Initialize database pool on module import