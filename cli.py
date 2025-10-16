import argparse
import asyncio
import logging

from app.config import TaskType, settings
from app.pipeline import MultiModelSEOManager
from app.utils.db import (
    close_db_pool,
    get_all_products,
    get_products_batch,
    init_db_pool,
)
from app.utils.logging_config import setup_logging
from app.worker_pool import initialize_worker_pool, shutdown_worker_pool


async def main():
    """Main function to run MCP workflows from the CLI."""
    setup_logging()

    task_choices = [t.value for t in TaskType]

    parser = argparse.ArgumentParser(description="MCP Workflow CLI")
    parser.add_argument(
        "task",
        type=str,
        choices=task_choices,
        help=f"The pipeline task to run. Choices: {', '.join(task_choices)}",
    )
    parser.add_argument(
        "--product-ids",
        type=int,
        nargs="+",
        help="Specific product IDs to process. If not provided, processes a sample.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all products instead of a sample.",
    )
    parser.add_argument(
        "--quantize",
        action="store_true",
        help="Use quantized models for the task.",
    )

    args = parser.parse_args()

    manager = MultiModelSEOManager()
    task_type = TaskType(args.task)

    product_ids = args.product_ids
    try:
        logging.info("🔧 Initializing database pool...")
        await init_db_pool()

        if not product_ids:
            if args.all:
                logging.info("Fetching all product IDs...")
                all_products = await get_all_products()
                product_ids = [product["id"] for product in all_products]
            else:
                logging.info("Fetching a sample of 10 unprocessed products...")
                sample_products = await get_products_batch(limit=10)
                product_ids = [product["id"] for product in sample_products]

        if not product_ids:
            logging.warning("No product IDs to process.")
            return

        logging.info(
            f"🚀 Starting task '{task_type.value}' for {len(product_ids)} products..."
        )

        task_handlers = {
            TaskType.META_OPTIMIZATION.value: manager.optimize_meta_tags,
            TaskType.CONTENT_REWRITING.value: manager.rewrite_content,
            TaskType.KEYWORD_ANALYSIS.value: manager.analyze_keywords,
            TaskType.TAG_OPTIMIZATION.value: manager.optimize_tags,
            TaskType.CATEGORY_NORMALIZATION.value: manager.normalize_categories,
        }

        logging.info("🔧 Initializing worker pool...")
        await initialize_worker_pool(
            max_workers=settings.workers.max_workers, task_handlers=task_handlers
        )

        results = await manager.batch_process_products(
            product_ids, task_type, quantize=args.quantize
        )

        success_count = len(
            [
                r
                for r in results
                if r.get("status") == "success"
                or r.get("status") == "Category normalized"
                or r.get("status") == "completed"
            ]
        )
        error_count = len(results) - success_count

        logging.info(f"✅ Processed {success_count} products successfully.")
        if error_count > 0:
            logging.error(f"❌ Failed to process {error_count} products.")

    except Exception as e:
        logging.error(f"An error occurred during the pipeline run: {e}", exc_info=True)
    finally:
        logging.info("🛑 Shutting down worker pool...")
        await shutdown_worker_pool()
        logging.info("🛑 Closing database pool...")
        await close_db_pool()


if __name__ == "__main__":
    asyncio.run(main())
