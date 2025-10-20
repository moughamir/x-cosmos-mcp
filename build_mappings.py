#!/usr/bin/env python3
"""
build_mappings.py
Generate suggested tag_mappings.csv and type_mappings.csv from the analyzer outputs.
Optional: use Ollama to suggest google root categories (set OLLAMA_URL env to use).
"""

import csv
import os
import requests
from pathlib import Path
from typing import Optional

OLLAMA_URL = os.getenv("OLLAMA_URL")  # e.g. http://localhost:11434
EMBED_MODEL = "nomic-embed-text"  # not used here, placeholder


def simple_canonical_tag(tag: str) -> str:
    # Basic normalization rules: lowercase, strip, replace non-alnum with hyphen, collapse hyphens
    s = tag.strip().lower()
    import re

    s = re.sub(r"[^\w\d]+", "-", s)  # non-alnum -> hyphen
    s = re.sub(r"-{2,}", "-", s)  # collapse multiple hyphens
    s = s.strip("-")
    return s or "other"


def suggest_root_category_via_ollama(
    product_type: str, sample_taxonomy: list
) -> Optional[str]:
    if not OLLAMA_URL:
        return None
    prompt = f"""Map the following product type to one of these root taxonomy labels (choose only one and return it exactly):
{chr(10).join(sample_taxonomy)}

Product type: "{product_type}" """
    try:
        r = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": "qwen2:0.5b",
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.0, "num_predict": 64},
            },
            timeout=10,
        )
        if r.ok:
            out = r.json().get("response", "").strip()
            return out
    except Exception as e:
        print("OLLAMA suggestion failed:", e)
    return None


def build_tag_mappings(
    tag_csv_path: str, out_csv: str = "tag_mappings.csv", top_n: int = 5000
):
    tags = []
    with open(tag_csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            tag = (row.get("Tag") or "").strip()
            cnt = int(row.get("Count") or 0)
            tags.append((tag, cnt))
    tags_sorted = sorted(tags, key=lambda x: x[1], reverse=True)[:top_n]
    with open(out_csv, "w", newline="", encoding="utf-8") as out:
        w = csv.writer(out)
        w.writerow(["original_tag", "canonical_tag", "reason", "approved"])
        for t, cnt in tags_sorted:
            canonical = simple_canonical_tag(t)
            reason = "auto-normalized"
            approved = "no" if canonical == "other" else "no"  # require manual check
            w.writerow([t, canonical, reason, approved])
    print("Wrote", out_csv)


def build_type_mappings(
    type_csv_path: str,
    taxonomy_roots: list,
    out_csv: str = "type_mappings.csv",
    top_n: int = 2000,
):
    types = []
    with open(type_csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            ptype = (row.get("Original Type") or "").strip()
            cnt = int(row.get("Count") or 0)
            types.append((ptype, cnt))
    types_sorted = sorted(types, key=lambda x: x[1], reverse=True)[:top_n]
    with open(out_csv, "w", newline="", encoding="utf-8") as out:
        w = csv.writer(out)
        w.writerow(
            [
                "original_type",
                "google_root_category",
                "google_path",
                "suggested_by",
                "confidence",
                "approved",
            ]
        )
        for p, cnt in types_sorted:
            # try a heuristic: check tokens that match root names
            p_low = p.lower()
            matched_root = None
            for root in taxonomy_roots:
                if root.lower() in p_low:
                    matched_root = root
                    break
            suggested = matched_root
            suggested_by = (
                "rule" if matched_root else "llm" if OLLAMA_URL else "heuristic"
            )
            confidence = "high" if matched_root else "low"
            if not suggested and OLLAMA_URL:
                llm_s = suggest_root_category_via_ollama(p, taxonomy_roots)
                if llm_s:
                    suggested = llm_s
                    confidence = "medium"
            if not suggested:
                suggested = "Other"
            w.writerow([p, suggested, "", suggested_by, confidence, "no"])
    print("Wrote", out_csv)


if __name__ == "__main__":
    # discover analyzer CSVs (pick latest)
    ap = Path("analysis_output")
    tag_csv = None
    type_csv = None
    if ap.exists():
        tag_matches = sorted(ap.glob("tag_analysis_*.csv"), reverse=True)
        type_matches = sorted(ap.glob("type_analysis_*.csv"), reverse=True)
        if tag_matches:
            tag_csv = str(tag_matches[0])
        if type_matches:
            type_csv = str(type_matches[0])
    if not tag_csv or not type_csv:
        print("Analyzer CSVs not found in analysis_output/. Run analyzer first.")
        raise SystemExit(1)

    # Example list of google root taxonomy labels (short)
    google_roots = [
        "Animals & Pet Supplies",
        "Apparel & Accessories",
        "Arts & Entertainment",
        "Baby & Toddler",
        "Business & Industrial",
        "Cameras & Optics",
        "Electronics",
        "Food, Beverages & Tobacco",
        "Furniture",
        "Hardware",
        "Health & Beauty",
        "Home & Garden",
        "Luggage & Bags",
        "Media",
        "Office Supplies",
        "Religious & Ceremonial",
        "Software",
        "Sporting Goods",
        "Toys & Games",
        "Vehicles & Parts",
        "Other",
    ]

    build_tag_mappings(tag_csv, out_csv="tag_mappings.csv", top_n=10000)
    build_type_mappings(
        type_csv, taxonomy_roots=google_roots, out_csv="type_mappings.csv", top_n=5000
    )
