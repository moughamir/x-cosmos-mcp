#!/bin/bash

# Set the OLLAMA_MODELS environment variable to store models in the project directory
OLLAMA_MODELS_PATH="$(pwd)/data/ollama.models"

# Create a .env file for Docker Compose to use
echo "OLLAMA_MODELS=${OLLAMA_MODELS_PATH}" > .env

echo "OLLAMA_MODELS is set to: ${OLLAMA_MODELS_PATH}"

# Ensure the ollama.models directory exists
mkdir -p "${OLLAMA_MODELS_PATH}"

# List of models to download, optimized for low-end hardware
MODELS=(
    "llama3.2:1b-instruct-q4_K_M"
    "gemma3:1b-it-qat"
    "qwen2:1.5b"
    "llama3.2:1b-instruct-q2_K"
    "gemma3:1b-it-q2_K"
    "qwen2:0.5b"
    "nomic-embed-text"
)

echo "Starting Ollama model downloads..."

for model in "${MODELS[@]}"; do
    echo "Attempting to pull model: $model"
    ollama pull "$model"
    if [ $? -eq 0 ]; then
        echo "Successfully pulled $model"
    else
        echo "Failed to pull $model"
    fi
done

echo "Ollama model configuration and download complete."
