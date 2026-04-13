import asyncio
import json
import logging
from time import time
from typing import Any

from pydantic import BaseModel
from redis.asyncio import Redis
from fastapi import HTTPException, WebSocket

from partygame import schemas
from partygame.core.config import settings
from partygame.schemas.events import Event
from partygame.schemas import Lobby, Player, ConnectionStatus
from partygame.utils import publish
from partygame.service.game import GameRuntimeService
from . import realtime
from partygame.state import GameStateRepository, GameKeyFactory

log = logging.getLogger(__name__)


async def refresh_idle_ttl(
    repo: GameStateRepository,
    lobby: Lobby | None,
):
    if lobby is None or lobby.phase == "finished":
        return
    await repo.apply_game_ttl(lobby.id, settings.GAME_IDLE_TTL_SECONDS)


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
    await refresh_idle_ttl(repo, lobby)
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

    def _snapshot_for_viewer(
        self,
        snapshot: schemas.RuntimeSnapshotEvent,
        *,
        include_host_answer: bool,
    ) -> schemas.RuntimeSnapshotEvent:
        if include_host_answer:
            return snapshot
        return snapshot.model_copy(update={"host_answer": None, "submissions": []})

    def _build_patch_changes(
        self,
        before: dict[str, Any],
        after: dict[str, Any],
    ) -> dict[str, Any]:
        changes: dict[str, Any] = {}
        for key, after_value in after.items():
            if key in {"type_", "revision"}:
                continue
            before_value = before.get(key)
            if key == "lobby":
                lobby_changes = {
                    field: value
                    for field, value in after_value.items()
                    if before_value is None or before_value.get(field) != value
                }
                if lobby_changes:
                    changes[key] = lobby_changes
                continue
            if before_value != after_value:
                changes[key] = after_value
        return changes

    def _patch_for_viewer(
        self,
        before_snapshot: schemas.RuntimeSnapshotEvent,
        after_snapshot: schemas.RuntimeSnapshotEvent,
        *,
        include_host_answer: bool,
    ) -> schemas.RuntimePatchEvent | None:
        before_view = self._snapshot_for_viewer(
            before_snapshot, include_host_answer=include_host_answer
        ).model_dump(mode="json")
        after_view = self._snapshot_for_viewer(
            after_snapshot, include_host_answer=include_host_answer
        ).model_dump(mode="json")
        changes = self._build_patch_changes(before_view, after_view)
        if not changes:
            return None
        return schemas.RuntimePatchEvent(
            base_revision=before_snapshot.revision,
            revision=after_snapshot.revision,
            changes=changes,
        )

    async def _send_runtime_patch(
        self,
        before_snapshot: schemas.RuntimeSnapshotEvent,
        after_snapshot: schemas.RuntimeSnapshotEvent,
    ):
        host_patch = self._patch_for_viewer(
            before_snapshot, after_snapshot, include_host_answer=True
        )
        public_patch = self._patch_for_viewer(
            before_snapshot, after_snapshot, include_host_answer=False
        )
        if host_patch is not None:
            await self.send(host_patch)
        if public_patch is not None:
            await self._safe_send("display patch publish", self.publish_display(public_patch))
            await self._safe_send(
                "player patch broadcast",
                self.broadcast(public_patch, exclude=self.player.id),
            )

    async def _emit_runtime_state(
        self,
        before_snapshot: schemas.RuntimeSnapshotEvent | None,
        *,
        force_snapshot: bool,
    ) -> schemas.RuntimeSnapshotEvent:
        if before_snapshot is None:
            snapshot = await self.runtime.build_snapshot(self.lobby)
            await self.send(snapshot)
            await self._safe_send("local snapshot fanout", self.send_local_snapshot(snapshot))
            await self._safe_send("display snapshot publish", self.publish_display(snapshot))
            await self._safe_send(
                "snapshot player broadcast",
                self.broadcast(snapshot, exclude=self.player.id),
            )
            await self._schedule_timer_from_snapshot(snapshot)
            return snapshot

        current_snapshot = await self.runtime.build_snapshot(
            self.lobby, revision=before_snapshot.revision
        )
        patch_preview = self._patch_for_viewer(
            before_snapshot, current_snapshot, include_host_answer=True
        )
        if patch_preview is None and not force_snapshot:
            await self._schedule_timer_from_snapshot(current_snapshot)
            return current_snapshot

        next_revision = await self.repo.increment_state_revision(self.lobby.id)
        snapshot = await self.runtime.build_snapshot(self.lobby, revision=next_revision)
        if force_snapshot:
            await self.send(snapshot)
            await self._safe_send("local snapshot fanout", self.send_local_snapshot(snapshot))
            await self._safe_send("display snapshot publish", self.publish_display(snapshot))
            await self._safe_send(
                "snapshot player broadcast",
                self.broadcast(snapshot, exclude=self.player.id),
            )
            await self._schedule_timer_from_snapshot(snapshot)
            return snapshot

        await self._send_runtime_patch(before_snapshot, snapshot)
        await self._schedule_timer_from_snapshot(snapshot)
        return snapshot

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
        await refresh_idle_ttl(self.repo, self.lobby)
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
        connected_players = await self.repo.count_connected_players(self.lobby.id)
        if self.lobby.phase != "finished":
            # Both active and abandoned lobbies keep the standard idle TTL;
            # the count check makes the zero-connected branch explicit.
            _ = connected_players
            await self.repo.apply_game_ttl(self.lobby.id, settings.GAME_IDLE_TTL_SECONDS)
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
        if isinstance(payload, schemas.RuntimeSnapshotEvent):
            payload = self._snapshot_for_viewer(payload, include_host_answer=self.is_host())
        if isinstance(payload, BaseModel):
            await self.websocket.send_text(payload.model_dump_json())
        elif isinstance(payload, dict):
            await self.websocket.send_json(payload)
        else:
            await self.websocket.send_text(payload)

    async def publish_display(self, msg: dict | BaseModel | str):
        if isinstance(msg, schemas.RuntimeSnapshotEvent):
            msg = self._snapshot_for_viewer(msg, include_host_answer=False)
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
        if isinstance(msg, schemas.RuntimeSnapshotEvent):
            msg = self._snapshot_for_viewer(msg, include_host_answer=False)
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
        before_snapshot = await self.runtime.build_snapshot(self.lobby)
        await self._emit_runtime_state(before_snapshot, force_snapshot=True)

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
        if msg.get("type_") == Event.RESYNC_REQUEST:
            await self.send(await self.runtime.sync_lobby(self.lobby))
            if self.is_host():
                await self._schedule_timer_from_snapshot()
            return
        if self.is_host():
            await self.process_controller(json.dumps(msg))
            return
        await publish(self.redis, self.command_channel, msg)

    async def start_game(self):
        before_snapshot = await self.runtime.build_snapshot(self.lobby)
        self.lobby, _ = await self.runtime.start_game(self.lobby)
        await self.relay_event(schemas.StartGameEvent())
        await self._emit_runtime_state(before_snapshot, force_snapshot=True)

    async def sync_host_runtime_state(
        self,
        snapshot: schemas.RuntimeSnapshotEvent | None = None,
    ):
        snapshot = snapshot or await self.runtime.build_snapshot(self.lobby)
        await self._schedule_timer_from_snapshot(snapshot)

    async def process_controller(self, msg: str):
        data = json.loads(msg)
        event_type = data.get("type_")
        await refresh_idle_ttl(self.repo, self.lobby)

        if event_type == Event.START_GAME:
            await self.start_game()
            return

        if event_type == Event.RESET_STEP:
            before_snapshot = await self.runtime.build_snapshot(self.lobby)
            events = await self.runtime.reset_current_step(self.lobby)
            if not events:
                return
            for event in events:
                if not isinstance(event, schemas.RuntimeSnapshotEvent):
                    await self.relay_event(event)
            snapshot = await self._emit_runtime_state(before_snapshot, force_snapshot=True)
            await self.sync_host_runtime_state(snapshot)
            return

        if event_type == Event.SHOW_ANSWER_REVEAL:
            before_snapshot = await self.runtime.build_snapshot(self.lobby)
            events = await self.runtime.show_answer_reveal(self.lobby)
            if not events:
                return
            for event in events:
                if not isinstance(event, schemas.RuntimeSnapshotEvent):
                    await self.relay_event(event)
            snapshot = await self._emit_runtime_state(before_snapshot, force_snapshot=False)
            await self.sync_host_runtime_state(snapshot)
            return

        if event_type == Event.SHOW_QUESTION:
            before_snapshot = await self.runtime.build_snapshot(self.lobby)
            events = await self.runtime.show_question(self.lobby)
            if not events:
                return
            for event in events:
                if not isinstance(event, schemas.RuntimeSnapshotEvent):
                    await self.relay_event(event)
            snapshot = await self._emit_runtime_state(before_snapshot, force_snapshot=False)
            await self.sync_host_runtime_state(snapshot)
            return

        if event_type == Event.SCOREBOARD_VISIBILITY:
            visibility = schemas.ScoreboardVisibilityEvent.model_validate(data)
            before_snapshot = await self.runtime.build_snapshot(self.lobby)
            events = await self.runtime.set_scoreboard_visibility(self.lobby, visibility.visible)
            if not events:
                return
            for event in events:
                if not isinstance(event, schemas.RuntimeSnapshotEvent):
                    await self.relay_event(event)
            snapshot = await self._emit_runtime_state(before_snapshot, force_snapshot=False)
            await self.sync_host_runtime_state(snapshot)
            return

        if event_type == Event.STEP_ADVANCED:
            before_snapshot = await self.runtime.build_snapshot(self.lobby)
            events = await self.runtime.advance_step(self.lobby)
            if not events:
                return
            for event in events:
                if not isinstance(event, schemas.RuntimeSnapshotEvent):
                    await self.relay_event(event)
            snapshot = await self._emit_runtime_state(before_snapshot, force_snapshot=True)
            await self.sync_host_runtime_state(snapshot)
            return

        if event_type == Event.CLOSE_STEP:
            before_snapshot = await self.runtime.build_snapshot(self.lobby)
            events = await self.runtime.close_step(self.lobby)
            if not events:
                return
            for event in events:
                if not isinstance(event, schemas.RuntimeSnapshotEvent):
                    await self.relay_event(event)
            snapshot = await self._emit_runtime_state(before_snapshot, force_snapshot=False)
            await self.sync_host_runtime_state(snapshot)
            return

        if event_type == Event.PLAYER_INPUT_SUBMITTED:
            payload = schemas.PlayerInputSubmittedEvent.model_validate(data)
            before_snapshot = await self.runtime.build_snapshot(self.lobby)
            events, handled = await self.runtime.submit_player_input(
                self.lobby,
                payload.player_id,
                payload.value,
            )
            for event in events:
                await self.relay_event(event)
            if handled:
                await self._emit_runtime_state(before_snapshot, force_snapshot=False)
            return

        if event_type == Event.BUZZER_STATE:
            buzzer_state = schemas.BuzzerStateEvent.model_validate(data)
            before_snapshot = await self.runtime.build_snapshot(self.lobby)
            for event in await self.runtime.set_buzzer_state(self.lobby, buzzer_state.active):
                if not isinstance(event, schemas.RuntimeSnapshotEvent):
                    await self.relay_event(event)
            await self._emit_runtime_state(before_snapshot, force_snapshot=False)
            return

        if event_type == Event.UPDATE_SCORE:
            before_snapshot = await self.runtime.build_snapshot(self.lobby)
            update_score = await self.runtime.update_score(
                self.lobby, schemas.UpdateScoreEvent.model_validate(data)
            )
            await self.relay_event(update_score, exclude=update_score.player_id)
            await self._emit_runtime_state(before_snapshot, force_snapshot=False)
            return

        if event_type == Event.REVIEW_SUBMISSION:
            before_snapshot = await self.runtime.build_snapshot(self.lobby)
            review_events = await self.runtime.review_submission(
                self.lobby,
                schemas.ReviewSubmissionEvent.model_validate(data),
            )
            for event in review_events:
                exclude = None
                if not isinstance(event, schemas.BuzzerReviewedEvent):
                    exclude = getattr(event, "player_id", None)
                await self.relay_event(event, exclude=exclude)
            await self._emit_runtime_state(before_snapshot, force_snapshot=False)
            return

        if event_type == Event.REVEALED_SUBMISSION:
            before_snapshot = await self.runtime.build_snapshot(self.lobby)
            player_id = (
                data.get("submission", {}).get("player_id")
                if data.get("submission")
                else data.get("player_id")
            )
            reveal_event = await self.runtime.reveal_submission(self.lobby, player_id)
            await self.relay_event(reveal_event)
            await self._emit_runtime_state(before_snapshot, force_snapshot=False)
            return

        if event_type == Event.SCORES_UPDATED:
            before_snapshot = await self.runtime.build_snapshot(self.lobby)
            scores_event = await self.runtime.evaluate_auto_step(self.lobby)
            await self.relay_event(scores_event)
            await self._emit_runtime_state(before_snapshot, force_snapshot=False)
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
        before_snapshot = await self.runtime.build_snapshot(self.lobby)
        events = await self.runtime.close_step(self.lobby)
        for event in events:
            if not isinstance(event, schemas.RuntimeSnapshotEvent):
                await self.relay_event(event)
        snapshot = await self._emit_runtime_state(before_snapshot, force_snapshot=False)
        await self.sync_host_runtime_state(snapshot)
