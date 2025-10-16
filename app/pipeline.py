from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List

import jinja2
from bs4 import BeautifulSoup

from .config import settings, TaskType
from .utils.db import (
    complete_pipeline_run,
    create_pipeline_run,
    get_product_details,
    log_change,
    update_pipeline_run,
    update_product_details,
)
from .utils.ollama_client import OllamaClient
from .utils.text_cleaner import shorten
from .worker_pool import get_worker_pool

logger = logging.getLogger(__name__)

prompt_loader = jinja2.FileSystemLoader(searchpath=settings.paths.prompt_dir)
prompt_env = jinja2.Environment(loader=prompt_loader)


class MultiModelSEOManager:
    def __init__(self, websocket_manager=None):
        self.ollama_client = OllamaClient()
        self.model_capabilities = settings.model_capabilities.capabilities
        self.fallback_order = settings.model_capabilities.fallback_order
        self.websocket_manager = websocket_manager

    async def get_best_model_for_task(self, task_type: TaskType) -> str:
        """Select the best available model for a specific task"""
        for model_name, capabilities in self.model_capabilities.items():
            if task_type in capabilities.tasks:
                if await self.ollama_client._check_model_availability(model_name):
                    return model_name

        # Fallback to any available model
        for model_name in self.fallback_order:
            if await self.ollama_client._check_model_availability(model_name):
                return model_name

        raise Exception("No models available")

    async def _perform_task(
        self,
        product_data: Dict[str, Any],
        template_name: str,
        task_type: TaskType,
        prompt_kwargs: Dict[str, Any] | None = None,
        quantize: bool = False,
    ) -> Dict[str, Any]:
        if prompt_kwargs is None:
            prompt_kwargs = {}

        quantize = product_data.get("quantize", False)
        model = await self.get_best_model_for_task(task_type)
        template = prompt_env.get_template(template_name)
        prompt = template.render(
            product_data=product_data, clean_html=self._clean_html, **prompt_kwargs
        )
        return await self._call_model_with_fallback(
            model, prompt, task_type=task_type, quantize=quantize
        )

    async def optimize_meta_tags(
        self, product_data: Dict[str, Any], prompt_kwargs: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        """Optimize meta title and description using specialized model"""
        return await self._perform_task(
            product_data,
            "meta_optimization.j2",
            TaskType.META_OPTIMIZATION,
            prompt_kwargs=prompt_kwargs,
        )

    async def rewrite_content(
        self, product_data: Dict[str, Any], prompt_kwargs: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        return await self._perform_task(
            product_data,
            "rewrite_content.j2",
            TaskType.CONTENT_REWRITING,
            prompt_kwargs=prompt_kwargs,
        )

    async def analyze_keywords(
        self, product_data: Dict[str, Any], prompt_kwargs: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        return await self._perform_task(
            product_data,
            "analyze_keywords.j2",
            TaskType.KEYWORD_ANALYSIS,
            prompt_kwargs=prompt_kwargs,
        )

    async def optimize_tags(
        self, product_data: Dict[str, Any], prompt_kwargs: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        return await self._perform_task(
            product_data,
            "optimize_tags.j2",
            TaskType.TAG_OPTIMIZATION,
            prompt_kwargs=prompt_kwargs,
        )

    async def analyze_schema(
        self, product_data: Dict[str, Any], prompt_kwargs: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        return await self._perform_task(
            product_data,
            "schema_analysis.j2",
            TaskType.SCHEMA_ANALYSIS,
            prompt_kwargs=prompt_kwargs,
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
                capabilities_obj = self.model_capabilities.get(current_model)
                if capabilities_obj:
                    capabilities = capabilities_obj.model_dump()
                else:
                    capabilities = {"max_tokens": 1024}

                result = await self.ollama_client.generate(
                    current_model, prompt, capabilities, quantize=quantize
                )
                if result and self.ollama_client.validate_response(result, task_type):
                    logger.info(
                        f"✅ Success with {current_model} for {task_type.value}"
                    )
                    return result
                else:
                    logger.warning(
                        f"❌ Model {current_model} failed validation for {task_type.value} on attempt {attempt + 1}/{max_retries}"
                    )
            except Exception as e:
                logger.warning(
                    f"❌ Error with model {current_model} for {task_type.value} on attempt {attempt + 1}/{max_retries}: {e}"
                )
            # If current model failed, try next in fallback order (handled by get_best_model_for_task)
            # For now, we just continue to the next attempt with the same model or raise if all attempts fail.
            # The model selection logic is in get_best_model_for_task, so here we just retry with the current model.

        # If all model attempts fail, use rule-based fallback
        logger.warning(
            f"All model attempts failed for {task_type.value}. Using rule-based fallback."
        )
        return self._rule_based_fallback(task_type, prompt)

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
        elif task_type == TaskType.SCHEMA_ANALYSIS:
            return {
                "schema_compliance": True,
                "issues": [],
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
        return shorten(
            text, max_tokens
        )  # Use shorten instead of truncate_text_to_tokens

    async def _broadcast_pipeline_update(
        self,
        pipeline_run_id: int,
        processed_count: int,
        failed_count: int,
        total_products: int,
    ):
        """Broadcast pipeline progress update via WebSocket"""
        if self.websocket_manager:
            try:
                from .utils.db import get_pipeline_runs

                runs = await get_pipeline_runs(limit=10)
                runs_dict = [dict(run) for run in runs]

                await self.websocket_manager.broadcast(
                    {
                        "type": "pipeline_progress_update",
                        "pipeline_runs": runs_dict,
                        "current_run": {
                            "id": pipeline_run_id,
                            "processed": processed_count,
                            "failed": failed_count,
                            "total": total_products,
                            "percentage": (
                                (processed_count / total_products * 100)
                                if total_products > 0
                                else 0
                            ),
                        },
                    },
                    "pipeline_progress",
                )
            except Exception as e:
                logger.warning(f"Failed to broadcast pipeline update: {e}")

    async def normalize_categories(
        self, product_data: Dict[str, Any], prompt_kwargs: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        return await self._perform_task(
            product_data,
            "normalize_product.j2",
            TaskType.CATEGORY_NORMALIZATION,
            prompt_kwargs=prompt_kwargs,
        )

    async def batch_process_products(
        self, product_ids: List[int], task_type: TaskType, quantize: bool = False
    ):
        """Process multiple products with the appropriate model using worker pool"""
        processed_count = 0
        failed_count = 0
        pipeline_run_id = None

        try:
            pipeline_run_id = await create_pipeline_run(
                task_type.value, len(product_ids)
            )

            results = []

            # Get worker pool
            worker_pool = get_worker_pool()

            # Submit all tasks to worker pool
            task_futures = []

            for product_id in product_ids:
                product_details = await get_product_details(product_id)
                product = product_details["product"]

                if product:
                    product_id = product["id"]
                    title = product["title"]
                    body_html = product["body_html"]
                    product_type = product["category"]
                    tags = product["tags"]
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
                        priority=1,  # Higher priority for product processing
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
                        original_product_details = await get_product_details(product_id)
                        original_product = original_product_details["product"]

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
                            await update_product_details(product_id, **update_data)

                        await log_change(
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
                        pipeline_run_id,
                        processed_products=processed_count,
                        failed_products=failed_count,
                    )

            return results

        finally:
            if pipeline_run_id:
                status = "COMPLETED" if failed_count == 0 else "FAILED"
                await complete_pipeline_run(
                    pipeline_run_id, status, processed_count, failed_count
                )
