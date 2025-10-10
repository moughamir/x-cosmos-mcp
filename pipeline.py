#!/usr/bin/env python3
"""
Master Copy Pipeline (MCP) - Refactored
"""

import json
import asyncio
import re
import csv
from pathlib import Path
from utils.db import get_products_batch, log_change, update_product
from utils.db_migrate import migrate_schema
from utils.ollama_client import OllamaClient
from jinja2 import Template
from rapidfuzz import process, fuzz
from config import settings

# --- Configuration ---
MIN_MATCH_SCORE = 72
LOW_CONFIDENCE_THRESHOLD = 0.65

# --- Helper Functions ---

def load_taxonomy_from_url(url=settings.categories.taxonomy_url):
    import requests

    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        return [line.strip() for line in r.text.splitlines() if line.strip()]
    except requests.RequestException as e:
        print(f"Error fetching taxonomy: {e}")
        return []

def prepare_prompt(product, template_file):
    """Renders a prompt from a Jinja2 template."""
    template = Template((Path(settings.paths.prompt_dir) / template_file).read_text())
    return template.render(product=product)

def parse_response_to_json(resp_text):
    """Extracts a JSON object from the model's response."""
    try:
        match = re.search(r"\{.*\}", resp_text, re.S)
        if match:
            return json.loads(match.group(1))
        return None
    except (json.JSONDecodeError, AttributeError) as e:
        print(f"JSON parse error: {e}")
        return None

def map_to_taxonomy(candidate_label, taxonomy_list):
    """Finds the best matching taxonomy label for a candidate label."""
    if not candidate_label or not taxonomy_list:
        return None, 0
    choice, score, _ = process.extractOne(
        candidate_label, taxonomy_list, scorer=fuzz.WRatio
    ) or (None, 0, None)
    return choice, score


# --- Pipeline Steps ---


async def process_product(
    product: dict, title_client: OllamaClient, desc_client: OllamaClient, taxonomy: list
):
    """Processes a single product to generate normalized data."""
    # Generate title
    title_prompt = prepare_prompt(product, "normalize_product.j2")
    normalized_title_raw = await asyncio.to_thread(
        title_client.get_response, title_prompt
    )

    # Generate description and other fields
    desc_prompt = prepare_prompt(product, "rewrite_description.j2")
    desc_response_raw = await asyncio.to_thread(desc_client.get_response, desc_prompt)
    enriched_data = parse_response_to_json(desc_response_raw)

    if not enriched_data:
        print(f"Could not parse response for product {product['id']}")
        return None

    # Validate and extract data
    normalized_title = normalized_title_raw if normalized_title_raw else product["title"]
    normalized_body = enriched_data.get("body_html", product["body_html"])
    normalized_tags = enriched_data.get("tags", [])
    category_suggest = enriched_data.get("category")
    confidence = float(enriched_data.get("confidence", 0.0))

    # Map to taxonomy
    mapped_category, tax_score = map_to_taxonomy(category_suggest, taxonomy)
    final_category = mapped_category if tax_score >= MIN_MATCH_SCORE else None

    # Update database
    await update_product(
        settings.paths.database,
        product["id"],
        normalized_title,
        normalized_body,
        normalized_tags,
        final_category,
        desc_client.model_name,
        confidence,
    )

    # Log changes
    await log_change(
        settings.paths.database,
        product["id"],
        "title",
        product["title"],
        normalized_title,
        title_client.model_name,
    )
    await log_change(
        settings.paths.database,
        product["id"],
        "body_html",
        product["body_html"],
        normalized_body,
        desc_client.model_name,
    )

    # Return data for review queue
    if confidence < LOW_CONFIDENCE_THRESHOLD or (
        category_suggest and tax_score < MIN_MATCH_SCORE
    ):
        return {
            "product_id": product["id"],
            "original_title": product["title"],
            "suggested_title": normalized_title,
            "suggested_category": category_suggest,
            "mapped_category": final_category,
            "confidence": confidence,
            "taxonomy_score": tax_score,
        }
    return None


async def main():
    """Main pipeline execution function."""
    # Setup
    await migrate_schema(settings.paths.database)
    taxonomy = load_taxonomy_from_url()

    if not taxonomy:
        print("Could not load taxonomy. Exiting.")
        return

    title_client = OllamaClient(
        model_name=settings.models.title_model,
        host=settings.ollama.host,
        port=settings.ollama.port,
    )
    desc_client = OllamaClient(
        model_name=settings.models.description_model,
        host=settings.ollama.host,
        port=settings.ollama.port,
    )

    low_confidence_products = []
    offset = 0

    while True:
        batch = await get_products_batch(settings.paths.database, limit=settings.models.batch_size)

        if not batch:
            print("No more products to process.")
            break

        tasks = [
            process_product(dict(p), title_client, desc_client, taxonomy) for p in batch
        ]
        results = await asyncio.gather(*tasks)

        for result in results:
            if result:
                low_confidence_products.append(result)

        offset += len(batch)
        print(f"Processed batch of {len(batch)}. Total processed: {offset}")

    # Write low-confidence products to CSV
    if low_confidence_products:
        with open("low_confidence_review.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=low_confidence_products[0].keys())
            writer.writeheader()
            writer.writerows(low_confidence_products)
        print(
            f"Wrote {len(low_confidence_products)} products to low_confidence_review.csv"
        )


if __name__ == "__main__":
    asyncio.run(main())
