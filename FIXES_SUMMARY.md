# Backend Fixes Summary - 2025-10-17

## Overview
Fixed multiple critical issues preventing frontend features from working properly, including category normalization, product updates, tags management, and WebSocket connections.

---

## 🎯 Issue 1: Category Normalization Not Saving Changes

### Problem
- Category normalization was running but not saving results to database
- Products were showing "no category" even though they had product types

### Root Cause
1. **Wrong database field**: Query was looking for `category` field which was NULL
2. **Missing data extraction**: Pipeline wasn't extracting normalized results
3. **Schema mismatch**: Products use `product_type_id` (FK) not direct `category` field

### Solution
**File: `app/utils/category_normalizer.py`**
- Updated SQL query to use `COALESCE(p.category, pt.name)` to fetch product type via JOIN
- Added detailed logging to track normalization: `Product X: 'Original' -> 'Normalized' (confidence: 0.XX)`
- Return normalized data for single products

**File: `app/pipeline.py`**
- Added extraction of `normalized_category` and `category_confidence` fields
- Updated `normalize_categories` method to return actual normalized data
- Added fields to update_data dictionary for database persistence

### Result
✅ Category normalization now works correctly
✅ Database updates persist
✅ Detailed logging shows normalization process

---

## 🎯 Issue 2: Product Update Endpoint Failing

### Problem
```
column "vendor_name" of relation "products" does not exist
```

### Root Cause
Frontend was sending entire product object including read-only JOIN fields:
- `vendor_name` (should be `vendor_id`)
- `product_type_name` (should be `product_type_id`)
- `tags`, `images`, `variants`, `options` (separate tables)
- `created_at`, `updated_at` (auto-managed)

### Solution
**File: `app/api.py`**
```python
readonly_fields = {
    'vendor_name', 'product_type_name', 'images', 'variants', 'options',
    'created_at', 'updated_at'
}
filtered_updates = {
    k: v for k, v in updates.items()
    if k not in readonly_fields
}
```

### Result
✅ Product updates work without database errors
✅ Only actual database columns are updated
✅ Read-only fields are safely ignored

---

## 🎯 Issue 3: Tags Not Updating

### Problem
- Tags are in a many-to-many relationship via `product_tags` junction table
- No function existed to properly update tags
- Tags were being filtered out as read-only

### Solution
**File: `app/utils/db.py`**
- Created `update_product_tags()` function:
  1. Deletes all existing tag associations
  2. Creates/finds tag IDs in `tags` table
  3. Creates new associations in `product_tags` junction table

**File: `app/api.py`**
- Extract tags from updates before filtering
- Handle both string (comma-separated) and array formats
- Call `update_product_tags()` separately after product update

### Result
✅ Tags can be updated from frontend
✅ Properly handles many-to-many relationship
✅ Supports both string and array formats

---

## 🎯 Issue 4: WebSocket Connection Errors

### Problem
```
WebSocket error: Cannot call "send" once a close message has been sent
ValueError: list.remove(x): x not in list
```

### Root Cause
1. Trying to send messages after connection closed
2. Trying to remove websocket from list twice
3. No initial data sent to clients on connection

### Solution
**File: `app/api.py`**

1. **Added connection state checks**:
```python
if websocket.client_state != WebSocketState.CONNECTED:
    break
```

2. **Safe disconnect handling**:
```python
try:
    self.active_connections[channel].remove(websocket)
except ValueError:
    pass  # Already removed
```

3. **Send initial data on connect**:
```python
pipeline_runs = await get_pipeline_runs(limit=10)
await websocket.send_json({
    "type": "initial_data",
    "pipeline_runs": runs_dict
})
```

4. **Improved broadcast method**:
- Checks connection state before sending
- Safely removes disconnected clients
- Changed error log level to warning

### Result
✅ No more WebSocket errors
✅ Clients receive initial data immediately
✅ Graceful handling of disconnections
✅ Real-time updates work properly

---

## 📊 Database Schema Reference

### Products Table Structure
```sql
products (
    id BIGINT PRIMARY KEY,
    title TEXT,
    handle TEXT,
    body_html TEXT,
    vendor_id INTEGER FK -> vendors(id),
    product_type_id INTEGER FK -> product_types(id),
    category TEXT,  -- Optional, usually NULL
    normalized_category TEXT,  -- AI-generated
    category_confidence DECIMAL(3,2),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)
```

### Tags Relationship
```sql
tags (id, name)
product_tags (product_id, tag_id)  -- Junction table
```

---

## 🧪 Testing

### Category Normalization
```bash
python cli.py category_normalization --all
```
Expected output:
```
Product 5856071680150: 'Balances & Scales' -> 'Hardware > Tools > Measuring Tools & Sensors > Measuring Scales' (confidence: 0.34)
Updated product 5856071680150 with fields: ['normalized_category', 'category_confidence']
```

### Product Updates
1. Open product detail page in frontend
2. Edit any field (title, body_html, etc.)
3. Save changes
4. Should see success message without errors

### Tags Updates
1. Edit product tags in frontend
2. Save changes
3. Tags should update in database and display correctly

### WebSocket Connection
1. Open Pipeline Progress page
2. Should see "Connected to pipeline updates" toast
3. No console errors
4. Real-time updates appear when running pipelines

---

## 🔑 Key Learnings

1. **Always filter frontend data** - Don't trust that frontend sends only valid fields
2. **Handle relationships properly** - Many-to-many relationships need special handling
3. **Check connection state** - Always verify WebSocket is still connected before sending
4. **Use COALESCE for optional fields** - Handle NULL values gracefully with fallbacks
5. **Log everything** - Detailed logging helps debug issues quickly

---

## 📝 Files Modified

1. `app/utils/category_normalizer.py` - Fixed category query and added logging
2. `app/pipeline.py` - Added normalized data extraction and return values
3. `app/api.py` - Fixed product update endpoint, added field filtering, fixed WebSocket
4. `app/utils/db.py` - Added `update_product_tags()` function

---

## 🚀 Next Steps

All major backend issues are now resolved. Frontend features should work properly:
- ✅ Category normalization
- ✅ Product updates
- ✅ Tags management
- ✅ WebSocket real-time updates
- ✅ Taxonomy viewing

If you encounter any other issues, check the logs for detailed error messages.
