import logging
from typing import List, Optional

from .db import get_db_connection, release_db_connection, update_product_details
from .taxonomy import find_best_category, load_taxonomy

logger = logging.getLogger(__name__)


async def normalize_categories(
    product_ids: Optional[List[int]] = None, batch_size: int = 100
):
    """Normalize product categories using Google taxonomy."""
    taxonomy_tree = load_taxonomy()
    conn = None
    try:
        conn = await get_db_connection()
        products = []
        if product_ids:
            placeholders = ",".join(f"${i + 1}" for i, _ in enumerate(product_ids))
            products = await conn.fetch(
                f"SELECT id, category FROM products WHERE id IN ({placeholders})",
                *product_ids,
            )
        else:
            products = await conn.fetch(
                "SELECT id, category FROM products WHERE normalized_category IS NULL LIMIT $1",
                batch_size,
            )

        if not products:
            logger.info("✅ No categories left to normalize.")
            return

        logger.info(f"Processing {len(products)} categories...")

        for product in products:
            if not product["category"]:
                continue

            best_category, confidence = find_best_category(
                product["category"], taxonomy_tree
            )

            # Update product with normalized category and confidence
            await update_product_details(
                product["id"],
                normalized_category=best_category,
                category_confidence=confidence,
            )

        logger.info("✅ Category normalization batch complete.")
    finally:
        if conn:
            await release_db_connection(conn)
