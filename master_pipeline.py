#!/usr/bin/env python3
"""
master_pipeline.py

End-to-end product normalization pipeline:
- Streams gzipped product JSON files from disk: data/json/products_by_id/*.json.gz
- Loads mapping CSVs: tag_mappings.csv and type_mappings.csv (approved=yes only applied)
- For each product:
    - Normalize tags (mapping + canonicalization)
    - Normalize product_type (map to Google root taxonomy if mapping exists, else ask LLM or heuristic)
    - Generate SEO-optimized title and description (LLM with fallback)
    - Optimize tags (LLM or heuristic)
    - Check schema compliance (LLM or heuristic)
    - (optional) Generate embedding using an embedding model via Ollama
    - Save normalized JSON per-product and a combined JSONL
- Uses ThreadPoolExecutor + tqdm for progress

Usage:
  python master_pipeline.py --input-folder data/json/products_by_id --output-dir normalized_output --workers 4 --embed

Requirements:
  pip install requests tqdm python-dotenv jinja2 beautifulsoup4
"""

from __future__ import annotations
import os
import json
import gzip
import csv
import time
import argparse
import logging
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

# Optional BeautifulSoup for safer HTML cleaning
try:
    from bs4 import BeautifulSoup, Comment
except Exception:
    BeautifulSoup = None

import requests

# ---------- Config & Logging ----------
DEFAULT_OLLAMA = os.getenv("OLLAMA_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
GEN_MODEL = os.getenv("GEN_MODEL", "qwen2:0.5b")

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
logger = logging.getLogger("master_pipeline")
logger.setLevel(logging.INFO)
if not logger.handlers:
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s: %(message)s", "%Y-%m-%dT%H:%M:%S%z"
    )
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    fh = TimedRotatingFileHandler(
        LOG_DIR / f"master_pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
        when="midnight",
        backupCount=7,
    )
    fh.setFormatter(fmt)
    logger.addHandler(fh)


# ---------- Utilities ----------
def read_gz_json(fp: Path) -> List[Dict[str, Any]]:
    """Load a gzipped JSON file which may contain an object or an array"""
    try:
        with gzip.open(fp, "rt", encoding="utf-8") as fh:
            data = json.load(fh)
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                return [data]
            logger.debug(f"Unexpected JSON type in {fp}: {type(data)}")
            return []
    except Exception as e:
        logger.error(f"Failed reading {fp}: {e}")
        return []


def safe_json_load_from_text(text: str) -> Any:
    """Attempt to extract the first JSON object from a text blob robustly."""
    text = text.strip()
    # quick direct try
    try:
        return json.loads(text)
    except Exception:
        pass
    # try to find first { ... } balanced substring
    start = text.find("{")
    if start == -1:
        return None
    braces = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            braces += 1
        elif text[i] == "}":
            braces -= 1
            if braces == 0:
                candidate = text[start : i + 1]
                try:
                    return json.loads(candidate)
                except Exception:
                    break
    # fallback: try to locate a JSON array
    astart = text.find("[")
    if astart != -1:
        br = 0
        for i in range(astart, len(text)):
            if text[i] == "[":
                br += 1
            elif text[i] == "]":
                br -= 1
                if br == 0:
                    candidate = text[astart : i + 1]
                    try:
                        return json.loads(candidate)
                    except Exception:
                        break
    return None


def canonicalize_tag(tag: str) -> str:
    t = (tag or "").strip().lower()
    # replace sequences of non-word with hyphen
    t = re.sub(r"[^\w\d]+", "-", t)
    t = re.sub(r"-{2,}", "-", t).strip("-")
    return t or "other"


