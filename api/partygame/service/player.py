from redis.asyncio import Redis
from fastapi import HTTPException, WebSocket

from partygame import schemas
from partygame.schemas import Lobby, Player, ConnectionStatus
from partygame.utils.utils import publish


async def create(
    redis: Redis,
    *,
    join_request: schemas.JoinRequest,
    game_id: str,
):
    player = Player(
        name=join_request.player_name,
    )
    await redis.hset(
        f"player.{player.id}", mapping=player.model_dump(exclude={"score"}, exclude_none=True)
    )
    await redis.zadd(f"scores.{game_id}", mapping={player.id: player.score})
    await publish(
        redis,
        f"game.{game_id}.host",
        schemas.PlayerJoinedEvent(player=player)
    )
    return player


async def get(redis: Redis, player_id: str):
    if await redis.hexists(f"player.{player_id}", "name"):
        return Player.model_validate(await redis.hgetall(f"player.{player_id}"))
    raise HTTPException(status_code=404, detail="Player data not found.")


class ClientController:
    def __init__(
        self, websocket: WebSocket, redis: Redis, lobby: Lobby, player: Player
    ):
        self.websocket = websocket
        self.redis = redis
        self.lobby = lobby
        self.player = player

        self.game_channel = f"game.{self.lobby.id}.host"
        self.player_channel = f"game.{self.lobby.id}.{self.player.id}"
        self.player_key = f"player.{self.player.id}"

    async def connected(self):
        self.player.status = ConnectionStatus.CONNECTED
        await self.redis.hset(self.player_key, "status", self.player.status)
        await publish(
            self.redis,
            self.game_channel,
            schemas.PlayerConnectedEvent(player_id=self.player.id),
        )

    async def disconnected(self):
        self.player.status = ConnectionStatus.DISCONNECTED
        await self.redis.hset(self.player_key, "status", self.player.status)
        await publish(
            self.redis,
            self.game_channel,
            schemas.PlayerDisconnectedEvent(player_id=self.player.id),
        )
