import json
import random
import string

from redis.asyncio import Redis
from pydantic import BaseModel


def id_generator(size=5, chars=string.ascii_uppercase):
    return "".join(random.choice(chars) for _ in range(size))


async def get_unique_join_code(redis: Redis) -> str:
    join_code = id_generator()
    while await redis.get(f"join.{join_code}") is not None:
        join_code = id_generator()
    return join_code


async def publish(redis: Redis, channel: str, payload: dict | BaseModel):
    if isinstance(payload, BaseModel):
        data = payload.model_dump_json()
    else:
        data = json.dumps(payload)
    await redis.publish(channel, data)
