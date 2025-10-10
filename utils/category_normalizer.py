import aiosqlite
import logging
from typing import Optional, List
from utils.taxonomy import load_taxonomy, find_best_category
from utils.db import update_product_details

logger = logging.getLogger(__name__)

async def normalize_categories(db_path: str, product_ids: Optional[List[int]] = None, batch_size: int = 100):
    """Normalize product categories using Google taxonomy."""
    taxonomy = load_taxonomy()

    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.cursor()

        if product_ids:
            placeholders = ','.join('?' * len(product_ids))
            await cursor.execute(
                f"SELECT id, category FROM products WHERE id IN ({placeholders})",
                product_ids,
            )
        else:
            await cursor.execute(
                "SELECT id, category FROM products WHERE normalized_category IS NULL LIMIT ?",
                (batch_size,),
            )
        products = await cursor.fetchall()

        if not products:
            logger.info("✅ No categories left to normalize.")
            return

        logger.info(f"Processing {len(products)} categories...")

        for product in products:
            best_category, confidence = find_best_category(product["category"], taxonomy)

            # Update product with normalized category and confidence
            await update_product_details(
                db_path,
                product["id"],
                normalized_category=best_category,
                category_confidence=confidence
            )

        logger.info("✅ Category normalization batch complete.")