import os
import difflib
import json
from typing import List, Dict, Optional

# Use local taxonomy file instead of remote URL
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TAXONOMY_DIR = os.path.join(PROJECT_ROOT, 'data', 'taxonomy')
CACHE_PATH = os.path.join(PROJECT_ROOT, '.cache', 'taxonomy_tree_cache.json')

class TaxonomyNode:
    def __init__(self, name: str, full_path: str, parent: Optional['TaxonomyNode'] = None):
        self.name = name
        self.full_path = full_path
        self.children: Dict[str, TaxonomyNode] = {}
        self.parent = parent

    def to_dict(self):
        return {
            "name": self.name,
            "full_path": self.full_path,
            "children": {name: child.to_dict() for name, child in self.children.items()}
        }

    @classmethod
    def from_dict(cls, data: Dict, parent: Optional['TaxonomyNode'] = None):
        node = cls(data["name"], data["full_path"], parent)
        for child_name, child_data in data["children"].items():
            node.children[child_name] = cls.from_dict(child_data, node)
        return node

def load_taxonomy() -> Dict[str, TaxonomyNode]:
    """Loads the Google taxonomy list from local files and builds a hierarchical tree."""
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "r") as f:
            cached_data = json.load(f)
            root_nodes = {}
            for name, data in cached_data.items():
                root_nodes[name] = TaxonomyNode.from_dict(data)
            return root_nodes

    print("Loading Google Product Taxonomy from local files and building tree...")
    if not os.path.isdir(TAXONOMY_DIR):
        raise FileNotFoundError(f"Taxonomy directory not found at {TAXONOMY_DIR}")

    root_nodes: Dict[str, TaxonomyNode] = {}
    all_nodes: Dict[str, TaxonomyNode] = {}

    for filename in os.listdir(TAXONOMY_DIR):
        if filename.endswith(".txt"):
            with open(os.path.join(TAXONOMY_DIR, filename), 'r', encoding='utf-8') as f:
                for line in f.readlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    parts = line.split(' > ')
                    current_parent: Optional[TaxonomyNode] = None
                    current_path = []

                    for i, part in enumerate(parts):
                        current_path.append(part)
                        full_path = ' > '.join(current_path)

                        if full_path not in all_nodes:
                            node = TaxonomyNode(part, full_path, current_parent)
                            all_nodes[full_path] = node

                            if current_parent:
                                current_parent.children[part] = node
                            else:
                                root_nodes[part] = node
                        
                        current_parent = all_nodes[full_path]

    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w") as f:
        json.dump({name: node.to_dict() for name, node in root_nodes.items()}, f)

    print(f"Built taxonomy tree with {len(root_nodes)} top-level categories.")
    return root_nodes

def find_best_category(raw_category: str, taxonomy_tree: Dict[str, TaxonomyNode]) -> tuple[str, float]:
    """Fuzzy matches a local category name to Google's hierarchical taxonomy."""
    if not raw_category:
        return ("Uncategorized", 0.0)

    best_match_path = "Uncategorized"
    best_match_ratio = 0.0

    # Flatten the tree to get all full paths for matching
    all_full_paths = []
    queue = list(taxonomy_tree.values())
    while queue:
        node = queue.pop(0)
        all_full_paths.append(node.full_path)
        queue.extend(node.children.values())

    matches = difflib.get_close_matches(raw_category, all_full_paths, n=1, cutoff=0.3)
    if matches:
        ratio = difflib.SequenceMatcher(None, raw_category, matches[0]).ratio()
        best_match_path = matches[0]
        best_match_ratio = round(ratio, 3)

    return (best_match_path, best_match_ratio)

def get_top_level_categories() -> List[str]:
    """Returns a list of top-level category names from the taxonomy tree."""
    taxonomy_tree = load_taxonomy()
    return sorted(list(taxonomy_tree.keys()))
