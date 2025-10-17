#!/bin/bash
# This script takes a product JSON file as an argument and outputs its structure.

if [ -z "$1" ]; then
  echo "Usage: $0 <product_json_file>"
  exit 1
fi

if [ ! -f "$1" ]; then
  echo "File not found: $1"
  exit 1
fi

# Use jq to extract keys from the product and its nested objects.
jq '{ "product_keys": keys, "variant_keys": .variants[0] | keys, "image_keys": .images[0] | keys, "option_keys": .options[0] | keys }' "$1" > product_schema.json

echo "Product schema saved to product_schema.json"