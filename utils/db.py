import asyncpg
import asyncio
import datetime
import json
import logging
from config import settings

# Global connection pool
_pool = None

async def init_db_pool():
    global _pool
    if _pool is None:
        logging.info("Initializing PostgreSQL connection pool...")
        _pool = await asyncpg.create_pool(
            user=settings.postgres.user,
            password=settings.postgres.password,
            host=settings.postgres.host,
            port=settings.postgres.port,
            database=settings.postgres.database,
            min_size=1,
            max_size=10,
            timeout=60,
            command_timeout=60,
        )
        logging.info("PostgreSQL connection pool initialized.")

async def close_db_pool():
    global _pool
    if _pool:
        logging.info("Closing PostgreSQL connection pool...")
        await _pool.close()
        _pool = None
        logging.info("PostgreSQL connection pool closed.")

async def get_db_connection():
    if _pool is None:
        await init_db_pool()
    return await _pool.acquire()

async def release_db_connection(conn):
    if _pool:
        await _pool.release(conn)



logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def get_products_batch(limit=10):
    conn = None
    try:
        conn = await get_db_connection()
        rows = await conn.fetch(
            "SELECT id, title, body_html, tags, category FROM products WHERE normalized_title IS NULL LIMIT $1",
            limit,
        )
        return [dict(row) for row in rows]
    finally:
        if conn:
            await release_db_connection(conn)

async def get_products_for_review(limit=10):
    conn = None
    try:
        conn = await get_db_connection()
        rows = await conn.fetch(
            "SELECT id, title, normalized_title, body_html, normalized_body_html, llm_confidence FROM products WHERE llm_confidence < 0.7 LIMIT $1",
            limit,
        )
        return [dict(row) for row in rows]
    finally:
        if conn:
            await release_db_connection(conn)

async def get_all_products():
    conn = None
    try:
        conn = await get_db_connection()
        rows = await conn.fetch("SELECT id, title, llm_confidence, gmc_category_label FROM products")
        return [dict(row) for row in rows]
    except Exception as e:
        logging.error(f"Error in get_all_products: {e}", exc_info=True)
        raise
    finally:
        if conn:
            await release_db_connection(conn)

async def get_product_details(product_id: int):
    conn = None
    try:
        conn = await get_db_connection()
        product_row = await conn.fetchrow("SELECT * FROM products WHERE id = $1", product_id)
        changes_rows = await conn.fetch("SELECT * FROM changes_log WHERE product_id = $1 ORDER BY created_at DESC", product_id)

        product = dict(product_row) if product_row else None
        changes = [dict(row) for row in changes_rows]

        return {"product": product, "changes": changes}
    except Exception as e:
        logging.error(f"Error in get_product_details for product ID {product_id}: {e}", exc_info=True)
        raise
    finally:
        if conn:
            await release_db_connection(conn)

async def update_product_details(product_id: int, **kwargs):
    conn = None
    try:
        conn = await get_db_connection()
        set_clauses = []
        values = []
        param_counter = 1
        for key, value in kwargs.items():
            # Exclude 'llm_confidence' from direct update if it's None, as it has a default
            if key == 'llm_confidence' and value is None:
                continue
            set_clauses.append(f"{key} = ${param_counter}")
            values.append(value)
            param_counter += 1
        
        if not set_clauses:
            return # No fields to update

        sql = f"UPDATE products SET {', '.join(set_clauses)} WHERE id = ${param_counter}"
        values.append(product_id)
        
        await conn.execute(sql, *values)
    except Exception as e:
        logging.error(f"Error in update_product_details for product ID {product_id}: {e}", exc_info=True)
        raise
    finally:
        if conn:
            await release_db_connection(conn)

async def get_change_log(limit=100):
    conn = None
    try:
        conn = await get_db_connection()
        rows = await conn.fetch(
            "SELECT id, product_id, field, old, new, created_at, reviewed FROM changes_log ORDER BY id DESC LIMIT $1",
            limit,
        )
        return [dict(row) for row in rows]
    finally:
        if conn:
            await release_db_connection(conn)

