import csv
import io
from typing import List

import aiosqlite


async def export_products_to_csv(
    db_path: str, product_ids: List[int] = None
) -> io.StringIO:
    """Exports product data to a CSV format in a StringIO object."""
    output = io.StringIO()
    writer = csv.writer(output)

    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.cursor()

        if product_ids:
            placeholders = ",".join("?" * len(product_ids))
            await cursor.execute(
                f"SELECT * FROM products WHERE id IN ({placeholders})", product_ids
            )
        else:
            await cursor.execute("SELECT * FROM products")

        products = await cursor.fetchall()

        if not products:
            return output

        # Write header
        header = products[0].keys()
        writer.writerow(header)

        # Write rows
        for product in products:
            writer.writerow(list(product))

    output.seek(0)
    return output
