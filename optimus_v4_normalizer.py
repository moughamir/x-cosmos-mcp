#!/usr/bin/env python3
"""
optimus_v4_normalizer.py (updated)
Apply normalization and create unified product dataset.

Changes:
- Added ability to read products from disk: data/json/products_by_id/*.json.gz
- Fixed tag mapping key normalization (store mappings lowercased)
- Add CLI options: --source (disk|api), --input-folder, --output-dir, etc.
- Save normalized products to disk (JSON files); optionally batches as JSON files.

Based on your original uploaded file. :contentReference[oaicite:3]{index=3}
"""

import os
import json
import csv
import logging
import argparse
import requests
import gzip
from pathlib import Path
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("optimus_v4_normalizer")


class ProductNormalizer:
    def __init__(
        self,
        cosmos_api_url: str = None,
        cosmos_api_key: str = None,
        ollama_url: str = None,
        ollama_model: str = "qwen2:0.5b",
        supabase_url: str = None,
        supabase_key: str = None,
        output_dir: str = "normalized_output",
        input_folder: str = "data/json/products_by_id",
    ):
        self.cosmos_api_url = cosmos_api_url or os.getenv(
            "COSMOS_API_URL", "https://moritotabi.com/cosmos"
        )
        self.cosmos_api_key = cosmos_api_key or os.getenv("COSMOS_API_KEY")
        self.ollama_url = ollama_url or os.getenv(
            "OLLAMA_URL", "http://localhost:11434"
        )
        self.ollama_model = ollama_model

        # Supabase (optional)
        supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        supabase_key = supabase_key or os.getenv("SUPABASE_SERVICE_KEY")
        try:
            if supabase_url and supabase_key:
                from supabase import create_client, Client

                self.supabase: Optional[Client] = create_client(
                    supabase_url, supabase_key
                )
            else:
                self.supabase = None
                logger.info("Supabase not configured; will skip upserts.")
        except Exception:
            self.supabase = None
            logger.info(
                "Supabase client import failed or not configured; skipping upserts."
            )

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.input_folder = Path(input_folder)

        # Mapping dictionaries loaded from CSVs
        # store lowercased keys for reliable lookup
        self.tag_mappings: Dict[str, str] = {}
        self.type_mappings: Dict[str, str] = {}

    # ------------------------
    # Disk reading utilities
    # ------------------------
    def read_products_from_disk(self, folder: str = None, limit: int = None):
        folder = Path(folder or self.input_folder)
        files = sorted(folder.glob("*.json.gz"))
        if limit:
            files = files[:limit]

        products = []
        for fp in files:
            try:
                with gzip.open(fp, "rt", encoding="utf-8") as fh:
                    data = json.load(fh)
                    if isinstance(data, list):
                        products.extend(data)
                    elif isinstance(data, dict):
                        products.append(data)
                    else:
                        logger.debug(f"Unexpected JSON type in {fp}: {type(data)}")
            except Exception as e:
                logger.error(f"Error reading {fp}: {e}")
        return products

    # ------------------------
    # CSV loaders (fixed lowercase keys)
    # ------------------------
    def load_tag_mappings(self, csv_path: str) -> None:
        """Load tag mappings from analysis CSV; keys are lowercased."""
        self.tag_mappings = {}
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                original = (row.get("Tag") or "").strip()
                normalized = (row.get("Suggested Normalized") or "").strip()
                if original:
                    self.tag_mappings[original.lower()] = normalized or original
        logger.info(f"Loaded {len(self.tag_mappings)} tag mappings")

    def load_type_mappings(self, csv_path: str) -> None:
        """Load product_type mappings from analysis CSV"""
        self.type_mappings = {}
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                original = (row.get("Original Type") or "").strip()
                suggested = (row.get("Suggested Taxonomy (LLM)") or "").strip()
                confidence = (row.get("Confidence") or "medium").strip().lower()
                if original and confidence in ["high", "medium"]:
                    self.type_mappings[original.lower()] = suggested or original
        logger.info(f"Loaded {len(self.type_mappings)} type mappings")

    # ------------------------
    # Normalization
    # ------------------------
    def normalize_product(self, product: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(product)  # shallow copy

        # Normalize tags
        original_tags = product.get("tags", [])
        if isinstance(original_tags, str):
            original_tags = [t.strip() for t in original_tags.split(",") if t.strip()]
        elif not isinstance(original_tags, list):
            original_tags = []

        new_tags = []
        seen = set()
        for tag in original_tags:
            tag_lower = tag.lower()
            mapped_tag = self.tag_mappings.get(tag_lower, tag)
            if mapped_tag and mapped_tag.lower() not in seen:
                new_tags.append(mapped_tag)
                seen.add(mapped_tag.lower())

        normalized["tags"] = new_tags

        # Normalize product_type using taxonomy
        original_type = (product.get("product_type") or "").strip()
        if original_type:
            type_lower = original_type.lower()
            normalized["product_type"] = self.type_mappings.get(
                type_lower, original_type
            )
        else:
            normalized["product_type"] = "Miscellaneous"

        return normalized

    # ------------------------
    # Disk saving utilities
    # ------------------------
    @staticmethod
    def _safe_filename(s: str) -> str:
        keep = "".join(c if (c.isalnum() or c in "-_.") else "_" for c in s)
        return keep or "unknown"

    def save_normalized_product(self, product: Dict[str, Any]) -> None:
        product_id = str(product.get("id", product.get("handle", "unknown")))
        safe_id = self._safe_filename(product_id)
        output_file = self.output_dir / f"product_{safe_id}.json"
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(product, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save {output_file}: {e}")

    def save_batch_normalized(
        self, products: List[Dict[str, Any]], batch_num: int
    ) -> None:
        output_file = self.output_dir / f"batch_{batch_num:04d}.json"
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(products, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved batch {batch_num} with {len(products)} products")
        except Exception as e:
            logger.error(f"Failed to save batch {batch_num}: {e}")

    # ------------------------
    # Supabase (optional)
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
            logger.error(f"Supabase upsert failed: {e}")
            return False

    # ------------------------
    # Process runner (supports disk or api)
    # ------------------------
    def process_all(
        self,
        tag_csv: str,
        type_csv: str,
        source: str = "disk",
        input_folder: Optional[str] = None,
        max_products: int = None,
        batch_size: int = 100,
        update_supabase: bool = False,
    ):
        # Load mappings
        self.load_tag_mappings(tag_csv)
        self.load_type_mappings(type_csv)

        total_processed = 0
        batch_num = 1
        batch_products: List[Dict[str, Any]] = []

        logger.info("Starting normalization process...")

        if source == "disk":
            products = self.read_products_from_disk(
                folder=input_folder or str(self.input_folder), limit=max_products
            )
            # process in batches
            for i in range(0, len(products), batch_size):
                chunk = products[i : i + batch_size]
                for product in chunk:
                    normalized = self.normalize_product(product)
                    self.save_normalized_product(normalized)
                    batch_products.append(normalized)
                    if update_supabase:
                        self.upsert_to_supabase(normalized)
                    total_processed += 1

                if batch_products:
                    self.save_batch_normalized(batch_products, batch_num)
                    batch_num += 1
                    batch_products = []
                logger.info(f"Processed {total_processed} products")

                if max_products and total_processed >= max_products:
                    break
        else:
            # legacy API path
            offset = 0
            while True:
                limit = batch_size
                if max_products:
                    limit = min(batch_size, max_products - total_processed)
                    if limit <= 0:
                        break

                headers = (
                    {"X-API-Key": self.cosmos_api_key} if self.cosmos_api_key else {}
                )
                params = {"limit": limit, "offset": offset}
                url = f"{self.cosmos_api_url}/products"
                try:
                    r = requests.get(url, headers=headers, params=params, timeout=30)
                    r.raise_for_status()
                    data = r.json()
                except Exception as e:
                    logger.error(f"Error fetching products from API: {e}")
                    break

                if not data:
                    break

                products = (
                    data
                    if isinstance(data, list)
                    else (data.get("products") or data.get("data") or [])
                )
                for product in products:
                    normalized = self.normalize_product(product)
                    self.save_normalized_product(normalized)
                    batch_products.append(normalized)
                    if update_supabase:
                        self.upsert_to_supabase(normalized)
                    total_processed += 1

                if batch_products:
                    self.save_batch_normalized(batch_products, batch_num)
                    batch_num += 1
                    batch_products = []

                offset += len(products)
                logger.info(f"Processed {total_processed} products")
                if max_products and total_processed >= max_products:
                    break

        logger.info(f"Normalization complete. Total: {total_processed}")
        return {"total_processed": total_processed, "output_dir": str(self.output_dir)}


def main():
    parser = argparse.ArgumentParser(
        description="Normalize products using analysis results"
    )
    parser.add_argument("--tag-csv", required=True, help="Path to tag analysis CSV")
    parser.add_argument("--type-csv", required=True, help="Path to type analysis CSV")
    parser.add_argument(
        "--source",
        choices=["disk", "api"],
        default="disk",
        help="Where to read products from",
    )
    parser.add_argument(
        "--input-folder",
        type=str,
        default="data/json/products_by_id",
        help="Folder for gzipped product JSONs",
    )
    parser.add_argument("--limit", type=int, help="Max products to process")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size")
    parser.add_argument(
        "--update-supabase", action="store_true", help="Update Supabase"
    )
    parser.add_argument(
        "--output-dir", default="normalized_output", help="Output directory"
    )

    args = parser.parse_args()

    normalizer = ProductNormalizer(
        output_dir=args.output_dir,
        input_folder=args.input_folder,
    )

    results = normalizer.process_all(
        tag_csv=args.tag_csv,
        type_csv=args.type_csv,
        source=args.source,
        input_folder=args.input_folder,
        max_products=args.limit,
        batch_size=args.batch_size,
        update_supabase=args.update_supabase,
    )

    logger.info("=" * 60)
    logger.info("NORMALIZATION COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Total processed: {results['total_processed']}")
    logger.info(f"Output directory: {results['output_dir']}")


if __name__ == "__main__":
    main()
