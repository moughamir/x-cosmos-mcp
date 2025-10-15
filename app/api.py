import logging
from contextlib import asynccontextmanager
from typing import Dict, List

import os
from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .pipeline import MultiModelSEOManager, set_websocket_manager, TaskType
from .utils.db import (
    get_all_products,
    update_database_schema,
)
from .utils.db_migrate import migrate_schema

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


from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect, APIRouter

# ... (imports remain the same)

# Initialize FastAPI app and API router
app = FastAPI(lifespan=lifespan)
api_router = APIRouter(prefix="/api")

# ... (lifespan and ConnectionManager remain the same)

@api_router.get("/products")
async def get_products():
    # ... (endpoint logic remains the same)

@api_router.get("/products/{product_id}")
async def get_product(product_id: int):
    # ... (endpoint logic remains the same)

# ... (move all other @app.get, @app.post, @app.put routes to @api_router)

# Include the API router in the main app
app.include_router(api_router)

# Mount static files for the frontend
app.mount("/static", StaticFiles(directory=settings.paths.static_dir), name="static")

@app.get("/{catchall:path}")
async def serve_frontend(request: Request):
    return FileResponse("views/admin/templates/index.html")
