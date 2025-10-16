import csv
import json
import os
from typing import List, Dict, Any


def generate_training_examples(products_file: str) -> List[Dict[str, Any]]:
    """Read products from a JSON file."""
    with open(products_file, "r") as f:
        products = json.load(f)
    return products


def append_to_csv(csv_file, examples):
    """Append examples to a CSV file."""
    # Check if the file is empty to write headers
    write_header = not os.path.exists(csv_file) or os.path.getsize(csv_file) == 0

    with open(csv_file, "a", newline="") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["input", "output"])
        for example in examples:
            writer.writerow(example)


if __name__ == "__main__":
    # Assuming the script is run from the project root
    products_file = "data/json/products.json"
    csv_file = "data/training/classifier.csv"

    if not os.path.exists(products_file):
        print(f"Error: Products file not found at {products_file}")
    else:
        products = generate_training_examples(products_file)
        # For now, just print the number of products read
        print(f"Successfully read {len(products)} products from {products_file}")
        # Further logic to transform products into input/output pairs and append to CSV would go here
