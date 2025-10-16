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
    -   `configure_ollama.sh`: Script to configure Ollama.
    -   `healthcheck.py`: Healthcheck script for Docker.
    -   `migrations/`: Database migration scripts.
        -   `migrate_sqlite_to_postgres.py`: Script to migrate data from SQLite to PostgreSQL.
        -   `migrate_to_postgres.py`: Script to migrate the database to PostgreSQL.

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
