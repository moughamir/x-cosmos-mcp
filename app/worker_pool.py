import asyncio
import logging
import time
import uuid
from asyncio import Future
from typing import Any, Awaitable, Callable, Dict, List, Mapping, Optional

from .worker_task import WorkerResult, WorkerStatus, WorkerTask

logger = logging.getLogger(__name__)


class Worker:
    def __init__(
        self,
        worker_id: str,
        worker_pool: "WorkerPool",
        task_handlers: Mapping[str, Callable[[Any], Awaitable[Any]]],
    ):
        self.worker_id = worker_id
        self.worker_pool = worker_pool
        self.status = WorkerStatus.IDLE
        self.current_task: Optional[WorkerTask] = None
        self.task_count = 0
        self.error_count = 0
        self.task_handlers = task_handlers

    async def process_task(self, task: WorkerTask) -> WorkerResult:
        start_time = time.time()
        self.status = WorkerStatus.BUSY
        self.current_task = task

        max_retries = (
            task.data.get("_max_retries", 3) if hasattr(task.data, "get") else 3
        )

        try:
            for attempt in range(max_retries + 1):
                try:
                    logger.debug(
                        f"Worker {self.worker_id} processing task {task.task_id} (attempt {attempt + 1})"
                    )

                    handler = self.task_handlers.get(task.task_type)
                    if not handler:
                        raise ValueError(
                            f"No handler found for task type: {task.task_type}"
                        )

                    result = await handler(task.data)

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
                        wait_time = min(2**attempt, 30)
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
        return WorkerResult(
            task.task_id,
            False,
            error="Unknown error in process_task",
            execution_time=time.time() - start_time,
        )


class WorkerPool:
    def __init__(
        self,
        max_workers: int = 4,
        queue_size: int = 100,
        task_handlers: Optional[Mapping[str, Callable[[Any], Awaitable[Any]]]] = None,
    ):
        self.max_workers = max_workers
        self.queue_size = queue_size
        self.task_handlers = task_handlers or {}
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

        for i in range(max_workers):
            worker = Worker(f"worker_{i + 1}", self, self.task_handlers)
            self.workers.append(worker)

    async def start(self):
        self.running = True
        logger.info(f"Starting worker pool with {self.max_workers} workers")
        for worker in self.workers:
            asyncio.create_task(self._worker_loop(worker))
        asyncio.create_task(self._result_processor())

    async def stop(self):
        self.running = False
        logger.info("Stopping worker pool")
        await self.task_queue.join()

    async def submit_task(self, task_type: str, data: Any, priority: int = 0) -> str:
        if not self.running:
            raise RuntimeError("Worker pool is not running")

        task_id = str(uuid.uuid4())
        task = WorkerTask(
            task_id=task_id, task_type=task_type, data=data, priority=priority
        )

        future: Future = asyncio.Future()
        self.task_futures[task_id] = future

        await self.task_queue.put((priority, task))
        self.worker_stats["total_tasks"] += 1
        logger.debug(f"Submitted task {task_id} with priority {priority}")
        return task_id

    async def get_result(
        self, task_id: str, timeout: Optional[float] = None
    ) -> WorkerResult:
        if task_id in self.results:
            return self.results[task_id]
        if task_id not in self.task_futures:
            raise ValueError(f"Task {task_id} not found")

        future = self.task_futures[task_id]
        result = await asyncio.wait_for(future, timeout=timeout)
        return result

    def get_worker_status(self) -> Dict[str, Any]:
        return {
            "total_workers": len(self.workers),
            "active_workers": len(
                [w for w in self.workers if w.status == WorkerStatus.BUSY]
            ),
            "idle_workers": len(
                [w for w in self.workers if w.status == WorkerStatus.IDLE]
            ),
            "error_workers": len(
                [w for w in self.workers if w.status == WorkerStatus.ERROR]
            ),
            "queue_size": self.task_queue.qsize(),
            "stats": self.worker_stats.copy(),
        }

    async def _worker_loop(self, worker: Worker):
        while self.running:
            try:
                priority, task = await self.task_queue.get()
                logger.debug(f"Worker {worker.worker_id} got task {task.task_id}")
                result = await worker.process_task(task)
                self.results[task.task_id] = result

                if result.success:
                    self.worker_stats["completed_tasks"] += 1
                else:
                    self.worker_stats["failed_tasks"] += 1

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

                if task.task_id in self.task_futures:
                    if result.success:
                        self.task_futures[task.task_id].set_result(result)
                    else:
                        self.task_futures[task.task_id].set_exception(
                            Exception(result.error)
                        )
                    del self.task_futures[task.task_id]

                self.task_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker.worker_id} error: {e}")
                worker.status = WorkerStatus.ERROR

    async def _result_processor(self):
        while self.running:
            try:
                await asyncio.sleep(10)
                current_time = time.time()
                expired_tasks = [
                    task_id
                    for task_id, result in self.results.items()
                    if current_time - result.execution_time > 3600
                ]
                for task_id in expired_tasks:
                    logger.debug(f"Cleaning up expired task {task_id}")
                    del self.results[task_id]
                await self._health_check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Result processor error: {e}")

    async def _health_check(self):
        current_time = time.time()
        for worker in self.workers:
            if worker.status == WorkerStatus.ERROR:
                logger.warning(
                    f"Worker {worker.worker_id} is in error state, resetting"
                )
                worker.status = WorkerStatus.IDLE
                worker.error_count = 0
            if (
                worker.status == WorkerStatus.BUSY
                and worker.current_task
                and current_time - worker.current_task.created_at > 300
            ):
                logger.warning(f"Worker {worker.worker_id} appears stuck, resetting")
                worker.status = WorkerStatus.IDLE
                worker.current_task = None


worker_pool: Optional[WorkerPool] = None


def get_worker_pool() -> WorkerPool:
    global worker_pool
    if worker_pool is None:
        raise RuntimeError("Worker pool has not been initialized")
    return worker_pool


async def initialize_worker_pool(
    max_workers: int, task_handlers: Mapping[str, Callable[[Any], Awaitable[Any]]]
):
    global worker_pool

    if worker_pool is None:
        worker_pool = WorkerPool(max_workers=max_workers, task_handlers=task_handlers)

        await worker_pool.start()

        logger.info(f"Worker pool initialized with {max_workers} workers")


async def shutdown_worker_pool():
    global worker_pool
    if worker_pool:
        await worker_pool.stop()
        worker_pool = None
        logger.info("Worker pool shutdown complete")