def clean_html(html: str) -> str:
    if not html:
        return ""
    if BeautifulSoup:
        # allow basic safe tags
        allowed_tags = {"p", "b", "i", "strong", "em", "ul", "ol", "li", "br", "a"}
        soup = BeautifulSoup(html, "html.parser")
        # remove comments
        for c in soup(text=lambda text: isinstance(text, Comment)):
            c.extract()
        # sanitize tags
        for tag in soup.find_all(True):
            if tag.name not in allowed_tags:
                tag.unwrap()
            else:
                # strip unsafe attributes except href on <a>
                attrs = dict(tag.attrs)
                for k in attrs.keys():
                    if tag.name == "a" and k == "href":
                        # optionally keep only http/https
                        href = attrs[k]
                        if isinstance(href, str) and href.startswith(
                            ("http://", "https://")
                        ):
                            tag.attrs = {"href": href}
                        else:
                            tag.attrs = {}
                    else:
                        tag.attrs.pop(k, None)
        # return cleaned HTML string
        out = str(soup)
        return out
    else:
        # fallback: strip tags and keep text paragraphs
        text = re.sub(r"<[^>]+>", "", html)
        text = re.sub(r"\s+\n", "\n", text)
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        return "\n\n".join(f"<p>{p}</p>" for p in paragraphs[:10])


# ---------- Mapping loaders ----------
def load_tag_mappings(path: Path) -> Dict[str, str]:
    """Load tag_mappings.csv into dict; expect original_tag,canonical_tag,reason,approved"""
    out = {}
    if not path.exists():
        logger.warning(f"Tag mapping file not found: {path}")
        return out
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            original = (row.get("original_tag") or row.get("Tag") or "").strip()
            canonical = (
                row.get("canonical_tag") or row.get("Suggested Normalized") or ""
            ).strip()
            approved = (row.get("approved") or "no").strip().lower()
            if original:
                key = original.strip().lower()
                # only use mapping if approved=yes; keep mapping otherwise but mark not approved
                if canonical:
                    out[key] = (
                        canonical if approved == "yes" else None
                    )  # None means suggested but not applied
                else:
                    out[key] = None
    return out


def load_type_mappings(path: Path) -> Dict[str, Dict[str, Any]]:
    """Load type_mappings.csv with columns: original_type,google_root_category,google_path,suggested_by,confidence,approved"""
    out = {}
    if not path.exists():
        logger.warning(f"Type mapping file not found: {path}")
        return out
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            original = (
                row.get("original_type") or row.get("Original Type") or ""
            ).strip()
            root = (
                row.get("google_root_category")
                or row.get("Suggested Taxonomy (LLM)")
                or ""
            ).strip()
            pathstr = (row.get("google_path") or "").strip()
            approved = (row.get("approved") or "no").strip().lower()
            confidence = (
                (row.get("confidence") or row.get("Confidence") or "").strip().lower()
            )
            if original:
                out[original.lower()] = {
                    "google_root": root or None,
                    "google_path": pathstr or None,
                    "approved": approved == "yes",
                    "confidence": confidence or "low",
                }
    return out


# ---------- Ollama helpers ----------
def call_ollama_generate(
    prompt: str, model: str = GEN_MODEL, ollama_url: str = DEFAULT_OLLAMA, timeout=25
) -> Optional[str]:
    """Call Ollama /api/generate; returns raw text response or None."""
    url = f"{ollama_url.rstrip('/')}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.0, "num_predict": 256},
    }
    try:
        r = requests.post(url, json=payload, timeout=timeout)
        r.raise_for_status()
        j = r.json()
        # Ollama typically returns {"id":..., "response": "text"...}
        # Some versions place the text under ["response"] or ["output"] etc; find the best candidate
        if isinstance(j, dict):
            if "response" in j:
                return j["response"]
            if "output" in j:
                return j["output"]
            # if streaming style provided segments, try to join
            if "choices" in j:
                ch = j["choices"]
                if isinstance(ch, list) and ch:
                    txts = []
                    for c in ch:
                        if isinstance(c, dict):
                            txts.append(
                                c.get("message")
                                or c.get("text")
                                or c.get("content")
                                or ""
                            )
                    return "\n".join(txts).strip()
        # fallback: try text body
        return r.text
    except Exception as e:
        logger.debug(f"Ollama generate failed: {e}")
        return None


