import requests
from ..config import settings

def count_tokens(text: str, model: str) -> int:
    """Count the number of tokens in a string using the Ollama API."""
    try:
        response = requests.post(
            f"{settings.ollama.base_url}/api/tokenize",
            json={"model": model, "text": text},
            timeout=10,
        )
        response.raise_for_status()
        return len(response.json().get("tokens", []))
    except requests.exceptions.RequestException as e:
        print(f"Error counting tokens: {e}")
        return -1

def tokenize(text: str, model: str) -> list[int]:
    """Tokenize a string using the Ollama API."""
    try:
        response = requests.post(
            f"{settings.ollama.base_url}/api/tokenize",
            json={"model": model, "text": text},
            timeout=10,
        )
        response.raise_for_status()
        return response.json().get("tokens", [])
    except requests.exceptions.RequestException as e:
        print(f"Error tokenizing text: {e}")
        return []

def truncate_text_to_tokens(text: str, model: str, max_tokens: int) -> str:
    """Truncate text to a specific number of tokens."""
    tokens = tokenize(text, model)
    if len(tokens) > max_tokens:
        return " ".join(text.split()[:max_tokens])  # A simple approximation
    return text