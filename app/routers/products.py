from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..utils.db import (
    get_all_products,
    get_product_details,
    get_products_batch,
    get_products_for_review,
    log_change,
    update_product_details,
)

router = APIRouter()


class ProductUpdate(BaseModel):
    # Define fields that can be updated. Use Optional if a field might not always be present.
    title: Optional[str] = None
    body_html: Optional[str] = None
    tags: Optional[str] = None
    product_type: Optional[str] = None
    vendor: Optional[str] = None
    normalized_title: Optional[str] = None
    normalized_body_html: Optional[str] = None
    normalized_tags_json: Optional[str] = None
    gmc_category_label: Optional[str] = None
    llm_model: Optional[str] = None
    llm_confidence: Optional[float] = None
    normalized_category: Optional[str] = None
    category_confidence: Optional[float] = None

    class Config:
        extra = "allow"  # Allow other fields not explicitly defined


async def log_product_updates(
    product_id: int, original_product: Dict[str, Any], updates: Dict[str, Any]
):
    """Helper function to log changes for product updates."""
    for field, new_value in updates.items():
        old_value = original_product.get(field)

        # Only log if the value has actually changed
        if old_value != new_value:
            await log_change(product_id, field, old_value, new_value, "api_update")


@router.get("/products")
async def get_products():
    """Get all products from the database."""
    products = await get_all_products()
    return {"products": products}


@router.get("/products/batch")
async def get_products_batch_endpoint(limit: int = 10):
    """Get products for batch processing."""
    products = await get_products_batch(limit)
    return {"products": products}


@router.get("/products/review")
async def get_products_for_review_endpoint(limit: int = 10):
    """Get products that need review (low confidence scores)."""
    products = await get_products_for_review(limit)
    return {"products": products}


@router.get("/products/{product_id}")
async def get_product(product_id: int):
    """Get specific product details and change history."""
    result = await get_product_details(product_id)
    if not result["product"]:
        raise HTTPException(status_code=404, detail="Product not found")

    return {"product": result["product"], "changes": result["changes"]}


@router.post("/products/{product_id}/update")
async def update_product(product_id: int, updates: ProductUpdate):
    """Update product details or create if not exists."""
    # Get original product data for logging if it exists
    original_product_details = await get_product_details(product_id)
    original_product = original_product_details["product"]

    # Convert Pydantic model to dict for database update
    update_data = updates.dict(exclude_unset=True)

    # Update or create the product
    await update_product_details(product_id, **update_data)

    # Log changes
    if original_product:
        await log_product_updates(product_id, original_product, update_data)
    else:
        # If it's a new product, log all fields as new
        for field, new_value in update_data.items():
            await log_change(product_id, field, None, new_value, "api_create")

    return {"message": "Product updated/created successfully"}
