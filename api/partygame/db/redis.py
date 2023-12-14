import redis.asyncio as redis

pool = redis.ConnectionPool.from_url("redis://localhost", decode_responses=True)

def get_connection():
    return redis.Redis(connection_pool=pool)
