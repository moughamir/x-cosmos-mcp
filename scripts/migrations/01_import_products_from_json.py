#!/usr/bin/env python3
"""
Migration script to import products from JSON files into the PostgreSQL database.
"""

import asyncio
import json
import logging
import os

import asyncpg

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def import_products_from_json():
    """Import products from JSON files into the PostgreSQL database"""

    # Connect to the database
    pg_conn = await asyncpg.connect(
        user=os.getenv("POSTGRES_USER", "mcp_user"),
        password=os.getenv("POSTGRES_PASSWORD", "mcp_password"),
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        database=os.getenv("POSTGRES_DB", "mcp_db"),
    )

    try:
        json_dir = "data/json"
        if not os.path.exists(json_dir):
            logger.warning(f"Directory not found: {json_dir}")
            return

        json_files = [f for f in os.listdir(json_dir) if f.endswith(".json")]
        if not json_files:
            logger.info("No JSON files found to import.")
            return

        logger.info(f"Found {len(json_files)} JSON files to import.")

        total_imported_count = 0
        for file_name in json_files:
            file_path = os.path.join(json_dir, file_name)
            with open(file_path, "r") as f:
                products = json.load(f)

            logger.info(f"Importing {len(products)} products from {file_name}...")

            imported_count = 0
            for product in products:
                try:
                    await pg_conn.execute(
                        """
                        INSERT INTO products (
                            id, title, body_html, tags, category
                        ) VALUES ($1, $2, $3, $4, $5)
                        ON CONFLICT (id) DO UPDATE SET
                            title = EXCLUDED.title,
                            body_html = EXCLUDED.body_html,
                            tags = EXCLUDED.tags,
                            category = EXCLUDED.category,
                            updated_at = CURRENT_TIMESTAMP
                    """,
                        product.get("id"),
                        product.get("title"),
                        product.get("body_html"),
                        product.get("tags"),
                        product.get("category"),
                    )
                    imported_count += 1
                except Exception as e:
                    logger.error(f"Error importing product {product.get('id')}: {e}")

            logger.info(
                f"✅ Successfully imported {imported_count}/{len(products)} products from {file_name}"
            )
            total_imported_count += imported_count

        logger.info(
            f"🎉 Total imported products: {total_imported_count}"
        )

    except Exception as e:
        logger.error(f"Error during product import: {e}")
        raise
    finally:
        await pg_conn.close()


async def main():
    """Main import function"""

    logger.info("🚀 Starting product import from JSON files")
    await import_products_from_json()
    logger.info("🎉 Product import completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
