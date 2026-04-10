import asyncio
import json
import logging
from time import time

from pydantic import BaseModel
from redis.asyncio import Redis
from fastapi import HTTPException, WebSocket

from partygame import schemas
from partygame.schemas.events import Event
from partygame.schemas import Lobby, Player, ConnectionStatus
from partygame.utils import publish
from partygame.service.game import GameRuntimeService
from . import realtime
from partygame.state import GameStateRepository, GameKeyFactory

log = logging.getLogger(__name__)


def score_key(lobby_id: str) -> str:
    return GameKeyFactory.game_scores(lobby_id)


def player_channel(game_id: str, player_id: str) -> str:
    return GameKeyFactory.player_channel(game_id, player_id)


def key(game_id: str, player_id: str) -> str:
    return GameKeyFactory.game_player(game_id, player_id)


async def remove(
    redis: Redis,
    *,
    lobby_id: str,
    player_id: str,
):
    repo = GameStateRepository(redis)
    await repo.remove_player(lobby_id, player_id)


async def create(
    redis: Redis,
    *,
    join_request: schemas.JoinRequest,
    game_id: str,
):
    repo = GameStateRepository(redis)
    player = Player(
        name=join_request.player_name,
        game_id=game_id,
    )
    await repo.create_player(player)
    lobby = await repo.get_lobby_meta(game_id)
    await publish(
        redis,
        GameKeyFactory.display_channel(game_id),
        schemas.PlayerJoinedEvent(player=player),
    )
    if lobby is not None and lobby.host_enabled and not lobby.host_id:
        await repo.set_lobby_fields(game_id, host_id=player.id)
        await publish(
            redis,
            GameKeyFactory.display_channel(game_id),
            schemas.SetHostEvent(player_id=player.id),
        )
        await publish(
            redis,
            GameKeyFactory.player_channel(game_id, player.id),
            schemas.SetHostEvent(player_id=player.id),
        )
    return player


async def get(redis: Redis, game_id: str, player_id: str):
    repo = GameStateRepository(redis)
    player = await repo.get_player(game_id, player_id)
    if player is not None:
        return player
    raise HTTPException(status_code=404, detail="Player data not found.")


