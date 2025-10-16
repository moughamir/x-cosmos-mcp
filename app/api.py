from typing import Any, Callable, Mapping, cast, Awaitable
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi import WebSocket

from .config import settings, TaskType
from .pipeline import MultiModelSEOManager
from .routers import products, pipelines, ollama, system
from .utils.db import (
    get_all_products,
    init_db_pool,
    update_database_schema,
)
from .websocket import ConnectionManager
from .worker_pool import initialize_worker_pool, shutdown_worker_pool
from .middleware.exception_handler import (
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)
import logging


# Initialize WebSocket manager globally
manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        # Initialize database connection pool
        await init_db_pool()
        logging.info("Database connection pool initialized successfully")

        # Update database schema
        await update_database_schema()
        logging.info("Database schema updated successfully")

        # Initialize SEO Manager with WebSocket manager
        seo_manager = MultiModelSEOManager(websocket_manager=manager)

        # Define task handlers
        task_handlers: Mapping[str, Callable[[Any], Awaitable[Any]]] = {
            TaskType.META_OPTIMIZATION.value: cast(
                Callable[[Any], Awaitable[Any]], seo_manager.optimize_meta_tags
            ),
            TaskType.CONTENT_REWRITING.value: cast(
                Callable[[Any], Awaitable[Any]], seo_manager.rewrite_content
            ),
            TaskType.KEYWORD_ANALYSIS.value: cast(
                Callable[[Any], Awaitable[Any]], seo_manager.analyze_keywords
            ),
            TaskType.TAG_OPTIMIZATION.value: cast(
                Callable[[Any], Awaitable[Any]], seo_manager.optimize_tags
            ),
            TaskType.CATEGORY_NORMALIZATION.value: cast(
                Callable[[Any], Awaitable[Any]], seo_manager.normalize_categories
            ),
            TaskType.SCHEMA_ANALYSIS.value: cast(
                Callable[[Any], Awaitable[Any]], seo_manager.analyze_schema
            ),
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

        # Set the seo_manager for the pipelines router to use
        pipelines.set_seo_manager(seo_manager)

    except Exception as e:
        logging.error(f"Startup error: {e}", exc_info=True)
        raise

    yield  # App runs here

    # Shutdown
    await shutdown_worker_pool()
    logging.info("Worker pool shutdown complete")


# Initialize FastAPI app and API router
app = FastAPI(lifespan=lifespan)

# Register exception handlers
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

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

# Include routers
api_router.include_router(products.router)
api_router.include_router(pipelines.router)
api_router.include_router(ollama.router)
api_router.include_router(system.router)


app.include_router(api_router)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket, "default")
    try:
        while True:
            await websocket.receive_text()
            # You can handle incoming WebSocket messages here if needed
            # await manager.send_personal_message(f"You wrote: {data}", websocket)
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
    finally:
        manager.disconnect(websocket, "default")