def call_ollama_embed(
    text: str, model: str = EMBED_MODEL, ollama_url: str = DEFAULT_OLLAMA, timeout=30
) -> Optional[List[float]]:
    """
    Call Ollama embed endpoint. Depending on Ollama versions, endpoint may be /api/embed or /api/generate with embedding config.
    Try /api/embed first then fallback.
    """
    # first try /api/embed
    try:
        url = f"{ollama_url.rstrip('/')}/api/embed"
        payload = {"model": model, "input": text}
        r = requests.post(url, json=payload, timeout=timeout)
        r.raise_for_status()
        j = r.json()
        # structure may be {"embedding": [...]} or {"data": [{"embedding": [...]}]}
        if isinstance(j, dict):
            if "embedding" in j:
                return j["embedding"]
            if "data" in j and isinstance(j["data"], list) and j["data"]:
                return j["data"][0].get("embedding")
        # fallback to parse text
    except Exception as e:
        logger.debug(f"Ollama embed endpoint failed: {e}")
    # fallback: try generate with model that returns embedding (less common)
    try:
        url = f"{ollama_url.rstrip('/')}/api/generate"
        payload = {
            "model": model,
            "prompt": text,
            "stream": False,
            "options": {"return_embedding": True},
        }
        r = requests.post(url, json=payload, timeout=timeout)
        r.raise_for_status()
        j = r.json()
        # locate embedding in response
        if isinstance(j, dict) and "embedding" in j:
            return j["embedding"]
    except Exception as e:
        logger.debug(f"Ollama generate-embed fallback failed: {e}")
    return None


# ---------- Prompts (JSON-only responses requested) ----------
TAXONOMY_PROMPT = """
You are a product taxonomy normalizer. Respond with ONLY valid JSON (no explanations).
Input:
{{"title": {title_json}, "product_type": {ptype_json}, "description": {desc_json}, "sample_categories": {sample_json}}}

Return exactly:
{{"category": "<best matching Google taxonomy category>"}}
"""

SEO_PROMPT = """
You are an expert SEO copywriter. Reply ONLY with a valid JSON object (no prose).
Input:
{{"title": {title_json}, "description": {desc_json}, "tags": {tags_json}}}

Return a JSON object:
{{"optimized_title": "<up to 80 chars>", "optimized_description": "<safe html, up to 800 chars>", "content_score": 0.0}}
"""

TAG_OPT_PROMPT = """
You are a product tag normalizer. Reply ONLY with valid JSON, no explanation.
Input:
{{"title": {title_json}, "description": {desc_json}, "current_tags": {tags_json}}}

Return:
{{"optimized_tags": ["tag1","tag2"], "removed_tags": [], "added_tags": [], "tag_analysis": "string"}}
"""

SCHEMA_PROMPT = """
Analyze the following product JSON for schema compliance. Respond with only a JSON object.
Input:
{product_json}

Return:
{{"schema_compliance": true_or_false, "issues": ["..."]}}
"""


# ---------- Fallback heuristics when LLM not available or returns invalid JSON ----------
def fallback_map_product_type(
    original_type: str, type_mappings: Dict[str, Any], taxonomy_roots: List[str]
) -> str:
    if not original_type:
        return "Miscellaneous"
    ot = original_type.strip().lower()
    # direct mapping if approved:
    if ot in type_mappings:
        mp = type_mappings[ot]
        if mp and mp.get("approved") and mp.get("google_root"):
            return mp["google_root"]
    # heuristic: token match root names
    for root in taxonomy_roots:
        if root.lower() in ot:
            return root
    # short heuristics by keywords
    keyword_map = {
        "shoe": "Apparel & Accessories",
        "shirt": "Apparel & Accessories",
        "camera": "Electronics",
        "battery": "Electronics",
        "lamp": "Home & Garden",
        "toy": "Toys & Games",
        "pet": "Animals & Pet Supplies",
        "food": "Food, Beverages & Tobacco",
    }
    for k, v in keyword_map.items():
        if k in ot:
            return v
    return "Miscellaneous"


