from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from utils.db import (
    get_products_for_review,
    mark_as_reviewed,
    get_change_log,
    get_all_products,
    get_product_details,
    update_product_details,
)
from config import settings

app = FastAPI()

app.mount("/static", StaticFiles(directory="admin/static"), name="static")

class ProductUpdate(BaseModel):
    title: str
    body_html: str

@app.get("/api/")
async def root():
    return {"message": "MCP Review API"}

@app.get("/api/products")
async def get_products():
    products = await get_all_products(settings.paths.database)
    return products

@app.get("/api/products/{product_id}")
async def get_product(product_id: int):
    details = await get_product_details(settings.paths.database, product_id)
    return details

@app.put("/api/products/{product_id}")
async def update_product(product_id: int, product_update: ProductUpdate):
    await update_product_details(settings.paths.database, product_id, product_update.dict())
    return {"status": "success"}

@app.get("/api/products/review")
async def get_review_products(limit: int = 10):
    products = await get_products_for_review(settings.paths.database, limit=limit)
    return products

@app.put("/api/products/{product_id}/review")
async def review_product(product_id: int):
    await mark_as_reviewed(settings.paths.database, product_id)
    return {"status": "success"}

@app.get("/api/changes")
async def get_changes(limit: int = 100):
    changes = await get_change_log(settings.paths.database, limit=limit)
    return changes

@app.get("/{catchall:path}")
async def serve_frontend(request: Request):
    return FileResponse("admin/templates/index.html")
