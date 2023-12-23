import os

import redis.asyncio as redis

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")

pool = redis.ConnectionPool.from_url(f"redis://{REDIS_HOST}", decode_responses=True)

def get_connection():
    return redis.Redis(connection_pool=pool)
