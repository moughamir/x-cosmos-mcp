import csv
import json
import os


def generate_training_examples(products_file, num_examples=2):
    """Generate training examples from a products JSON file."""
    with open(products_file, "r") as f:
        products = json.load(f)

    training_examples = []

    # Example 1: Samsung Galaxy Z Flip7
    if len(products) > 0:
        product1 = products[0]
        input1 = {
            "title": product1["title"],
            "body_html": product1["body_html"],
            "tags": ", ".join(product1["tags"]),
            "product_type": product1["product_type"],
        }
        output1 = {
            "title": "Samsung Galaxy Z Flip7 5G Unlocked Smartphone",
            "body_html": "<p>Discover the future of mobile technology with the Samsung Galaxy Z Flip7. Featuring a stunning foldable Dynamic AMOLED display, this unlocked smartphone delivers vibrant colors and a smooth 120Hz refresh rate. Its versatile dual-lens camera system with FlexCam allows for hands-free photos and creative angles. Running on the latest Android with Samsung's One UI, the Z Flip7 offers a seamless and intuitive user experience, optimized for its unique foldable design.</p><ul><li>Display: 6.7-inch Foldable Dynamic AMOLED</li><li>Camera: 12MP Wide, 12MP Ultra-Wide</li><li>Operating System: Android with One UI</li><li>Connectivity: 5G, Wi-Fi 6E, Bluetooth 5.3</li></ul>",
            "tags": "samsung, galaxy z flip, foldable phone, unlocked, 5g, smartphone, android",
            "category": "Electronics > Communications > Telephony > Mobile Phones",
            "confidence": 0.95,
        }
        training_examples.append((json.dumps(input1), json.dumps(output1)))

    # Example 2: Google Pixel 10 Pro XL
    if len(products) > 1:
        product2 = products[1]
        input2 = {
            "title": product2["title"],
            "body_html": product2["body_html"],
            "tags": ", ".join(product2["tags"]),
            "product_type": product2["product_type"],
        }
        output2 = {
            "title": "Google Pixel 10 Pro XL 5G Unlocked Smartphone",
            "body_html": "<p>Experience the power of Google AI with the Pixel 10 Pro XL. Its 6.8-inch Super Actua OLED display provides a brilliant and smooth viewing experience with an adaptive 120Hz refresh rate. The pro-grade triple camera system, featuring a 50MP main lens and 5x optical zoom, captures stunning photos and videos in any light. Powered by the Google Tensor G5 chip, the Pixel 10 Pro XL delivers intelligent performance and all-day battery life.</p><ul><li>Display: 6.8-inch Super Actua OLED (1-120Hz)</li><li>Camera: 50MP Wide, 48MP Ultra-Wide, 48MP Telephoto (5x Optical Zoom)</li><li>Processor: Google Tensor G5</li><li>Operating System: Android with 7 years of updates</li></ul>",
            "tags": "google pixel, pixel 10 pro, unlocked, 5g, smartphone, android, tensor",
            "category": "Electronics > Communications > Telephony > Mobile Phones",
            "confidence": 0.98,
        }
        training_examples.append((json.dumps(input2), json.dumps(output2)))

    return training_examples


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
        examples = generate_training_examples(products_file)
        append_to_csv(csv_file, examples)
        print(f"Successfully added {len(examples)} new examples to {csv_file}")
