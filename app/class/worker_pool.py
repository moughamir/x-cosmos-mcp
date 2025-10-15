import asyncio
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from app.class.worker_task import WorkerStatus, WorkerTask, WorkerResult

logger = logging.getLogger(__name__)


class Worker:
    def __init__(self, worker_id: str, worker_pool: "WorkerPool"):
        self.worker_id = worker_id
        self.worker_pool = worker_pool
        self.status = WorkerStatus.IDLE
        self.current_task: Optional[WorkerTask] = None
        self.task_count = 0
        self.error_count = 0

    async def process_task(self, task: WorkerTask) -> WorkerResult:
        """Process a single task with retry logic"""
        start_time = time.time()
        self.status = WorkerStatus.BUSY
        self.current_task = task

        max_retries = task.data.get("_max_retries", 3) if hasattr(task.data, "get") else 3

        try:
            for attempt in range(max_retries + 1):
                try:
                    logger.debug(
                        f"Worker {self.worker_id} processing task {task.task_id} (attempt {attempt + 1})"
                    )

                    # Execute the task based on its type
                    if task.task_type == "product_processing":
                        result = await self._process_product_task(task)
                    elif task.task_type == "model_inference":
                        result = await self._process_model_task(task)
                    elif task.task_type == "batch_processing":
                        result = await self._process_batch_task(task)
                    else:
                        raise ValueError(f"Unknown task type: {task.task_type}")

                    execution_time = time.time() - start_time
                    self.task_count += 1

                    logger.debug(
                        f"Worker {self.worker_id} completed task {task.task_id} in {execution_time:.2f}s"
                    )
                    return WorkerResult(
                        task.task_id, True, result, execution_time=execution_time
                    )

                except Exception as e:
                    execution_time = time.time() - start_time
                    logger.warning(
                        f"Worker {self.worker_id} attempt {attempt + 1} failed for task {task.task_id}: {e}"
                    )

                    if attempt < max_retries:
                        # Wait before retry (exponential backoff)
                        wait_time = min(2**attempt, 30)  # Max 30 seconds
                        logger.info(
                            f"Worker {self.worker_id} retrying task {task.task_id} in {wait_time}s"
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        self.error_count += 1
                        logger.error(
                            f"Worker {self.worker_id} failed task {task.task_id} after {max_retries + 1} attempts: {e}"
                        )
                        return WorkerResult(
                            task.task_id,
                            False,
                            error=str(e),
                            execution_time=execution_time,
                        )

        finally:
            self.status = WorkerStatus.IDLE
            self.current_task = None

    async def _process_product_task(self, task: WorkerTask) -> Any:
        """Process a single product optimization task"""
        from app.pipeline.pipeline import MultiModelSEOManager
        from app.config import TaskType

        manager = MultiModelSEOManager()
        product_data = task.data

        # Determine task type and execute appropriate method
        if product_data.get("task_type") == TaskType.META_OPTIMIZATION.value:
            return await manager.optimize_meta_tags(product_data)
        elif product_data.get("task_type") == TaskType.CONTENT_REWRITING.value:
            return await manager.rewrite_content(product_data)
        elif product_data.get("task_type") == TaskType.KEYWORD_ANALYSIS.value:
            return await manager.analyze_keywords(product_data)
        elif product_data.get("task_type") == TaskType.TAG_OPTIMIZATION.value:
            return await manager.optimize_tags(product_data)
        else:
            raise ValueError(f"Unknown product task type: {product_data.get('task_type')}")

    async def _process_model_task(self, task: WorkerTask) -> Any:
        """Process a model inference task"""
        from app.pipeline.pipeline import MultiModelSEOManager

        manager = MultiModelSEOManager()
        model_name = task.data["model"]
        prompt = task.data["prompt"]
        task_type = task.data.get("task_type")

        return await manager._call_ollama_model(model_name, prompt)

    async def _process_batch_task(self, task: WorkerTask) -> Any:
        """Process a batch of tasks"""
        batch_data = task.data
        results = []

        for item in batch_data:
            # Create individual task for each item in batch
            individual_task = WorkerTask(
                task_id=f"{task.task_id}_{len(results)}",
                task_type=item.get("task_type", task.task_type),
                data=item,
                priority=task.priority,
            )
            result = await self.process_task(individual_task)
            results.append(result)

        return results


class WorkerPool:
    def __init__(self, max_workers: int = 4, queue_size: int = 100):
        self.max_workers = max_workers
        self.queue_size = queue_size
        self.workers: List[Worker] = []
        self.task_queue: asyncio.Queue = asyncio.Queue(maxsize=queue_size)
        self.results: Dict[str, WorkerResult] = {}
        self.task_futures: Dict[str, asyncio.Future] = {}
        self.running = False
        self.worker_stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "avg_execution_time": 0.0,
        }

        # Create workers
        for i in range(max_workers):
            worker = Worker(f"worker_{i+1}", self)
            self.workers.append(worker)

    async def start(self):
        """Start the worker pool"""
        self.running = True
        logger.info(f"Starting worker pool with {self.max_workers} workers")

        # Start worker tasks
        for worker in self.workers:
            asyncio.create_task(self._worker_loop(worker))

        # Start result processor
        asyncio.create_task(self._result_processor())

    async def stop(self):
        """Stop the worker pool"""
        self.running = False
        logger.info("Stopping worker pool")

        # Wait for all tasks to complete
        await self.task_queue.join()

    async def submit_task(
        self, task_type: str, data: Any, priority: int = 0, retry_count: int = 0
    ) -> str:
        """Submit a task to the worker pool with retry support"""
        if not self.running:
            raise RuntimeError("Worker pool is not running")

        task_id = str(uuid.uuid4())
        task = WorkerTask(
            task_id=task_id, task_type=task_type, data=data, priority=priority
        )

        # Create future for tracking
        future = asyncio.Future()
        self.task_futures[task_id] = future

        # Add retry information if this is a retry
        if retry_count > 0:
            task.data["_retry_count"] = retry_count
            task.data["_original_task_id"] = task_id

        await self.task_queue.put((priority, task))

        self.worker_stats["total_tasks"] += 1
        logger.debug(
            f"Submitted task {task_id} with priority {priority} (retry: {retry_count})"
        )

        return task_id

    async def get_result(self, task_id: str, timeout: Optional[float] = None) -> WorkerResult:
        """Get the result of a submitted task"""
        # First check if result is already available
        if task_id in self.results:
            return self.results[task_id]

        # Then check if task is still in futures (not yet processed or cleaned up)
        if task_id not in self.task_futures:
            raise ValueError(f"Task {task_id} not found")

        future = self.task_futures[task_id]

        if timeout:
            result = await asyncio.wait_for(future, timeout=timeout)
        else:
            result = await future

        return result

    def get_worker_status(self) -> Dict[str, Any]:
        """Get current status of all workers"""
        return {
            "total_workers": len(self.workers),
            "active_workers": len([w for w in self.workers if w.status == WorkerStatus.BUSY]),
            "idle_workers": len([w for w in self.workers if w.status == WorkerStatus.IDLE]),
            "error_workers": len([w for w in self.workers if w.status == WorkerStatus.ERROR]),
            "queue_size": self.task_queue.qsize(),
            "stats": self.worker_stats.copy(),
        }

    async def _worker_loop(self, worker: Worker):
        """Main loop for a worker"""
        while self.running:
            try:
                # Get task from queue with priority
                priority, task = await self.task_queue.get()

                logger.debug(f"Worker {worker.worker_id} got task {task.task_id}")

                # Process the task
                result = await worker.process_task(task)

                # Store result
                self.results[task.task_id] = result

                # Update statistics
                if result.success:
                    self.worker_stats["completed_tasks"] += 1
                else:
                    self.worker_stats["failed_tasks"] += 1

                # Update average execution time
                total_time = self.worker_stats["avg_execution_time"] * (
                    self.worker_stats["completed_tasks"]
                    + self.worker_stats["failed_tasks"]
                    - 1
                )
                total_time += result.execution_time
                count = (
                    self.worker_stats["completed_tasks"]
                    + self.worker_stats["failed_tasks"]
                )
                self.worker_stats["avg_execution_time"] = (
                    total_time / count if count > 0 else 0
                )

                # Set future result
                if task.task_id in self.task_futures:
                    if result.success:
                        self.task_futures[task.task_id].set_result(result)
                    else:
                        self.task_futures[task.task_id].set_exception(Exception(result.error))

                    # Remove from futures since it's now complete
                    del self.task_futures[task.task_id]

                # Mark task as done
                self.task_queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker.worker_id} error: {e}")
                worker.status = WorkerStatus.ERROR

    async def _result_processor(self):
        """Process completed results and cleanup"""
        while self.running:
            try:
                await asyncio.sleep(10)  # Cleanup every 10 seconds

                # Cleanup old results (older than 1 hour)
                current_time = time.time()
                expired_tasks = [
                    task_id
                    for task_id, result in self.results.items()
                    if current_time - result.execution_time > 3600
                ]

                for task_id in expired_tasks:
                    logger.debug(f"Cleaning up expired task {task_id}")
                    del self.results[task_id]
                    # Note: Completed tasks are already removed from task_futures when set_result is called

                # Health check for workers
                await self._health_check()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Result processor error: {e}")

    async def _health_check(self):
        """Perform health check on workers"""
        current_time = time.time()

        for worker in self.workers:
            if worker.status == WorkerStatus.ERROR:
                logger.warning(f"Worker {worker.worker_id} is in error state, resetting")
                worker.status = WorkerStatus.IDLE
                worker.error_count = 0

            # Check for stuck workers (busy for more than 5 minutes)
            if (
                worker.status == WorkerStatus.BUSY
                and worker.current_task
                and current_time - worker.current_task.created_at > 300
            ):
                logger.warning(f"Worker {worker.worker_id} appears stuck, resetting")
                worker.status = WorkerStatus.IDLE
                worker.current_task = None
