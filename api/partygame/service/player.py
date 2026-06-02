import asyncio
import json
import logging
from collections import deque
from time import time
from typing import Any, Awaitable, Callable, Literal
from uuid import uuid4

from pydantic import BaseModel, ValidationError
from redis.asyncio import Redis
from fastapi import HTTPException, WebSocket

from partygame import schemas
from partygame.core.config import settings
from partygame.schemas.events import Event
from partygame.schemas import Lobby, Player, ConnectionStatus
from partygame.utils import publish
from partygame.service.game import GameRuntimeService
from partygame.service.media import get_media_storage
from partygame.service.runtime import RuntimeTransitionScheduler
from . import realtime
from partygame.state import GameStateRepository, GameKeyFactory

log = logging.getLogger(__name__)
PLAYER_REACTION_WINDOW_SECONDS = 2.0
PLAYER_REACTION_BURST_LIMIT = 8
DRAFT_COLLECTION_GRACE_SECONDS = 1.0


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


def public_runtime_snapshot(
    snapshot: schemas.RuntimeSnapshotEvent,
    *,
    viewer_player_id: str | None = None,
) -> schemas.RuntimeSnapshotEvent:
    submissions = snapshot.submissions if _should_reveal_public_submissions(snapshot) else []
    own_drawing_id = None
    if viewer_player_id and viewer_player_id in snapshot.drawing_owner_ids:
        own_drawing_id = f"drawing:{snapshot.drawing_owner_ids.index(viewer_player_id)}"
    return snapshot.model_copy(
        update={
            "host_answer": None,
            "submissions": submissions,
            "drawing_owner_ids": [],
            "own_drawing_id": own_drawing_id,
        }
    )


def _should_reveal_public_submissions(snapshot: schemas.RuntimeSnapshotEvent) -> bool:
    step = snapshot.active_step
    return (
        snapshot.display_phase == "answer_reveal"
        and step is not None
        and step.input_kind == schemas.PlayerInputKind.MAP
        and step.evaluation_type == schemas.EvaluationType.MAP_DISTANCE
    )


