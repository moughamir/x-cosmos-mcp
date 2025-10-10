import sqlite3
from utils.taxonomy import load_taxonomy, find_best_category

DB_PATH = "products.sqlite"


def normalize_categories(batch_size=100):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    taxonomy = load_taxonomy()

    products = cur.execute(
        "SELECT id, category FROM products WHERE normalized_category IS NULL LIMIT ?",
        (batch_size,),
    ).fetchall()

    if not products:
        print("✅ No categories left to normalize.")
        conn.close()
        return

    print(f"Processing {len(products)} categories...")

    for p in products:
        best, score = find_best_category(p["category"], taxonomy)
        cur.execute(
            "UPDATE products SET normalized_category = ?, category_confidence = ? WHERE id = ?",
            (best, score, p["id"]),
        )

    conn.commit()
    conn.close()
    print("✅ Batch complete.")
