import logging
from contextlib import asynccontextmanager
from typing import Dict, List

import os
from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect, APIRouter
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .pipeline import MultiModelSEOManager, set_websocket_manager, TaskType
from .utils.db import (
    get_all_products,
    get_product_details,
    update_product_details,
    get_products_batch,
    get_products_for_review,
    get_db_schema,
    get_change_log,
    mark_as_reviewed,
    log_change,
    get_pipeline_runs,
    update_database_schema,
)
from .utils.db_migrate import migrate_schema

from .utils.ollama_manager import list_ollama_models, pull_ollama_model


# WebSocket connection manager for real-time updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {
            "pipeline_progress": [],
            "pipeline_updates": [],
        }

    async def connect(self, websocket: WebSocket, channel: str):
        await websocket.accept()
        if channel not in self.active_connections:
            self.active_connections[channel] = []
        self.active_connections[channel].append(websocket)

    def disconnect(self, websocket: WebSocket, channel: str):
        if channel in self.active_connections:
            self.active_connections[channel].remove(websocket)

    async def broadcast(self, message: dict, channel: str):
        if channel in self.active_connections:
            disconnected = []
            for connection in self.active_connections[channel]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logging.error(f"Error broadcasting message: {e}")
                    disconnected.append(connection)

            # Remove disconnected connections
            for conn in disconnected:
                self.active_connections[channel].remove(conn)


# Global connection manager instance
manager = ConnectionManager()


# Set up WebSocket manager for pipeline broadcasting
set_websocket_manager(manager)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        # Update database schema
        await update_database_schema(settings.paths.database)
        logging.info("Database schema updated successfully")

        # Run migrations for additional tables (e.g., pipeline_runs)
        await migrate_schema(settings.paths.database)
        logging.info("Database migrations applied successfully")

        # Define task handlers
        manager = MultiModelSEOManager()
        task_handlers = {
            TaskType.META_OPTIMIZATION.value: manager.optimize_meta_tags,
            TaskType.CONTENT_REWRITING.value: manager.rewrite_content,
            TaskType.KEYWORD_ANALYSIS.value: manager.analyze_keywords,
            TaskType.TAG_OPTIMIZATION.value: manager.optimize_tags,
        }

        # Initialize worker pool for parallel processing
        await initialize_worker_pool(
            max_workers=settings.workers.max_workers, task_handlers=task_handlers
        )
        logging.info(
            f"Worker pool initialized with {settings.workers.max_workers} workers"
        )

        # Test database connection by fetching products
        products = await get_all_products(settings.paths.database)
        logging.info(f"Database connection successful. Found {len(products)} products.")
    except Exception as e:
        logging.error(f"Startup error: {e}", exc_info=True)
        raise

    yield  # App runs here

    # Shutdown
    await shutdown_worker_pool()
    logging.info("Worker pool shutdown complete")


# Initialize FastAPI app and API router
app = FastAPI(lifespan=lifespan)
api_router = APIRouter(prefix="/api")


