import aiosqlite
import datetime
import json

async def get_products_batch(db_path: str, limit=10):
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.cursor()
        await cur.execute(
            "SELECT id, title, body_html, tags, category FROM products WHERE normalized_title IS NULL LIMIT ?",
            (limit,),
        )
        return await cur.fetchall()

async def get_products_for_review(db_path: str, limit=10):
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.cursor()
        await cur.execute(
            "SELECT id, title, normalized_title, body_html, normalized_body_html, llm_confidence FROM products WHERE llm_confidence < 0.7 LIMIT ?",
            (limit,),
        )
        return await cur.fetchall()

async def get_all_products(db_path: str):
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.cursor()
        await cur.execute("SELECT id, title, llm_confidence, gmc_category_label FROM products")
        return await cur.fetchall()

async def get_product_details(db_path: str, product_id: int):
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.cursor()
        await cur.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        product = await cur.fetchone()
        await cur.execute("SELECT * FROM changes_log WHERE product_id = ? ORDER BY created_at DESC", (product_id,))
        changes = await cur.fetchall()
        return {"product": product, "changes": changes}

async def update_product_details(db_path: str, product_id: int, data: dict):
    async with aiosqlite.connect(db_path) as conn:
        cur = await conn.cursor()
        # Assuming data contains title, body_html, etc.
        # This is a simple example; you might want to be more specific about the fields
        await cur.execute(
            "UPDATE products SET title = ?, body_html = ? WHERE id = ?",
            (data.get("title"), data.get("body_html"), product_id)
        )
        await conn.commit()

async def get_change_log(db_path: str, limit=100):
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.cursor()
        await cur.execute(
            "SELECT id, product_id, field, old, new, created_at, reviewed FROM changes_log ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return await cur.fetchall()

async def mark_as_reviewed(db_path: str, product_id: int):
    async with aiosqlite.connect(db_path) as conn:
        cur = await conn.cursor()
        await cur.execute(
            "UPDATE changes_log SET reviewed = 1 WHERE product_id = ?",
            (product_id,),
        )
        await conn.commit()

async def log_change(db_path: str, pid, field, old, new, source):
    async with aiosqlite.connect(db_path) as conn:
        cur = await conn.cursor()
        await cur.execute(
            """
            INSERT INTO changes_log (product_id, field, old, new, created_at, source, reviewed)
            VALUES (?, ?, ?, ?, ?, ?, 0)
            """,
            (pid, field, old, new, datetime.datetime.utcnow().isoformat(), source),
        )
        await conn.commit()

async def update_product(db_path: str, pid, normalized_title, normalized_body, normalized_tags, final_category, model_name, confidence):
    async with aiosqlite.connect(db_path) as conn:
        cur = await conn.cursor()
        await cur.execute(
            """UPDATE products 
               SET normalized_title = ?, normalized_body_html = ?, normalized_tags_json = ?, 
                   gmc_category_label = ?, llm_model = ?, llm_confidence = ?
               WHERE id = ?""",
            (normalized_title, normalized_body, json.dumps(normalized_tags), final_category, model_name, confidence, pid)
        )
        await conn.commit()