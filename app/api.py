import logging
from contextlib import asynccontextmanager
from typing import Dict, List

from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .pipeline import set_websocket_manager
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

        # Initialize worker pool for parallel processing
        await initialize_worker_pool(max_workers=settings.workers.max_workers)
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


# Initialize FastAPI app with lifespan
app = FastAPI(lifespan=lifespan)

# Mount static files
app.mount("/static", StaticFiles(directory="/app/static"), name="static")


@app.get("/{catchall:path}")
async def serve_frontend(request: Request):
    return FileResponse("/app/static/index.html")
