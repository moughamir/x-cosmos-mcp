# test_transform.py
import json
import logging
from optimus_v3 import OptimusV3

# Configure logging to see output from the OptimusV3 class
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")


def main():
    """
    Test script to run the OptimusV3 transformation pipeline on a single sample product.
    """
    # Initialize the OptimusV3 engine
    # It will automatically use environment variables for configuration
    p = OptimusV3()

    # Load a sample product from a JSON file
    try:
        with open("sample_product.json", "r", encoding="utf-8") as f:
            prod = json.load(f)
    except FileNotFoundError:
        print(
            "[ERROR] sample_product.json not found. Please create it in the same directory."
        )
        return
    except json.JSONDecodeError:
        print("[ERROR] sample_product.json is not a valid JSON file.")
        return

    # Run the full transformation pipeline, including embeddings
    print("--- Starting Product Transformation ---")
    v3_output = p.transform_product_to_v3(prod, include_embeddings=True)
    print("--- Transformation Complete ---\n")

    # Print the final result in a readable format
    print("--- OptimusV3 Output ---")
    print(json.dumps(v3_output, indent=2, ensure_ascii=False))

    # Save the local enhanced copy for inspection
    p.save_local_copy(v3_output)


if __name__ == "__main__":
    main()
