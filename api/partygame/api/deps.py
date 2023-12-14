from typing import Generator

from partygame.db.redis import get_connection

async def get_redis() -> Generator:
    conn = get_connection()
    yield conn
    await conn.aclose()
