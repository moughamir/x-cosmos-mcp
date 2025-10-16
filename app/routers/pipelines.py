from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from ..pipeline import MultiModelSEOManager
from ..config import TaskType
from ..utils.db import get_pipeline_runs

router = APIRouter()

_seo_manager: Optional[MultiModelSEOManager] = None


def set_seo_manager(manager_instance: MultiModelSEOManager):
    global _seo_manager
    _seo_manager = manager_instance


class PipelineRunRequest(BaseModel):
    task_type: TaskType
    product_ids: Optional[List[int]] = []


@router.get("/pipeline/runs")
async def get_pipeline_runs_endpoint(limit: int = 100):
    """Get pipeline run history."""
    runs = await get_pipeline_runs(limit)
    return {"runs": [dict(run) for run in runs]}


@router.post("/pipeline/run")
async def run_pipeline_endpoint(
    request: PipelineRunRequest, background_tasks: BackgroundTasks
):
    """Run a pipeline task."""
    if _seo_manager is None:
        raise HTTPException(status_code=500, detail="SEO Manager not initialized")

    background_tasks.add_task(
        _seo_manager.batch_process_products,
        product_ids=request.product_ids,
        task_type=request.task_type,
    )

    product_count = len(request.product_ids or [])
    return {
        "message": f"Pipeline run initiated for {request.task_type.value}",
        "task_type": request.task_type.value,
        "product_count": product_count,
    }
