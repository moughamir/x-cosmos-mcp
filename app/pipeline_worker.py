import asyncio
import logging

from app.pipeline.pipeline import MultiModelSEOManager
from app.config import TaskType, settings
from app.worker_pool import initialize_worker_pool, shutdown_worker_pool
from app.api import pipeline_task_queue
from app.utils.logging_config import setup_logging

logger = logging.getLogger(__name__)

async def main():
    """Main function for the pipeline worker."""
    setup_logging()

    # Initialize the worker pool
    await initialize_worker_pool(max_workers=settings.workers.max_workers)

    # Create a manager for the pipeline
    manager = MultiModelSEOManager()

    # Start a worker to process tasks from the queue
    asyncio.create_task(worker(pipeline_task_queue, manager))

    # Keep the worker running
    while True:
        await asyncio.sleep(1)

async def worker(task_queue: asyncio.Queue, manager: MultiModelSEOManager):
    """Worker to process tasks from the queue."""
    while True:
        try:
            task = await task_queue.get()
            product_ids = task["product_ids"]
            task_type = task["task_type"]
            quantize = task.get("quantize", False)

            logger.info(f"Processing {len(product_ids)} products for task {task_type}")

            await manager.batch_process_products(product_ids, task_type, quantize=quantize)

            task_queue.task_done()
        except Exception as e:
            logger.error(f"Error processing task: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())
