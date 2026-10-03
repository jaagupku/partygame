"""Connection-independent, restart-safe deadline processing."""

import asyncio
import logging
from time import time

from partygame.db.redis import get_connection
from partygame.service.drawing.runtime import DUE_KEY, DrawingRuntime
from partygame.state import GameStateRepository

log = logging.getLogger(__name__)


async def run_scheduler():
    redis = get_connection()
    repo = GameStateRepository(redis)
    try:
        while True:
            try:
                for token in await redis.zrangebyscore(DUE_KEY, "-inf", time(), start=0, num=100):
                    lobby_id, run_id = token.split(":", 1)
                    try:
                        async with repo.mutation_lock(lobby_id):
                            lobby = await repo.get_lobby_meta(lobby_id)
                            if (
                                lobby is None
                                or lobby.game_type != "drawing_mashup"
                                or (lobby.run_id or lobby.id) != run_id
                            ):
                                await redis.zrem(DUE_KEY, token)
                                continue
                            # Another worker may already have consumed this deadline.
                            due = await redis.zscore(DUE_KEY, token)
                            if due is not None and due <= time():
                                await DrawingRuntime(repo).tick(lobby)
                    except Exception:
                        log.exception("Drawing transition failed for %s", lobby_id)
                        await redis.zadd(DUE_KEY, {token: time() + 5})
            except Exception:
                log.exception("Drawing scheduler unavailable; retrying")
            await asyncio.sleep(1)
    finally:
        await redis.aclose()
