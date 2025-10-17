import argparse
import asyncio
import logging
import sys
from typing import List, Optional

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


async def run_workflow(
    task_types: List[TaskType],
    product_ids: List[int],
    quantize: bool = False,
    manager: Optional[MultiModelSEOManager] = None,
) -> dict:
    """Run a workflow (single or multiple tasks) on products."""
    if manager is None:
        manager = MultiModelSEOManager()

    all_results = {}
    total_success = 0
    total_failed = 0

    for task_type in task_types:
        logging.info(f"\n{'='*60}")
        logging.info(f"🚀 Running task: {task_type.value}")
        logging.info(f"{'='*60}\n")

        results = await manager.batch_process_products(
            product_ids, task_type, quantize=quantize
        )

        success_count = len(
            [
                r
                for r in results
                if r.get("status") in ["success", "completed", "Category normalized"]
            ]
        )
        error_count = len(results) - success_count

        all_results[task_type.value] = {
            "results": results,
            "success": success_count,
            "failed": error_count,
        }

        total_success += success_count
        total_failed += error_count

        logging.info(
            f"✅ {task_type.value}: {success_count} succeeded, {error_count} failed"
        )

    return {
        "tasks": all_results,
        "total_success": total_success,
        "total_failed": total_failed,
    }


async def main():
    """Main function to run MCP workflows from the CLI."""
    setup_logging()

    task_choices = [t.value for t in TaskType]

    parser = argparse.ArgumentParser(
        description="MCP Workflow CLI - Run AI-powered SEO optimization tasks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run single task on specific products
  python cli.py category_normalization --product-ids 123 456 789

  # Run single task on all products
  python cli.py tag_optimization --all

  # Run workflow (multiple tasks in sequence)
  python cli.py workflow --tasks category_normalization tag_optimization meta_optimization --all

  # Run with quantized models for faster processing
  python cli.py content_rewriting --all --quantize

  # Process sample of 10 products (default)
  python cli.py keyword_analysis
        """,
    )
    parser.add_argument(
        "task",
        type=str,
        choices=task_choices + ["workflow"],
        help=f"The pipeline task to run. Use 'workflow' for multiple tasks. Choices: {', '.join(task_choices + ['workflow'])}",
    )
    parser.add_argument(
        "--tasks",
        type=str,
        nargs="+",
        choices=task_choices,
        help="Tasks to run in workflow mode (only used with 'workflow' task)",
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
        "--limit",
        type=int,
        default=10,
        help="Number of products to process if --all is not specified (default: 10)",
    )
    parser.add_argument(
        "--quantize",
        action="store_true",
        help="Use quantized models for faster processing.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without actually running tasks.",
    )

    args = parser.parse_args()

    # Validate workflow mode
    if args.task == "workflow":
        if not args.tasks:
            logging.error("❌ Error: --tasks is required when using 'workflow' mode")
            parser.print_help()
            sys.exit(1)
        task_types = [TaskType(t) for t in args.tasks]
    else:
        task_types = [TaskType(args.task)]

    manager = MultiModelSEOManager()
    product_ids = args.product_ids

    try:
        logging.info("🔧 Initializing database pool...")
        await init_db_pool()

        # Fetch product IDs
        if not product_ids:
            if args.all:
                logging.info("Fetching all product IDs...")
                all_products = await get_all_products()
                product_ids = [product["id"] for product in all_products]
            else:
                logging.info(
                    f"Fetching a sample of {args.limit} unprocessed products..."
                )
                sample_products = await get_products_batch(limit=args.limit)
                product_ids = [product["id"] for product in sample_products]

        if not product_ids:
            logging.warning("⚠️  No product IDs to process.")
            return

        # Dry run mode
        if args.dry_run:
            logging.info(f"\n{'='*60}")
            logging.info("🔍 DRY RUN MODE - No changes will be made")
            logging.info(f"{'='*60}")
            logging.info(f"Tasks to run: {', '.join([t.value for t in task_types])}")
            logging.info(f"Products to process: {len(product_ids)}")
            logging.info(
                f"Product IDs: {product_ids[:10]}{'...' if len(product_ids) > 10 else ''}"
            )
            logging.info(f"Quantized models: {'Yes' if args.quantize else 'No'}")
            logging.info(f"{'='*60}\n")
            return

        # Initialize worker pool
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

        # Run workflow
        logging.info(f"\n{'='*60}")
        logging.info(f"🚀 Starting workflow for {len(product_ids)} products")
        logging.info(f"Tasks: {', '.join([t.value for t in task_types])}")
        logging.info(f"{'='*60}\n")

        workflow_results = await run_workflow(
            task_types, product_ids, quantize=args.quantize, manager=manager
        )

        # Print summary
        logging.info(f"\n{'='*60}")
        logging.info("📊 WORKFLOW SUMMARY")
        logging.info(f"{'='*60}")
        for task_name, task_result in workflow_results["tasks"].items():
            logging.info(
                f"  {task_name}: ✅ {task_result['success']} succeeded, "
                f"❌ {task_result['failed']} failed"
            )
        logging.info(f"{'='*60}")
        logging.info(
            f"TOTAL: ✅ {workflow_results['total_success']} succeeded, "
            f"❌ {workflow_results['total_failed']} failed"
        )
        logging.info(f"{'='*60}\n")

    except KeyboardInterrupt:
        logging.warning("\n⚠️  Workflow interrupted by user")
        sys.exit(130)
    except Exception as e:
        logging.error(f"❌ An error occurred during the workflow: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logging.info("🛑 Shutting down worker pool...")
        await shutdown_worker_pool()
        logging.info("🛑 Closing database pool...")
        await close_db_pool()


if __name__ == "__main__":
    asyncio.run(main())
