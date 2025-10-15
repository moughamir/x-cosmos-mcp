import json
import logging
import re
from typing import Any, Dict, List

import aiosqlite
import httpx
import jinja2
from bs4 import BeautifulSoup
from .utils.db import (
    complete_pipeline_run,
    create_pipeline_run,
    log_change,
    update_pipeline_run,
    update_product_details,
)
from .config import TaskType, settings
from .utils.tokenizer import truncate_text_to_tokens

# Import worker pool initialization functions
from .worker_pool import (
    get_worker_pool,
    initialize_worker_pool,
    shutdown_worker_pool,
)

# WebSocket manager for real-time updates (imported dynamically to avoid circular imports)
websocket_manager = None


def set_websocket_manager(manager_instance):
    """Set the WebSocket manager for broadcasting updates"""
    global websocket_manager
    websocket_manager = manager_instance


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)



prompt_loader = jinja2.FileSystemLoader(searchpath=settings.paths.prompt_dir)
prompt_env = jinja2.Environment(loader=prompt_loader)


class MultiModelSEOManager:
    def __init__(self):
        self.db_path = settings.paths.database
        self.ollama_url = (
            settings.ollama.base_url
        )  # Use proper base_url instead of manual construction
        self.model_capabilities = settings.model_capabilities.capabilities
        self.fallback_order = settings.model_capabilities.fallback_order

    async def get_best_model_for_task(self, task_type: TaskType) -> str:
        """Select the best available model for a specific task"""
        for model_name, capabilities in self.model_capabilities.items():
            if task_type in capabilities.tasks:
                if await self._check_model_availability(model_name):
                    return model_name

        # Fallback to any available model
        for model_name in self.fallback_order:
            if await self._check_model_availability(model_name):
                return model_name

        raise Exception("No models available")

    async def _check_model_availability(self, model_name: str) -> bool:
        """Check if a model is available in Ollama"""
        try:
            async with httpx.AsyncClient() as client:
                # First check if model exists in the tags list
                response = await client.get(f"{self.ollama_url}/api/tags", timeout=5)
                if response.status_code == 200:
                    tags_data = response.json()
                    available_models = [
                        model["name"] for model in tags_data.get("models", [])
                    ]
                    if model_name in available_models:
                        return True

                # Fallback to generation test with shorter timeout
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={"model": model_name, "prompt": "test", "stream": False},
                    timeout=500,
                )
                return response.status_code == 200
        except Exception as e:
            logging.error(f"Error checking model availability: {e}")
            return False

    async def optimize_meta_tags(
        self, product_data: Dict[str, Any], quantize: bool = False
    ) -> Dict[str, Any]:
        """Optimize meta title and description using specialized model"""
        model = await self.get_best_model_for_task(TaskType.META_OPTIMIZATION)
        template = prompt_env.get_template("meta_optimization.j2")
        prompt = template.render(product_data=product_data, clean_html=self._clean_html)
        return await self._call_model_with_fallback(
            model, prompt, task_type=TaskType.META_OPTIMIZATION, quantize=quantize
        )

    async def rewrite_content(
        self, product_data: Dict[str, Any], quantize: bool = False
    ) -> Dict[str, Any]:
        """Rewrite product content for better SEO"""
        model = await self.get_best_model_for_task(TaskType.CONTENT_REWRITING)
        template = prompt_env.get_template("rewrite_content.j2")
        prompt = template.render(product_data=product_data, clean_html=self._clean_html)
        return await self._call_model_with_fallback(
            model, prompt, task_type=TaskType.CONTENT_REWRITING, quantize=quantize
        )

    async def analyze_keywords(
        self, product_data: Dict[str, Any], quantize: bool = False
    ) -> Dict[str, Any]:
        """Perform comprehensive keyword analysis"""
        model = await self.get_best_model_for_task(TaskType.KEYWORD_ANALYSIS)
        template = prompt_env.get_template("analyze_keywords.j2")
        prompt = template.render(product_data=product_data, clean_html=self._clean_html)
        return await self._call_model_with_fallback(
            model, prompt, task_type=TaskType.KEYWORD_ANALYSIS, quantize=quantize
        )

    async def optimize_tags(
        self, product_data: Dict[str, Any], quantize: bool = False
    ) -> Dict[str, Any]:
        """Analyze and optimize product tags using AI"""
        model = await self.get_best_model_for_task(TaskType.TAG_OPTIMIZATION)
        template = prompt_env.get_template("optimize_tags.j2")
        prompt = template.render(
            title=product_data.get("title", ""),
            category=product_data.get("product_type", ""),
            current_tags=product_data.get("tags", ""),
            description=self._clean_html(product_data.get("body_html", ""), model, 800),
        )
        return await self._call_model_with_fallback(
            model, prompt, task_type=TaskType.TAG_OPTIMIZATION, quantize=quantize
        )

    async def _call_model_with_fallback(
        self,
        model: str,
        prompt: str,
        task_type: TaskType,
        max_retries: int = 3,
        quantize: bool = False,
    ) -> Dict[str, Any]:
        """Call model with fallback to other models if needed"""
        for attempt in range(max_retries):
            current_model = model
            try:
                result = await self._call_ollama_model(
                    current_model, prompt, quantize=quantize
                )
                if result and self._validate_response(result, task_type):
                    logger.info(
                        f"✅ Success with {current_model} for {task_type.value}"
                    )
                    return result

            except Exception as e:
                logger.warning(
                    f"Attempt {attempt + 1} failed with {current_model}: {e}"
                )

            # Try next model in fallback order
            next_models = [m for m in self.fallback_order if m != current_model]
            if next_models:
                model = next_models[0]
            else:
                break

        # Final fallback to rule-based generation
        return self._rule_based_fallback(task_type, prompt)

    async def _call_ollama_model(
        self, model: str, prompt: str, quantize: bool = False
    ) -> Dict[str, Any]:
        """Make actual call to Ollama model"""
        if quantize:
            model = settings.models.quantized_models.get(model, model)

        capabilities_obj = self.model_capabilities.get(model)
        if capabilities_obj:
            capabilities = capabilities_obj.model_dump()
        else:
            capabilities = {"max_tokens": 1024}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "top_p": 0.9,
                        "num_predict": capabilities.get("max_tokens", 1024),
                    },
                },
                timeout=500,
            )

        if response.status_code == 200:
            result = response.json()
            return self._parse_model_response(result["response"])
        else:
            raise Exception(f"Model API error: {response.status_code}")

    def _parse_model_response(self, response: str) -> Dict[str, Any]:
        """Parse model response with robust error handling"""
        try:
            # Try to extract JSON from response
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError as e:
            logging.error(f"JSON decoding error in model response: {e}")
            pass

        # Fallback: return raw response
        return {"raw_response": response, "error": "JSON parsing failed"}

    def _validate_response(self, response: Dict[str, Any], task_type: TaskType) -> bool:
        """Validate that response contains required fields"""
        required_fields = {
            TaskType.META_OPTIMIZATION: [
                "meta_title",
                "meta_description",
                "seo_keywords",
            ],
            TaskType.CONTENT_REWRITING: ["optimized_title", "optimized_description"],
            TaskType.KEYWORD_ANALYSIS: ["primary_keywords", "long_tail_keywords"],
            TaskType.TAG_OPTIMIZATION: ["optimized_tags", "removed_tags", "added_tags"],
        }

        required = required_fields.get(task_type, [])
        return all(field in response for field in required)

    def _rule_based_fallback(self, task_type: TaskType, prompt: str) -> Dict[str, Any]:
        """Provide rule-based fallback when models fail"""
        if task_type == TaskType.META_OPTIMIZATION:
            return {
                "meta_title": "Optimized Product",
                "meta_description": "Quality product with excellent features and competitive pricing.",
                "seo_keywords": "product, quality, features, buy",
                "fallback_used": True,
            }
        elif task_type == TaskType.CONTENT_REWRITING:
            return {
                "optimized_title": "Enhanced Product Version",
                "optimized_description": "<p>Improved product description with better features.</p>",
                "content_score": 0.5,
                "improvements": ["Basic content optimization applied"],
                "fallback_used": True,
            }
        elif task_type == TaskType.KEYWORD_ANALYSIS:
            return {
                "primary_keywords": ["product", "features"],
                "long_tail_keywords": ["quality product features"],
                "competitor_terms": ["similar products"],
                "difficulty_estimate": "medium",
                "fallback_used": True,
            }
        elif task_type == TaskType.TAG_OPTIMIZATION:
            return {
                "optimized_tags": "product, quality, features",
                "removed_tags": ["old_irrelevant_tag"],
                "added_tags": ["new_relevant_tag"],
                "tag_analysis": "Basic tag optimization applied",
                "fallback_used": True,
            }
        else:
            return {
                "error": "No fallback defined for this task type",
                "fallback_used": True,
            }

    def _clean_html(self, html_content: str, model: str, max_tokens: int) -> str:
        """Clean HTML tags from content and truncate to a specific number of tokens."""
        if not html_content:
            return ""
        soup = BeautifulSoup(html_content, "html.parser")
        text = soup.get_text().strip()
        return truncate_text_to_tokens(text, model, max_tokens)

    async def _broadcast_pipeline_update(
        self,
        pipeline_run_id: int,
        processed_count: int,
        failed_count: int,
        total_products: int,
    ):
        """Broadcast pipeline progress update via WebSocket"""
        if websocket_manager:
            try:
                from utils.db import get_pipeline_runs

                runs = await get_pipeline_runs(self.db_path, limit=10)
                runs_dict = [dict(run) for run in runs]

                await websocket_manager.broadcast(
                    {
                        "type": "pipeline_progress_update",
                        "pipeline_runs": runs_dict,
                        "current_run": {
                            "id": pipeline_run_id,
                            "processed": processed_count,
                            "failed": failed_count,
                            "total": total_products,
                            "percentage": (processed_count / total_products * 100)
                            if total_products > 0
                            else 0,
                        },
                    },
                    "pipeline_progress",
                )
            except Exception as e:
                logger.warning(f"Failed to broadcast pipeline update: {e}")

    async def batch_process_products(
        self, product_ids: List[int], task_type: TaskType, quantize: bool = False
    ):
        """Process multiple products with the appropriate model using worker pool"""
        processed_count = 0
        failed_count = 0
        pipeline_run_id = None

        try:
            pipeline_run_id = await create_pipeline_run(
                self.db_path, task_type.value, len(product_ids)
            )

            results = []

            if task_type == TaskType.CATEGORY_NORMALIZATION:
                await self._normalize_categories_for_products(product_ids=product_ids)
                processed_count = len(product_ids)
                for product_id in product_ids:
                    results.append(
                        {"product_id": product_id, "status": "Category normalized"}
                    )
                return results

            # Get worker pool
            worker_pool = get_worker_pool()

            # Submit all tasks to worker pool
            task_futures = []

            for product_id in product_ids:
                async with aiosqlite.connect(self.db_path) as conn:
                    conn.row_factory = aiosqlite.Row
                    cursor = await conn.cursor()
                    await cursor.execute(
                        "SELECT id, title, body_html, product_type, tags FROM products WHERE id = ?",
                        (product_id,),
                    )
                    product = await cursor.fetchone()

                if product:
                    product_id, title, body_html, product_type, tags = product
                    product_data = {
                        "id": product_id,
                        "title": title,
                        "body_html": body_html,
                        "product_type": product_type,
                        "tags": tags,
                        "task_type": task_type.value,
                        "quantize": quantize,
                    }

                    # Submit task to worker pool
                    task_id = await worker_pool.submit_task(
                        task_type=task_type.value,
                        data=product_data,
                        priority=1  # Higher priority for product processing
                    )
                    task_futures.append((task_id, product_id))

            # Collect results from worker pool
            for task_id, product_id in task_futures:
                try:
                    result = await worker_pool.get_result(
                        task_id, timeout=settings.workers.timeout
                    )

                    if result.success:
                        processed_count += 1
                        results.append(
                            {
                                "product_id": product_id,
                                "status": "success",
                                "data": result.result,
                                "model_used": result.result.get(
                                    "model_used", "unknown"
                                ),
                            }
                        )

                        # Get original product data for logging
                        async with aiosqlite.connect(self.db_path) as conn:
                            conn.row_factory = aiosqlite.Row
                            cursor = await conn.cursor()
                            await cursor.execute(
                                "SELECT title, body_html, tags FROM products WHERE id = ?",
                                (product_id,),
                            )
                            original_product = await cursor.fetchone()

                        # Update product in DB and log change
                        update_data = {}
                        if "meta_title" in result.result:
                            update_data["title"] = result.result["meta_title"]
                        if "optimized_title" in result.result:
                            update_data["title"] = result.result["optimized_title"]
                        if "optimized_description" in result.result:
                            update_data["body_html"] = result.result[
                                "optimized_description"
                            ]
                        if "optimized_tags" in result.result:
                            update_data["tags"] = result.result["optimized_tags"]

                        if update_data:
                            await update_product_details(
                                self.db_path, product_id, **update_data
                            )

                        await log_change(
                            self.db_path,
                            product_id,
                            field=task_type.value,
                            old=dict(original_product),
                            new=result.result,
                            source=result.result.get("model_used", "worker_pool"),
                        )

                        logger.info(f"Processed product {product_id} via worker pool")

                    else:
                        failed_count += 1
                        results.append(
                            {
                                "product_id": product_id,
                                "status": "error",
                                "error": result.error,
                            }
                        )
                        logger.error(
                            f"Failed to process product {product_id}: {result.error}"
                        )

                except asyncio.TimeoutError:
                    failed_count += 1
                    results.append(
                        {
                            "product_id": product_id,
                            "status": "timeout",
                            "error": "Task timed out",
                        }
                    )
                    logger.error(f"Task {task_id} for product {product_id} timed out")

                except Exception as e:
                    failed_count += 1
                    results.append(
                        {"product_id": product_id, "status": "error", "error": str(e)}
                    )
                    logger.error(f"Error processing product {product_id}: {e}")

                # Broadcast progress update every 5 products or at the end
                if (processed_count + failed_count) % 5 == 0 or (
                    processed_count + failed_count
                ) == len(product_ids):
                    await self._broadcast_pipeline_update(
                        pipeline_run_id, processed_count, failed_count, len(product_ids)
                    )

                if pipeline_run_id:
                    await update_pipeline_run(
                        self.db_path,
                        pipeline_run_id,
                        processed_products=processed_count,
                        failed_products=failed_count,
                    )

            return results

        finally:
            if pipeline_run_id:
                status = "COMPLETED" if failed_count == 0 else "FAILED"
                await complete_pipeline_run(
                    self.db_path, pipeline_run_id, status, processed_count, failed_count
                )


