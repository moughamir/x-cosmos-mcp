from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..utils.ollama_manager import list_ollama_models, pull_ollama_model

router = APIRouter()


class PullModelRequest(BaseModel):
    model_name: str


@router.get("/ollama/models")
async def get_ollama_models():
    """Get available Ollama models."""
    models = await list_ollama_models()
    if models is None:  # Check if an error occurred in list_ollama_models
        raise HTTPException(status_code=500, detail="Failed to retrieve Ollama models")

    # Transform the response to match frontend expectations
    transformed_models = []
    for model in models:
        transformed_models.append(
            {
                "name": model.get("name", ""),
                "size": model.get("size", 0),
                "modified_at": model.get("modified_at", ""),
            }
        )

    return transformed_models


@router.post("/ollama/pull")
async def pull_ollama_model_endpoint(request: PullModelRequest):
    """Pull an Ollama model."""
    result = await pull_ollama_model(request.model_name)

    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return {"message": "Model pulled successfully"}
