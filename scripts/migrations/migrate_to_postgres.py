#!/usr/bin/env python3
"""
PostgreSQL database migration script for MCP Admin
Creates all necessary tables and indexes for the application
"""

import asyncio
import logging
import os

import asyncpg

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_tables():
    """Create all necessary PostgreSQL tables"""

    # Database connection
    conn = await asyncpg.connect(
        user=os.getenv("POSTGRES_USER", "mcp_user"),
        password=os.getenv("POSTGRES_PASSWORD", "mcp_password"),
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        database=os.getenv("POSTGRES_DB", "mcp_db"),
    )

    try:
        # Create products table
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id BIGINT PRIMARY KEY,
                title TEXT,
                body_html TEXT,
                tags TEXT,
                category TEXT,
                normalized_title TEXT,
                normalized_body_html TEXT,
                normalized_tags_json TEXT,
                gmc_category_label TEXT,
                llm_model TEXT,
                llm_confidence DECIMAL(3,2) DEFAULT 0.0,
                normalized_category TEXT,
                category_confidence DECIMAL(3,2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Create changes_log table
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

        # Create pipeline_runs table
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
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_products_llm_confidence ON products(llm_confidence)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_products_category ON products(category)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_changes_log_product_id ON changes_log(product_id)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_changes_log_created_at ON changes_log(created_at)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status ON pipeline_runs(status)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_pipeline_runs_start_time ON pipeline_runs(start_time)"
        )

        # Create full-text search index
        await conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_products_fts ON products
            USING GIN (to_tsvector('english', title || ' ' || body_html))
        """
        )

        logger.info("✅ All PostgreSQL tables and indexes created successfully")

    except Exception as e:
        logger.error(f"❌ Error creating tables: {e}")
        raise
    finally:
        await conn.close()


async def check_database():
    """Check if database connection and tables exist"""

    try:
        conn = await asyncpg.connect(
            user=os.getenv("POSTGRES_USER", "mcp_user"),
            password=os.getenv("POSTGRES_PASSWORD", "mcp_password"),
            host=os.getenv("POSTGRES_HOST", "postgres"),
            port=int(os.getenv("POSTGRES_PORT", 5432)),
            database=os.getenv("POSTGRES_DB", "mcp_db"),
        )

        # Check if tables exist
        tables = await conn.fetch(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
        """
        )

        table_names = [row["table_name"] for row in tables]
        logger.info(f"📊 Found tables: {', '.join(table_names)}")

        # Check products count
        count = await conn.fetchval("SELECT COUNT(*) FROM products")
        logger.info(f"📈 Products in database: {count}")

        await conn.close()
        return True

    except Exception as e:
        logger.error(f"❌ Database check failed: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(create_tables())
    asyncio.run(check_database())
