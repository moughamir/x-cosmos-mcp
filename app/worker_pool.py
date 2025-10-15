import asyncio
import logging
from typing import Optional

from app.class.worker_pool import WorkerPool

logger = logging.getLogger(__name__)

# Global worker pool instance
worker_pool: Optional[WorkerPool] = None

def get_worker_pool() -> WorkerPool:
    """Get or create the global worker pool"""
    global worker_pool
    if worker_pool is None:
        worker_pool = WorkerPool()
    return worker_pool

async def initialize_worker_pool(max_workers: int = 4):
    """Initialize the global worker pool"""
    global worker_pool
    if worker_pool is None:
        worker_pool = WorkerPool(max_workers=max_workers)
        await worker_pool.start()
        logger.info(f"Worker pool initialized with {max_workers} workers")

async def shutdown_worker_pool():
    """Shutdown the global worker pool"""
    global worker_pool
    if worker_pool:
        await worker_pool.stop()
        worker_pool = None
        logger.info("Worker pool shutdown complete")
