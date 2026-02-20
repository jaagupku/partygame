from redis.asyncio import Redis
from typing import AsyncGenerator

from partygame.db.redis import get_connection


async def get_redis() -> AsyncGenerator[Redis, None]:
    conn = get_connection()
    yield conn
    await conn.aclose()