def fallback_seo(title: str, description: str) -> Dict[str, Any]:
    # crude SEO generator: keep title, trim; create a short description
    ot = (title or "").strip()
    if len(ot) > 80:
        ot = ot[:77].rsplit(" ", 1)[0] + "..."
    body_text = re.sub(r"<[^>]+>", "", description or "")
    body_text = " ".join(body_text.split())
    desc = body_text[:760]
    # produce some basic tag extraction
    return {
        "optimized_title": ot,
        "optimized_description": f"<p>{desc}</p>",
        "content_score": 0.0,
    }


def fallback_tag_opt(
    title: str, description: str, current_tags: List[str]
) -> Dict[str, Any]:
    # combine current tags + keywords from title (split on non-word) and description top nouns (simple)
    tags = set([canonicalize_tag(t) for t in (current_tags or []) if t])
    # add tokens from title
    for token in re.split(r"[^\w]+", title or ""):
        if token and len(token) > 2:
            tags.add(canonicalize_tag(token))
    # simple frequency from description
    words = [
        w.lower() for w in re.split(r"[^\w]+", (description or "")) if w and len(w) > 3
    ]
    freq = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1
    for w, c in sorted(freq.items(), key=lambda x: -x[1])[:5]:
        tags.add(canonicalize_tag(w))
    tags_list = list(tags)[:12]
    return {
        "optimized_tags": tags_list,
        "removed_tags": [],
        "added_tags": [],
        "tag_analysis": "fallback",
    }


def fallback_schema_check(product: Dict[str, Any]) -> Dict[str, Any]:
    issues = []
    # required: id, title, body_html
    if not product.get("id"):
        issues.append("missing id")
    if not product.get("title"):
        issues.append("missing title")
    if not product.get("body_html"):
        issues.append("missing body_html")
    # types
    if product.get("tags") and not isinstance(product["tags"], list):
        issues.append("tags must be an array")
    return {"schema_compliance": len(issues) == 0, "issues": issues}


