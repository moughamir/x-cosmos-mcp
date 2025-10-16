# Database

The application uses a PostgreSQL database to store product data, change history, and pipeline run information.

## Schema

### `products` table

| Column | Type | Description |
| --- | --- | --- |
| `id` | `BIGINT` | Product ID (Primary Key) |
| `title` | `TEXT` | Product title |
| `body_html` | `TEXT` | Product description in HTML |
| `tags` | `TEXT` | Comma-separated list of product tags |
| `category` | `TEXT` | Product category |
| `normalized_title` | `TEXT` | Normalized product title |
| `normalized_body_html` | `TEXT` | Normalized product description |
| `normalized_tags_json` | `TEXT` | JSON array of normalized tags |
| `gmc_category_label` | `TEXT` | Google Merchant Center category label |
| `llm_model` | `TEXT` | LLM model used for optimization |
| `llm_confidence` | `DECIMAL(3,2)` | Confidence score of the LLM optimization |
| `normalized_category` | `TEXT` | Normalized product category |
| `category_confidence` | `DECIMAL(3,2)` | Confidence score of the category normalization |
| `created_at` | `TIMESTAMP` | Timestamp of creation |
| `updated_at` | `TIMESTAMP` | Timestamp of last update |

### `changes_log` table

| Column | Type | Description |
| --- | --- | --- |
| `id` | `SERIAL` | Change ID (Primary Key) |
| `product_id` | `BIGINT` | Foreign key to `products` table |
| `field` | `TEXT` | The field that was changed |
| `old` | `TEXT` | The old value |
| `new` | `TEXT` | The new value |
| `source` | `TEXT` | The source of the change (e.g., `api_update`, `worker_pool`) |
| `created_at` | `TIMESTAMP` | Timestamp of the change |
| `reviewed` | `BOOLEAN` | Whether the change has been reviewed |

### `pipeline_runs` table

| Column | Type | Description |
| --- | --- | --- |
| `id` | `SERIAL` | Run ID (Primary Key) |
| `task_type` | `TEXT` | The type of task that was run |
| `status` | `TEXT` | The status of the run (e.g., `RUNNING`, `COMPLETED`, `FAILED`) |
| `start_time` | `TIMESTAMP` | Timestamp of when the run started |
| `end_time` | `TIMESTAMP` | Timestamp of when the run finished |
| `total_products` | `INTEGER` | The total number of products to be processed |
| `processed_products` | `INTEGER` | The number of products that have been processed |
| `failed_products` | `INTEGER` | The number of products that failed to process |
