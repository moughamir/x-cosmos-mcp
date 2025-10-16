#!/usr/bin/env python3
"""
Complete migration script from SQLite to PostgreSQL for MCP Admin
"""

import asyncio
import json
import logging
import os

import aiosqlite
import asyncpg

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def migrate_products_table():
    """Migrate products table from SQLite to PostgreSQL"""

    # Connect to both databases
    sqlite_conn = await aiosqlite.connect(
        database=os.getenv("SQLITE_DB", "data/sqlite/products.sqlite")
    )
    pg_conn = await asyncpg.connect(
        user=os.getenv("POSTGRES_USER", "mcp_user"),
        password=os.getenv("POSTGRES_PASSWORD", "mcp_password"),
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        database=os.getenv("POSTGRES_DB", "mcp_db"),
    )

    try:
        # Get all products from SQLite
        sqlite_conn.row_factory = aiosqlite.Row
        cursor = await sqlite_conn.cursor()

        await cursor.execute("SELECT * FROM products")
        products = await cursor.fetchall()

        logger.info(f"Migrating {len(products)} products from SQLite to PostgreSQL")

        migrated_count = 0
        for product in products:
            try:
                # Convert SQLite row to dict
                product_dict = dict(product)

                # Handle JSON fields that might be strings
                for json_field in ["normalized_tags_json"]:
                    if product_dict.get(json_field) and isinstance(
                        product_dict[json_field], str
                    ):
                        try:
                            product_dict[json_field] = json.loads(
                                product_dict[json_field]
                            )
                        except (json.JSONDecodeError, TypeError):
                            product_dict[json_field] = None

                # Insert into PostgreSQL
                await pg_conn.execute(
                    """
                    INSERT INTO products (
                        id, title, body_html, tags, category, normalized_title,
                        normalized_body_html, normalized_tags_json, gmc_category_label,
                        llm_model, llm_confidence, created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                    ON CONFLICT (id) DO UPDATE SET
                        title = EXCLUDED.title,
                        body_html = EXCLUDED.body_html,
                        tags = EXCLUDED.tags,
                        category = EXCLUDED.category,
                        normalized_title = EXCLUDED.normalized_title,
                        normalized_body_html = EXCLUDED.normalized_body_html,
                        normalized_tags_json = EXCLUDED.normalized_tags_json,
                        gmc_category_label = EXCLUDED.gmc_category_label,
                        llm_model = EXCLUDED.llm_model,
                        llm_confidence = EXCLUDED.llm_confidence,
                        updated_at = EXCLUDED.updated_at
                """,
                    product_dict.get("id"),
                    product_dict.get("title"),
                    product_dict.get("body_html"),
                    product_dict.get("tags"),
                    product_dict.get("category"),
                    product_dict.get("normalized_title"),
                    product_dict.get("normalized_body_html"),
                    product_dict.get("normalized_tags_json"),
                    product_dict.get("gmc_category_label"),
                    product_dict.get("llm_model"),
                    product_dict.get("llm_confidence"),
                    product_dict.get("created_at"),
                    product_dict.get("updated_at"),
                )

                migrated_count += 1

            except Exception as e:
                logger.error(f"Error migrating product {product['id']}: {e}")

        logger.info(
            f"✅ Successfully migrated {migrated_count}/{len(products)} products"
        )

    except Exception as e:
        logger.error(f"Error during product migration: {e}")
        raise
    finally:
        await sqlite_conn.close()
        await pg_conn.close()


async def migrate_changes_log():
    """Migrate changes_log table from SQLite to PostgreSQL"""

    # Connect to both databases
    sqlite_conn = await aiosqlite.connect(
        database=os.getenv("SQLITE_DB", "data/sqlite/products.sqlite")
    )
    pg_conn = await asyncpg.connect(
        user=os.getenv("POSTGRES_USER", "mcp_user"),
        password=os.getenv("POSTGRES_PASSWORD", "mcp_password"),
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        database=os.getenv("POSTGRES_DB", "mcp_db"),
    )

    try:
        # Get all changes from SQLite
        sqlite_conn.row_factory = aiosqlite.Row
        cursor = await sqlite_conn.cursor()

        await cursor.execute("SELECT * FROM changes_log")
        changes = await cursor.fetchall()

        logger.info(f"Migrating {len(changes)} changes from SQLite to PostgreSQL")

        migrated_count = 0
        for change in changes:
            try:
                # Convert SQLite row to dict
                change_dict = dict(change)

                # Convert boolean (SQLite uses 0/1, PostgreSQL uses true/false)
                change_dict["reviewed"] = bool(change_dict["reviewed"])

                # Insert into PostgreSQL
                await pg_conn.execute(
                    """
                    INSERT INTO changes_log (
                        id, product_id, field, old, new, source, created_at, reviewed
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (id) DO NOTHING
                """,
                    change_dict.get("id"),
                    change_dict.get("product_id"),
                    change_dict.get("field"),
                    change_dict.get("old"),
                    change_dict.get("new"),
                    change_dict.get("source"),
                    change_dict.get("created_at"),
                    change_dict.get("reviewed"),
                )

                migrated_count += 1

            except Exception as e:
                logger.error(f"Error migrating change {change['id']}: {e}")

        logger.info(f"✅ Successfully migrated {migrated_count}/{len(changes)} changes")

    except Exception as e:
        logger.error(f"Error during changes migration: {e}")
        raise
    finally:
        await sqlite_conn.close()
        await pg_conn.close()


