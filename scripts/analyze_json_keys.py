#!/usr/bin/env python3
"""
analyze_json_keys.py
----------------------------------------
Multithreaded JSON key analyzer for large datasets.
Optimized for low-end hardware.
Caches partial results safely for incremental runs.
"""

import json
import hashlib
import concurrent.futures
from pathlib import Path
from tqdm import tqdm

# -------------------------------------
# Configuration
# -------------------------------------
JSON_DIR = Path("data/json/products_by_id")
CACHE_FILE = Path("data/json/keys_partial_cache.jsonl")
OUTPUT_FILE = Path("data/json/all_keys.json")
MAX_WORKERS = 4  # Adjust based on your CPU
SAVE_EVERY = 100  # Flush cache every N files


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


def extract_top_level_keys(file_path: Path):
    """Extract top-level keys from a JSON file."""
    data = safe_load_json(file_path)
    return list(data.keys()) if isinstance(data, dict) else []


def load_cached_entries(cache_file: Path) -> dict:
    """Load cached entries and return both seen hashes and all keys."""
    seen_hashes = set()
    all_keys = set()

    if not cache_file.exists():
        return {"hashes": seen_hashes, "keys": all_keys}

    with cache_file.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line)
                seen_hashes.add(entry.get("hash"))
                all_keys.update(entry.get("keys", []))
            except json.JSONDecodeError:
                continue

    return {"hashes": seen_hashes, "keys": all_keys}


def append_to_cache(file_path: Path, keys: list):
    """Append one file’s result to the cache JSONL file."""
    entry = {"path": str(file_path), "hash": file_hash(file_path), "keys": keys}
    with CACHE_FILE.open("a", encoding="utf-8") as f:
        json.dump(entry, f)
        f.write("\n")


def write_output(keys: set):
    """Write the current set of keys to the output JSON file."""
    with OUTPUT_FILE.open("w", encoding="utf-8") as out:
        json.dump(sorted(keys), out, indent=2)


# -------------------------------------
# Main Processing Logic
# -------------------------------------
def main():
    json_files = list(JSON_DIR.rglob("*.json"))
    if not json_files:
        print(f"❌ No JSON files found in {JSON_DIR}")
        return

    cache = load_cached_entries(CACHE_FILE)
    seen_hashes = cache["hashes"]
    all_keys = cache["keys"]

    print(f"✅ Loaded {len(seen_hashes)} cached entries")
    to_process = [f for f in json_files if file_hash(f) not in seen_hashes]
    print(f"🔍 Found {len(to_process)} new files to process")

    processed_count = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(extract_top_level_keys, path): path for path in to_process
        }

        for future in tqdm(
            concurrent.futures.as_completed(futures),
            total=len(futures),
            desc="Processing",
            unit="file",
        ):
            path = futures[future]
            try:
                keys = future.result()
                if keys:
                    append_to_cache(path, keys)
                    all_keys.update(keys)
            except Exception as e:
                print(f"⚠️  Error processing {path}: {e}")
                continue

            processed_count += 1
            if processed_count % SAVE_EVERY == 0:
                write_output(all_keys)

    # Final write
    write_output(all_keys)

    print(f"\n✅ Done! Processed {processed_count} new files.")
    print(f"🗝️  Unique top-level keys: {len(all_keys)}")
    print(f"💾 Results saved to: {OUTPUT_FILE}")
    print(f"🧩 Partial cache stored in: {CACHE_FILE}")


# -------------------------------------
# Entry Point
# -------------------------------------
if __name__ == "__main__":
    main()
