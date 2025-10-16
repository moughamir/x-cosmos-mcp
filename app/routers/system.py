from fastapi import APIRouter

from ..utils.db import get_change_log, get_db_schema, mark_as_reviewed

router = APIRouter()


@router.get("/schema")
async def get_db_schema_endpoint():
    """Get database schema information."""
    schema = await get_db_schema()
    return {"schema": schema}


@router.get("/changes")
async def get_changes(limit: int = 100):
    """Get change log."""
    changes = await get_change_log(limit)
    return {"changes": changes}


@router.post("/changes/{product_id}/review")
async def mark_changes_reviewed(product_id: int):
    """Mark all changes for a product as reviewed."""
    await mark_as_reviewed(product_id)
    return {"message": "Changes marked as reviewed"}