async def migrate_pipeline_runs():
    """Migrate pipeline_runs table from SQLite to PostgreSQL"""

    # Connect to both databases
    sqlite_conn = await aiosqlite.connect(
        database=os.getenv("SQLITE_DB", "data/sqlite/products.sqlite")
    )
    pg_conn = await asyncpg.connect(
        user=os.getenv("POSTGRES_USER", "mcp_user"),
        password=os.getenv("POSTGRES_PASSWORD", "mcp_password"),
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        database=os.getenv("POSTGRES_DB", "mcp_db"),
    )

    try:
        # Get all pipeline runs from SQLite
        sqlite_conn.row_factory = aiosqlite.Row
        cursor = await sqlite_conn.cursor()

        await cursor.execute("SELECT * FROM pipeline_runs")
        runs = await cursor.fetchall()

        logger.info(f"Migrating {len(runs)} pipeline runs from SQLite to PostgreSQL")

        migrated_count = 0
        for run in runs:
            try:
                # Convert SQLite row to dict
                run_dict = dict(run)

                # Insert into PostgreSQL
                await pg_conn.execute(
                    """
                    INSERT INTO pipeline_runs (
                        id, task_type, status, start_time, end_time,
                        total_products, processed_products, failed_products
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (id) DO NOTHING
                """,
                    run_dict.get("id"),
                    run_dict.get("task_type"),
                    run_dict.get("status"),
                    run_dict.get("start_time"),
                    run_dict.get("end_time"),
                    run_dict.get("total_products"),
                    run_dict.get("processed_products"),
                    run_dict.get("failed_products"),
                )

                migrated_count += 1

            except Exception as e:
                logger.error(f"Error migrating pipeline run {run['id']}: {e}")

        logger.info(
            f"✅ Successfully migrated {migrated_count}/{len(runs)} pipeline runs"
        )

    except Exception as e:
        logger.error(f"Error during pipeline runs migration: {e}")
        raise
    finally:
        await sqlite_conn.close()
        await pg_conn.close()


async def verify_migration():
    """Verify that the migration was successful"""

    pg_conn = await asyncpg.connect(
        user=os.getenv("POSTGRES_USER", "mcp_user"),
        password=os.getenv("POSTGRES_PASSWORD", "mcp_password"),
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        database=os.getenv("POSTGRES_DB", "mcp_db"),
    )

    try:
        # Check table counts
        products_count = await pg_conn.fetchval("SELECT COUNT(*) FROM products")
        changes_count = await pg_conn.fetchval("SELECT COUNT(*) FROM changes_log")
        runs_count = await pg_conn.fetchval("SELECT COUNT(*) FROM pipeline_runs")

        logger.info("✅ Migration verification:")
        logger.info(f"   Products: {products_count}")
        logger.info(f"   Changes: {changes_count}")
        logger.info(f"   Pipeline runs: {runs_count}")

        # Check data integrity
        sample_product = await pg_conn.fetchrow(
            "SELECT id, title FROM products LIMIT 1"
        )
        if sample_product:
            logger.info(
                f"   Sample product: {sample_product['id']} - {sample_product['title'][:50]}..."
            )

        return True

    except Exception as e:
        logger.error(f"❌ Migration verification failed: {e}")
        return False
    finally:
        await pg_conn.close()


async def main():
    """Main migration function"""

    logger.info("🚀 Starting MCP Admin migration from SQLite to PostgreSQL")

    try:
        # Step 1: Migrate products
        await migrate_products_table()

        # Step 2: Migrate changes
        await migrate_changes_log()

        # Step 3: Migrate pipeline runs
        await migrate_pipeline_runs()

        # Step 4: Verify migration
        success = await verify_migration()

        if success:
            logger.info("🎉 Migration completed successfully!")
            logger.info("📋 Next steps:")
            logger.info("   1. Update your application configuration")
            logger.info("   2. Test the application with PostgreSQL")
            logger.info("   3. Backup and remove the old SQLite database")
        else:
            logger.error("❌ Migration failed verification")

    except Exception as e:
        logger.error(f"💥 Migration failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