# ---------- Core product processing ----------
def process_single_product(
    product: Dict[str, Any],
    tag_mappings: Dict[str, Optional[str]],
    type_mappings: Dict[str, Any],
    taxonomy_roots: List[str],
    ollama_url: str = DEFAULT_OLLAMA,
    embed: bool = False,
) -> Dict[str, Any]:
    """
    Return normalized product dict with keys:
      id, title, body_html, tags (list), product_type (google root), ... optional embedding
    """
    pid = product.get("id") or product.get("handle") or str(int(time.time() * 1000))
    title = (product.get("title") or "").strip()
    raw_desc = product.get("body_html") or product.get("description") or ""
    clean_desc = clean_html(raw_desc)
    original_type = (product.get("product_type") or "").strip()
    current_tags = product.get("tags", [])
    if isinstance(current_tags, str):
        current_tags = [t.strip() for t in current_tags.split(",") if t.strip()]

    # 1) product_type (mapping -> LLM -> fallback)
    chosen_type = None
    # mapping if approved
    ot_key = original_type.strip().lower()
    if (
        ot_key
        and ot_key in type_mappings
        and type_mappings[ot_key].get("approved")
        and type_mappings[ot_key].get("google_root")
    ):
        chosen_type = type_mappings[ot_key]["google_root"]

    if not chosen_type:
        # try LLM
        prompt = TAXONOMY_PROMPT.format(
            title_json=json.dumps(title),
            ptype_json=json.dumps(original_type),
            desc_json=json.dumps(clean_desc),
            sample_json=json.dumps(taxonomy_roots[:30]),
        )
        resp_text = call_ollama_generate(prompt, model=GEN_MODEL, ollama_url=ollama_url)
        parsed = safe_json_load_from_text(resp_text) if resp_text else None
        if parsed and isinstance(parsed, dict) and parsed.get("category"):
            chosen_type = parsed["category"]
        else:
            chosen_type = fallback_map_product_type(
                original_type, type_mappings, taxonomy_roots
            )

    # 2) SEO optimization (LLM with fallback)
    seo = None
    prompt = SEO_PROMPT.format(
        title_json=json.dumps(title),
        desc_json=json.dumps(clean_desc),
        tags_json=json.dumps(current_tags),
    )
    resp_text = call_ollama_generate(prompt, model=GEN_MODEL, ollama_url=ollama_url)
    parsed = safe_json_load_from_text(resp_text) if resp_text else None
    if parsed and isinstance(parsed, dict) and parsed.get("optimized_title"):
        seo = parsed
        # ensure cleaned html body
        seo["optimized_description"] = clean_html(seo.get("optimized_description", ""))[
            :4000
        ]
    else:
        seo = fallback_seo(title, clean_desc)

    # 3) tag optimization (LLM or fallback), then apply mappings for approved canonical tags
    tag_result = None
    prompt = TAG_OPT_PROMPT.format(
        title_json=json.dumps(title),
        desc_json=json.dumps(clean_desc),
        tags_json=json.dumps(current_tags),
    )
    resp_text = call_ollama_generate(prompt, model=GEN_MODEL, ollama_url=ollama_url)
    parsed = safe_json_load_from_text(resp_text) if resp_text else None
    if parsed and isinstance(parsed, dict) and parsed.get("optimized_tags"):
        tag_result = parsed
    else:
        tag_result = fallback_tag_opt(title, clean_desc, current_tags)

    optimized_tags = []
    for t in tag_result.get("optimized_tags", []):
        if not t:
            continue
        mapped = tag_mappings.get(t.lower()) if tag_mappings else None
        if mapped:
            # only apply mapping if approved mapping present (non-None in loader)
            if mapped:
                optimized_tags.append(mapped)
            else:
                # mapping present but not approved; keep canonicalized version (but not mapping)
                optimized_tags.append(canonicalize_tag(t))
        else:
            optimized_tags.append(canonicalize_tag(t))
    # remove duplicates while preserving order
    seen = set()
    final_tags = []
    for t in optimized_tags:
        if t not in seen:
            seen.add(t)
            final_tags.append(t)

    # 4) schema compliance (LLM then fallback)
    schema_result = None
    try:
        prompt = SCHEMA_PROMPT.format(product_json=json.dumps(product))
        resp_text = call_ollama_generate(prompt, model=GEN_MODEL, ollama_url=ollama_url)
        parsed = safe_json_load_from_text(resp_text) if resp_text else None
        if parsed and isinstance(parsed, dict) and "schema_compliance" in parsed:
            schema_result = parsed
        else:
            schema_result = fallback_schema_check(product)
    except Exception:
        schema_result = fallback_schema_check(product)

    # 5) optional embedding
    embedding_vec = None
    if embed:
        emb_text = (title or "") + "\n\n" + re.sub(r"<[^>]+>", "", clean_desc)
        embedding_vec = call_ollama_embed(
            emb_text, model=EMBED_MODEL, ollama_url=ollama_url
        )
        if embedding_vec is None:
            logger.debug(
                f"Embedding failed for product {pid}; continuing without embedding."
            )

    # final structure
    normalized = {
        "id": pid,
        "title": seo.get("optimized_title") or title,
        "body_html": seo.get("optimized_description") or clean_desc,
        "tags": final_tags,
        "product_type": chosen_type,
        "original_type": original_type,
        "schema_compliance": schema_result.get("schema_compliance", False),
        "schema_issues": schema_result.get("issues", []),
        "tag_analysis_meta": {
            "removed": tag_result.get("removed_tags", []),
            "added": tag_result.get("added_tags", []),
            "tag_analysis": tag_result.get("tag_analysis", ""),
        },
        "confidence": {
            "type_src": "llm"
            if chosen_type not in ("Miscellaneous",)
            and (
                original_type.strip().lower() not in type_mappings
                or not type_mappings.get(original_type.strip().lower(), {}).get(
                    "approved"
                )
            )
            else "mapping"
        },
        "normalized_at": datetime.now().isoformat() + "Z",
    }
    if embedding_vec:
        normalized["embedding"] = embedding_vec

    # carry some metadata useful for downstream (price, handle etc)
    for k in ("handle", "vendor", "variants", "price", "created_at"):
        if product.get(k) is not None:
            normalized[k] = product.get(k)

    return normalized


