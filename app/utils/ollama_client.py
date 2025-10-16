import json
import logging
import re
from typing import Any, Dict

import httpx

from ..config import settings

logger = logging.getLogger(__name__)


class OllamaClient:
    def __init__(self):
        self.ollama_url = settings.ollama.base_url

    async def _check_model_availability(self, model_name: str) -> bool:
        """Check if a model is available in Ollama"""
        try:
            async with httpx.AsyncClient() as client:
                # First check if model exists in the tags list
                response = await client.get(f"{self.ollama_url}/api/tags", timeout=5)
                if response.status_code == 200:
                    tags_data = response.json()
                    available_models = [
                        model["name"] for model in tags_data.get("models", [])
                    ]
                    if model_name in available_models:
                        return True

                # Fallback to generation test with shorter timeout
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={"model": model_name, "prompt": "test", "stream": False},
                    timeout=500,
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Error checking model availability: {e}")
            return False

    async def generate(
        self,
        model: str,
        prompt: str,
        capabilities: Dict[str, Any],
        quantize: bool = False,
    ) -> Dict[str, Any]:
        """Make actual call to Ollama model"""
        if quantize:
            model = settings.models.quantized_models.get(model, model)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "top_p": 0.9,
                        "num_predict": capabilities.get("max_tokens", 1024),
                    },
                },
                timeout=500,
            )

        if response.status_code == 200:
            result = response.json()
            return self._parse_model_response(result["response"])
        else:
            raise Exception(f"Model API error: {response.status_code}")

    def _parse_model_response(self, response: str) -> Dict[str, Any]:
        """Parse model response with robust error handling"""
        try:
            # Try to extract JSON from response
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError as e:
            logger.error(f"JSON decoding error in model response: {e}")
            pass

        # Fallback: return raw response
        return {"raw_response": response, "error": "JSON parsing failed"}

    @staticmethod
    def validate_response(response: Dict[str, Any], task_type: Any) -> bool:
        """Validate that response contains required fields"""
        from ..config import TaskType

        required_fields = {
            TaskType.META_OPTIMIZATION: [
                "meta_title",
                "meta_description",
                "seo_keywords",
            ],
            TaskType.CONTENT_REWRITING: ["optimized_title", "optimized_description"],
            TaskType.KEYWORD_ANALYSIS: ["primary_keywords", "long_tail_keywords"],
            TaskType.TAG_OPTIMIZATION: ["optimized_tags", "removed_tags", "added_tags"],
            TaskType.SCHEMA_ANALYSIS: ["schema_compliance", "issues"],
        }

        required = required_fields.get(task_type, [])
        return all(field in response for field in required)
