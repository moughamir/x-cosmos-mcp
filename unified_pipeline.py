#!/usr/bin/env python3
"""
Unified Pipeline Framework
Consolidates: master_pipeline.py + app/pipeline.py + cli.py
Features: AsyncIO, batch processing, retry logic, local files support
"""

import asyncio
import httpx
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

# Conditional imports for database mode
import importlib.util

ASYNCPG_AVAILABLE = importlib.util.find_spec("asyncpg") is not None

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ========== CONFIGURATION ==========
@dataclass
class PipelineConfig:
    """Single source of configuration"""

    db_pool: Optional[Any] = None  # asyncpg.Pool when database mode
    ollama_url: str = "http://localhost:11434"
    model: str = "qwen2:0.5b"
    timeout: int = 30
    max_workers: int = 4
    batch_size: int = 10
    input_source: str = "database"  # "database" or "files"
    input_path: Optional[Path] = None
    output_dir: Optional[Path] = None
    file_limit: Optional[int] = None  # Limit number of files to process (for testing)
    tag_mappings: Dict[str, str] = field(default_factory=dict)
    type_mappings: Dict[str, Any] = field(default_factory=dict)
    taxonomy_roots: List[str] = field(default_factory=list)


class TaskType(Enum):
    CATEGORY_NORM = "category_normalization"
    SEO_OPTIMIZATION = "seo_optimization"
    TAG_OPTIMIZATION = "tag_optimization"
    SCHEMA_VALIDATION = "schema_validation"


# ========== OLLAMA CLIENT WITH CIRCUIT BREAKER ==========
class OllamaClient:
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
        self.circuit_open = False
        self.failure_count = 0
        self.MAX_FAILURES = 5

    async def generate(
        self, prompt: str, model: str, max_retries: int = 3
    ) -> Optional[str]:
        if self.circuit_open:
            logger.warning("Circuit breaker OPEN - using fallback")
            return None

        for attempt in range(max_retries):
            try:
                response = await self.client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.0, "num_predict": 512},
                    },
                )
                response.raise_for_status()
                self.failure_count = 0
                return response.json().get("response")
            except Exception as e:
                wait = min(2**attempt, 30)
                logger.warning(
                    f"LLM attempt {attempt + 1} failed: {e}, retry in {wait}s"
                )
                await asyncio.sleep(wait)

        self.failure_count += 1
        if self.failure_count >= self.MAX_FAILURES:
            self.circuit_open = True
            logger.error("Circuit breaker OPENED")
        return None

    async def batch_generate(
        self, prompts: List[str], model: str
    ) -> List[Optional[str]]:
        """Parallel batch generation"""
        tasks = [self.generate(p, model) for p in prompts]
        return await asyncio.gather(*tasks)


