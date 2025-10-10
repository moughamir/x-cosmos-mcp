from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
from contextlib import asynccontextmanager
import logging
import os
import sys
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

# Import after path setup
# Database and utility imports
from utils.db import (
    get_all_products, get_product_details, update_product_details,
    get_products_for_review, mark_as_reviewed, get_change_log, update_database_schema, get_db_schema, get_pipeline_runs
)
from utils.db_migrate import migrate_schema
from utils.ollama_manager import list_ollama_models, pull_ollama_model
from pipeline import MultiModelSEOManager
from config import settings, TaskType
import asyncio
import aiohttp
import aiosqlite

# Lifespan event handler for startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        # Update database schema
        await update_database_schema(settings.paths.database)
        logging.info("Database schema updated successfully")

        # Test database connection by fetching products
        products = await get_all_products(settings.paths.database)
        logging.info(f"Database connection successful. Found {len(products)} products.")
    except Exception as e:
        logging.error(f"Startup error: {e}", exc_info=True)
        raise

    yield  # App runs here

    # Shutdown (if needed)
    # Add any cleanup logic here

# Initialize FastAPI app with lifespan
app = FastAPI(lifespan=lifespan)

# Mount static files
app.mount("/static", StaticFiles(directory="admin/static"), name="static")

@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration"""
    return {"status": "healthy"}

# Models
class ProductUpdate(BaseModel):
    title: Optional[str] = None
    body_html: Optional[str] = None
    tags: Optional[str] = None
    category: Optional[str] = None
    normalized_title: Optional[str] = None
    normalized_body_html: Optional[str] = None
    llm_confidence: Optional[float] = None
    gmc_category_label: Optional[str] = None

class ModelPullRequest(BaseModel):
    model_name: str

class PipelineRunRequest(BaseModel):
    task_type: TaskType
    product_ids: Optional[List[int]] = None

@app.get("/api/products")
async def get_products():
    try:
        products = await get_all_products(settings.paths.database)
        return products
    except Exception as e:
        logging.error(f"Error fetching all products: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/api/products/{product_id}")
async def get_product(product_id: int):
    try:
        details = await get_product_details(settings.paths.database, product_id)
        if not details["product"]:
            raise HTTPException(status_code=404, detail="Product not found")
        return details
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Error fetching product details for ID {product_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.put("/api/products/{product_id}")
async def update_product(product_id: int, product_update: ProductUpdate):
    await update_product_details(settings.paths.database, product_id, **product_update.model_dump())
    return {"status": "success"}

@app.get("/api/products/review")
async def get_review_products(limit: int = 10):
    products = await get_products_for_review(settings.paths.database, limit=limit)
    return products

@app.put("/api/products/{product_id}/review")
async def review_product(product_id: int):
    await mark_as_reviewed(settings.paths.database, product_id)
    return {"status": "success"}

@app.get("/api/changes")
async def get_changes(limit: int = 100):
    changes = await get_change_log(settings.paths.database, limit=limit)
    return changes

@app.get("/api/ollama/models")
async def get_ollama_models():
    models = await list_ollama_models()
    return models

@app.post("/api/ollama/pull")
async def pull_model(request: ModelPullRequest):
    result = await pull_ollama_model(request.model_name)
    return result

@app.post("/api/pipeline/run")
async def run_pipeline(request: PipelineRunRequest):
    manager = MultiModelSEOManager()
    if not request.product_ids:
        # Fetch all product IDs if none are specified
        products = await get_all_products(settings.paths.database)
        product_ids = [product['id'] for product in products]
    else:
        product_ids = request.product_ids

    results = await manager.batch_process_products(product_ids, request.task_type)
    return {"status": "success", "results": results}

@app.get("/api/pipeline/runs")
async def get_pipeline_runs_endpoint(limit: int = 100):
    try:
        runs = await get_pipeline_runs(settings.paths.database, limit=limit)
        return runs
    except Exception as e:
        logging.error(f"Error fetching pipeline runs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/api/db/schema")
async def get_db_schema_endpoint():
    try:
        schema = await get_db_schema(settings.paths.database)
        # Convert aiosqlite.Row objects to dicts for JSON serialization
        # The schema returned by get_db_schema is already a dict of lists of dicts, so no direct conversion needed here.
        # However, ensure that the inner column details are plain dicts if they were aiosqlite.Row
        # For now, assuming get_db_schema already returns serializable data.
        return schema
    except Exception as e:
        logging.error(f"Error fetching DB schema: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.post("/api/db/migrate")
async def run_migrations():
    await migrate_schema(settings.paths.database)
    return {"status": "success", "message": "Database migrations applied."}

@app.get("/{catchall:path}")
async def serve_frontend(request: Request):
    return FileResponse("admin/templates/index.html")