async def get_db_schema() -> list[dict]:
    conn = None
    try:
        conn = await get_db_connection()
        
        # Get table names
        tables_query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """
        table_names = [row['table_name'] for row in await conn.fetch(tables_query)]
        
        schema = []
        for table_name in table_names:
            # Get column info for each table
            columns_query = """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = $1
                ORDER BY ordinal_position;
            """
            columns_data = await conn.fetch(columns_query, table_name)
            columns = [{'name': col['column_name'], 'type': col['data_type']} for col in columns_data]
            schema.append({'name': table_name, 'columns': columns})
            
        return schema
    except Exception as e:
        logging.error(f"Error in get_db_schema: {e}", exc_info=True)
        raise
    finally:
        if conn:
            await release_db_connection(conn)

async def mark_as_reviewed(product_id: int):
    conn = None
    try:
        conn = await get_db_connection()
        await conn.execute(
            "UPDATE changes_log SET reviewed = TRUE WHERE product_id = $1",
            product_id,
        )
    except Exception as e:
        logging.error(f"Error in mark_as_reviewed for product ID {product_id}: {e}", exc_info=True)
        raise
    finally:
        if conn:
            await release_db_connection(conn)

async def log_change(pid: int, field: str, old: Any, new: Any, source: str):
    conn = None
    try:
        conn = await get_db_connection()
        await conn.execute(
            """
            INSERT INTO changes_log (product_id, field, old, new, source, created_at)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            pid, field, json.dumps(old), json.dumps(new), source, datetime.datetime.now(),
        )
    except Exception as e:
        logging.error(f"Error in log_change for product ID {pid}: {e}", exc_info=True)
        raise
    finally:
        if conn:
            await release_db_connection(conn)

async def update_database_schema():

    """Update the database schema to include required tables and columns for PostgreSQL."""

    conn = None

    try:

        conn = await get_db_connection()

        

        # Create products table if it doesn't exist

        await conn.execute("""

            CREATE TABLE IF NOT EXISTS products (

                id SERIAL PRIMARY KEY,

                title TEXT,

                body_html TEXT,

                tags TEXT,

                category TEXT,

                normalized_title TEXT,

                normalized_body_html TEXT,

                llm_confidence REAL DEFAULT 0.0,

                gmc_category_label TEXT,

                llm_model TEXT,

                normalized_category TEXT,

                category_confidence REAL DEFAULT 0.0,

                normalized_tags_json TEXT,

                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP

            )

        """

        )

        

        # Add any missing columns to products table

        # Check for column existence before adding

        async def add_column_if_not_exists(table_name, column_name, column_type):

            exists = await conn.fetchval(f"""

                SELECT EXISTS (

                    SELECT 1

                    FROM information_schema.columns

                    WHERE table_schema = 'public'

                    AND table_name = 


                    AND column_name = $2

                );

            """, table_name, column_name)

            if not exists:

                await conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")

                logging.info(f"Added column {column_name} to table {table_name}")



        await add_column_if_not_exists('products', 'normalized_title', 'TEXT')

        await add_column_if_not_exists('products', 'normalized_body_html', 'TEXT')

        await add_column_if_not_exists('products', 'llm_confidence', 'REAL DEFAULT 0.0')

        await add_column_if_not_exists('products', 'gmc_category_label', 'TEXT')

        await add_column_if_not_exists('products', 'llm_model', 'TEXT')

        await add_column_if_not_exists('products', 'normalized_category', 'TEXT')

        await add_column_if_not_exists('products', 'category_confidence', 'REAL DEFAULT 0.0')

        await add_column_if_not_exists('products', 'normalized_tags_json', 'TEXT')

        await add_column_if_not_exists('products', 'created_at', 'TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP')

        await add_column_if_not_exists('products', 'updated_at', 'TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP')

        

        # Create changes_log table if it doesn't exist

        await conn.execute("""

            CREATE TABLE IF NOT EXISTS changes_log (

                id SERIAL PRIMARY KEY,

                product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,

                field TEXT,

                old TEXT,

                new TEXT,

                source TEXT,

                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

                reviewed BOOLEAN DEFAULT FALSE

            )

        """

        )



        # Create pipeline_runs table if it doesn't exist

        await conn.execute("""

            CREATE TABLE IF NOT EXISTS pipeline_runs (

                id SERIAL PRIMARY KEY,

                task_type TEXT NOT NULL,

                status TEXT NOT NULL,

                start_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

                end_time TIMESTAMP WITH TIME ZONE,

                total_products INTEGER,

                processed_products INTEGER DEFAULT 0,

                failed_products INTEGER DEFAULT 0

            )

        """

        )

        

    except Exception as e:

        logging.error(f"Error in update_database_schema: {e}", exc_info=True)

        raise

    finally:

        if conn:

            await release_db_connection(conn)

