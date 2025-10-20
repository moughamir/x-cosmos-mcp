#!/usr/bin/env python3
"""
optimus_v4_normalizer.py (streaming + multithreaded + tqdm)

- Streams gzipped product JSON files from disk
- Uses ThreadPoolExecutor to process files concurrently
- Each product is normalized and saved to disk individually (product_{id}.json)
- Progress bars and detailed logging are included

Usage:
    python optimus_v4_normalizer.py --tag-csv analysis_output/tag_analysis_*.csv --type-csv analysis_output/type_analysis_*.csv --input-folder data/json/products_by_id --output-dir normalized_output --workers 4
"""

import json
import csv
import logging
import argparse
import gzip
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from logging.handlers import TimedRotatingFileHandler
import threading

load_dotenv()


# ---------- Logging setup ----------
def setup_logger(name: str, output_dir: Path):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s: %(message)s", "%Y-%m-%dT%H:%M:%S%z"
    )
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    output_dir.mkdir(parents=True, exist_ok=True)
    logfile = output_dir / f"{name}_{datetime_now_str()}.log"
    fh = TimedRotatingFileHandler(str(logfile), when="midnight", backupCount=7)
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    return logger


def datetime_now_str():
    from datetime import datetime

    return datetime.now().strftime("%Y%m%d_%H%M%S")


