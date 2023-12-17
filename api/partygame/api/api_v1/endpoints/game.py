from redis.asyncio import Redis
from fastapi import APIRouter, Depends, WebSocket

from partygame import service
from partygame.api import deps
from partygame.service.player import ClientController

router = APIRouter()


@router.websocket("/{game_id}/host")
async def game_websocket(
    websocket: WebSocket,
    game_id: str,
    redis: Redis = Depends(deps.get_redis),
):
    lobby = await service.lobby.get(redis, game_id)

    pubsub = redis.pubsub()
    channel = f"game.{game_id}.host"
    await pubsub.subscribe(channel)

    await websocket.accept()
    # Game Running
    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=58)
            if message is None:
                # Just send ping message
                continue
            if message["type"] == "message":
                await websocket.send_text(message["data"])
    finally:
        await pubsub.unsubscribe(channel)
        # Game paused


@router.websocket("/{game_id}/controller/{player_id}")
async def game_websocket(
    websocket: WebSocket,
    game_id: str,
    player_id: str,
    redis: Redis = Depends(deps.get_redis),
):
    player = await service.player.get(redis, player_id)
    lobby = await service.lobby.get(redis, game_id)

    client = ClientController(redis, lobby, player)

    pubsub = redis.pubsub()
    channel = f"game.{game_id}.{player_id}"
    await pubsub.subscribe(channel)

    await websocket.accept()
    await client.connected()
    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True)
            if message["type"] == "message":
                await websocket.send_text(message["data"])
    finally:
        await pubsub.unsubscribe(channel)
        await client.disconnected()
