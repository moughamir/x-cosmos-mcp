import asyncio
import os
import sys

import asyncpg
import httpx


async def test_db_connection():
    try:
        conn = await asyncpg.connect(
            user=os.getenv("POSTGRES_USER", "mcp_user"),
            password=os.getenv("POSTGRES_PASSWORD", "mcp_password"),
            host=os.getenv("POSTGRES_HOST", "postgres"),
            port=int(os.getenv("POSTGRES_PORT", 5432)),
            database=os.getenv("POSTGRES_DB", "mcp_db"),
        )
        await conn.fetchval("SELECT 1")
        await conn.close()
        print("PostgreSQL connection successful")
        return True
    except Exception as e:
        print(f"PostgreSQL connection failed: {e}")
        return False


async def test_ollama_connection():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{os.getenv('OLLAMA_HOST', 'http://ollama:11434')}/api/tags",
                timeout=10,
            )
            response.raise_for_status()
            print("Ollama connection successful")
            return True
    except Exception as e:
        print(f"Ollama connection failed: {e}")
        return False


async def healthcheck():
    db_ok = await test_db_connection()
    ollama_ok = await test_ollama_connection()
    return db_ok and ollama_ok


if __name__ == "__main__":
    if asyncio.run(healthcheck()):
        sys.exit(0)
    else:
        sys.exit(1)
