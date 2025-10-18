#!/usr/bin/env python3
"""
optimus_v3.py
Full product enrichment -> normalized Supabase upsert pipeline.

Features:
- Reads products from Cosmos API (paginated)
- Enhances products via Ollama (analyze/optimize/rewrite)
- Generates embeddings via Ollama embeddings endpoint
- Normalizes product data to the requested JSON shape
- Upserts into normalized Supabase tables:
    - products
    - product_variants
    - product_images
    - product_options
- Saves local enhanced JSON for inspection
"""

import os
import argparse
import re
import json
import logging
import requests  # type: ignore[import-untyped]
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader, nodes
from jinja2.ext import Extension
from supabase import create_client, Client


class SystemTagExtension(Extension):
    """
    Allows using {% system %} ... {% endsystem %} in templates.
    Content inside is rendered as normal (this simply ignores the tag semantics).
    """

    tags = {"system"}

    def parse(self, parser):
        lineno = next(parser.stream).lineno
        # parse until {% endsystem %}
        body = parser.parse_statements(["name:endsystem"], drop_needle=True)
        return nodes.CallBlock(
            self.call_method("_render_system", []), [], [], body
        ).set_lineno(lineno)

    def _render_system(self, caller):
        # just render the inner block text exactly
        return caller()


# -----------------------
# Configuration / Logging
# -----------------------
load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("optimus_v3")

DEFAULT_EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "768"))


# -----------------------
# Utilities
# -----------------------
def slugify(text: str) -> str:
    if not text:
        return ""
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text.strip("-")[:240]


def ensure_list(x):
    if x is None:
        return []
    if isinstance(x, list):
        return x
    if isinstance(x, str):
        try:
            parsed = json.loads(x)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
        return [t.strip() for t in x.split(",") if t.strip()]
    return [x]


