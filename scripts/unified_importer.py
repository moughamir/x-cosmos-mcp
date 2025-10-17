#!/usr/bin/env python3
"""
unified_importer.py
----------------------------------------
A single, robust script to handle the entire ETL process.
It reads compressed JSON files, processes them in memory, and inserts the data
directly into the PostgreSQL database within a transaction.
This replaces the fragile, multi-step process of using intermediate TSV files.
"""

import asyncio
import logging
from pathlib import Path
import json
import hashlib
from tqdm import tqdm
from datetime import datetime
from asyncpg.exceptions import UniqueViolationError

# Add project root to sys.path to allow absolute imports from scripts folder
import sys
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from scripts.utils import get_db_connection, safe_load_json

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

JSON_DIR = Path("data/json/products_by_id")
CACHE_FILE = Path("data/json/importer_processed_files.jsonl")
MAX_CONCURRENT_TASKS = 25  # Limit concurrent DB connections
MAX_FILES_TO_PROCESS = 100 # Limit the number of files to process for testing


# --- Helper Functions ---
def file_hash(path: Path) -> str:
    """Return a short, consistent hash of a file path."""
    return hashlib.md5(str(path).encode()).hexdigest()[:10]

def load_cached_hashes() -> set:
    """Load cached file hashes from the cache file."""
    if not CACHE_FILE.exists():
        return set()
    with CACHE_FILE.open("r", encoding="utf-8") as f:
        return {json.loads(line).get("hash") for line in f}

def append_to_cache(path: Path):
    """Append a file's hash to the cache."""
    with CACHE_FILE.open("a", encoding="utf-8") as f:
        json.dump({"path": str(path), "hash": file_hash(path)}, f)
        f.write("\n")

def parse_datetime(date_string: str | None) -> datetime | None:
    """Safely parse an ISO 8601 datetime string into a datetime object."""
    if not date_string:
        return None
    try:
        return datetime.fromisoformat(date_string)
    except (ValueError, TypeError):
        return None

