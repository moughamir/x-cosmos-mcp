#!/usr/bin/env python3
"""
Standalone test for unified pipeline without database
Creates mock products and tests the pipeline logic
"""

import asyncio
from unified_pipeline import UnifiedPipeline, PipelineConfig, TaskType


async def test_pipeline_standalone():
    """Test pipeline with mock data (no database required)"""

    # Mock products
    mock_products = [
        {
            "id": 1001,
            "title": "Wireless Bluetooth Headphones Premium Quality",
            "body_html": "<p>High-quality wireless headphones with noise cancellation</p>",
            "tags": ["electronics", "audio", "headphones", "wireless", "bluetooth"],
        },
        {
            "id": 1002,
            "title": "Organic Cotton T-Shirt Men's Casual Wear",
            "body_html": "<p>Comfortable 100% organic cotton t-shirt</p>",
            "tags": ["clothing", "mens", "tshirt", "organic", "cotton", "casual"],
        },
        {
            "id": 1003,
            "title": "Stainless Steel Water Bottle Insulated 32oz",
            "body_html": "<p>Keep drinks cold for 24 hours or hot for 12 hours</p>",
            "tags": [
                "kitchen",
                "drinkware",
                "water bottle",
                "insulated",
                "stainless steel",
            ],
        },
    ]

    print("🧪 Testing Unified Pipeline (Standalone Mode)\n")
    print(f"Processing {len(mock_products)} mock products...\n")

    # Create config without database
    config = PipelineConfig(
        input_source="mock",  # Not files or database
        batch_size=3,
        ollama_url="http://localhost:11434",
        model="qwen2:0.5b",
    )

    pipeline = UnifiedPipeline(config)

    # Test SEO optimization
    print("📝 Testing SEO Optimization...")
    seo_results = await pipeline.process_batch(mock_products, TaskType.SEO_OPTIMIZATION)
    print(f"✅ Processed {len(seo_results)} SEO results\n")

    for i, result in enumerate(seo_results):
        print(f"Product {mock_products[i]['id']}:")
        print(f"  Original: {mock_products[i]['title'][:50]}...")
        print(f"  Optimized: {result.get('optimized_title', 'N/A')[:50]}...")
        print()

    # Test tag optimization
    print("🏷️  Testing Tag Optimization...")
    tag_results = await pipeline.process_batch(mock_products, TaskType.TAG_OPTIMIZATION)
    print(f"✅ Processed {len(tag_results)} tag results\n")

    for i, result in enumerate(tag_results):
        print(f"Product {mock_products[i]['id']}:")
        print(f"  Original tags: {mock_products[i]['tags'][:3]}")
        print(f"  Optimized tags: {result.get('optimized_tags', [])[:3]}")
        print()

    # Print stats
    print("📊 Pipeline Statistics:")
    print(f"  LLM Calls: {pipeline.stats['llm_calls']}")
    print(f"  Fallbacks: {pipeline.stats['fallback']}")
    print(f"  Processed: {pipeline.stats['processed']}")
    print(f"  Failed: {pipeline.stats['failed']}")

    # Test circuit breaker
    if pipeline.ollama.circuit_open:
        print("\n⚠️  Circuit breaker OPEN - using fallback mode")
    else:
        print("\n✅ Circuit breaker CLOSED - normal operation")

    return pipeline.stats


if __name__ == "__main__":
    print("=" * 60)
    print("UNIFIED PIPELINE STANDALONE TEST")
    print("=" * 60)
    print()

    stats = asyncio.run(test_pipeline_standalone())

    print("\n" + "=" * 60)
    print("✅ TEST COMPLETE")
    print("=" * 60)
