import asyncio
import asyncpg
import os
import sys

async def test_db_connection():
    try:
        conn = await asyncpg.connect(
            user=os.getenv('POSTGRES_USER', 'mcp_user'),
            password=os.getenv('POSTGRES_PASSWORD', 'mcp_password'),
            host=os.getenv('POSTGRES_HOST', 'postgres'),
            port=int(os.getenv('POSTGRES_PORT', 5432)),
            database=os.getenv('POSTGRES_DB', 'mcp_db')
        )
        await conn.fetchval('SELECT 1')
        await conn.close()
        print('PostgreSQL connection successful')
        return True
    except Exception as e:
        print(f'PostgreSQL connection failed: {e}')
        return False

if __name__ == '__main__':
    if asyncio.run(test_db_connection()):
        sys.exit(0)
    else:
        sys.exit(1)
