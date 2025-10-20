#!/usr/bin/env python3
"""
optimus_v4.py (updated)
Product data analysis and normalization pipeline.

Changes:
- Added ability to read products from disk: data/json/products_by_id/*.json.gz
- Added CLI options: --source (disk|api), --input-folder, --taxonomy-dir, --ollama-url, etc.
- Handles gzipped single-product files or files containing arrays.
- Processes disk input in batches to avoid huge memory spikes.
- Minor robustness and logging improvements.

Based on your original uploaded file. :contentReference[oaicite:2]{index=2}
"""

import os
import json
import gzip
import csv
import logging
import argparse
import requests
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict
from dotenv import load_dotenv
from datetime import datetime
from glob import glob

# Setup logging
load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("optimus_v4_analyzer")


class ProductAnalyzer:
    def __init__(
        self,
        cosmos_api_url: str = None,
        cosmos_api_key: str = None,
        ollama_url: str = None,
        ollama_model: str = "qwen2:0.5b",
        taxonomy_dir: str = "data/taxonomy",
        output_dir: str = "analysis_output",
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

        # Load taxonomy
        self.taxonomy = self._load_taxonomies(taxonomy_dir)
        self.taxonomy_lookup = self._build_taxonomy_lookup()

        # Output directory
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Input folder for local disk reading
        self.input_folder = Path(input_folder)

        # Analysis storage
        self.products = []
        self.tag_analysis = defaultdict(lambda: {"count": 0, "product_ids": []})
        self.type_analysis = defaultdict(lambda: {"count": 0, "product_ids": []})

        logger.info(f"Initialized analyzer with model: {self.ollama_model}")

    def _load_taxonomies(self, taxonomy_dir: str) -> List[str]:
        tax = []
        p = Path(taxonomy_dir)
        if not p.exists():
            logger.warning(f"Taxonomy directory not found: {taxonomy_dir}")
            return tax

        for f in sorted(p.glob("*.txt")):
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        tax.append(line)
                logger.info(f"Loaded {len(tax)} taxonomy entries from {f.name}")
            except Exception as e:
                logger.error(f"Error loading {f}: {e}")

        return tax

    def _build_taxonomy_lookup(self) -> Dict[str, List[str]]:
        lookup = defaultdict(list)
        for taxonomy in self.taxonomy:
            parts = taxonomy.split(" > ")
            for i, part in enumerate(parts):
                key = part.lower().strip()
                lookup[key].append(taxonomy)
        return dict(lookup)

    # ------------------------
    # Disk reading utilities
    # ------------------------
    def _iter_product_files(self, folder: str = None):
        folder = folder or str(self.input_folder)
        files = sorted(glob(os.path.join(folder, "*.json.gz")))
        for f in files:
            yield f

    def read_products_from_disk(
        self, folder: str = None, limit: int = None, batch_size: int = 100
    ):
        """
        Generator that yields batches (lists) of product dicts read from gzipped files.
        Each file may contain a single product object or an array of products.
        """
        folder = folder or str(self.input_folder)
        files = sorted(glob(os.path.join(folder, "*.json.gz")))
        if limit:
            files = files[:limit]

        batch = []
        for idx, fp in enumerate(files):
            try:
                with gzip.open(fp, "rt", encoding="utf-8") as fh:
                    data = json.load(fh)
                    if isinstance(data, list):
                        for item in data:
                            batch.append(item)
                    elif isinstance(data, dict):
                        batch.append(data)
                    else:
                        logger.debug(f"Unexpected JSON type in {fp}: {type(data)}")
            except Exception as e:
                logger.error(f"Failed to read {fp}: {e}")

            if len(batch) >= batch_size:
                yield batch
                batch = []

        if batch:
            yield batch

    # ------------------------
    # API fetching (legacy)
    # ------------------------
    def fetch_products_compressed(
        self, limit: int = 100, offset: int = 0
    ) -> List[Dict]:
        headers = {"X-API-Key": self.cosmos_api_key} if self.cosmos_api_key else {}
        params = {"limit": limit, "offset": offset}
        url = f"{self.cosmos_api_url}/products"

        try:
            r = requests.get(url, headers=headers, params=params, timeout=30)
            r.raise_for_status()

            content_encoding = r.headers.get("Content-Encoding", "").lower()
            if content_encoding == "gzip" or url.endswith(".gz"):
                data = json.loads(gzip.decompress(r.content).decode("utf-8"))
            else:
                data = r.json()

            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                return data.get("products") or data.get("data") or []
            return []
        except Exception as e:
            logger.error(f"Error fetching products: {e}")
            return []

    # ------------------------
    # Analysis routines
    # ------------------------
    def analyze_tags(self, products: List[Dict]) -> None:
        for product in products:
            product_id = str(product.get("id", "unknown"))
            tags = product.get("tags", [])
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]
            for tag in tags:
                tag_normalized = tag.strip().lower()
                self.tag_analysis[tag_normalized]["count"] += 1
                self.tag_analysis[tag_normalized]["product_ids"].append(product_id)

    def analyze_product_types(self, products: List[Dict]) -> None:
        for product in products:
            product_id = str(product.get("id", "unknown"))
            product_type = (product.get("product_type") or "").strip()
            if product_type:
                type_normalized = product_type.lower()
                self.type_analysis[type_normalized]["count"] += 1
                self.type_analysis[type_normalized]["product_ids"].append(product_id)

    def export_tag_analysis_csv(self) -> str:
        output_file = (
            self.output_dir
            / f"tag_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )

        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["Tag", "Count", "Product IDs (sample)", "Suggested Normalized"]
            )

            sorted_tags = sorted(
                self.tag_analysis.items(), key=lambda x: x[1]["count"], reverse=True
            )

            for tag, data in sorted_tags:
                sample_ids = ", ".join(data["product_ids"][:5])
                if len(data["product_ids"]) > 5:
                    sample_ids += f" ... ({len(data['product_ids'])} total)"
                normalized = self._normalize_tag(tag)
                writer.writerow([tag, data["count"], sample_ids, normalized])

        logger.info(f"Tag analysis exported to: {output_file}")
        return str(output_file)

    def export_type_analysis_csv(self) -> str:
        output_file = (
            self.output_dir
            / f"type_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )

        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "Original Type",
                    "Count",
                    "Product IDs (sample)",
                    "Suggested Taxonomy (LLM)",
                    "Confidence",
                ]
            )

            sorted_types = sorted(
                self.type_analysis.items(), key=lambda x: x[1]["count"], reverse=True
            )

            for idx, (ptype, data) in enumerate(sorted_types):
                sample_ids = ", ".join(data["product_ids"][:5])
                if len(data["product_ids"]) > 5:
                    sample_ids += f" ... ({len(data['product_ids'])} total)"
                suggested, confidence = self._suggest_taxonomy_llm(ptype)
                writer.writerow(
                    [ptype, data["count"], sample_ids, suggested, confidence]
                )

                if (idx + 1) % 10 == 0:
                    logger.info(
                        f"Processed {idx + 1}/{len(sorted_types)} product types"
                    )

        logger.info(f"Type analysis exported to: {output_file}")
        return str(output_file)

    def _normalize_tag(self, tag: str) -> str:
        normalized = tag.strip().lower()
        normalized = " ".join(normalized.split())
        return normalized.title()

    def _suggest_taxonomy_llm(self, product_type: str) -> Tuple[str, str]:
        direct_match = self._find_direct_taxonomy_match(product_type)
        if direct_match:
            return direct_match, "high"

        sample_taxonomies = self.taxonomy[:50]
        prompt = f"""Given this product type: "{product_type}"

Select the MOST APPROPRIATE category from this taxonomy list:
{chr(10).join(sample_taxonomies[:30])}

Respond with ONLY the category path, nothing else.
If no good match, respond with "Miscellaneous"."""

        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1, "num_predict": 100},
                },
                timeout=30,
            )

            if response.ok:
                result = response.json().get("response", "").strip()
                if result in self.taxonomy:
                    return result, "medium"
                for tax in self.taxonomy:
                    if result.lower() in tax.lower():
                        return tax, "low"

        except Exception as e:
            logger.debug(f"LLM suggestion failed for '{product_type}': {e}")

        return "Miscellaneous", "none"

    def _find_direct_taxonomy_match(self, product_type: str) -> str:
        key = product_type.lower().strip()
        if key in self.taxonomy_lookup:
            matches = self.taxonomy_lookup[key]
            return matches[0] if matches else None

        for tax_key, taxonomies in self.taxonomy_lookup.items():
            if key in tax_key or tax_key in key:
                return taxonomies[0]

        return None

    # ------------------------
    # Main run (supports disk or api)
    # ------------------------
    def run_analysis(
        self, source: str = "disk", max_products: int = None, batch_size: int = 100
    ):
        """
        source: 'disk' or 'api'
        """
        logger.info("Starting product analysis pipeline...")
        total_processed = 0

        if source == "disk":
            # process in batches via generator
            for batch in self.read_products_from_disk(
                folder=str(self.input_folder), limit=max_products, batch_size=batch_size
            ):
                self.products.extend(batch)
                self.analyze_tags(batch)
                self.analyze_product_types(batch)
                total_processed += len(batch)
                logger.info(f"Processed {total_processed} products so far (disk)")
                if max_products and total_processed >= max_products:
                    break
        else:
            # API path (legacy)
            offset = 0
            while True:
                limit = batch_size
                if max_products:
                    limit = min(batch_size, max_products - total_processed)
                    if limit <= 0:
                        break

                products = self.fetch_products_compressed(limit=limit, offset=offset)
                if not products:
                    break

                self.products.extend(products)
                self.analyze_tags(products)
                self.analyze_product_types(products)

                total_processed += len(products)
                offset += len(products)

                logger.info(f"Processed {total_processed} products so far (api)")

                if max_products and total_processed >= max_products:
                    break

        logger.info(f"Analysis complete. Total products: {total_processed}")

        tag_csv = self.export_tag_analysis_csv()
        type_csv = self.export_type_analysis_csv()

        logger.info(f"Unique tags found: {len(self.tag_analysis)}")
        logger.info(f"Unique product types found: {len(self.type_analysis)}")

        return {
            "total_products": total_processed,
            "unique_tags": len(self.tag_analysis),
            "unique_types": len(self.type_analysis),
            "tag_csv": tag_csv,
            "type_csv": type_csv,
        }