# Usage example and CLI interface
async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Multi-Model SEO Optimizer")
    parser.add_argument(
        "--task", choices=["meta", "content", "keywords", "tags"], required=True
    )
    parser.add_argument(
        "--product-ids", type=int, nargs="+", help="Specific product IDs to process"
    )

    args = parser.parse_args()

    manager = MultiModelSEOManager()

    task_mapping = {
        "meta": TaskType.META_OPTIMIZATION,
        "content": TaskType.CONTENT_REWRITING,
        "keywords": TaskType.KEYWORD_ANALYSIS,
        "tags": TaskType.TAG_OPTIMIZATION,
    }
    task_type = task_mapping[args.task]

    product_ids = args.product_ids
    if not product_ids:
        async with aiosqlite.connect(manager.db_path) as conn:
            cursor = await conn.cursor()
            await cursor.execute("SELECT id FROM products LIMIT 10")
            product_ids = [row[0] for row in await cursor.fetchall()]

    print(f"🚀 Starting {task_type.value} for {len(product_ids)} products...")

    # Define task handlers
    task_handlers = {
        TaskType.META_OPTIMIZATION.value: manager.optimize_meta_tags,
        TaskType.CONTENT_REWRITING.value: manager.rewrite_content,
        TaskType.KEYWORD_ANALYSIS.value: manager.analyze_keywords,
        TaskType.TAG_OPTIMIZATION.value: manager.optimize_tags,
    }

    try:
        print("🔧 Initializing worker pool...")
        await initialize_worker_pool(
            max_workers=settings.workers.max_workers, task_handlers=task_handlers
        )

        results = await manager.batch_process_products(product_ids, task_type)

        print(
            f"✅ Processed {len([r for r in results if 'error' not in r])} products successfully"
        )
        print(f"❌ Failed {len([r for r in results if 'error' in r])} products")

        for result in results:
            if "error" not in result:
                print(
                    f"Product {result['product_id']}: {result.get('meta_title', result.get('optimized_title', result.get('optimized_tags', 'Unknown')))}"
                )

    finally:
        print("🛑 Shutting down worker pool...")
        await shutdown_worker_pool()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
