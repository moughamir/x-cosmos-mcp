import os
from pathlib import Path
from typing import List, Dict, Any, Tuple, Set
import functools

from app.config import settings

TAXONOMY_DIR = Path(settings.paths.prompt_dir).parent / "taxonomy"

# --- Functions for Frontend Taxonomy Viewer ---

def list_taxonomy_files() -> List[str]:
    """Lists all available taxonomy .txt files."""
    if not TAXONOMY_DIR.exists() or not TAXONOMY_DIR.is_dir():
        return []
    return sorted([f.name for f in TAXONOMY_DIR.glob("*.txt")])

def parse_taxonomy_file(filename: str) -> List[Dict[str, Any]]:
    """Parses a single taxonomy file into a tree structure for the frontend."""
    file_path = TAXONOMY_DIR / filename
    if not file_path.exists():
        return []

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]

    root_nodes: List[Dict[str, Any]] = []
    node_map: Dict[str, Dict[str, Any]] = {}

    for i, line in enumerate(lines):
        parts = [p.strip() for p in line.split('>')]
        current_level_nodes = root_nodes
        parent_path = ""

        for part_index, part in enumerate(parts):
            current_path = f"{parent_path}>{part}" if parent_path else part

            if current_path not in node_map:
                new_node = {
                    "id": current_path,
                    "name": part,
                    "children": []
                }
                node_map[current_path] = new_node
                current_level_nodes.append(new_node)
            
            current_level_nodes = node_map[current_path]["children"]
            parent_path = current_path

    return root_nodes

# --- Functions for Backend Category Normalizer ---

@functools.lru_cache(maxsize=1)
def load_taxonomy() -> List[str]:
    """Loads all taxonomy files into a single list of strings."""
    all_categories = []
    for f in TAXONOMY_DIR.glob("*.txt"):
        with open(f, 'r', encoding='utf-8') as file:
            all_categories.extend([line.strip() for line in file if line.strip()])
    return all_categories

def find_best_category(product_category: str, taxonomy_tree: List[str]) -> Tuple[str, float]:
    """Finds the best matching Google Product Category for a given product category string."""
    if not product_category or not taxonomy_tree:
        return "", 0.0

    product_words = set(product_category.lower().split())
    best_match = ""
    max_score = 0.0

    for official_category in taxonomy_tree:
        official_words = set(official_category.lower().replace('>', ' ').split())
        
        # Score based on word overlap
        intersection = product_words.intersection(official_words)
        union = product_words.union(official_words)
        if not union:
            continue

        score = len(intersection) / len(union) # Jaccard similarity

        # Boost score for full phrase matches
        if product_category.lower() in official_category.lower():
            score += 0.1

        if score > max_score:
            max_score = score
            best_match = official_category

    # Normalize confidence to be between 0 and 1
    confidence = min(max_score * 1.2, 1.0) # Amplify score slightly but cap at 1.0

    return best_match, round(confidence, 2)