async def remove(
    redis: Redis,
    *,
    lobby_id: str,
    player_id: str,
):
    repo = GameStateRepository(redis)
    player = await repo.get_player(lobby_id, player_id)
    if player is not None and player.avatar_kind == "custom" and player.avatar_asset_id:
        storage = get_media_storage()
        try:
            await storage.delete(player.avatar_asset_id)
        except HTTPException as error:
            if error.status_code != 404:
                raise
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
        avatar_kind=join_request.avatar_kind,
        avatar_preset_key=join_request.avatar_preset_key,
        avatar_url=join_request.avatar_url,
        avatar_asset_id=join_request.avatar_asset_id,
    )
    await repo.create_player(player)
    lobby = await repo.get_lobby_meta(game_id)
    await refresh_idle_ttl(repo, lobby)
    await publish(
        redis,
        GameKeyFactory.display_channel(game_id),
        schemas.PlayerJoinedEvent(player=player),
    )
    if lobby is not None:
        lobby_updates: dict[str, str] = {}
        if not lobby.starter_id:
            lobby_updates["starter_id"] = player.id
        if lobby.host_enabled and not lobby.host_id:
            lobby_updates["host_id"] = player.id
        if lobby_updates:
            await repo.set_lobby_fields(game_id, **lobby_updates)
    if lobby is not None and lobby.host_enabled and not lobby.host_id:
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
        self.transition_scheduler = RuntimeTransitionScheduler()
        self.reaction_timestamps: deque[float] = deque()

    def _snapshot_for_viewer(
        self,
        snapshot: schemas.RuntimeSnapshotEvent,
        *,
        include_host_answer: bool,
        viewer_player_id: str | None = None,
    ) -> schemas.RuntimeSnapshotEvent:
        if include_host_answer:
            return snapshot
        return public_runtime_snapshot(snapshot, viewer_player_id=viewer_player_id)

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
        viewer_player_id: str | None = None,
    ) -> schemas.RuntimePatchEvent | None:
        before_view = self._snapshot_for_viewer(
            before_snapshot,
            include_host_answer=include_host_answer,
            viewer_player_id=viewer_player_id,
        ).model_dump(mode="json")
        after_view = self._snapshot_for_viewer(
            after_snapshot,
            include_host_answer=include_host_answer,
            viewer_player_id=viewer_player_id,
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
            self._broadcast_runtime_patch(before_snapshot, after_snapshot, exclude=self.player.id),
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

    def _entered_new_round(
        self,
        before_snapshot: schemas.RuntimeSnapshotEvent,
        after_snapshot: schemas.RuntimeSnapshotEvent,
    ) -> bool:
        before_round_id = before_snapshot.active_round.id if before_snapshot.active_round else None
        after_round_id = after_snapshot.active_round.id if after_snapshot.active_round else None
        return (
            after_snapshot.lobby.phase == "question_active"
            and after_round_id is not None
            and after_round_id != before_round_id
        )

    async def _begin_round_intro_if_needed(
        self,
        before_snapshot: schemas.RuntimeSnapshotEvent,
        after_snapshot: schemas.RuntimeSnapshotEvent,
    ) -> schemas.RuntimeSnapshotEvent:
        if not self._entered_new_round(before_snapshot, after_snapshot):
            return after_snapshot
        return await self.runtime.begin_round_intro(self.lobby)

    def is_host(self) -> bool:
        return self.lobby.host_id == self.player.id

    def can_start_hostless_game(self) -> bool:
        return not self.lobby.host_enabled and self.lobby.starter_id == self.player.id

    async def can_control_hostless_info_slide(self) -> bool:
        if not self.can_start_hostless_game():
            return False
        step = await self.runtime.get_current_step(self.lobby)
        return step is not None and self.runtime.is_information_slide(step)

    async def refresh_lobby(self):
        lobby = await self.repo.get_lobby_meta(self.lobby.id)
        if lobby is not None:
            self.lobby.starter_id = lobby.starter_id
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
            payload = self._snapshot_for_viewer(
                payload,
                include_host_answer=self.is_host(),
                viewer_player_id=self.player.id,
            )
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

    async def _broadcast_runtime_patch(
        self,
        before_snapshot: schemas.RuntimeSnapshotEvent,
        after_snapshot: schemas.RuntimeSnapshotEvent,
        *,
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

        tasks = []
        for player_id in players:
            if player_id in excluded:
                continue
            patch = self._patch_for_viewer(
                before_snapshot,
                after_snapshot,
                include_host_answer=False,
                viewer_player_id=player_id,
            )
            if patch is not None:
                tasks.append(
                    publish(
                        self.redis, GameKeyFactory.player_channel(self.lobby.id, player_id), patch
                    )
                )
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    log.exception(
                        "Player runtime patch broadcast failed for game %s",
                        self.lobby.id,
                        exc_info=result,
                    )

    async def _safe_send(self, label: str, operation: Awaitable[Any]) -> None:
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

        tasks = []
        for player_id in players:
            if player_id in excluded:
                continue
            payload = (
                self._snapshot_for_viewer(
                    msg,
                    include_host_answer=False,
                    viewer_player_id=player_id,
                )
                if isinstance(msg, schemas.RuntimeSnapshotEvent)
                else msg
            )
            tasks.append(
                publish(
                    self.redis, GameKeyFactory.player_channel(self.lobby.id, player_id), payload
                )
            )
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
        if msg.get("type_") == Event.PLAYER_REACTION:
            await self._process_player_reaction(msg)
            return
        if (
            self.is_host()
            or (msg.get("type_") == Event.START_GAME and self.can_start_hostless_game())
            or (
                msg.get("type_")
                in {Event.CLOSE_STEP, Event.SHOW_ANSWER_REVEAL, Event.STEP_ADVANCED}
                and await self.can_control_hostless_info_slide()
            )
            or (msg.get("type_") == Event.PLAYER_INPUT_SUBMITTED and not self.lobby.host_enabled)
        ):
            await self.process_controller(json.dumps(msg))
            return
        if msg.get("type_") in {Event.PLAYER_INPUT_SUBMITTED, Event.DRAWING_VOTE_SUBMITTED}:
            msg = msg | {"player_id": self.player.id}
        await publish(self.redis, self.command_channel, msg)

    def _can_send_reactions(self) -> bool:
        return self.lobby.state == schemas.GameState.RUNNING or self.lobby.phase == "finished"

    def _allow_reaction_now(self) -> bool:
        now = time()
        cutoff = now - PLAYER_REACTION_WINDOW_SECONDS
        while self.reaction_timestamps and self.reaction_timestamps[0] < cutoff:
            self.reaction_timestamps.popleft()
        if len(self.reaction_timestamps) >= PLAYER_REACTION_BURST_LIMIT:
            return False
        self.reaction_timestamps.append(now)
        return True

    async def _process_player_reaction(self, msg: dict):
        if not self._can_send_reactions() or not self._allow_reaction_now():
            return
        try:
            event = schemas.PlayerReactionEvent.model_validate(
                {
                    "type_": Event.PLAYER_REACTION,
                    "player_id": self.player.id,
                    "reaction": msg.get("reaction"),
                    "instance_id": msg.get("instance_id") or uuid4().hex,
                    "emitted_at": float(msg.get("emitted_at") or time()),
                }
            )
        except TypeError, ValueError, ValidationError:
            return
        await self.runtime.record_player_reaction(self.lobby, event.player_id, event.reaction)
        await self.relay_event(event)

    async def start_game(self):
        before_snapshot = await self.runtime.build_snapshot(self.lobby)
        self.lobby, _ = await self.runtime.start_game(self.lobby)
        await self.runtime.begin_round_intro(self.lobby)
        await self.relay_event(schemas.StartGameEvent())
        await self._emit_runtime_state(before_snapshot, force_snapshot=True)

    async def sync_host_runtime_state(
        self,
        snapshot: schemas.RuntimeSnapshotEvent | None = None,
    ):
        snapshot = snapshot or await self.runtime.build_snapshot(self.lobby)
        await self._schedule_timer_from_snapshot(snapshot)

    async def _relay_non_snapshot_events(self, events: list[schemas.BaseEvent]):
        for event in events:
            if not isinstance(event, schemas.RuntimeSnapshotEvent):
                await self.relay_event(event)

    async def _emit_and_sync_runtime_state(
        self,
        before_snapshot: schemas.RuntimeSnapshotEvent,
        *,
        force_snapshot: bool,
    ):
        snapshot = await self._emit_runtime_state(
            before_snapshot,
            force_snapshot=force_snapshot,
        )
        await self.sync_host_runtime_state(snapshot)

    async def _run_runtime_events(
        self,
        action: Callable[[], Awaitable[list[schemas.BaseEvent]]],
        *,
        force_snapshot: bool = False,
        relay_events: bool = True,
        begin_round_intro: bool = False,
    ):
        before_snapshot = await self.runtime.build_snapshot(self.lobby)
        events = await action()
        if not events:
            return
        if relay_events:
            await self._relay_non_snapshot_events(events)
        if begin_round_intro:
            after_snapshot = await self.runtime.build_snapshot(self.lobby)
            await self._begin_round_intro_if_needed(before_snapshot, after_snapshot)
        await self._emit_and_sync_runtime_state(
            before_snapshot,
            force_snapshot=force_snapshot,
        )

    async def _collect_player_drafts_before_close(
        self,
        *,
        reason: str,
    ) -> bool:
        await self.refresh_lobby()
        if self.lobby.phase != "question_active":
            return False
        step = await self.runtime.get_current_step(self.lobby)
        if step is None or step.player_input.kind in {
            schemas.PlayerInputKind.NONE,
            schemas.PlayerInputKind.BUZZER,
        }:
            return False

        state = await self.runtime.get_step_state(self.lobby.id)
        submitted_player_ids = set(state.get("answers", {}).keys())
        player_ids = [
            player.id
            for player in await self.repo.get_players(self.lobby.id)
            if player.id
            and player.id != self.lobby.host_id
            and player.id not in submitted_player_ids
        ]
        if not player_ids:
            return False

        event = schemas.CollectPlayerDraftsEvent(step_id=step.id, reason=reason)
        if self.player.id in player_ids:
            await self.send(event)
            player_ids = [player_id for player_id in player_ids if player_id != self.player.id]
        await self._safe_send(
            "draft collection broadcast", self.broadcast(event, players=player_ids)
        )
        await asyncio.sleep(DRAFT_COLLECTION_GRACE_SECONDS)
        await self.refresh_lobby()
        return True

    async def process_controller(self, msg: str):
        data = json.loads(msg)
        event_type = data.get("type_")
        await refresh_idle_ttl(self.repo, self.lobby)

        match event_type:
            case Event.START_GAME:
                await self.start_game()

            case Event.RESET_STEP:
                await self._run_runtime_events(
                    lambda: self.runtime.reset_current_step(self.lobby),
                    force_snapshot=True,
                )

            case Event.SHOW_ANSWER_REVEAL:
                await self._collect_player_drafts_before_close(reason="host_reveal")
                await self._run_runtime_events(
                    lambda: self.runtime.show_answer_reveal(self.lobby),
                )

            case Event.SHOW_QUESTION:
                await self._run_runtime_events(
                    lambda: self.runtime.show_question(self.lobby),
                )

            case Event.SHOW_PREVIOUS_REVEAL:
                await self._run_runtime_events(
                    lambda: self.runtime.show_previous_reveal(self.lobby),
                    relay_events=False,
                )

            case Event.SHOW_NEXT_REVEAL:
                await self._run_runtime_events(
                    lambda: self.runtime.show_next_reveal(self.lobby),
                    relay_events=False,
                )

            case Event.REVEAL_END_GAME:
                await self._run_runtime_events(
                    lambda: self.runtime.reveal_end_game(self.lobby),
                    relay_events=False,
                )

            case Event.ADVANCE_END_GAME_STAGE:
                await self._run_runtime_events(
                    lambda: self.runtime.advance_end_game_stage(self.lobby),
                    relay_events=False,
                )

            case Event.TOGGLE_END_GAME_AUTOPLAY:
                autoplay = schemas.ToggleEndGameAutoplayEvent.model_validate(data)
                await self._run_runtime_events(
                    lambda: self.runtime.toggle_end_game_autoplay(
                        self.lobby,
                        autoplay.enabled,
                    ),
                    relay_events=False,
                )

            case Event.SCOREBOARD_VISIBILITY:
                visibility = schemas.ScoreboardVisibilityEvent.model_validate(data)
                await self._run_runtime_events(
                    lambda: self.runtime.set_scoreboard_visibility(
                        self.lobby,
                        visibility.visible,
                    ),
                )

            case Event.MEDIA_PLAYBACK:
                playback = schemas.MediaPlaybackEvent.model_validate(data)
                await self._run_runtime_events(
                    lambda: self.runtime.set_media_playback(
                        self.lobby,
                        paused=playback.paused,
                        restart=playback.restart,
                        volume=playback.volume,
                    ),
                    relay_events=False,
                )

            case Event.STEP_ADVANCED:
                await self._run_runtime_events(
                    lambda: self.runtime.advance_step(self.lobby),
                    force_snapshot=True,
                    begin_round_intro=True,
                )

            case Event.CLOSE_STEP:
                await self._collect_player_drafts_before_close(reason="host_reveal")
                await self._run_runtime_events(
                    lambda: self.runtime.close_step(self.lobby),
                    force_snapshot=True,
                    begin_round_intro=True,
                )

            case Event.PLAYER_INPUT_SUBMITTED:
                payload = schemas.PlayerInputSubmittedEvent.model_validate(
                    data | {"player_id": data.get("player_id") or self.player.id}
                )
                before_snapshot = await self.runtime.build_snapshot(self.lobby)
                events, handled = await self.runtime.submit_player_input(
                    self.lobby,
                    payload.player_id,
                    payload.value,
                )
                await self._relay_non_snapshot_events(events)
                if handled:
                    await self._emit_runtime_state(before_snapshot, force_snapshot=False)
                else:
                    await self._send_submission_rejected(payload, before_snapshot)

            case Event.DRAWING_VOTE_SUBMITTED:
                payload = schemas.DrawingVoteSubmittedEvent.model_validate(
                    data | {"player_id": data.get("player_id") or self.player.id}
                )
                before_snapshot = await self.runtime.build_snapshot(self.lobby)
                events, handled = await self.runtime.submit_drawing_vote(
                    self.lobby,
                    payload.player_id,
                    payload.drawing_id,
                )
                await self._relay_non_snapshot_events(events)
                if handled:
                    await self._emit_runtime_state(before_snapshot, force_snapshot=False)

            case Event.BUZZER_STATE:
                buzzer_state = schemas.BuzzerStateEvent.model_validate(data)
                before_snapshot = await self.runtime.build_snapshot(self.lobby)
                events = await self.runtime.set_buzzer_state(self.lobby, buzzer_state.active)
                await self._relay_non_snapshot_events(events)
                await self._emit_runtime_state(before_snapshot, force_snapshot=False)

            case Event.UPDATE_SCORE:
                before_snapshot = await self.runtime.build_snapshot(self.lobby)
                update_score = await self.runtime.update_score(
                    self.lobby,
                    schemas.UpdateScoreEvent.model_validate(data),
                )
                await self.relay_event(update_score, exclude=update_score.player_id)
                await self._emit_runtime_state(before_snapshot, force_snapshot=False)

            case Event.REVIEW_SUBMISSION:
                before_snapshot = await self.runtime.build_snapshot(self.lobby)
                review_events = await self.runtime.review_submission(
                    self.lobby,
                    schemas.ReviewSubmissionEvent.model_validate(data),
                )
                for event in review_events:
                    exclude = None
                    if not isinstance(
                        event,
                        (schemas.AnswerJudgedEvent, schemas.BuzzerReviewedEvent),
                    ):
                        exclude = getattr(event, "player_id", None)
                    await self.relay_event(event, exclude=exclude)
                await self._emit_runtime_state(before_snapshot, force_snapshot=False)

            case Event.REVEALED_SUBMISSION:
                before_snapshot = await self.runtime.build_snapshot(self.lobby)
                player_id = (
                    data.get("submission", {}).get("player_id")
                    if data.get("submission")
                    else data.get("player_id")
                )
                reveal_event = await self.runtime.reveal_submission(self.lobby, player_id)
                await self.relay_event(reveal_event)
                await self._emit_runtime_state(before_snapshot, force_snapshot=False)

            case Event.SCORES_UPDATED:
                before_snapshot = await self.runtime.build_snapshot(self.lobby)
                for score_event in await self.runtime.evaluate_auto_step(self.lobby):
                    await self.relay_event(score_event)
                await self._emit_runtime_state(before_snapshot, force_snapshot=False)

    async def _send_submission_rejected(
        self,
        payload: schemas.PlayerInputSubmittedEvent,
        snapshot: schemas.RuntimeSnapshotEvent,
    ):
        event = schemas.SubmissionRejectedEvent(
            player_id=payload.player_id,
            reason=self._submission_rejection_reason(payload, snapshot),
        )
        if payload.player_id == self.player.id:
            await self.send(event)
            return
        await self.broadcast(event, players=[payload.player_id])

    def _submission_rejection_reason(
        self,
        payload: schemas.PlayerInputSubmittedEvent,
        snapshot: schemas.RuntimeSnapshotEvent,
    ) -> Literal[
        "invalid_drawing",
        "invalid_submission",
        "duplicate_submission",
        "step_closed",
    ]:
        if payload.player_id in snapshot.submitted_player_ids:
            return "duplicate_submission"
        if (
            snapshot.lobby.phase != "question_active"
            or snapshot.active_step is None
            or not snapshot.active_step.input_enabled
        ):
            return "step_closed"
        if snapshot.active_step.input_kind == schemas.PlayerInputKind.DRAWING:
            return "invalid_drawing"
        return "invalid_submission"

    async def _schedule_timer_from_snapshot(
        self, snapshot: schemas.RuntimeSnapshotEvent | None = None
    ):
        if self.timer_task is not None:
            self.timer_task.cancel()
            self.timer_task = None

        snapshot = snapshot or await self.runtime.build_snapshot(self.lobby)
        transition = await self.transition_scheduler.next_transition(
            lobby=self.lobby,
            snapshot=snapshot,
            runtime=self.runtime,
        )
        if transition is None:
            return

        if transition.kind == "round_intro":
            self.timer_task = asyncio.create_task(
                self._finish_round_intro(transition.delay_seconds)
            )
            return
        if transition.kind == "hostless_end_game_stage":
            self.timer_task = asyncio.create_task(
                self._advance_hostless_end_game_stage(transition.delay_seconds)
            )
            return
        if transition.kind == "hostless_answer_reveal":
            self.timer_task = asyncio.create_task(
                self._advance_hostless_reveal(transition.delay_seconds)
            )
            return
        if transition.kind == "timer_expired":
            self.timer_task = asyncio.create_task(self._expire_timer(transition.delay_seconds))

    async def _finish_round_intro(self, delay: float):
        await asyncio.sleep(delay)
        lobby = await self.repo.get_lobby_meta(self.lobby.id)
        if lobby is None:
            return
        self.lobby = lobby
        if self.lobby.phase != "round_intro":
            return
        before_snapshot = await self.runtime.build_snapshot(self.lobby)
        snapshot = await self.runtime.open_current_step_after_round_intro(self.lobby)
        if snapshot is None:
            return
        snapshot = await self._emit_runtime_state(before_snapshot, force_snapshot=True)
        await self.sync_host_runtime_state(snapshot)

    async def _advance_hostless_reveal(self, delay: float):
        await asyncio.sleep(delay)
        lobby = await self.repo.get_lobby_meta(self.lobby.id)
        if lobby is None:
            return
        self.lobby = lobby
        if self.lobby.phase != "step_complete":
            return
        current_step = await self.runtime.get_current_step(self.lobby)
        if current_step is None or not self.runtime.is_hostless_auto_progress_step(
            self.lobby, current_step
        ):
            return
        before_snapshot = await self.runtime.build_snapshot(self.lobby)
        events = await self.runtime.advance_step(self.lobby)
        for event in events:
            if not isinstance(event, schemas.RuntimeSnapshotEvent):
                await self.relay_event(event)
        after_snapshot = await self.runtime.build_snapshot(self.lobby)
        await self._begin_round_intro_if_needed(before_snapshot, after_snapshot)
        snapshot = await self._emit_runtime_state(before_snapshot, force_snapshot=True)
        await self.sync_host_runtime_state(snapshot)

    async def _advance_hostless_end_game_stage(self, delay: float):
        await asyncio.sleep(delay)
        lobby = await self.repo.get_lobby_meta(self.lobby.id)
        if lobby is None:
            return
        self.lobby = lobby
        if self.lobby.phase != "finished":
            return
        snapshot = await self.runtime.build_snapshot(self.lobby)
        end_game = snapshot.end_game
        if (
            end_game is None
            or not end_game.revealed
            or not end_game.autoplay_enabled
            or end_game.sequence_stage == "scoreboard"
        ):
            return
        before_snapshot = snapshot
        events = await self.runtime.advance_end_game_stage(self.lobby)
        for event in events:
            if not isinstance(event, schemas.RuntimeSnapshotEvent):
                await self.relay_event(event)
        snapshot = await self._emit_runtime_state(before_snapshot, force_snapshot=False)
        await self.sync_host_runtime_state(snapshot)

    async def _expire_timer(self, delay: float):
        await asyncio.sleep(delay)
        lobby = await self.repo.get_lobby_meta(self.lobby.id)
        if lobby is None:
            return
        self.lobby = lobby
        if self.lobby.phase != "question_active":
            return
        await self._collect_player_drafts_before_close(reason="timer_expired")
        if self.lobby.phase != "question_active":
            return
        before_snapshot = await self.runtime.build_snapshot(self.lobby)
        events = await self.runtime.close_step(self.lobby)
        for event in events:
            if not isinstance(event, schemas.RuntimeSnapshotEvent):
                await self.relay_event(event)
        after_snapshot = await self.runtime.build_snapshot(self.lobby)
        await self._begin_round_intro_if_needed(before_snapshot, after_snapshot)
        snapshot = await self._emit_runtime_state(before_snapshot, force_snapshot=True)
        await self.sync_host_runtime_state(snapshot)
