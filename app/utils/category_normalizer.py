import logging
from typing import List, Optional

from .db import get_db_connection, release_db_connection, update_product_details
from .taxonomy import find_best_category, load_taxonomy

logger = logging.getLogger(__name__)


async def normalize_categories(
    product_ids: Optional[List[int]] = None, batch_size: int = 100
):
    """Normalize product categories using Google taxonomy.

    Returns:
        Dict with normalized category data for single product, or None for batch
    """
    taxonomy_tree = load_taxonomy()
    conn = None
    result = None

    try:
        conn = await get_db_connection()
        products = []
        if product_ids:
            placeholders = ",".join(f"${i + 1}" for i, _ in enumerate(product_ids))
            products = await conn.fetch(
                f"""
                SELECT p.id, COALESCE(p.category, pt.name) as category
                FROM products p
                LEFT JOIN product_types pt ON p.product_type_id = pt.id
                WHERE p.id IN ({placeholders})
                """,
                *product_ids,
            )
        else:
            products = await conn.fetch(
                """
                SELECT p.id, COALESCE(p.category, pt.name) as category
                FROM products p
                LEFT JOIN product_types pt ON p.product_type_id = pt.id
                WHERE p.normalized_category IS NULL
                LIMIT $1
                """,
                batch_size,
            )

        if not products:
            logger.info("✅ No categories left to normalize.")
            return None

        logger.info(f"Processing {len(products)} categories...")

        for product in products:
            if not product["category"]:
                logger.warning(f"Product {product['id']} has no category, skipping")
                continue

            best_category, confidence = find_best_category(
                product["category"], taxonomy_tree
            )

            logger.info(
                f"Product {product['id']}: '{product['category']}' -> '{best_category}' (confidence: {confidence})"
            )

            # Update product with normalized category and confidence
            await update_product_details(
                product["id"],
                normalized_category=best_category,
                category_confidence=confidence,
            )

            # If processing a single product, return the result
            if product_ids and len(product_ids) == 1:
                result = {
                    "normalized_category": best_category,
                    "category_confidence": confidence,
                    "original_category": product["category"],
                }

        logger.info("✅ Category normalization batch complete.")
        return result

    finally:
        if conn:
            await release_db_connection(conn)
