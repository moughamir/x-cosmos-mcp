import requests
from typing import List, Dict, Any
from config import settings

OLLAMA_URL = f"{settings.ollama.host}:{settings.ollama.port}"

async def list_ollama_models() -> List[Dict[str, Any]]:
    """Lists available Ollama models."""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=10)
        response.raise_for_status()
        return response.json().get("models", [])
    except requests.exceptions.RequestException as e:
        print(f"Error listing Ollama models: {e}")
        return []

async def pull_ollama_model(model_name: str) -> Dict[str, Any]:
    """Pulls a specific Ollama model."""
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/pull",
            json={
                "name": model_name,
                "stream": False # Set to True for streaming output
            },
            timeout=300 # Increased timeout for model pulls
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error pulling Ollama model {model_name}: {e}")
        return {"error": str(e)}