# ---------- Normalizer ----------
class ProductNormalizer:
    def __init__(
        self,
        output_dir: str = "normalized_output",
        input_folder: str = "data/json/products_by_id",
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.input_folder = Path(input_folder)

        # Try to configure supabase client if provided
        self.supabase = None
        if supabase_url and supabase_key:
            try:
                from supabase import create_client

                self.supabase = create_client(supabase_url, supabase_key)
            except Exception:
                self.supabase = None

        self.tag_mappings: Dict[str, str] = {}
        self.type_mappings: Dict[str, str] = {}

        self.logger = setup_logger("optimus_v4_normalizer", self.output_dir)
        self.product_counter = 0
        self.counter_lock = threading.Lock()

    # ------------------------
    # Disk streaming (file list generator)
    # ------------------------
    def iter_gz_files(self, folder: Optional[str] = None):
        folder = Path(folder or self.input_folder)
        if not folder.exists():
            self.logger.error(f"Input folder does not exist: {folder}")
            return []
        return sorted(folder.glob("*.json.gz"))

    # ------------------------
    # CSV loaders (lowercase keys)
    # ------------------------
    def load_tag_mappings(self, csv_path: str) -> None:
        self.tag_mappings = {}
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                original = (row.get("Tag") or "").strip()
                normalized = (row.get("Suggested Normalized") or "").strip()
                if original:
                    self.tag_mappings[original.lower()] = normalized or original
        self.logger.info(
            f"Loaded {len(self.tag_mappings)} tag mappings from {csv_path}"
        )

    def load_type_mappings(self, csv_path: str) -> None:
        self.type_mappings = {}
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                original = (row.get("Original Type") or "").strip()
                suggested = (row.get("Suggested Taxonomy (LLM)") or "").strip()
                confidence = (row.get("Confidence") or "medium").strip().lower()
                if original and confidence in ["high", "medium"]:
                    self.type_mappings[original.lower()] = suggested or original
        self.logger.info(
            f"Loaded {len(self.type_mappings)} type mappings from {csv_path}"
        )

    # ------------------------
    # Normalize single product
    # ------------------------
    def normalize_product(self, product: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(product)
        # tags
        original_tags = product.get("tags", [])
        if isinstance(original_tags, str):
            original_tags = [t.strip() for t in original_tags.split(",") if t.strip()]
        elif not isinstance(original_tags, list):
            original_tags = []

        new_tags = []
        seen = set()
        for tag in original_tags:
            mapped = self.tag_mappings.get(tag.lower(), tag)
            if mapped and mapped.lower() not in seen:
                new_tags.append(mapped)
                seen.add(mapped.lower())
        normalized["tags"] = new_tags

        # product_type
        original_type = (product.get("product_type") or "").strip()
        if original_type:
            normalized["product_type"] = self.type_mappings.get(
                original_type.lower(), original_type
            )
        else:
            normalized["product_type"] = "Miscellaneous"

        return normalized

    @staticmethod
    def _safe_filename(s: str) -> str:
        keep = "".join(c if (c.isalnum() or c in "-_.") else "_" for c in s)
        return keep or "unknown"

    # ------------------------
    # Save normalized product (thread-safe per-file)
    # ------------------------
    def save_normalized_product(self, product: Dict[str, Any]) -> Optional[Path]:
        prod_id = str(product.get("id") or product.get("handle") or "")
        safe_id = self._safe_filename(prod_id) if prod_id else datetime_now_str()
        out = self.output_dir / f"product_{safe_id}.json"
        try:
            with open(out, "w", encoding="utf-8") as fh:
                json.dump(product, fh, indent=2, ensure_ascii=False)
            return out
        except Exception as e:
            self.logger.error(f"Failed to save product {prod_id} to {out}: {e}")
            return None

    # ------------------------
    # Optional Supabase upsert (defensive)
    # ------------------------
    def upsert_to_supabase(self, product: Dict[str, Any]) -> bool:
        if not self.supabase:
            return False
        try:
            payload = {
                "product_id": str(product.get("id")),
                "title": product.get("title"),
                "description": product.get("body_html") or "",
                "handle": product.get("handle"),
                "product_type": product.get("product_type"),
                "tags": product.get("tags", []),
            }
            self.supabase.table("products").upsert(
                payload, on_conflict="product_id"
            ).execute()
            return True
        except Exception as e:
            self.logger.error(f"Supabase upsert error: {e}")
            return False

    # ------------------------
    # File-level processor (called in threads)
    # ------------------------
    def _process_file(self, fp: Path, update_supabase: bool = False) -> int:
        try:
            with gzip.open(fp, "rt", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception as e:
            self.logger.error(f"Error reading {fp}: {e}")
            return 0

        count = 0
        records = (
            data if isinstance(data, list) else [data] if isinstance(data, dict) else []
        )
        for product in records:
            normalized = self.normalize_product(product)
            saved = self.save_normalized_product(normalized)
            if update_supabase:
                self.upsert_to_supabase(normalized)
            count += 1
            with self.counter_lock:
                self.product_counter += 1
        return count

    # ------------------------
    # Main runner (stream + multithread)
    # ------------------------
    def process_all_stream(
        self,
        tag_csv: str,
        type_csv: str,
        input_folder: Optional[str] = None,
        workers: int = 4,
        max_files: Optional[int] = None,
        update_supabase: bool = False,
        show_progress: bool = True,
    ):
        # Load mappings
        self.load_tag_mappings(tag_csv)
        self.load_type_mappings(type_csv)

        files = list(self.iter_gz_files(input_folder))
        if max_files:
            files = files[:max_files]

        total_files = len(files)
        if total_files == 0:
            self.logger.warning("No gz files found to process.")
            return {"total_files": 0, "total_products": 0}

        self.logger.info(
            f"Starting normalization: {total_files} files, workers={workers}"
        )

        processed_files = 0
        pbar = tqdm(
            total=total_files,
            desc="Normalizing files",
            unit="file",
            disable=not show_progress,
        )
        futures = []
        with ThreadPoolExecutor(max_workers=workers) as exec:
            for fp in files:
                futures.append(exec.submit(self._process_file, fp, update_supabase))

            for fut in as_completed(futures):
                try:
                    cnt = fut.result()
                except Exception as e:
                    self.logger.error(f"Worker error: {e}")
                    cnt = 0
                processed_files += 1
                pbar.update(1)
                pbar.set_postfix({"products_total": self.product_counter})
        pbar.close()

        self.logger.info(
            f"Normalization complete. Files processed: {processed_files}, Products: {self.product_counter}"
        )
        return {"total_files": processed_files, "total_products": self.product_counter}


# CLI
def main():
    parser = argparse.ArgumentParser(
        description="Streamed product normalizer (multithreaded)"
    )
    parser.add_argument(
        "--tag-csv", required=True, help="Tag analysis CSV generated by analyzer"
    )
    parser.add_argument(
        "--type-csv", required=True, help="Type analysis CSV generated by analyzer"
    )
    parser.add_argument("--input-folder", default="data/json/products_by_id")
    parser.add_argument("--output-dir", default="normalized_output")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument(
        "--max-files", type=int, help="Limit number of gz files to process"
    )
    parser.add_argument("--update-supabase", action="store_true")
    parser.add_argument(
        "--no-progress", action="store_true", help="Disable tqdm output"
    )

    args = parser.parse_args()

    normalizer = ProductNormalizer(
        output_dir=args.output_dir, input_folder=args.input_folder
    )
    res = normalizer.process_all_stream(
        tag_csv=args.tag_csv,
        type_csv=args.type_csv,
        input_folder=args.input_folder,
        workers=args.workers,
        max_files=args.max_files,
        update_supabase=args.update_supabase,
        show_progress=not args.no_progress,
    )
    normalizer.logger.info(f"Normalizer results: {res}")


if __name__ == "__main__":
    main()