# --- Database Operations ---
async def process_product_file(file_path: Path, semaphore: asyncio.Semaphore):
    """Processes a single JSON file and inserts its data into the database."""
    async with semaphore:
        conn = None
        try:
            data = safe_load_json(file_path)
            if not data or not data.get("id"):
                logger.warning(f"Skipping empty or invalid file: {file_path}")
                return

            product_id = data["id"]

            conn = await get_db_connection()
            async with conn.transaction():
                # 1. Handle normalized columns (UPSERT and get ID)
                vendor_name = data.get("vendor")
                vendor_id = None
                if vendor_name:
                    vendor_id = await conn.fetchval(
                        'INSERT INTO vendors (name) VALUES ($1) ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name RETURNING id',
                        vendor_name
                    )

                product_type_name = data.get("product_type")
                product_type_id = None
                if product_type_name:
                    product_type_id = await conn.fetchval(
                        'INSERT INTO product_types (name) VALUES ($1) ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name RETURNING id',
                        product_type_name
                    )

                # 2. Insert Product (with datetime parsing)
                await conn.execute(
                    """INSERT INTO products (id, title, handle, body_html, published_at, created_at, updated_at, vendor_id, product_type_id, category)
                       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                       ON CONFLICT (id) DO UPDATE SET
                           title = EXCLUDED.title, handle = EXCLUDED.handle, body_html = EXCLUDED.body_html, published_at = EXCLUDED.published_at,
                           created_at = EXCLUDED.created_at, updated_at = EXCLUDED.updated_at, vendor_id = EXCLUDED.vendor_id,
                           product_type_id = EXCLUDED.product_type_id, category = EXCLUDED.category;""",
                    product_id, data.get("title"), data.get("handle"), data.get("body_html"),
                    parse_datetime(data.get("published_at")), parse_datetime(data.get("created_at")), parse_datetime(data.get("updated_at")),
                    vendor_id, product_type_id, data.get("category")
                )

                # 3. Handle Tags and Product_Tags junction table
                tag_ids = []
                if data.get("tags"):
                    for tag_name in data["tags"]:
                        tag_id = await conn.fetchval(
                            'INSERT INTO tags (name) VALUES ($1) ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name RETURNING id',
                            tag_name
                        )
                        tag_ids.append(tag_id)
                
                if tag_ids:
                    await conn.executemany(
                        'INSERT INTO product_tags (product_id, tag_id) VALUES ($1, $2) ON CONFLICT DO NOTHING',
                        [(product_id, tag_id) for tag_id in tag_ids]
                    )

                # 4. Insert Variants, Images, Options, etc. (with datetime parsing and ON CONFLICT)
                if data.get("variants"):
                    variants_to_insert = [
                        (v.get("id"), product_id, v.get("title"), v.get("option1"), v.get("option2"), v.get("option3"), v.get("sku"), v.get("price"),
                         parse_datetime(v.get("created_at")), parse_datetime(v.get("updated_at"))) for v in data["variants"]
                    ]
                    await conn.executemany(
                        """INSERT INTO variants (id, product_id, title, option1, option2, option3, sku, price, created_at, updated_at)
                           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                           ON CONFLICT (id) DO UPDATE SET
                               title = EXCLUDED.title, option1 = EXCLUDED.option1, option2 = EXCLUDED.option2, option3 = EXCLUDED.option3,
                               sku = EXCLUDED.sku, price = EXCLUDED.price, created_at = EXCLUDED.created_at, updated_at = EXCLUDED.updated_at;""",
                        variants_to_insert
                    )

                if data.get("images"):
                    images_to_insert = [
                        (i.get("id"), product_id, i.get("src"), i.get("width"), i.get("height"), i.get("position"),
                         parse_datetime(i.get("created_at")), parse_datetime(i.get("updated_at"))) for i in data["images"]
                    ]
                    await conn.executemany(
                        """INSERT INTO images (id, product_id, src, width, height, position, created_at, updated_at)
                           VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                           ON CONFLICT (id) DO UPDATE SET
                               src = EXCLUDED.src, width = EXCLUDED.width, height = EXCLUDED.height, position = EXCLUDED.position,
                               created_at = EXCLUDED.created_at, updated_at = EXCLUDED.updated_at;""",
                        images_to_insert
                    )

            # If transaction is successful, add to cache
            append_to_cache(file_path)

        except UniqueViolationError as e:
            # This is an expected error if the data has duplicates on a unique column like 'handle'.
            # We log it as a warning and move on, as the transaction will be rolled back.
            logger.warning(f"Data integrity issue for file {file_path}: {e}")
        except Exception as e:
            logger.error(f"Failed to process file {file_path}: {e}")
        finally:
            if conn:
                await conn.close()

# --- Main Execution ---
async def main():
    logger.info("Starting unified import process...")
    json_files = list(JSON_DIR.rglob("*.json.gz"))
    if not json_files:
        logger.error(f"No .json.gz files found in {JSON_DIR}")
        return

    cached_hashes = load_cached_hashes()
    to_process = [f for f in json_files if file_hash(f) not in cached_hashes]
    
    if not to_process:
        logger.info("No new files to process. Database is up to date.")
        return

    # Limit the number of files to process if the constant is set
    if MAX_FILES_TO_PROCESS > 0:
        to_process = to_process[:MAX_FILES_TO_PROCESS]

    logger.info(f"Found {len(to_process)} new files to import.")

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
    
    tasks = [process_product_file(path, semaphore) for path in to_process]
    
    # Use asyncio.as_completed with tqdm for a progress bar
    for future in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Importing Products"):
        await future

    logger.info("Unified import process completed successfully!")

if __name__ == "__main__":
    # Ensure database is running before starting
    logger.info("Please ensure the PostgreSQL container is running before starting the import.")
    # In case of Ctrl+C, we want to gracefully handle the shutdown
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Import process interrupted by user.")