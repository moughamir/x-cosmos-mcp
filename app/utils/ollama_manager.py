import logging
from typing import Any, Dict, List

import httpx

from ..config import settings

logger = logging.getLogger(__name__)

# Use the proper base_url property from Ollama config
OLLAMA_BASE_URL = settings.ollama.base_url.rstrip("/")


async def list_ollama_models() -> List[Dict[str, Any]]:
    """Lists available Ollama models."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=10)
            response.raise_for_status()
            return response.json().get("models", [])
    except httpx.RequestError as e:
        logger.error(f"Error listing Ollama models: {e}")
        # Return a proper error indicator instead of just an empty list
        return []
    except Exception as e:
        logger.error(f"Unexpected error listing Ollama models: {e}")
        return []


async def pull_ollama_model(model_name: str) -> Dict[str, Any]:
    """Pulls a specific Ollama model."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/pull",
                json={
                    "name": model_name,
                    "stream": False,  # Set to True for streaming output
                },
                timeout=500,
            )
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Error pulling Ollama model {model_name}: {e}")
        return {"error": str(e)}