class ClientController:
    def __init__(self, websocket: WebSocket, redis: Redis, lobby: Lobby, player: Player):
        self.websocket = websocket
        self.redis = redis
        self.repo = GameStateRepository(redis)
        self.runtime = GameRuntimeService(self.repo)
        self.lobby = lobby
        self.player = player

        self.command_channel = GameKeyFactory.host_channel(self.lobby.id)
        self.display_channel = GameKeyFactory.display_channel(self.lobby.id)
        self.player_channel = player_channel(self.lobby.id, self.player.id)
        self.pubsub = None
        self.send_task: asyncio.Task | None = None
        self.timer_task: asyncio.Task | None = None

    def is_host(self) -> bool:
        return self.lobby.host_id == self.player.id

    async def refresh_lobby(self):
        lobby = await self.repo.get_lobby_meta(self.lobby.id)
        if lobby is not None:
            self.lobby.host_id = lobby.host_id
            self.lobby.state = lobby.state
            self.lobby.phase = lobby.phase
            self.lobby.current_step = lobby.current_step
            self.lobby.host_enabled = lobby.host_enabled
            self.lobby.definition_id = lobby.definition_id

    async def connect(self):
        await self.websocket.accept()
        await self.refresh_lobby()
        realtime.register_player(self.lobby.id, self.player.id, self)
        self.player.status = ConnectionStatus.CONNECTED
        await self.repo.set_player_status(self.lobby.id, self.player.id, self.player.status)
        await publish(
            self.redis,
            self.display_channel,
            schemas.PlayerConnectedEvent(player_id=self.player.id),
        )

        self.pubsub = self.redis.pubsub()
        await self.pubsub.subscribe(self.player_channel)
        if self.is_host():
            await self.pubsub.subscribe(self.command_channel)
        self.send_task = asyncio.create_task(self.publish_websocket())
        await self.send(await self.runtime.sync_lobby(self.lobby))
        if self.is_host():
            await self.send(await self.runtime.build_submissions_event(self.lobby))
            await self._schedule_timer_from_snapshot()

    async def disconnect(self):
        realtime.unregister_player(self.lobby.id, self.player.id, self)
        if self.send_task is not None:
            self.send_task.cancel()
        if self.timer_task is not None:
            self.timer_task.cancel()
        if self.pubsub is not None:
            await self.pubsub.unsubscribe(self.player_channel)
            if self.is_host():
                await self.pubsub.unsubscribe(self.command_channel)

        self.player.status = ConnectionStatus.DISCONNECTED
        await self.repo.set_player_status(self.lobby.id, self.player.id, self.player.status)
        await publish(
            self.redis,
            self.display_channel,
            schemas.PlayerDisconnectedEvent(player_id=self.player.id),
        )

    async def publish_websocket(self):
        try:
            while True:
                message = await self.pubsub.get_message(ignore_subscribe_messages=True, timeout=1)
                if message is None:
                    continue
                if message["type"] == "message":
                    channel = message.get("channel")
                    if isinstance(channel, bytes):
                        channel = channel.decode()
                    if channel == self.command_channel and self.is_host():
                        await self.process_controller(message["data"])
                    else:
                        await self.websocket.send_text(message["data"])
        except Exception as error:
            log.error(error)

    async def send(self, payload: dict | BaseModel | str):
        if isinstance(payload, BaseModel):
            await self.websocket.send_text(payload.model_dump_json())
        elif isinstance(payload, dict):
            await self.websocket.send_json(payload)
        else:
            await self.websocket.send_text(payload)

    async def publish_display(self, msg: dict | BaseModel | str):
        await publish(self.redis, self.display_channel, msg)

    async def _safe_send(self, label: str, operation):
        try:
            await operation
        except Exception:
            log.exception("Realtime %s failed for game %s", label, self.lobby.id)

    async def broadcast(
        self,
        msg: dict | BaseModel | str,
        players: list[str] | None = None,
        exclude: str | list[str] | set[str] | tuple[str, ...] | None = None,
    ):
        if players is None:
            players = await self.repo.get_player_ids(self.lobby.id, withscores=False)
        players = [player_id for player_id in players if player_id]

        excluded: set[str] = set()
        if isinstance(exclude, str):
            excluded.add(exclude)
        elif exclude is not None:
            excluded.update(player_id for player_id in exclude if player_id)

        tasks = [
            publish(self.redis, GameKeyFactory.player_channel(self.lobby.id, player_id), msg)
            for player_id in players
            if player_id not in excluded
        ]
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    log.exception(
                        "Player broadcast failed for game %s", self.lobby.id, exc_info=result
                    )

    async def relay_event(
        self,
        msg: dict | BaseModel | str,
        players: list[str] | None = None,
        exclude: str | list[str] | set[str] | tuple[str, ...] | None = None,
    ):
        host_exclusions = {self.player.id}
        if isinstance(exclude, str):
            host_exclusions.add(exclude)
        elif exclude is not None:
            host_exclusions.update(player_id for player_id in exclude if player_id)

        await self.send(msg)
        await self._safe_send("display publish", self.publish_display(msg))
        await self._safe_send(
            "player broadcast",
            self.broadcast(msg, players=players, exclude=host_exclusions),
        )

    async def broadcast_snapshot(self):
        snapshot = await self.runtime.build_snapshot(self.lobby)
        await self.send(snapshot)
        await self._safe_send("local snapshot fanout", self.send_local_snapshot(snapshot))
        await self._safe_send("display snapshot publish", self.publish_display(snapshot))
        await self._safe_send(
            "snapshot player broadcast",
            self.broadcast(snapshot, exclude=self.player.id),
        )
        submissions = await self.runtime.build_submissions_event(self.lobby)
        await self.send(submissions)
        await self._schedule_timer_from_snapshot(snapshot)

    async def send_local_snapshot(self, snapshot: schemas.RuntimeSnapshotEvent):
        tasks = []
        for controller in realtime.get_displays(self.lobby.id):
            if controller is self:
                continue
            tasks.append(controller.send(snapshot))
        for controller in realtime.get_players(self.lobby.id, exclude={self.player.id}):
            tasks.append(controller.send(snapshot))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def process_input(self, msg: dict):
        await self.refresh_lobby()
        if self.is_host():
            await self.process_controller(json.dumps(msg))
            return
        await publish(self.redis, self.command_channel, msg)

    async def start_game(self):
        self.lobby, _ = await self.runtime.start_game(self.lobby)
        await self.relay_event(schemas.StartGameEvent())
        await self.broadcast_snapshot()

    async def sync_host_runtime_state(
        self,
        snapshot: schemas.RuntimeSnapshotEvent | None = None,
    ):
        snapshot = snapshot or await self.runtime.build_snapshot(self.lobby)
        await self.send(await self.runtime.build_submissions_event(self.lobby))
        await self._schedule_timer_from_snapshot(snapshot)

    async def process_controller(self, msg: str):
        data = json.loads(msg)
        event_type = data.get("type_")

        if event_type == Event.START_GAME:
            await self.start_game()
            return

        if event_type == Event.STEP_ADVANCED:
            events = await self.runtime.advance_step(self.lobby)
            snapshot = None
            for event in events:
                await self.relay_event(event)
                if isinstance(event, schemas.RuntimeSnapshotEvent):
                    snapshot = event
            await self.sync_host_runtime_state(snapshot)
            return

        if event_type == Event.CLOSE_STEP:
            events = await self.runtime.close_step(self.lobby)
            snapshot = None
            for event in events:
                await self.relay_event(event)
                if isinstance(event, schemas.RuntimeSnapshotEvent):
                    snapshot = event
            await self.sync_host_runtime_state(snapshot)
            return

        if event_type == Event.PLAYER_INPUT_SUBMITTED:
            payload = schemas.PlayerInputSubmittedEvent.model_validate(data)
            events, handled = await self.runtime.submit_player_input(
                self.lobby,
                payload.player_id,
                payload.value,
            )
            for event in events:
                await self.relay_event(event)
            if handled:
                await self.broadcast_snapshot()
            return

        if event_type == Event.BUZZER_STATE:
            buzzer_state = schemas.BuzzerStateEvent.model_validate(data)
            for event in await self.runtime.set_buzzer_state(self.lobby, buzzer_state.active):
                await self.relay_event(event)
            return

        if event_type == Event.UPDATE_SCORE:
            update_score = await self.runtime.update_score(
                self.lobby, schemas.UpdateScoreEvent.model_validate(data)
            )
            await self.relay_event(update_score, exclude=update_score.player_id)
            await self.broadcast_snapshot()
            return

        if event_type == Event.REVIEW_SUBMISSION:
            review_events = await self.runtime.review_submission(
                self.lobby,
                schemas.ReviewSubmissionEvent.model_validate(data),
            )
            for event in review_events:
                await self.relay_event(event, exclude=getattr(event, "player_id", None))
            await self.broadcast_snapshot()
            return

        if event_type == Event.REVEALED_SUBMISSION:
            player_id = (
                data.get("submission", {}).get("player_id")
                if data.get("submission")
                else data.get("player_id")
            )
            reveal_event = await self.runtime.reveal_submission(self.lobby, player_id)
            await self.relay_event(reveal_event)
            await self.broadcast_snapshot()
            return

        if event_type == Event.SCORES_UPDATED:
            scores_event = await self.runtime.evaluate_auto_step(self.lobby)
            await self.relay_event(scores_event)
            await self.broadcast_snapshot()
            return

    async def _schedule_timer_from_snapshot(
        self, snapshot: schemas.RuntimeSnapshotEvent | None = None
    ):
        if self.timer_task is not None:
            self.timer_task.cancel()
            self.timer_task = None

        snapshot = snapshot or await self.runtime.build_snapshot(self.lobby)
        if (
            snapshot.active_step is None
            or snapshot.active_step.timer.ends_at is None
            or not snapshot.active_step.timer.enforced
            or self.lobby.phase != "question_active"
        ):
            return

        delay = max(0, snapshot.active_step.timer.ends_at - time())
        self.timer_task = asyncio.create_task(self._expire_timer(delay))

    async def _expire_timer(self, delay: float):
        await asyncio.sleep(delay)
        lobby = await self.repo.get_lobby_meta(self.lobby.id)
        if lobby is None:
            return
        self.lobby = lobby
        if self.lobby.phase != "question_active":
            return
        events = await self.runtime.close_step(self.lobby)
        snapshot = None
        for event in events:
            await self.relay_event(event)
            if isinstance(event, schemas.RuntimeSnapshotEvent):
                snapshot = event
        await self.sync_host_runtime_state(snapshot)
