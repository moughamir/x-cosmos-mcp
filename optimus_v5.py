#!/usr/bin/env python3
"""
optimus_v4.py (streaming + tqdm)

- Streams gzipped product JSON files from disk (data/json/products_by_id/*.json.gz)
- Processes file-by-file (each file may contain a single JSON object or an array)
- Produces CSV analysis outputs
- Uses tqdm for progress and writes logs (console + file) with timestamps

Usage:
    python optimus_v4.py --input-folder data/json/products_by_id --output-dir analysis_output --batch-size 50
"""

import os
import json
import gzip
import csv
import logging
import argparse
import requests
from pathlib import Path
from typing import Dict, List, Any, Tuple, Iterator
from collections import defaultdict
from dotenv import load_dotenv
from datetime import datetime
from tqdm import tqdm
from logging.handlers import TimedRotatingFileHandler

load_dotenv()


# ---------- Logging setup ----------
def setup_logger(name: str, output_dir: Path):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s: %(message)s", "%Y-%m-%dT%H:%M:%S%z"
    )

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    output_dir.mkdir(parents=True, exist_ok=True)
    logfile = output_dir / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    fh = TimedRotatingFileHandler(str(logfile), when="midnight", backupCount=7)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger


# ---------- Analyzer ----------
class ProductAnalyzer:
    def __init__(
        self,
        ollama_url: str = None,
        ollama_model: str = "qwen2:0.5b",
        taxonomy_dir: str = "data/taxonomy",
        output_dir: str = "analysis_output",
        input_folder: str = "data/json/products_by_id",
    ):
        self.ollama_url = ollama_url or os.getenv(
            "OLLAMA_URL", "http://localhost:11434"
        )
        self.ollama_model = ollama_model

        self.taxonomy = self._load_taxonomies(taxonomy_dir)
        self.taxonomy_lookup = self._build_taxonomy_lookup()

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.input_folder = Path(input_folder)

        self.products_seen = 0
        self.tag_analysis = defaultdict(lambda: {"count": 0, "product_ids": []})
        self.type_analysis = defaultdict(lambda: {"count": 0, "product_ids": []})

        self.logger = setup_logger("optimus_v4_analyzer", self.output_dir)
        self.logger.info(
            f"Analyzer initialized. Input: {self.input_folder}, Output: {self.output_dir}"
        )

    def _load_taxonomies(self, taxonomy_dir: str) -> List[str]:
        tax = []
        p = Path(taxonomy_dir)
        if not p.exists():
            self.logger.warning(f"Taxonomy directory not found: {taxonomy_dir}")
            return tax

        for f in sorted(p.glob("*.txt")):
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        tax.append(line)
                self.logger.info(f"Loaded taxonomy entries from {f.name}")
            except Exception as e:
                self.logger.error(f"Error loading taxonomy {f}: {e}")
        return tax

    def _build_taxonomy_lookup(self) -> Dict[str, List[str]]:
        lookup = defaultdict(list)
        for taxonomy in self.taxonomy:
            parts = taxonomy.split(" > ")
            for part in parts:
                key = part.lower().strip()
                lookup[key].append(taxonomy)
        return dict(lookup)

    # ---------------------
    # Streaming disk reader
    # ---------------------
    def iter_gz_json_files(self, folder: str = None) -> Iterator[Path]:
        folder = Path(folder or self.input_folder)
        if not folder.exists():
            self.logger.error(f"Input folder does not exist: {folder}")
            return
        for fp in sorted(folder.glob("*.json.gz")):
            yield fp

    def process_file(self, fp: Path):
        try:
            with gzip.open(fp, "rt", encoding="utf-8") as fh:
                data = json.load(fh)
                if isinstance(data, dict):
                    records = [data]
                elif isinstance(data, list):
                    records = data
                else:
                    self.logger.debug(f"Skipping file with unexpected JSON type: {fp}")
                    return 0
        except Exception as e:
            self.logger.error(f"Failed to read {fp}: {e}")
            return 0

        count = 0
        for product in records:
            self._analyze_product(product)
            count += 1
        return count

    # ---------------------
    # Analysis helpers
    # ---------------------
    def _analyze_product(self, product: Dict[str, Any]):
        pid = str(product.get("id", "unknown"))
        # tags
        tags = product.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        for t in tags:
            key = t.strip().lower()
            self.tag_analysis[key]["count"] += 1
            self.tag_analysis[key]["product_ids"].append(pid)
        # product_type
        ptype = (product.get("product_type") or "").strip()
        if ptype:
            key = ptype.lower()
            self.type_analysis[key]["count"] += 1
            self.type_analysis[key]["product_ids"].append(pid)

    # ---------------------
    # Exports
    # ---------------------
    def export_tag_analysis_csv(self) -> str:
        out = (
            self.output_dir
            / f"tag_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        with open(out, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(
                ["Tag", "Count", "Product IDs (sample)", "Suggested Normalized"]
            )
            for tag, data in sorted(
                self.tag_analysis.items(), key=lambda x: x[1]["count"], reverse=True
            ):
                sample = ", ".join(data["product_ids"][:5])
                if len(data["product_ids"]) > 5:
                    sample += f" ... ({len(data['product_ids'])} total)"
                writer.writerow([tag, data["count"], sample, self._normalize_tag(tag)])
        self.logger.info(f"Wrote tag CSV: {out}")
        return str(out)

    def export_type_analysis_csv(self) -> str:
        out = (
            self.output_dir
            / f"type_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        with open(out, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(
                [
                    "Original Type",
                    "Count",
                    "Product IDs (sample)",
                    "Suggested Taxonomy (LLM)",
                    "Confidence",
                ]
            )
            for idx, (ptype, data) in enumerate(
                sorted(
                    self.type_analysis.items(),
                    key=lambda x: x[1]["count"],
                    reverse=True,
                )
            ):
                sample = ", ".join(data["product_ids"][:5])
                if len(data["product_ids"]) > 5:
                    sample += f" ... ({len(data['product_ids'])} total)"
                suggested, confidence = self._suggest_taxonomy_llm(ptype)
                writer.writerow([ptype, data["count"], sample, suggested, confidence])
                if (idx + 1) % 50 == 0:
                    self.logger.info(f"Exported {idx+1} type rows")
        self.logger.info(f"Wrote type CSV: {out}")
        return str(out)

    def _normalize_tag(self, tag: str) -> str:
        normalized = " ".join(tag.strip().lower().split())
        return normalized.title()

    def _suggest_taxonomy_llm(self, product_type: str) -> Tuple[str, str]:
        direct = self._find_direct_taxonomy_match(product_type)
        if direct:
            return direct, "high"

        # Minimal LLM call; keep defensive
        sample_tax = self.taxonomy[:30]
        prompt = (
            f'Given this product type: "{product_type}"\nPick the best match from:\n'
            + "\n".join(sample_tax[:30])
        )
        try:
            resp = requests.post(
                f"{self.ollama_url}/api/generate",
                json={"model": self.ollama_model, "prompt": prompt, "stream": False},
                timeout=15,
            )
            if resp.ok:
                result = resp.json().get("response", "").strip()
                if result in self.taxonomy:
                    return result, "medium"
                for tax in self.taxonomy:
                    if result.lower() in tax.lower():
                        return tax, "low"
        except Exception as e:
            self.logger.debug(
                f"LLM taxonomy suggestion failed for '{product_type}': {e}"
            )
        return "Miscellaneous", "none"

    def _find_direct_taxonomy_match(self, product_type: str) -> Any:
        key = (product_type or "").lower().strip()
        if not key:
            return None
        if key in self.taxonomy_lookup:
            return self.taxonomy_lookup[key][0]
        for tax_key, tax_list in self.taxonomy_lookup.items():
            if key in tax_key or tax_key in key:
                return tax_list[0]
        return None

    # ---------------------
    # Runner
    # ---------------------
    def run_analysis(self, max_files: int = None, show_progress: bool = True):
        self.logger.info("Starting analysis (streaming)...")
        files_iter = list(self.iter_gz_json_files(self.input_folder))
        if max_files:
            files_iter = files_iter[:max_files]

        total_files = len(files_iter)
        pbar = tqdm(
            files_iter,
            desc="Analyzing files",
            unit="file",
            disable=not show_progress,
            total=total_files,
        )
        processed_products = 0
        for fp in pbar:
            cnt = self.process_file(fp)
            processed_products += cnt
            self.products_seen += cnt
            pbar.set_postfix({"products": processed_products})
        pbar.close()

        self.logger.info(
            f"Analysis complete. Files processed: {total_files}, Products seen: {processed_products}"
        )
        tag_csv = self.export_tag_analysis_csv()
        type_csv = self.export_type_analysis_csv()
        return {
            "total_files": total_files,
            "total_products": processed_products,
            "tag_csv": tag_csv,
            "type_csv": type_csv,
        }


# CLI
def main():
    parser = argparse.ArgumentParser(description="Stream product analysis")
    parser.add_argument("--input-folder", default="data/json/products_by_id")
    parser.add_argument("--output-dir", default="analysis_output")
    parser.add_argument(
        "--max-files", type=int, help="Limit number of gz files to process"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Not used for disk streaming; kept for backwards compatibility",
    )
    parser.add_argument(
        "--no-progress", action="store_true", help="Disable tqdm progress bar"
    )
    parser.add_argument("--ollama-url", type=str, default=None)
    parser.add_argument("--ollama-model", default="qwen2:0.5b")

    args = parser.parse_args()

    analyzer = ProductAnalyzer(
        ollama_url=args.ollama_url,
        ollama_model=args.ollama_model,
        input_folder=args.input_folder,
        output_dir=args.output_dir,
    )
    res = analyzer.run_analysis(
        max_files=args.max_files, show_progress=not args.no_progress
    )
    analyzer.logger.info(f"Results: {res}")


if __name__ == "__main__":
    main()