# ---------- Main runner ----------
def main():
    parser = argparse.ArgumentParser(
        description="Master product normalization pipeline"
    )
    parser.add_argument("--input-folder", default="data/json/products_by_id")
    parser.add_argument("--output-dir", default="normalized_output")
    parser.add_argument("--tag-mappings", default="tag_mappings.csv")
    parser.add_argument("--type-mappings", default="type_mappings.csv")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument(
        "--max-files", type=int, help="Limit number of gz files to process"
    )
    parser.add_argument(
        "--embed",
        action="store_true",
        help="Generate embeddings (requires Ollama embed model)",
    )
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA, help="Ollama base URL")
    parser.add_argument("--no-progress", action="store_true", help="Disable tqdm")
    args = parser.parse_args()

    input_folder = Path(args.input_folder)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    tag_map_path = Path(args.tag_mappings)
    type_map_path = Path(args.type_mappings)

    # load mappings
    tag_mappings = load_tag_mappings(tag_map_path)
    type_mappings = load_type_mappings(type_map_path)

    # small root taxonomy list (short) — you can expand this list from your taxonomy files
    taxonomy_roots = [
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

    # collect filenames
    files = sorted(list(Path(input_folder).glob("*.json.gz")))
    if not files:
        logger.error(f"No gz product files found in {input_folder}")
        return

    if args.max_files:
        files = files[: args.max_files]

    logger.info(
        f"Found {len(files)} gz files to process. workers={args.workers} embed={args.embed}"
    )

    all_out_path = output_dir / "all_normalized.jsonl"
    # write header / ensure file exists
    with open(all_out_path, "w", encoding="utf-8") as _:
        pass

    # threadpool processing
    futures = []
    total_products = 0
    file_list = files
    show_progress = not args.no_progress

    with ThreadPoolExecutor(max_workers=args.workers) as exe:
        for fp in file_list:
            futures.append(exe.submit(read_gz_json, fp))

        # as each file yields list of products, we will process products in main thread to avoid nested ThreadPools;
        # but we can also submit product processing tasks to the pool — here we do product-level submit for concurrency.
        product_futures = []
        for fut in tqdm(
            as_completed(futures),
            total=len(futures),
            desc="Reading files",
            disable=not show_progress,
        ):
            file_products = fut.result()
            if not file_products:
                continue
            for prod in file_products:
                # submit processing
                product_futures.append(
                    exe.submit(
                        process_single_product,
                        prod,
                        tag_mappings,
                        type_mappings,
                        taxonomy_roots,
                        args.ollama_url,
                        args.embed,
                    )
                )

        # collect processed products and write them
        with open(all_out_path, "a", encoding="utf-8") as allfh:
            for pf in tqdm(
                as_completed(product_futures),
                total=len(product_futures),
                desc="Processing products",
                disable=not show_progress,
            ):
                try:
                    normalized = pf.result()
                except Exception as e:
                    logger.error(f"Product processing worker failed: {e}")
                    continue
                # save per-product JSON
                pid = normalized.get("id") or str(int(time.time() * 1000))
                safe_id = re.sub(r"[^\w\d\-_.]+", "_", str(pid))
                outp = output_dir / f"product_{safe_id}.json"
                try:
                    with open(outp, "w", encoding="utf-8") as f:
                        json.dump(normalized, f, indent=2, ensure_ascii=False)
                except Exception as e:
                    logger.error(f"Failed to write {outp}: {e}")
                # append to JSONL
                try:
                    allfh.write(json.dumps(normalized, ensure_ascii=False) + "\n")
                except Exception as e:
                    logger.error(f"Failed to append to JSONL: {e}")
                total_products += 1

    logger.info(
        f"Done. Total products normalized: {total_products}. Outputs in: {output_dir} (jsonl: {all_out_path})"
    )


if __name__ == "__main__":
    main()
