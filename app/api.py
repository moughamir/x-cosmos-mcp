import logging
from contextlib import asynccontextmanager
from typing import Dict, List

from fastapi import (
    APIRouter,
    BackgroundTasks,
    FastAPI,
    HTTPException,
    WebSocket,
)
from fastapi.middleware.cors import CORSMiddleware
from functools import wraps

from .config import settings
from .pipeline import MultiModelSEOManager, TaskType, set_websocket_manager
from .utils.db import (
    get_all_products,
    get_change_log,
    get_db_schema,
    get_pipeline_runs,
    get_product_details,
    get_products_batch,
    get_products_for_review,
    log_change,
    mark_as_reviewed,
    update_database_schema,
    update_product_details,
)
from .utils.ollama_manager import list_ollama_models, pull_ollama_model

# Import worker pool for initialization
from .worker_pool import initialize_worker_pool, shutdown_worker_pool


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
seo_manager = MultiModelSEOManager()  # Make manager global


# Set up WebSocket manager for pipeline broadcasting
set_websocket_manager(manager)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        # Update database schema
        await update_database_schema()
        logging.info("Database schema updated successfully")

        # Initialize database connection pool
        from .utils.db import init_db_pool

        await init_db_pool()
        logging.info("Database connection pool initialized successfully")

        # Define task handlers
        task_handlers = {
            TaskType.META_OPTIMIZATION.value: seo_manager.optimize_meta_tags,
            TaskType.CONTENT_REWRITING.value: seo_manager.rewrite_content,
            TaskType.KEYWORD_ANALYSIS.value: seo_manager.analyze_keywords,
            TaskType.TAG_OPTIMIZATION.value: seo_manager.optimize_tags,
            TaskType.CATEGORY_NORMALIZATION.value: seo_manager.normalize_categories,  # ADDED
            TaskType.SCHEMA_ANALYSIS.value: seo_manager.analyze_schema,
        }

        # Initialize worker pool for parallel processing
        await initialize_worker_pool(
            max_workers=settings.workers.max_workers, task_handlers=task_handlers
        )
        logging.info(
            f"Worker pool initialized with {settings.workers.max_workers} workers"
        )

        # Test database connection by fetching products
        products = await get_all_products()
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

# CORS middleware
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_router = APIRouter(prefix="/api")


def api_error_handler(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            raise
        except Exception as e:
            logging.error(f"Error in {func.__name__}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error")

    return wrapper


@api_router.get("/products")
@api_error_handler
async def get_products():
    """Get all products from the database."""
    products = await get_all_products()
    return {"products": [dict(product) for product in products]}


@api_router.get("/products/batch")
async def get_products_batch_endpoint(limit: int = 10):
    """Get products for batch processing."""
    try:
        products = await get_products_batch(limit)
        return {"products": [dict(product) for product in products]}
    except Exception as e:
        logging.error(f"Error fetching products batch: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api_router.get("/products/review")
async def get_products_for_review_endpoint(limit: int = 10):
    """Get products that need review (low confidence scores)."""
    try:
        products = await get_products_for_review(limit)
        return {"products": [dict(product) for product in products]}
    except Exception as e:
        logging.error(f"Error fetching products for review: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api_router.get("/products/{product_id}")
async def get_product(product_id: int):
    """Get specific product details and change history."""
    try:
        result = await get_product_details(product_id)
        if not result["product"]:
            raise HTTPException(status_code=404, detail="Product not found")

        return {
            "product": dict(result["product"]),
            "changes": [dict(change) for change in result["changes"]],
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error fetching product {product_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api_router.post("/products/{product_id}/update")
async def update_product(product_id: int, updates: dict):
    """Update product details or create if not exists."""
    try:
        # Get original product data for logging if it exists
        original_product_details = await get_product_details(product_id)
        original_product = original_product_details["product"]

        # Update or create the product
        await update_product_details(product_id, **updates)

        # Log changes for each field being updated
        for field, new_value in updates.items():
            # Only log if the field existed and changed, or if it's a new field being set
            if (
                original_product
                and field in original_product
                and original_product[field] != new_value
            ):
                await log_change(
                    product_id, field, original_product[field], new_value, "api_update"
                )
            elif (
                not original_product and new_value is not None
            ):  # New product, log all fields being set
                await log_change(product_id, field, None, new_value, "api_create")

        return {"message": "Product updated/created successfully"}
    except Exception as e:
        logging.error(
            f"Error updating/creating product {product_id}: {e}", exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@api_router.get("/schema")
async def get_db_schema_endpoint():
    """Get database schema information."""
    try:
        schema = await get_db_schema()
        return {"schema": schema}
    except Exception as e:
        logging.error(f"Error fetching database schema: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api_router.get("/changes")
async def get_changes(limit: int = 100):
    """Get change log."""
    try:
        changes = await get_change_log(limit)
        return {"changes": [dict(change) for change in changes]}
    except Exception as e:
        logging.error(f"Error fetching changes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api_router.post("/changes/{product_id}/review")
async def mark_changes_reviewed(product_id: int):
    """Mark all changes for a product as reviewed."""
    try:
        await mark_as_reviewed(product_id)
        return {"message": "Changes marked as reviewed"}
    except Exception as e:
        logging.error(
            f"Error marking changes as reviewed for product {product_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@api_router.get("/pipeline/runs")
async def get_pipeline_runs_endpoint(limit: int = 100):
    """Get pipeline run history."""
    try:
        runs = await get_pipeline_runs(limit)
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
            transformed_models.append(
                {
                    "name": model.get("name", ""),
                    "size": model.get("size", 0),
                    "modified_at": model.get("modified_at", ""),
                }
            )

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
        return {"message": "Model pulled successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error pulling Ollama model: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.websocket("/ws/pipeline-progress")
async def websocket_pipeline_progress(websocket: WebSocket):
    """WebSocket endpoint for real-time pipeline progress updates."""
    await manager.connect(websocket, "pipeline_progress")
    try:
        while True:
            # Keep the connection alive and listen for messages
            data = await websocket.receive_text()
            # Echo back or handle specific commands if needed
            await websocket.send_text(f"Echo: {data}")
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, "pipeline_progress")


@api_router.post("/pipeline/run")
async def run_pipeline_endpoint(request: dict, background_tasks: BackgroundTasks):
    """Run a pipeline task."""
    try:
        task_type = request.get("task_type")
        product_ids = request.get("product_ids", [])

        if not task_type:
            raise HTTPException(status_code=400, detail="task_type is required")

        # Convert task_type string to TaskType enum
        try:
            from .pipeline import TaskType

            task_type_enum = TaskType(task_type)
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Invalid task_type: {task_type}"
            )

        # Use the global manager and run in background
        background_tasks.add_task(
            seo_manager.batch_process_products,
            product_ids=product_ids,
            task_type=task_type_enum,
        )

        return {
            "message": f"Pipeline run initiated for {task_type}",
            "task_type": task_type,
            "product_count": len(product_ids),
        }

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error running pipeline: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


app.include_router(api_router)
