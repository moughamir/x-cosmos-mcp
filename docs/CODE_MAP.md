# Code Map

This document provides a map of the codebase.

## Backend

-   `app/`: The main application directory.
    -   `api.py`: FastAPI endpoints.
    -   `config.py`: Pydantic settings.
    -   `main.py`: FastAPI application entry point.
    -   `models.py`: Pydantic models.
    -   `pipeline.py`: SEO pipeline logic.
    -   `worker_pool.py`: Worker pool for parallel processing.
    -   `worker_task.py`: Worker task and result models.
    -   `utils/`: Utility functions.
        -   `category_normalizer.py`: Category normalization logic.
        -   `db.py`: Database utilities.
        -   `logging_config.py`: Logging configuration.
        -   `ollama_client.py`: Ollama client.
        -   `ollama_manager.py`: Ollama model manager.
        -   `product_exporter.py`: Product exporter.
        -   `taxonomy.py`: Google Product Taxonomy utilities.
        -   `text_cleaner.py`: Text cleaning utilities.
        -   `tokenizer.py`: Tokenizer utilities.
-   `scripts/`: Standalone scripts.
    -   `analyze_json_keys.py`: Analyzes top-level keys in JSON data.
    -   `compress_json_data.py`: Compresses JSON files to .gz format.
    -   `export_sqlite_to_json.py`: Exports data from SQLite to JSON.
    -   `extract_data.py`: Extracts and transforms data from (compressed) JSON files to (compressed) TSV files.
    -   `get_product_structure.sh`: Shell script to get product structure.
    -   `import_to_postgres.sh`: Imports (compressed) TSV data into PostgreSQL.
    -   `mcp_server.py`: MCP server implementation.
    -   `schema.sql`: PostgreSQL database schema.
    -   `utils.py`: Utility functions for scripts.
    -   `migrations/`: Database migration scripts.
        -   `01_import_products_from_json.py`: Migration script to import products from JSON.

## Frontend

-   `frontend/`: Next.js frontend application.
    -   `src/`: Source code.
        -   `app/`: Next.js app router.
        -   `components/`: React components.
        -   `hooks/`: React hooks.
        -   `lib/`: Library functions.
        -   `types/`: TypeScript types.

## Other

-   `data/`: Data files.
    -   `json/`: JSON data.
    -   `migrations/`: SQL migration files.
    -   `ollama.models/`: Ollama models.
    -   `prompts/`: Jinja2 prompts for the LLM.
    -   `sqlite/`: SQLite database.
    -   `taxonomy/`: Google Product Taxonomy files.
    -   `training/`: Training data.
-   `docs/`: Documentation files.
-   `views/`: HTML templates.