# -----------------------
# Main OptimusV3 class
# -----------------------
class OptimusV3:
    def __init__(
        self,
        ollama_url: Optional[str] = None,
        ollama_model: Optional[str] = None,
        embedding_model: Optional[str] = None,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        prompts_dir: str = "data/prompts",
        taxonomy_dir: str = "data/taxonomy",
        cosmos_api_url: Optional[str] = None,
        cosmos_api_key: Optional[str] = None,
        embedding_dim: int = DEFAULT_EMBEDDING_DIM,
        save_local_dir: str = "output_v3",
    ):
        # env / defaults
        self.ollama_url = ollama_url or os.getenv(
            "OLLAMA_URL", "http://localhost:11434"
        )
        self.ollama_model = ollama_model or os.getenv(
            "OLLAMA_MODEL", "llama3.2:1b-instruct-q4_K_M"
        )
        self.embedding_model = embedding_model or os.getenv(
            "EMBEDDING_MODEL", "nomic-embed-text:latest"
        )
        self.cosmos_api_url = cosmos_api_url or os.getenv(
            "COSMOS_API_URL", "https://moritotabi.com/cosmos"
        )
        self.cosmos_api_key = cosmos_api_key or os.getenv("COSMOS_API_KEY")
        self.embedding_dim = embedding_dim or int(os.getenv("EMBEDDING_DIM", "768"))

        # Supabase client (prefer service key for server-side jobs)
        supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        supabase_key = (
            supabase_key
            or os.getenv("SUPABASE_SERVICE_KEY")
            or os.getenv("SUPABASE_KEY")
        )
        if supabase_url and supabase_key:
            self.supabase: Client = create_client(supabase_url, supabase_key)
        else:
            self.supabase = None
            logger.warning(
                "Supabase client not initialized. Set SUPABASE_SERVICE_KEY for server writes."
            )

        # prompts & taxonomy
        self.prompts_dir = prompts_dir
        self.jinja_env = (
            Environment(
                loader=FileSystemLoader(prompts_dir),
                extensions=[SystemTagExtension],
            )
            if Path(prompts_dir).exists()
            else None
        )
        self.taxonomies = self._load_taxonomies(taxonomy_dir)

        # output
        self.output_dir = Path(save_local_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            "OptimusV3 initialized (ollama=%s, embedding_model=%s, embedding_dim=%d)",
            self.ollama_model,
            self.embedding_model,
            self.embedding_dim,
        )

    def _load_taxonomies(self, taxonomy_dir: str) -> List[str]:
        tax: List[str] = []
        p = Path(taxonomy_dir)
        if not p.exists():
            return tax
        for f in sorted(p.glob("*.txt")):
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        tax.append(line)
            except Exception:
                continue
        return tax

    # -----------------------
    # Ollama helpers
    # -----------------------
    def call_ollama(
        self, prompt: str, temperature: float = 0.7, max_tokens: int = 500
    ) -> str:
        try:
            payload = {
                "model": self.ollama_model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            }
            r = requests.post(
                f"{self.ollama_url}/api/generate", json=payload, timeout=120
            )
            r.raise_for_status()
            return r.json().get("response", "").strip()
        except Exception:
            logger.exception("call_ollama failed")
            return ""

    def call_ollama_json(
        self, prompt: str, temperature: float = 0.5, max_tokens: int = 800
    ) -> Dict[str, Any]:
        json_prompt = f"{prompt}\n\nCRITICAL: You must respond with ONLY valid JSON. Start with {{ and end with }}."
        raw = self.call_ollama(json_prompt, temperature, max_tokens)
        if not raw:
            return {}
        # strip markdown fences
        raw_clean = re.sub(r"```(?:json)?", "", raw).strip()
        # locate first { and last }
        start = raw_clean.find("{")
        end = raw_clean.rfind("}")
        if start == -1 or end == -1:
            logger.error(
                "No JSON object found in Ollama response. Raw response:\n%s",
                raw_clean[:2000],
            )
            return {}
        candidate = raw_clean[start : end + 1]
        # remove trailing commas
        candidate = re.sub(r",\s*([\}\]])", r"\1", candidate)
        candidate = candidate.replace("\\'", "'")
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as e:
            logger.error(
                "Failed parsing JSON from Ollama response: %s\nRaw:\n%s\nCandidate JSON:\n%s",
                e,
                raw_clean[:2000],
                candidate[:2000],
            )
            return {}

    def get_embedding(self, text: str) -> List[float]:
        if not text:
            return []
        try:
            payload = {"model": self.embedding_model, "prompt": text}
            r = requests.post(
                f"{self.ollama_url}/api/embeddings", json=payload, timeout=60
            )
            r.raise_for_status()
            emb = r.json().get("embedding")
            if not isinstance(emb, list):
                logger.warning("Embedding response not a list (type=%s).", type(emb))
                return []
            emb = [float(x) for x in emb]
            if len(emb) != self.embedding_dim:
                logger.warning(
                    "Embedding dim mismatch: got %d expected %d. Will pad/truncate.",
                    len(emb),
                    self.embedding_dim,
                )
                if len(emb) < self.embedding_dim:
                    emb = emb + [0.0] * (self.embedding_dim - len(emb))
                else:
                    emb = emb[: self.embedding_dim]
            return emb
        except Exception:
            logger.exception("get_embedding failed")
            return []

    # -----------------------
    # Prompt wrappers / fallbacks
    # -----------------------
    def analyze_keywords_prompt(self, product: Dict[str, Any]) -> Dict[str, Any]:
        if self.jinja_env and Path(self.prompts_dir, "analyze_keywords.j2").exists():
            prompt = self.jinja_env.get_template("analyze_keywords.j2").render(
                product_data=product, clean_html=self.clean_html
            )
            return self.call_ollama_json(prompt, temperature=0.45, max_tokens=400)
        # fallback
        title = product.get("title", "")
        tags = ensure_list(product.get("tags", []))
        return {
            "primary_keywords": [title] if title else [],
            "long_tail_keywords": tags[:5],
            "competitor_terms": [],
            "difficulty_estimate": "unknown",
        }

    def meta_opt_prompt(self, product: Dict[str, Any]) -> Dict[str, Any]:
        if self.jinja_env and Path(self.prompts_dir, "meta_optimization.j2").exists():
            prompt = self.jinja_env.get_template("meta_optimization.j2").render(
                product_data=product, clean_html=self.clean_html
            )
            return self.call_ollama_json(prompt, temperature=0.6, max_tokens=300)
        # fallback
        title = product.get("title", "")
        desc = product.get("body_html") or ""
        desc_text = self.clean_html(desc)
        return {
            "meta_title": (title or "")[:60],
            "meta_description": (desc_text[:155] + "...")
            if len(desc_text) > 160
            else desc_text,
            "seo_keywords": [],
        }

    def rewrite_content_prompt(self, product: Dict[str, Any]) -> Dict[str, Any]:
        if self.jinja_env and Path(self.prompts_dir, "rewrite_content.j2").exists():
            prompt = self.jinja_env.get_template("rewrite_content.j2").render(
                product_data=product, clean_html=self.clean_html
            )
            return self.call_ollama_json(prompt, temperature=0.7, max_tokens=600)
        # fallback
        title = product.get("title", "")
        desc_text = self.clean_html(product.get("body_html", "") or "")
        return {
            "optimized_title": title,
            "optimized_description": desc_text,
            "content_score": 0.0,
        }

    def is_valid_taxonomy(self, candidate: str) -> bool:
        if not candidate or not isinstance(candidate, str):
            return False
        candidate = candidate.strip()
        # fail fast on obvious non-taxonomy replies
        if len(candidate.split()) > 10:  # too many words
            return False
        if candidate.lower().startswith(("i'm", "i am", "sure", "happy", "here")):
            return False
        # simple length checks
        if len(candidate) < 3 or len(candidate) > 200:
            return False
        # allow slashes or '>' or known taxonomy words
        return True

    def normalize_product_type(self, product: Dict[str, Any]) -> str:
        """
        Call Ollama but expect a JSON response with { "category": "..." }.
        If the response is invalid, fallback to the original product_type.
        """
        # Prefer a strict JSON prompt template if available
        if self.jinja_env and Path(self.prompts_dir, "normalize_product.j2").exists():
            prompt = self.jinja_env.get_template("normalize_product.j2").render(
                product_data=product,
                sample_categories="\n".join(self.taxonomies[:200]),
                clean_html=self.clean_html,
            )
            resp = self.call_ollama_json(prompt, temperature=0.2, max_tokens=160)
            # expect a JSON like { "category": "Lighting > Lamps > Floor Lamps" }
            candidate = (
                resp.get("category")
                or resp.get("normalized_category")
                or resp.get("product_type")
                or ""
            )
            if self.is_valid_taxonomy(candidate):
                return candidate.strip()
            logger.warning(
                "normalize_product_type: invalid candidate from Ollama: %r", candidate
            )

        # Fallback: prefer existing product_type if it looks reasonable
        fallback = product.get("product_type") or ""
        if self.is_valid_taxonomy(fallback):
            return fallback if fallback else "Miscellaneous"

        # last resort: keep original title as minimal category
        return product.get("product_type") or product.get("title", "")[:80]

    # -----------------------
    # Helpers
    # -----------------------
    @staticmethod
    def clean_html(html_text: str) -> str:
        if not html_text:
            return ""
        text = re.sub(r"<[^>]+>", " ", html_text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    # -----------------------
    # Transform & Upsert
    # -----------------------
    def transform_product_to_v3(
        self, api_product: Dict[str, Any], include_embeddings: bool = True
    ) -> Dict[str, Any]:
        def safe_datetime(dt):
            if isinstance(dt, datetime):
                return dt.isoformat()
            return dt

        def safe_list(x):
            if isinstance(x, list):
                return x
            return []

        pid = str(api_product.get("id", "unknown"))

        # Ollama prompts with safe fallback
        try:
            keyword_analysis = self.analyze_keywords_prompt(api_product) or {}
        except Exception:
            logger.exception("Keyword analysis failed for product %s", pid)
            keyword_analysis = {}

        try:
            meta = self.meta_opt_prompt(api_product) or {}
        except Exception:
            logger.exception("Meta optimization failed for product %s", pid)
            meta = {}

        try:
            rewrite = self.rewrite_content_prompt(api_product) or {
                "optimized_title": api_product.get("title") or "",
                "optimized_description": self.clean_html(
                    api_product.get("body_html", "") or ""
                ),
                "content_score": 0.0,
            }
        except Exception:
            logger.exception("Content rewrite failed for product %s", pid)
            rewrite = {
                "optimized_title": api_product.get("title") or "",
                "optimized_description": self.clean_html(
                    api_product.get("body_html", "") or ""
                ),
                "content_score": 0.0,
            }

        try:
            taxonomy = self.normalize_product_type(api_product)
        except Exception:
            logger.exception("Product type normalization failed for product %s", pid)
            taxonomy = api_product.get("product_type") or ""

        title_opt = rewrite.get("optimized_title") or api_product.get("title") or ""
        desc_opt = rewrite.get("optimized_description") or self.clean_html(
            api_product.get("body_html", "") or ""
        )
        handle = slugify(api_product.get("handle") or title_opt or f"product-{pid}")

        # Normalize tags
        tags_raw = ensure_list(api_product.get("tags") or [])
        seen = set()
        normalized_tags = []
        for t in tags_raw:
            s = (t or "").strip()
            if not s:
                continue
            key = s.lower()
            if key not in seen:
                seen.add(key)
                normalized_tags.append(s)

        meta_obj = {
            "title": meta.get("meta_title") or title_opt,
            "description": meta.get("meta_description")
            or (desc_opt[:160] + "..." if len(desc_opt) > 160 else desc_opt),
            "keywords": meta.get("seo_keywords")
            or keyword_analysis.get("primary_keywords")
            or [],
            "canonical": None,
        }

        score_value = rewrite.get("content_score")
        if isinstance(score_value, dict):
            score_value = score_value.get("score")

        v3 = {
            "id": None,
            "product_id": pid,
            "title": title_opt,
            "description": desc_opt,
            "handle": handle,
            "created_at": safe_datetime(api_product.get("created_at")),
            "published_at": safe_datetime(api_product.get("published_at")),
            "product_type": taxonomy
            if self.is_valid_taxonomy(taxonomy)
            else api_product.get("product_type") or "",
            "tags": normalized_tags,
            "meta": meta_obj,
            "seo_keywords": meta.get("seo_keywords")
            or keyword_analysis.get("primary_keywords")
            or [],
            "primary_keywords": keyword_analysis.get("primary_keywords") or [],
            "long_tail_keywords": keyword_analysis.get("long_tail_keywords") or [],
            "competitor_terms": keyword_analysis.get("competitor_terms") or [],
            "keyword_difficulty": keyword_analysis.get("difficulty_estimate")
            or keyword_analysis.get("keyword_difficulty")
            or "unknown",
            "content_score": float(score_value or 0.0),
            "embedding": [0.0] * self.embedding_dim,
            "_source_variants": safe_list(api_product.get("variants")),
            "_source_images": safe_list(api_product.get("images")),
            "_source_options": safe_list(api_product.get("options")),
        }

        # Embeddings
        if include_embeddings:
            try:
                combined_text = f"{v3['title']} {v3['description']}"
                emb = self.get_embedding(combined_text)
                if isinstance(emb, list) and len(emb) == self.embedding_dim:
                    v3["embedding"] = [float(x) for x in emb]
                else:
                    v3["embedding"] = [0.0] * self.embedding_dim
            except Exception:
                logger.exception("Embedding generation failed for product %s", pid)
                v3["embedding"] = [0.0] * self.embedding_dim

        return v3

    def upsert_product(self, product_v3: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.supabase:
            logger.warning("Supabase not configured; skipping product upsert.")
            return None

        payload = {
            "product_id": product_v3.get("product_id"),
            "title": product_v3.get("title"),
            "description": product_v3.get("description"),
            "handle": product_v3.get("handle"),
            "created_at": product_v3.get("created_at"),
            "published_at": product_v3.get("published_at"),
            "updated_at": product_v3.get("updated_at"),
            "product_type": product_v3.get("product_type"),
            "tags": product_v3.get("tags") or [],
            "meta": product_v3.get("meta") or {},
            "seo_keywords": product_v3.get("seo_keywords") or [],
            "primary_keywords": product_v3.get("primary_keywords") or [],
            "long_tail_keywords": product_v3.get("long_tail_keywords") or [],
            "competitor_terms": product_v3.get("competitor_terms") or [],
            "keyword_difficulty": product_v3.get("keyword_difficulty"),
            "content_score": product_v3.get("content_score"),
            "embedding": product_v3.get("embedding"),
        }

        # strip None values
        payload = {k: v for k, v in payload.items() if v is not None}

        try:
            res = (
                self.supabase.table("products")
                .upsert(payload, on_conflict="product_id")
                .execute()
            )
            # try to get returned row
            data = getattr(res, "data", None) or (
                res.json() if hasattr(res, "json") else None
            )
            if isinstance(data, list) and len(data) > 0:
                return data[0]
            # fallback: fetch row by product_id
            fetch = (
                self.supabase.table("products")
                .select("*")
                .eq("product_id", payload["product_id"])
                .limit(1)
                .execute()
            )
            fdata = getattr(fetch, "data", None) or (
                fetch.json() if hasattr(fetch, "json") else None
            )
            if isinstance(fdata, list) and len(fdata) > 0:
                return fdata[0]
            return None
        except Exception:
            logger.exception("upsert_product failed")
            return None

    def upsert_variants_and_images(
        self, product_db_row: Dict[str, Any], product_v3: Dict[str, Any]
    ) -> None:
        if not self.supabase:
            logger.debug("Supabase not configured; skipping variants/images upsert.")
            return

        db_product_id = product_db_row.get("id")
        if not db_product_id:
            logger.error("No DB product id to attach variants/images to.")
            return

        # Upsert variants
        for v in product_v3.get("_source_variants", []):
            payload = {
                "product_id": db_product_id,
                "source_variant_id": str(v.get("id"))
                if v.get("id") is not None
                else None,
                "title": v.get("title"),
                "sku": v.get("sku"),
                "price": float(v.get("price")) if v.get("price") else None,
                "compare_at_price": float(v.get("compare_at_price"))
                if v.get("compare_at_price")
                else None,
                "inventory_quantity": v.get("inventory_quantity"),
                "available": v.get("available"),
                "grams": v.get("grams"),
                "options": v.get("options")
                or [{"name": "Finish", "value": v.get("option1")}]
                if v.get("option1")
                else [],
                "metadata": v.get("featured_image") or {},
                "created_at": v.get("created_at"),
            }
            payload = {k: x for k, x in payload.items() if x is not None}
            try:
                if payload.get("source_variant_id"):
                    res = (
                        self.supabase.table("product_variants")
                        .upsert(payload, on_conflict="product_id,source_variant_id")
                        .execute()
                    )
                else:
                    res = (
                        self.supabase.table("product_variants")
                        .insert(payload)
                        .execute()
                    )
                if hasattr(res, "error") and res.error:
                    logger.warning("Variant upsert error: %s", res.error)
            except Exception:
                logger.exception("Failed to upsert variant: %s", payload.get("sku"))

        # Upsert images
        for img in product_v3.get("_source_images", []):
            payload = {
                "product_id": db_product_id,
                "source_image_id": str(img.get("id"))
                if img.get("id") is not None
                else None,
                "url": img.get("src") or img.get("url"),
                "alt_text": img.get("alt"),
                "position": img.get("position"),
                "metadata": {
                    "width": img.get("width"),
                    "height": img.get("height"),
                    "variant_ids": img.get("variant_ids") or [],
                },
                "created_at": img.get("created_at"),
            }
            payload = {k: x for k, x in payload.items() if x is not None}
            try:
                if payload.get("source_image_id"):
                    res = (
                        self.supabase.table("product_images")
                        .upsert(payload, on_conflict="product_id,source_image_id")
                        .execute()
                    )
                else:
                    res = (
                        self.supabase.table("product_images").insert(payload).execute()
                    )
                if hasattr(res, "error") and res.error:
                    logger.warning("Image upsert error: %s", res.error)
            except Exception:
                logger.exception("Failed to upsert image: %s", payload.get("url"))

        # Upsert options
        for opt in product_v3.get("_source_options", []):
            payload = {
                "product_id": db_product_id,
                "name": opt.get("name"),
                "position": opt.get("position"),
                "values": opt.get("values") or [],
            }
            payload = {k: x for k, x in payload.items() if x is not None}
            try:
                res = (
                    self.supabase.table("product_options")
                    .upsert(payload, on_conflict="product_id,name")
                    .execute()
                )
                if hasattr(res, "error") and res.error:
                    logger.warning("Option upsert error: %s", res.error)
            except Exception:
                logger.exception("Failed to upsert option: %s", payload.get("name"))

    @staticmethod
    def safe_json(obj):
        if isinstance(obj, (dict, list, str, int, float, bool, type(None))):
            return obj
        if isinstance(obj, datetime):
            return obj.isoformat()
        return str(obj)

    def save_local_copy(self, product_v3: Dict[str, Any]) -> None:
        pid = product_v3.get("product_id", "unknown")
        out_path = self.output_dir / f"{pid}_enhanced.json"
        try:
            to_write = dict(product_v3)
            with open(out_path, "w", encoding="utf-8") as fh:
                json.dump(
                    to_write, fh, indent=2, ensure_ascii=False, default=self.safe_json
                )
            logger.debug("Saved local enhanced copy: %s", out_path)
        except Exception:
            logger.exception("Failed saving local copy for product %s", pid)

    # -----------------------
    # API list + orchestrator
    # -----------------------
    def list_products_from_api(
        self, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        headers = {"X-API-Key": self.cosmos_api_key} if self.cosmos_api_key else {}
        params = {"limit": limit, "offset": offset}
        url = f"{self.cosmos_api_url}/products"
        try:
            r = requests.get(url, headers=headers, params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                return data.get("products") or data.get("data") or []
            return []
        except Exception:
            logger.exception("Failed to list products from API")
            return []

    def process_all_products_paginated(
        self,
        batch_size: int = 10,
        max_products: Optional[int] = None,
        start_offset: int = 0,
        include_embeddings: bool = True,
    ):
        total_processed = 0
        offset = start_offset
        while True:
            limit = (
                batch_size
                if not max_products
                else min(batch_size, max_products - total_processed)
            )
            if limit <= 0:
                break
            logger.info("Fetching batch: offset=%s, limit=%s", offset, limit)
            products = self.list_products_from_api(limit=limit, offset=offset)
            if not products:
                logger.info("No more products returned from API.")
                break
            for api_product in products:
                try:
                    p_v3 = self.transform_product_to_v3(
                        api_product, include_embeddings=include_embeddings
                    )
                    self.save_local_copy(p_v3)
                    db_row = self.upsert_product(p_v3)
                    if db_row:
                        logger.info(
                            "Upserted product_id=%s db_id=%s",
                            p_v3.get("product_id"),
                            db_row.get("id"),
                        )
                        self.upsert_variants_and_images(db_row, p_v3)
                    else:
                        logger.error(
                            "Failed to upsert product_id=%s", p_v3.get("product_id")
                        )
                except Exception:
                    logger.exception(
                        "Unhandled error processing product id=%s",
                        api_product.get("id"),
                    )
                total_processed += 1
                if max_products and total_processed >= max_products:
                    break
            if max_products and total_processed >= max_products:
                break
            offset += len(products)
        logger.info("Processing finished. Total processed: %d", total_processed)


# -----------------------
# Entrypoint
# -----------------------


def main():
    parser = argparse.ArgumentParser(
        description="Run the OptimusV3 product enrichment pipeline."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of products to process. Omit to process all products.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of products to fetch in each API call.",
    )
    parser.add_argument(
        "--offset", type=int, default=0, help="Starting offset for fetching products."
    )
    parser.add_argument(
        "--no-embeddings", action="store_true", help="Disable embedding generation."
    )
    args = parser.parse_args()

    processor = OptimusV3(
        ollama_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3.2:1b-instruct-q4_K_M"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "nomic-embed-text:latest"),
        supabase_url=os.getenv("SUPABASE_URL"),
        supabase_key=os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY"),
        prompts_dir=os.getenv("PROMPTS_DIR", "data/prompts"),
        taxonomy_dir=os.getenv("TAXONOMY_DIR", "data/taxonomy"),
        cosmos_api_url=os.getenv("COSMOS_API_URL", "https://moritotabi.com/cosmos"),
        cosmos_api_key=os.getenv("COSMOS_API_KEY"),
        embedding_dim=int(os.getenv("EMBEDDING_DIM", "768")),
        save_local_dir=os.getenv("OUTPUT_DIR", "output_v3"),
    )

    logger.info(
        f"Starting pipeline with limit={args.limit}, batch_size={args.batch_size}, offset={args.offset}"
    )
    processor.process_all_products_paginated(
        batch_size=args.batch_size,
        max_products=args.limit,
        start_offset=args.offset,
        include_embeddings=not args.no_embeddings,
    )


if __name__ == "__main__":
    main()
