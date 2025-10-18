import datetime
import logging
from contextlib import asynccontextmanager
from typing import Dict, List, Optional
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
    update_product_details,
    update_product_tags,
)
from .utils.ollama_manager import list_ollama_models, pull_ollama_model
from .utils.taxonomy import list_taxonomy_files, parse_taxonomy_file
from .utils.prompts import get_prompt_files, get_prompt_content, save_prompt_content

# Import worker pool for initialization
from .worker_pool import initialize_worker_pool, shutdown_worker_pool
import asyncio
from starlette.websockets import WebSocketDisconnect, WebSocketState


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
            try:
                self.active_connections[channel].remove(websocket)
            except ValueError:
                # WebSocket already removed (e.g., during broadcast cleanup)
                pass

    async def broadcast(self, message: dict, channel: str):
        if channel in self.active_connections:
            disconnected = []
            for connection in self.active_connections[channel]:
                try:
                    # Check if connection is still open before sending
                    if connection.client_state == WebSocketState.CONNECTED:
                        await connection.send_json(message)
                    else:
                        disconnected.append(connection)
                except Exception as e:
                    logging.warning(f"Error broadcasting to client: {e}")
                    disconnected.append(connection)

            # Remove disconnected connections
            for conn in disconnected:
                try:
                    self.active_connections[channel].remove(conn)
                except ValueError:
                    pass  # Already removed


# Global connection manager instance
manager = ConnectionManager()
seo_manager = MultiModelSEOManager()  # Make manager global


# Set up WebSocket manager for pipeline broadcasting
set_websocket_manager(manager)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
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


@api_router.get("/prompts")
@api_error_handler
async def get_prompts():
    """Lists all available prompt files."""
    prompts = get_prompt_files()
    return {"prompts": prompts}


@api_router.get("/prompts/{path:path}")
@api_error_handler
async def get_single_prompt(path: str):
    """Gets the content of a single prompt file."""
    content = get_prompt_content(path)
    if content is None:
        raise HTTPException(status_code=404, detail="Prompt file not found")
    return {"path": path, "content": content}


@api_router.post("/prompts/{path:path}")
@api_error_handler
async def save_single_prompt(path: str, request: dict):
    """Saves content to a single prompt file."""
    content = request.get("content")
    if content is None:
        raise HTTPException(status_code=400, detail="Content is required")

    success = save_prompt_content(path, content)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save prompt file")
    return {"message": "Prompt saved successfully"}


@api_router.get("/taxonomy")
@api_error_handler
async def get_taxonomy_files():
    """Lists all available taxonomy files."""
    files = list_taxonomy_files()
    return {"files": files}


@api_router.get("/taxonomy/{filename}")
@api_error_handler
async def get_taxonomy_tree(filename: str):
    """Returns the parsed tree structure for a given taxonomy file."""
    if not filename.endswith(".txt") or "/" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    tree = parse_taxonomy_file(filename)
    if not tree:
        raise HTTPException(status_code=404, detail="Taxonomy file not found")
    return {"tree": tree}


@api_router.get("/products")
@api_error_handler
async def get_products(
    page: int = 1,
    limit: int = 50,
    search: Optional[str] = None,
    category: Optional[str] = None,
    min_confidence: Optional[float] = None,
    max_confidence: Optional[float] = None,
):
    """Get products with pagination and filtering."""
    from .utils.db import get_products_paginated

    result = await get_products_paginated(
        page=page,
        limit=limit,
        search=search,
        category=category,
        min_confidence=min_confidence,
        max_confidence=max_confidence,
    )
    return result


@api_router.get("/products/batch")
@api_error_handler
async def get_products_batch_endpoint(limit: int = 10):
    """Get products for batch processing."""
    try:
        products = await get_products_batch(limit)
        return {"products": [dict(product) for product in products]}
    except Exception as e:
        logging.error(f"Error fetching products batch: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api_router.get("/products/review")
@api_error_handler
async def get_products_for_review_endpoint(limit: int = 10):
    """Get products that need review (low confidence scores)."""
    try:
        products = await get_products_for_review(limit)
        return {"products": [dict(product) for product in products]}
    except Exception as e:
        logging.error(f"Error fetching products for review: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api_router.get("/products/{product_id}")
@api_error_handler
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
@api_error_handler
async def update_product(product_id: int, updates: dict):
    """Update product details or create if not exists."""
    try:
        # Get original product data for logging if it exists
        original_product_details = await get_product_details(product_id)
        original_product = original_product_details["product"]

        # Filter out read-only/computed fields that shouldn't be updated directly
        # These are JOIN results or computed fields, not actual columns in products table
        readonly_fields = {
            "vendor_name",
            "product_type_name",
            "images",
            "variants",
            "options",
            "created_at",
            "updated_at",  # These are auto-managed
        }

        # Extract tags separately (they need special handling via junction table)
        tags = updates.pop("tags", None)

        filtered_updates = {
            k: v for k, v in updates.items() if k not in readonly_fields
        }

        # Update or create the product with filtered fields
        await update_product_details(product_id, **filtered_updates)

        # Handle tags separately if provided
        if tags is not None:
            # Convert tags to list if it's a string or array
            if isinstance(tags, str):
                tags_list = [t.strip() for t in tags.split(",") if t.strip()]
            elif isinstance(tags, list):
                tags_list = tags
            else:
                tags_list = []

            await update_product_tags(product_id, tags_list)

        # Log changes for each field being updated (only filtered fields)
        for field, new_value in filtered_updates.items():
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
@api_error_handler
async def get_db_schema_endpoint():
    """Get database schema information."""
    try:
        schema = await get_db_schema()
        return {"schema": schema}
    except Exception as e:
        logging.error(f"Error fetching database schema: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api_router.get("/changes")
@api_error_handler
async def get_changes(limit: int = 100):
    """Get change log."""
    try:
        changes = await get_change_log(limit)
        return {"changes": [dict(change) for change in changes]}
    except Exception as e:
        logging.error(f"Error fetching changes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api_router.post("/changes/{product_id}/review")
@api_error_handler
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
@api_error_handler
async def get_pipeline_runs_endpoint(limit: int = 100):
    """Get pipeline run history."""
    try:
        runs = await get_pipeline_runs(limit)
        return {"runs": [dict(run) for run in runs]}
    except Exception as e:
        logging.error(f"Error fetching pipeline runs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api_router.get("/ollama/models")
@api_error_handler
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

        return {"models": transformed_models}
    except Exception as e:
        logging.error(f"Error fetching Ollama models: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api_router.post("/ollama/pull")
@api_error_handler
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
        # Send initial data when client connects
        pipeline_runs = await get_pipeline_runs(limit=10)
        # Convert datetime objects to ISO format strings for JSON serialization
        runs_dict = []
        for run in pipeline_runs:
            run_dict = dict(run)
            for key, value in run_dict.items():
                if isinstance(value, datetime.datetime):
                    run_dict[key] = value.isoformat()
            runs_dict.append(run_dict)

        await websocket.send_json({"type": "initial_data", "pipeline_runs": runs_dict})

        # Keep the connection alive by periodically sending a ping.
        while True:
            # Check if connection is still open before sending
            if websocket.client_state != WebSocketState.CONNECTED:
                break
            await websocket.send_json(
                {"type": "ping", "timestamp": datetime.datetime.now().isoformat()}
            )
            await asyncio.sleep(25)  # Send ping every 25 seconds
    except WebSocketDisconnect:
        logging.info("Client disconnected from pipeline progress.")
    except Exception as e:
        logging.error(f"WebSocket error: {e}", exc_info=True)
    finally:
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
