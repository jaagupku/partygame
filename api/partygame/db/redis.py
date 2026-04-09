import os

import redis.asyncio as redis

VALKEY_HOST = os.environ.get("VALKEY_HOST") or os.environ.get("REDIS_HOST", "localhost")

pool = redis.ConnectionPool.from_url(f"redis://{VALKEY_HOST}", decode_responses=True)


def get_connection():
    return redis.Redis(connection_pool=pool)
