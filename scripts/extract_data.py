#!/usr/bin/env python3
"""
extract_data.py
----------------------------------------
Multithreaded ETL script to extract data from JSON files and transform it into a
PostgreSQL-friendly TSV format.

Optimized for low-end hardware with features like:
- Multithreading
- Batch processing
- Caching for incremental runs
"""

import json
import hashlib
import concurrent.futures
from pathlib import Path
from tqdm import tqdm
import csv

# -------------------------------------
# Configuration
# -------------------------------------
JSON_DIR = Path("./data/json/products_by_id")
OUTPUT_DIR = Path("./scripts/psql_import")
CACHE_FILE = Path("processed_files.jsonl")
MAX_WORKERS = 4
BATCH_SIZE = 10


# -------------------------------------
# Helper Functions
# -------------------------------------
def file_hash(path: Path) -> str:
    """Return a short, consistent hash of a file path."""
    return hashlib.md5(str(path).encode()).hexdigest()[:10]


def safe_load_json(file_path: Path):
    """Safely load a JSON file and return its content or None."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


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


def process_file(file_path: Path):
    """
    Processes a single JSON file and extracts all relevant information.
    Returns a dictionary containing extracted data for different tables.
    """
    data = safe_load_json(file_path)
    if not data:
        return None

    product_id = data.get("id")

    # Product data
    product_data = {
        "id": product_id,
        "title": data.get("title"),
        "handle": data.get("handle"),
        "body_html": data.get("body_html", ""),
        "published_at": data.get("published_at"),
        "created_at": data.get("created_at"),
        "updated_at": data.get("updated_at"),
        "vendor": data.get("vendor"),
        "product_type": data.get("product_type"),
    }

    # Variants data
    variants_data = [
        {
            "id": v.get("id"),
            "product_id": product_id,
            "title": v.get("title"),
            "option1": v.get("option1"),
            "option2": v.get("option2"),
            "option3": v.get("option3"),
            "sku": v.get("sku"),
            "requires_shipping": v.get("requires_shipping"),
            "taxable": v.get("taxable"),
            "featured_image_id": v.get("featured_image", {}).get("id")
            if v.get("featured_image")
            else None,
            "available": v.get("available"),
            "price": v.get("price"),
            "compare_at_price": v.get("compare_at_price"),
            "grams": v.get("grams"),
            "position": v.get("position"),
            "created_at": v.get("created_at"),
            "updated_at": v.get("updated_at"),
        }
        for v in data.get("variants", [])
    ]

    # Images data
    images_data = [
        {
            "id": img.get("id"),
            "product_id": product_id,
            "position": img.get("position"),
            "src": img.get("src"),
            "width": img.get("width"),
            "height": img.get("height"),
            "created_at": img.get("created_at"),
            "updated_at": img.get("updated_at"),
        }
        for img in data.get("images", [])
    ]

    # Variant-Image relationships
    variant_images_data = [
        {"variant_id": variant_id, "image_id": image["id"]}
        for image in data.get("images", [])
        for variant_id in image.get("variant_ids", [])
    ]

    # Tags
    tags_data = data.get("tags", [])

    # Product-Tag relationships
    product_tags_data = [{"product_id": product_id, "tag": tag} for tag in tags_data]

    # Options
    options_data = [
        {
            "product_id": product_id,
            "name": opt.get("name"),
            "position": opt.get("position"),
        }
        for opt in data.get("options", [])
    ]

    # Option Values
    option_values_data = [
        {
            "product_id": product_id,
            "option_position": opt.get("position"),
            "option_name": opt.get("name"),
            "value": value,
        }
        for opt in data.get("options", [])
        for value in opt.get("values", [])
    ]

    return {
        "products": [product_data],
        "variants": variants_data,
        "images": images_data,
        "variant_images": variant_images_data,
        "tags": tags_data,
        "product_tags": product_tags_data,
        "vendors": [data.get("vendor")] if data.get("vendor") else [],
        "product_types": [data.get("product_type")] if data.get("product_type") else [],
        "options": options_data,
        "option_values": option_values_data,
    }


def write_batch_to_tsv(output_dir: Path, batch_data: dict):
    """Writes a batch of data to the corresponding TSV files."""
    for key, data in batch_data.items():
        if not data:
            continue

        file_path = output_dir / f"{key}.tsv"
        # Use 'a' mode to append to the file
        with file_path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter="\t")
            for item in data:
                if isinstance(item, dict):
                    writer.writerow(item.values())
                else:
                    writer.writerow([item])


# -------------------------------------
# Main Processing Logic
# -------------------------------------
def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    json_files = list(JSON_DIR.rglob("*.json"))
    if not json_files:
        print(f"❌ No JSON files found in {JSON_DIR}")
        return

    cached_hashes = load_cached_hashes()
    to_process = [f for f in json_files if file_hash(f) not in cached_hashes]

    print(f"✅ Loaded {len(cached_hashes)} cached file hashes.")
    print(f"🔍 Found {len(to_process)} new files to process.")

    batch_data = {
        "products": [],
        "variants": [],
        "images": [],
        "variant_images": [],
        "tags": set(),
        "product_tags": [],
        "vendors": set(),
        "product_types": set(),
        "options": [],
        "option_values": [],
    }

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_file, path): path for path in to_process}

        for future in tqdm(
            concurrent.futures.as_completed(futures),
            total=len(futures),
            desc="Processing Files",
            unit="file",
        ):
            path = futures[future]
            try:
                result = future.result()
                if result:
                    for key, data in result.items():
                        if isinstance(batch_data[key], list):
                            batch_data[key].extend(data)
                        elif isinstance(batch_data[key], set):
                            batch_data[key].update(data)

                    if len(batch_data["products"]) >= BATCH_SIZE:
                        write_batch_to_tsv(OUTPUT_DIR, batch_data)
                        # Clear lists after writing
                        for key in batch_data:
                            if isinstance(batch_data[key], list):
                                batch_data[key].clear()

                    append_to_cache(path)

            except Exception as e:
                print(f"⚠️ Error processing {path}: {e}")

    # Write any remaining data in the batch
    write_batch_to_tsv(OUTPUT_DIR, batch_data)

    # Process unique sets (vendors, product_types, tags) and write to TSV
    for key in ["vendors", "product_types", "tags"]:
        with (OUTPUT_DIR / f"{key}.tsv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter="\t")
            for i, item in enumerate(sorted(list(batch_data[key])), 1):
                writer.writerow([i, item])

    print("\n✅ ETL process completed successfully!")
    print(f"💾 Data extracted to: {OUTPUT_DIR}")


# -------------------------------------
# Entry Point
# -------------------------------------
if __name__ == "__main__":
    main()
