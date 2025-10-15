from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, field_validator
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager
import logging
import os
import sys
from pathlib import Path
import asyncio
import json
import aiosqlite
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseCallNext

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
from app.config import settings, TaskType
from app.worker_pool import initialize_worker_pool, shutdown_worker_pool, get_worker_pool

# Create a global queue for pipeline tasks
pipeline_task_queue = asyncio.Queue()

# WebSocket connection manager for real-time updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {
            "pipeline_progress": [],
            "pipeline_updates": []
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
                except:
                    disconnected.append(connection)

            # Remove disconnected connections
            for conn in disconnected:
                self.active_connections[channel].remove(conn)

# Global connection manager instance
manager = ConnectionManager()

# Import the pipeline module to set up WebSocket broadcasting
from pipeline import set_websocket_manager

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

        # Initialize worker pool for parallel processing
        await initialize_worker_pool(max_workers=settings.workers.max_workers)
        logging.info(f"Worker pool initialized with {settings.workers.max_workers} workers")

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

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseCallNext):
        try:
            return await call_next(request)
        except Exception as e:
            logging.error(f"Unhandled exception: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal Server Error"},
            )

# Initialize FastAPI app with lifespan
app = FastAPI(lifespan=lifespan)
app.add_middleware(ErrorHandlingMiddleware)

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
    @field_validator('llm_confidence')
    @classmethod
    def validate_confidence(cls, v):
        if v is not None and (v < 0 or v > 1):
            raise ValueError('Confidence must be between 0 and 1')
        return v

class ModelPullRequest(BaseModel):
    model_name: str

class PipelineRunRequest(BaseModel):
    task_type: TaskType
    product_ids: Optional[List[int]] = None
    quantize: bool = False

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
    """Get available Ollama models"""
    try:
        models = await list_ollama_models()+
        return {"models": models, "status": "connected"}
    except Exception as e:
        logging.error(f"Error fetching Ollama models: {e}", exc_info=True)
        # Return a proper JSON error response instead of HTML
        return {"models": [], "status": "error", "error": "Unable to connect to Ollama service. Please ensure Ollama is running."}

@app.post("/api/ollama/pull")
async def pull_model(request: ModelPullRequest):
    result = await pull_ollama_model(request.model_name)
    return result

class BatchProcessRequest(BaseModel):
    task_type: TaskType
    product_ids: Optional[List[int]] = None
    batch_size: Optional[int] = None

@app.post("/api/pipeline/run")
async def run_pipeline_endpoint(request: PipelineRunRequest):
    """Run pipeline processing for products"""
    try:
        if not request.product_ids:
            # Fetch all product IDs if none are specified
            products = await get_all_products(settings.paths.database)
            product_ids = [product['id'] for product in products]
        else:
            product_ids = request.product_ids

        # Put the task on the queue
        await pipeline_task_queue.put({
            "product_ids": product_ids,
            "task_type": request.task_type,
            "quantize": request.quantize,
        })

        return {
            "status": "queued",
            "task_type": request.task_type.value,
            "product_count": len(product_ids),
            "message": f"Pipeline {request.task_type.value} queued for {len(product_ids)} products"
        }

    except Exception as e:
        logging.error(f"Error starting pipeline: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/api/pipeline/queue-status")
async def get_pipeline_queue_status():
    """Get the status of the pipeline queue."""
    return {"queue_size": pipeline_task_queue.qsize()}

