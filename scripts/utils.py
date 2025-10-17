#!/usr/bin/env python3
import json
import hashlib
from pathlib import Path
import asyncpg
import os


def file_hash(path: Path) -> str:
    """Return a short, consistent hash of a file path."""
    return hashlib.md5(str(path).encode()).hexdigest()[:10]


def safe_load_json(file_path: Path):
    """Safely load a JSON file (compressed or not) and return its content or None."""
    try:
        if file_path.suffix == ".gz":
            import gzip

            with gzip.open(file_path, "rt", encoding="utf-8") as f:
                return json.load(f)
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def write_gzipped_json(file_path: Path, data: dict):
    """Write data to a gzipped JSON file."""
    import gzip

    with gzip.open(file_path, "wt", encoding="utf-8") as f:
        json.dump(data, f)


async def get_db_connection():
    """Get a database connection."""
    return await asyncpg.connect(
        user=os.getenv("POSTGRES_USER", "mcp_user"),
        password=os.getenv("POSTGRES_PASSWORD", "mcp_password"),
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        database=os.getenv("POSTGRES_DB", "mcp_db"),
    )