def main():
    parser = argparse.ArgumentParser(
        description="Analyze product data for normalization"
    )
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
    parser.add_argument("--limit", type=int, help="Max products to analyze")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size")
    parser.add_argument("--model", type=str, default="qwen2:0.5b", help="Ollama model")
    parser.add_argument(
        "--taxonomy-dir", type=str, default="data/taxonomy", help="Taxonomy folder"
    )
    parser.add_argument(
        "--output-dir", type=str, default="analysis_output", help="Output directory"
    )
    parser.add_argument(
        "--ollama-url", type=str, default=None, help="Override Ollama URL"
    )

    args = parser.parse_args()

    analyzer = ProductAnalyzer(
        ollama_model=args.model,
        taxonomy_dir=args.taxonomy_dir,
        output_dir=args.output_dir,
        input_folder=args.input_folder,
        ollama_url=args.ollama_url,
    )

    results = analyzer.run_analysis(
        source=args.source,
        max_products=args.limit,
        batch_size=args.batch_size,
    )

    logger.info("=" * 60)
    logger.info("ANALYSIS RESULTS")
    logger.info("=" * 60)
    logger.info(f"Total products analyzed: {results['total_products']}")
    logger.info(f"Unique tags found: {results['unique_tags']}")
    logger.info(f"Unique product types: {results['unique_types']}")
    logger.info(f"Tag analysis CSV: {results['tag_csv']}")
    logger.info(f"Type analysis CSV: {results['type_csv']}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