@app.post("/api/batch/process")
async def batch_process_endpoint(request: BatchProcessRequest):
    """Process products in batches using worker pool"""
    from worker_pool import get_worker_pool

    try:
        if not request.product_ids:
            # Fetch all product IDs if none are specified
            products = await get_all_products(settings.paths.database)
            product_ids = [product['id'] for product in products]
        else:
            product_ids = request.product_ids

        # Use worker pool for batch processing
        worker_pool = get_worker_pool()
        batch_size = request.batch_size or settings.workers.batch_size

        # Split product IDs into batches
        batches = [product_ids[i:i + batch_size] for i in range(0, len(product_ids), batch_size)]

        batch_results = []
        for batch in batches:
            batch_data = {
                'batch': batch,
                'task_type': request.task_type.value,
                'products': []
            }

            # Prepare product data for each product in batch
            for product_id in batch:
                async with aiosqlite.connect(settings.paths.database) as conn:
                    conn.row_factory = aiosqlite.Row
                    cursor = await conn.cursor()
                    await cursor.execute(
                        "SELECT id, title, body_html, product_type, tags FROM products WHERE id = ?",
                        (product_id,)
                    )
                    product = await cursor.fetchone()

                if product:
                    product_id, title, body_html, product_type, tags = product
                    product_data = {
                        'id': product_id,
                        'title': title,
                        'body_html': body_html,
                        'product_type': product_type,
                        'tags': tags,
                        'task_type': request.task_type.value
                    }
                    batch_data['products'].append(product_data)

            # Submit batch task to worker pool
            task_id = await worker_pool.submit_task(
                task_type="batch_processing",
                data=batch_data,
                priority=2  # Higher priority for batch processing
            )

            batch_results.append({
                'batch_id': task_id,
                'product_count': len(batch),
                'status': 'submitted'
            })

        return {
            "status": "success",
            "batches_submitted": len(batch_results),
            "batch_details": batch_results
        }

    except Exception as e:
        logging.error(f"Error in batch processing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

# Remove duplicate run_pipeline_endpoint function (lines 300-348)
# This function is duplicated - keeping the first implementation (lines 192-225)
# which returns immediate results instead of just starting the pipeline

@app.get("/api/workers/status")
async def get_worker_status():
    """Get current worker pool status"""
    from worker_pool import get_worker_pool

    try:
        worker_pool = get_worker_pool()
        status = worker_pool.get_worker_status()
        return {
            "status": "active",
            "worker_pool": status
        }
    except Exception as e:
        logging.error(f"Error getting worker status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/api/taxonomy/tree")
async def get_taxonomy_tree_endpoint():
    try:
        taxonomy_tree = load_taxonomy()
        # Convert TaxonomyNode objects to dicts for JSON serialization
        return {name: node.to_dict() for name, node in taxonomy_tree.items()}
    except Exception as e:
        logging.error(f"Error fetching taxonomy tree: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/api/taxonomy/top-level")
async def get_top_level_taxonomy_endpoint():
    try:
        top_level_categories = get_top_level_categories()
        return top_level_categories
    except Exception as e:
        logging.error(f"Error fetching top-level taxonomy categories: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/api/prompts")
async def list_prompts():
    try:
        prompt_dir = settings.paths.prompt_dir
        prompt_files = [f for f in os.listdir(prompt_dir) if f.endswith(".j2")]
        return {"prompts": prompt_files}
    except Exception as e:
        logging.error(f"Error listing prompt files: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/api/prompts/{prompt_name}")
async def get_prompt_content(prompt_name: str):
    try:
        prompt_path = os.path.join(settings.paths.prompt_dir, prompt_name)
        if not os.path.exists(prompt_path) or not prompt_path.endswith(".j2"):
            raise HTTPException(status_code=404, detail="Prompt not found")
        
        with open(prompt_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"name": prompt_name, "content": content}
    except HTTPException as he:
    except Exception as e:
        logging.error(f"Error fetching prompt content for {prompt_name}: {e}", exc_info=True)
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

@app.websocket("/ws/pipeline-progress")
async def websocket_pipeline_progress(websocket: WebSocket):
    """WebSocket endpoint for real-time pipeline progress updates"""
    await manager.connect(websocket, "pipeline_progress")

    try:
        # Send initial pipeline runs data
        runs = await get_pipeline_runs(settings.paths.database, limit=50)
        runs_dict = [dict(run) for run in runs]
        await websocket.send_json({
            "type": "initial_data",
            "pipeline_runs": runs_dict
        })

        # Keep connection alive and listen for client messages
        while True:
            try:
                data = await websocket.receive_text()
                # Client can send messages to request specific data or control updates
                message = json.loads(data)

                if message.get("type") == "request_refresh":
                    # Send fresh data when client requests it
                    runs = await get_pipeline_runs(settings.paths.database, limit=50)
                    runs_dict = [dict(run) for run in runs]
                    await websocket.send_json({
                        "type": "pipeline_runs_update",
                        "pipeline_runs": runs_dict
                    })

            except json.JSONDecodeError:
                # Ignore invalid JSON
                continue

    except WebSocketDisconnect:
        manager.disconnect(websocket, "pipeline_progress")
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, "pipeline_progress")

@app.get("/{catchall:path}")
async def serve_frontend(request: Request):
    return FileResponse("admin/templates/index.html")