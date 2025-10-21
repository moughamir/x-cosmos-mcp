"""
Example: Integrating UnifiedPipeline into FastAPI Application
"""

import asyncio
from fastapi import BackgroundTasks, APIRouter
from unified_pipeline import UnifiedPipeline, PipelineConfig, TaskType

router = APIRouter()


# Example 1: Simple batch processing
@router.post("/api/v2/pipeline/batch")
async def run_batch_pipeline(
    product_ids: list[int],
    batch_size: int = 10,
    background_tasks: BackgroundTasks = None,
):
    """Process products in batches with new unified pipeline"""

    config = PipelineConfig(
        db_pool=True,  # Will use existing pool from app.utils.db
        batch_size=batch_size,
        input_source="database",
        ollama_url="http://localhost:11434",
    )

    pipeline = UnifiedPipeline(config)

    # Run in background
    if background_tasks:
        background_tasks.add_task(pipeline.run_pipeline, product_ids)
        return {"message": "Pipeline started", "product_count": len(product_ids)}
    else:
        # Run synchronously (for small batches)
        stats = await pipeline.run_pipeline(product_ids)
        return {"message": "Pipeline complete", "stats": stats}


# Example 2: File-based processing (local development)
@router.post("/api/v2/pipeline/local")
async def run_local_pipeline(input_path: str):
    """Process local JSON files without database"""
    from pathlib import Path

    config = PipelineConfig(
        input_source="files",
        input_path=Path(input_path),
        output_dir=Path("normalized_output"),
        batch_size=10,
    )

    pipeline = UnifiedPipeline(config)
    stats = await pipeline.run_pipeline()

    return {"message": "Local processing complete", "stats": stats}


# Example 3: Custom task processing
async def process_custom_workflow(product_ids: list[int]):
    """Custom workflow with specific tasks"""

    config = PipelineConfig(db_pool=True, batch_size=5, input_source="database")

    pipeline = UnifiedPipeline(config)

    # Fetch products
    from app.utils.db import get_product_details

    products = [await get_product_details(pid) for pid in product_ids]

    # Process only SEO (skip tags)
    seo_results = await pipeline.process_batch(products, TaskType.SEO_OPTIMIZATION)

    # Save results
    from app.utils.db import update_product_details

    for i, product in enumerate(products):
        if i < len(seo_results):
            await update_product_details(
                product["product"]["id"],
                title=seo_results[i].get("optimized_title"),
                body_html=seo_results[i].get("optimized_description"),
            )

    return {"processed": len(seo_results)}


# Example 4: CLI wrapper (replaces cli.py)
async def cli_main():
    """
    Replacement for cli.py using unified pipeline
    Usage: python -m examples.unified_pipeline_integration
    """
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--product-ids", type=int, nargs="+", required=True)
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--source", choices=["database", "files"], default="database")
    args = parser.parse_args()

    # Initialize database if needed
    if args.source == "database":
        from app.utils.db import init_db_pool, close_db_pool

        await init_db_pool()

    config = PipelineConfig(
        db_pool=args.source == "database",
        batch_size=args.batch_size,
        input_source=args.source,
    )

    pipeline = UnifiedPipeline(config)
    stats = await pipeline.run_pipeline(args.product_ids)

    print("\n✅ Pipeline Complete:")
    print(f"   Processed: {stats['processed']}")
    print(f"   Failed: {stats['failed']}")
    print(f"   LLM Calls: {stats['llm_calls']}")
    print(f"   Fallbacks: {stats['fallback']}")

    if args.source == "database":
        await close_db_pool()


if __name__ == "__main__":
    asyncio.run(cli_main())