@api_router.get("/products")
async def get_products():
    """Get all products from the database."""
    try:
        products = await get_all_products(settings.paths.database)
        return {"products": [dict(product) for product in products]}
    except Exception as e:
        logging.error(f"Error fetching products: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api_router.get("/products/batch")
async def get_products_batch_endpoint(limit: int = 10):
    """Get products for batch processing."""
    try:
        products = await get_products_batch(settings.paths.database, limit)
        return {"products": [dict(product) for product in products]}
    except Exception as e:
        logging.error(f"Error fetching products batch: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api_router.get("/products/review")
async def get_products_for_review_endpoint(limit: int = 10):
    """Get products that need review (low confidence scores)."""
    try:
        products = await get_products_for_review(settings.paths.database, limit)
        return {"products": [dict(product) for product in products]}
    except Exception as e:
        logging.error(f"Error fetching products for review: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api_router.get("/products/{product_id}")
async def get_product(product_id: int):
    """Get specific product details and change history."""
    try:
        result = await get_product_details(settings.paths.database, product_id)
        if not result["product"]:
            raise HTTPException(status_code=404, detail="Product not found")

        return {
            "product": dict(result["product"]),
            "changes": [dict(change) for change in result["changes"]]
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error fetching product {product_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api_router.post("/products/{product_id}/update")
async def update_product(product_id: int, updates: dict):
    """Update product details."""
    try:
        # Log the changes before updating
        result = await get_product_details(settings.paths.database, product_id)
        if not result["product"]:
            raise HTTPException(status_code=404, detail="Product not found")

        product = dict(result["product"])

        # Log changes for each field being updated
        for field, new_value in updates.items():
            if field in product and product[field] != new_value:
                await log_change(
                    settings.paths.database,
                    product_id,
                    field,
                    product[field],
                    new_value,
                    "api_update"
                )

        # Update the product
        await update_product_details(settings.paths.database, product_id, **updates)

        return {"message": "Product updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error updating product {product_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api_router.get("/schema")
async def get_db_schema():
    """Get database schema information."""
    try:
        async with aiosqlite.connect(settings.paths.database) as conn:
            cur = await conn.cursor()
            await cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in await cur.fetchall()]

            schema = []
            # Exclude system tables that might cause issues
            exclude_tables = {'sqlite_sequence', 'sqlite_stat1', 'sqlite_stat4', 'products_fts_data', 'products_fts_idx', 'products_fts_docsize', 'products_fts_config'}

            for table_name in tables:
                if table_name in exclude_tables:
                    continue

                try:
                    await cur.execute(f"PRAGMA table_info({table_name});")
                    columns = await cur.fetchall()
                    schema.append({
                        "name": table_name,
                        "columns": [{"name": col[1], "type": col[2]} for col in columns]
                    })
                except Exception as e:
                    # Skip tables that cause issues
                    logging.warning(f"Skipping table {table_name} due to error: {e}")
                    continue

            return {"schema": schema}
    except Exception as e:
        logging.error(f"Error fetching database schema: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api_router.get("/changes")
async def get_changes(limit: int = 100):
    """Get change log."""
    try:
        changes = await get_change_log(settings.paths.database, limit)
        return {"changes": [dict(change) for change in changes]}
    except Exception as e:
        logging.error(f"Error fetching changes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api_router.post("/changes/{product_id}/review")
async def mark_changes_reviewed(product_id: int):
    """Mark all changes for a product as reviewed."""
    try:
        await mark_as_reviewed(settings.paths.database, product_id)
        return {"message": "Changes marked as reviewed"}
    except Exception as e:
        logging.error(f"Error marking changes as reviewed for product {product_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api_router.get("/pipeline/runs")
async def get_pipeline_runs(limit: int = 100):
    """Get pipeline run history."""
    try:
        runs = await get_pipeline_runs(settings.paths.database, limit)
        return {"runs": [dict(run) for run in runs]}
    except Exception as e:
        logging.error(f"Error fetching pipeline runs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api_router.get("/ollama/models")
async def get_ollama_models():
    """Get available Ollama models."""
    try:
        models = await list_ollama_models()
        # Transform the response to match frontend expectations
        transformed_models = []
        for model in models:
            transformed_models.append({
                "name": model.get("name", ""),
                "size": model.get("size", 0),
                "modified_at": model.get("modified_at", "")
            })

        return transformed_models
    except Exception as e:
        logging.error(f"Error fetching Ollama models: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api_router.post("/ollama/pull")
async def pull_ollama_model_endpoint(request: dict):
    """Pull an Ollama model."""
    try:
        model_name = request.get("model_name")
        if not model_name:
            raise HTTPException(status_code=400, detail="model_name is required")

        result = await pull_ollama_model(model_name)

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        return {"message": f"Model {model_name} pull initiated successfully", "result": result}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error pulling Ollama model: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

# Include the API router in the main app
app.include_router(api_router)

# Mount static files for the frontend
app.mount("/static", StaticFiles(directory=settings.paths.static_dir), name="static")

@app.get("/{catchall:path}")
async def serve_frontend(request: Request):
    return FileResponse("views/admin/templates/index.html")
