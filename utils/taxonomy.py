import os
import requests
import difflib
import json

TAXONOMY_URL = "https://www.google.com/basepages/producttype/taxonomy.en-US.txt"
CACHE_PATH = os.path.expanduser("~/.cache/mcp_google_taxonomy.json")


def load_taxonomy():
    """Loads or downloads the Google taxonomy list."""
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "r") as f:
            return json.load(f)

    print("Downloading Google Product Taxonomy...")
    r = requests.get(TAXONOMY_URL, timeout=500)
    r.raise_for_status()
    categories = [
        line.strip()
        for line in r.text.splitlines()
        if line.strip() and not line.startswith("#")
    ]
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w") as f:
        json.dump(categories, f)
    return categories


def find_best_category(raw_category: str, taxonomy: list[str]) -> tuple[str, float]:
    """Fuzzy matches a local category name to Google's taxonomy."""
    if not raw_category:
        return ("Uncategorized", 0.0)
    matches = difflib.get_close_matches(raw_category, taxonomy, n=1, cutoff=0.3)
    if matches:
        ratio = difflib.SequenceMatcher(None, raw_category, matches[0]).ratio()
        return (matches[0], round(ratio, 3))
    return ("Uncategorized", 0.0)
