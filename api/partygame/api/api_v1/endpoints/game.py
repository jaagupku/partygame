import logging

from redis.asyncio import Redis
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from partygame import service
from partygame.api import deps
from partygame.service.player import ClientController
from partygame.service.lobby import GameController

log = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/{game_id}/host")
async def game_websocket_host(
    websocket: WebSocket,
    game_id: str,
    redis: Redis = Depends(deps.get_redis),
):
    lobby = await service.lobby.get(redis, game_id)
    server = GameController(websocket, redis, lobby)

    await server.connect()
    # Game Running
    try:
        while True:
            msg = await websocket.receive_json()
            await server.process_input(msg)
    except WebSocketDisconnect:
        log.warning(f"Host for game < {lobby.id} > disconnected.")
    except Exception:
        log.exception("Display websocket failed for game < %s >", lobby.id)
    finally:
        await server.disconnect()
        # Game paused


@router.websocket("/{game_id}/controller/{player_id}")
async def game_websocket_controller(
    websocket: WebSocket,
    game_id: str,
    player_id: str,
    redis: Redis = Depends(deps.get_redis),
):
    player = await service.player.get(redis, game_id, player_id)
    lobby = await service.lobby.get(redis, game_id)

    client = ClientController(websocket, redis, lobby, player)

    log.warning(f"Player < {player.name} > connected.")
    await client.connect()
    try:
        while True:
            msg = await websocket.receive_json()
            await client.process_input(msg)
    except WebSocketDisconnect:
        log.warning(f"Player < {player.name} > disconnected.")
    except Exception:
        log.exception("Controller websocket failed for player < %s >", player.name)
    finally:
        await client.disconnect()