async def create_pipeline_run(task_type: str, total_products: int) -> int:
    conn = None
    try:
        conn = await get_db_connection()
        now = datetime.datetime.now()
        # asyncpg returns the inserted ID directly if RETURNING is used
        run_id = await conn.fetchval(
            """
            INSERT INTO pipeline_runs (task_type, status, start_time, total_products)
            VALUES ($1, $2, $3, $4)
            RETURNING id
            """,
            task_type, "RUNNING", now, total_products,
        )
        return run_id
    except Exception as e:
        logging.error(f"Error in create_pipeline_run: {e}", exc_info=True)
        raise
    finally:
        if conn:
            await release_db_connection(conn)

async def update_pipeline_run(run_id: int, processed_products: int = None, failed_products: int = None, status: str = None):
    conn = None
    try:
        conn = await get_db_connection()
        set_clauses = []
        values = []
        param_counter = 1
        if processed_products is not None:
            set_clauses.append(f"processed_products = ${param_counter}")
            values.append(processed_products)
            param_counter += 1
        if failed_products is not None:
            set_clauses.append(f"failed_products = ${param_counter}")
            values.append(failed_products)
            param_counter += 1
        if status is not None:
            set_clauses.append(f"status = ${param_counter}")
            values.append(status)
            param_counter += 1
        
        if not set_clauses:
            return # No fields to update

        sql = f"UPDATE pipeline_runs SET {', '.join(set_clauses)} WHERE id = ${param_counter}"
        values.append(run_id)
        
        await conn.execute(sql, *values)
    except Exception as e:
        logging.error(f"Error in update_pipeline_run for run ID {run_id}: {e}", exc_info=True)
        raise
    finally:
        if conn:
            await release_db_connection(conn)

async def complete_pipeline_run(run_id: int, status: str, processed_products: int, failed_products: int):
    conn = None
    try:
        conn = await get_db_connection()
        now = datetime.datetime.now()
        await conn.execute(
            "UPDATE pipeline_runs SET status = $1, end_time = $2, processed_products = $3, failed_products = $4 WHERE id = $5",
            status, now, processed_products, failed_products, run_id,
        )
    except Exception as e:
        logging.error(f"Error in complete_pipeline_run for run ID {run_id}: {e}", exc_info=True)
        raise
    finally:
        if conn:
            await release_db_connection(conn)

async def get_pipeline_runs(limit: int = 100):
    conn = None
    try:
        conn = await get_db_connection()
        rows = await conn.fetch(
            "SELECT id, task_type, status, start_time, end_time, total_products, processed_products, failed_products FROM pipeline_runs ORDER BY start_time DESC LIMIT $1",
            limit,
        )
        return [dict(row) for row in rows]
    except Exception as e:
        logging.error(f"Error in get_pipeline_runs: {e}", exc_info=True)
        raise
    finally:
        if conn:
            await release_db_connection(conn)