# ========== UNIFIED PIPELINE ==========
class UnifiedPipeline:
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.ollama = OllamaClient(config.ollama_url, config.timeout)
        self.stats = {"processed": 0, "failed": 0, "llm_calls": 0, "fallback": 0}

    async def process_batch(self, products: List[Dict], task: TaskType) -> List[Dict]:
        """Process batch with single LLM call"""
        if task == TaskType.SEO_OPTIMIZATION:
            prompt = self._build_batch_seo_prompt(products)
            response = await self.ollama.generate(prompt, self.config.model)
            self.stats["llm_calls"] += 1

            if response:
                return self._parse_seo_batch(response, products)
            else:
                self.stats["fallback"] += len(products)
                return [self._fallback_seo(p) for p in products]

        elif task == TaskType.TAG_OPTIMIZATION:
            results = []
            for p in products:
                prompt = self._build_tag_prompt(p)
                response = await self.ollama.generate(prompt, self.config.model)
                self.stats["llm_calls"] += 1
                results.append(
                    self._parse_tag_response(response, p)
                    if response
                    else self._fallback_tags(p)
                )
            return results

        return products

    def _build_batch_seo_prompt(self, products: List[Dict]) -> str:
        product_list = [
            {
                "id": p.get("id"),
                "title": p.get("title"),
                "description": (p.get("body_html") or "")[:500],
            }
            for p in products
        ]
        return f"""Optimize SEO for products. Return JSON array:
{json.dumps(product_list)}
Return: [{{"id": "...", "optimized_title": "...", "optimized_description": "..."}}, ...]"""

    def _build_tag_prompt(self, product: Dict) -> str:
        return f"""Optimize tags for: {{"title": "{product.get("title")}", "tags": {product.get("tags", [])}}}
Return: {{"optimized_tags": ["tag1", "tag2"]}}"""

    def _parse_seo_batch(self, response: str, products: List[Dict]) -> List[Dict]:
        try:
            results = json.loads(response.strip())
            if isinstance(results, list):
                return results
        except Exception:
            pass
        return [self._fallback_seo(p) for p in products]

    def _parse_tag_response(self, response: str, product: Dict) -> Dict:
        try:
            result = json.loads(response.strip())
            if "optimized_tags" in result:
                return result
        except Exception:
            pass
        return self._fallback_tags(product)

    def _fallback_seo(self, product: Dict) -> Dict:
        title = (product.get("title") or "")[:80]
        desc = (product.get("body_html") or "")[:160]
        return {
            "id": product.get("id"),
            "optimized_title": title,
            "optimized_description": desc,
        }

    def _fallback_tags(self, product: Dict) -> Dict:
        tags = product.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]
        return {"optimized_tags": tags[:10]}

    async def run_pipeline(self, product_ids: Optional[List[int]] = None) -> Dict:
        """Execute complete pipeline"""
        logger.info("🚀 Starting unified pipeline...")
        products = await self._fetch_products(product_ids)
        logger.info(f"📦 Loaded {len(products)} products")

        if not products:
            logger.warning("⚠️  No products found to process")
            return self.stats

        batches = [
            products[i : i + self.config.batch_size]
            for i in range(0, len(products), self.config.batch_size)
        ]
        logger.info(
            f"📊 Processing {len(batches)} batches (batch_size={self.config.batch_size})"
        )

        for batch_num, batch in enumerate(batches, 1):
            logger.info(
                f"⚙️  Processing batch {batch_num}/{len(batches)} ({len(batch)} products)"
            )

            # Parallel task execution
            seo_task = self.process_batch(batch, TaskType.SEO_OPTIMIZATION)
            tag_task = self.process_batch(batch, TaskType.TAG_OPTIMIZATION)

            seo_results, tag_results = await asyncio.gather(seo_task, tag_task)

            # Merge results
            for i, product in enumerate(batch):
                if i < len(seo_results):
                    product.update(seo_results[i])
                if i < len(tag_results):
                    product.update(tag_results[i])

            # Save batch
            await self._save_batch(batch)
            self.stats["processed"] += len(batch)
            logger.info(f"✅ Batch {batch_num}/{len(batches)} complete")

        return self.stats

    async def _fetch_products(self, product_ids: Optional[List[int]]) -> List[Dict]:
        """Fetch from database or files"""
        if self.config.input_source == "database" and self.config.db_pool:
            if not ASYNCPG_AVAILABLE:
                logger.error("Database mode requires asyncpg")
                return []
            try:
                from app.utils.db import get_all_products, get_product_details

                if product_ids:
                    return [await get_product_details(pid) for pid in product_ids]
                return await get_all_products()
            except Exception as e:
                logger.error(f"Database fetch failed: {e}")
                return []
        elif self.config.input_source == "files" and self.config.input_path:
            return await self._load_from_files()
        return []

    async def _load_from_files(self) -> List[Dict]:
        """Load from local JSON files"""
        import gzip

        products = []
        if self.config.input_path is None:
            logger.error("Input path is not set for file input source.")
            return []
        files = list(self.config.input_path.glob("*.json.gz"))

        # Apply limit if specified
        limit = getattr(self.config, "file_limit", None)
        if limit and limit > 0:
            files = files[:limit]
            logger.info(
                f"📂 Processing first {len(files)} of many JSON files (limited)"
            )
        else:
            logger.info(f"📂 Found {len(files)} JSON files to process")

        for i, file in enumerate(files, 1):
            try:
                with gzip.open(file, "rt") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        products.extend(data)
                    elif isinstance(data, dict):
                        products.append(data)
                if i % 100 == 0 or (
                    limit and i % 10 == 0
                ):  # Log every 100 files, or every 10 if limited
                    logger.info(
                        f"  Loaded {i}/{len(files)} files ({len(products)} products so far)..."
                    )
            except Exception as e:
                logger.error(f"Failed to load {file}: {e}")

        logger.info(f"✅ Loaded {len(products)} products from {len(files)} files")
        return products

    async def _save_batch(self, products: List[Dict]):
        """Save to database or files"""
        if self.config.input_source == "database" and self.config.db_pool:
            if not ASYNCPG_AVAILABLE:
                logger.error("Database mode requires asyncpg")
                return
            try:
                from app.utils.db import update_product_details

                for p in products:
                    await update_product_details(p.get("id"), **p)
            except Exception as e:
                logger.error(f"Database save failed: {e}")
        elif self.config.output_dir:
            self.config.output_dir.mkdir(parents=True, exist_ok=True)
            for p in products:
                file_path = self.config.output_dir / f"product_{p.get('id')}.json"
                with open(file_path, "w") as f:
                    json.dump(p, f, indent=2)


# ========== CLI INTERFACE ==========
async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Unified Pipeline")
    parser.add_argument("--source", choices=["database", "files"], default="database")
    parser.add_argument("--input-path", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("normalized_output"))
    parser.add_argument("--product-ids", type=int, nargs="+")
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument(
        "--limit", type=int, help="Limit number of files to process (for testing)"
    )
    parser.add_argument("--ollama-url", default="http://localhost:11434")
    args = parser.parse_args()

    print("=" * 60)
    print("UNIFIED PIPELINE FRAMEWORK")
    print("=" * 60)
    print(f"Source: {args.source}")
    print(f"Batch Size: {args.batch_size}")
    print(f"Ollama URL: {args.ollama_url}")
    if args.input_path:
        print(f"Input Path: {args.input_path}")
    if args.output_dir:
        print(f"Output Dir: {args.output_dir}")
    print("=" * 60)
    print()

    config = PipelineConfig(
        input_source=args.source,
        input_path=args.input_path,
        output_dir=args.output_dir,
        batch_size=args.batch_size,
        max_workers=args.workers,
        file_limit=args.limit,
        ollama_url=args.ollama_url,
    )

    if args.source == "database":
        if not ASYNCPG_AVAILABLE:
            print("❌ Error: asyncpg not installed. Install with: pip install asyncpg")
            print("💡 Tip: Use --source files for local development without database")
            return
        try:
            from app.utils.db import init_db_pool, close_db_pool

            await init_db_pool()
            config.db_pool = True
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            print("💡 Tip: Use --source files for local development without database")
            return

    pipeline = UnifiedPipeline(config)
    stats = await pipeline.run_pipeline(args.product_ids)

    print(f"\n✅ Pipeline Complete: {stats}")

    if args.source == "database":
        await close_db_pool()


if __name__ == "__main__":
    asyncio.run(main())
