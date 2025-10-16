# MCP Admin API Documentation

## Overview

The MCP (Model Context Protocol) Admin application provides a comprehensive REST API for managing products, database operations, and AI model management through Ollama integration.

## Base URL

```
http://localhost:8000/api
```

## Authentication

Currently, no authentication is required. All endpoints are publicly accessible.

---

## Product Management Endpoints

### Get All Products

**Endpoint:** `GET /products`

**Description:** Retrieve all products from the database with basic information.

**Response:**
```json
{
  "products": [
    {
      "id": 172840065,
      "title": "Product Title",
      "llm_confidence": 0.85,
      "gmc_category_label": "Home & Garden > Decor"
    }
  ]
}
```

**Status:** ✅ Working

---

### Get Product Details

**Endpoint:** `GET /products/{product_id}`

**Description:** Retrieve detailed information about a specific product including change history.

**Response:**
```json
{
  "product": {
    "id": 172840065,
    "title": "Product Title",
    "body_html": "Product description...",
    "tags": "tag1, tag2, tag3",
    "category": "Home & Garden",
    "normalized_title": "Normalized Title",
    "llm_confidence": 0.85,
    "gmc_category_label": "Home & Garden > Decor",
    "created_at": "2023-01-01T00:00:00",
    "updated_at": "2023-01-01T00:00:00"
  },
  "changes": [
    {
      "id": 1,
      "product_id": 172840065,
      "field": "title",
      "old": "Old Title",
      "new": "New Title",
      "source": "manual_edit",
      "created_at": "2023-01-01T00:00:00",
      "reviewed": false
    }
  ]
}
```

**Status:** ✅ Working

---

### Update Product

**Endpoint:** `POST /products/{product_id}/update`

**Description:** Update product information and automatically log changes.

**Request Body:**
```json
{
  "title": "Updated Product Title",
  "body_html": "Updated description...",
  "category": "New Category"
}
```

**Response:**
```json
{
  "message": "Product updated successfully"
}
```

**Status:** ✅ Working

---

### Get Products Batch

**Endpoint:** `GET /products/batch?limit=10`

**Description:** Get products for batch processing operations.

**Query Parameters:**
- `limit` (optional): Number of products to return (default: 10)

**Response:**
```json
{
  "products": [
    {
      "id": 172840065,
      "title": "Product Title",
      "body_html": "Description...",
      "tags": "tag1, tag2",
      "category": "Category"
    }
  ]
}
```

**Status:** ✅ Working

---

### Get Products for Review

**Endpoint:** `GET /products/review?limit=10`

**Description:** Get products that need manual review (low confidence scores).

**Query Parameters:**
- `limit` (optional): Number of products to return (default: 10)

**Response:** Same format as `/products/batch`

**Status:** ✅ Working

---

## Database Management Endpoints

### Get Database Schema

**Endpoint:** `GET /schema`

**Description:** Retrieve database schema information including tables and columns.

**Response:**
```json
{
  "schema": [
    {
      "name": "products",
      "columns": [
        {"name": "id", "type": "INTEGER"},
        {"name": "title", "type": "TEXT"}
      ]
    }
  ]
}
```

**Status:** ✅ Working

---

### Get Change Log

**Endpoint:** `GET /changes?limit=100`

**Description:** Retrieve the complete change history across all products.

**Query Parameters:**
- `limit` (optional): Number of changes to return (default: 100)

**Response:**
```json
{
  "changes": [
    {
      "id": 1,
      "product_id": 172840065,
      "field": "title",
      "old": "Old Title",
      "new": "New Title",
      "source": "manual_edit",
      "created_at": "2023-01-01T00:00:00",
      "reviewed": false
    }
  ]
}
```

**Status:** ✅ Working

---

### Mark Changes as Reviewed

**Endpoint:** `POST /changes/{product_id}/review`

**Description:** Mark all changes for a specific product as reviewed.

**Response:**
```json
{
  "message": "Changes marked as reviewed"
}
```

**Status:** ✅ Working

---

## Pipeline Management Endpoints

### Run Pipeline

**Endpoint:** `POST /pipeline/run`

**Description:** Run a pipeline task.

The following tasks are available:

*   `meta`: Optimize meta title and description.
*   `content`: Rewrite product content for better SEO.
*   `keywords`: Perform comprehensive keyword analysis.
*   `tags`: Analyze and optimize product tags.
*   `schema_analysis`: Analyze product data against a schema.

**Request Body:**
```json
{
  "task_type": "meta",
  "product_ids": [1, 2, 3]
}
```

**Response:**
```json
{
  "message": "Pipeline run initiated for meta",
  "task_type": "meta",
  "product_count": 3
}
```

**Status:** ✅ Working

---

### Get Pipeline Runs

**Endpoint:** `GET /pipeline/runs?limit=100`

**Description:** Retrieve history of pipeline execution runs.

**Response:**
```json
{
  "runs": [
    {
      "id": 1,
      "task_type": "meta_optimization",
      "status": "COMPLETED",
      "start_time": "2023-01-01T00:00:00",
      "end_time": "2023-01-01T00:01:00",
      "total_products": 100,
      "processed_products": 95,
      "failed_products": 5
    }
  ]
}
```

**Status:** ✅ Working

---

## Ollama Model Management Endpoints

### Get Available Models

**Endpoint:** `GET /ollama/models`

**Description:** Retrieve all installed Ollama models.

**Response:**
```json
[
  {
    "name": "llama3.2:1b",
    "size": 1234567890,
    "modified_at": "2023-01-01T00:00:00"
  }
]
```

**Status:** ✅ Working

---

### Pull New Model

**Endpoint:** `POST /ollama/pull`

**Description:** Initiate download of a new Ollama model.

**Request Body:**
```json
{
  "model_name": "llama3.2:1b"
}
```

**Response:**
```json
{
  "message": "Model llama3.2:1b pull initiated successfully",
  "result": {
    "status": "pulling",
    "digest": "...",
    "total": 1234567890,
    "completed": 0
  }
}
```

**Status:** ✅ Working

---

## Error Responses

All endpoints may return the following error responses:

### 404 Not Found
```json
{
  "detail": "Product not found"
}
```

### 400 Bad Request
```json
{
  "detail": "model_name is required"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

---

## Rate Limits

Currently, no rate limiting is implemented. All endpoints are available without restrictions.

---

## Response Formats

All endpoints return JSON responses. Successful responses include relevant data, while errors include appropriate HTTP status codes and error messages.
