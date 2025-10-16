import csv
import io
import logging
from typing import List, Optional

from app.utils.db import get_connection

logger = logging.getLogger(__name__)


async def export_products_to_csv(
    product_ids: Optional[List[int]] = None,
) -> io.StringIO:
    """Exports product data to a CSV format in a StringIO object."""
    output = io.StringIO()
    writer = csv.writer(output)

    try:
        async with get_connection() as conn:
            if product_ids:
                placeholders = ",".join([f"${i+1}" for i in range(len(product_ids))])
                rows = await conn.fetch(
                    f"SELECT * FROM products WHERE id IN ({placeholders})", *product_ids
                )
            else:
                rows = await conn.fetch("SELECT * FROM products")

            if not rows:
                return output

            # Write header
            # asyncpg returns records, which can be converted to dicts to get keys
            header = list(rows[0].keys())
            writer.writerow(header)

            # Write rows
            for row in rows:
                writer.writerow(list(row.values()))

    except Exception as e:
        logger.error(f"Error exporting products to CSV: {e}")
        # Depending on desired behavior, you might want to re-raise or return an empty/error indicator
        return io.StringIO()  # Return empty StringIO on error

    output.seek(0)
    return output
