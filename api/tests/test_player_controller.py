import asyncio
import json
from time import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from partygame import schemas
from partygame.service import lobby as lobby_service
from partygame.service import player as player_service
from partygame.state import GameKeyFactory


class DummyTask:
    def cancel(self):
        return None


class FakeWebSocket:
    def __init__(self):
        self.accepted = False
        self.messages: list[str] = []

    async def accept(self):
        self.accepted = True

    async def send_text(self, value: str):
        self.messages.append(value)

    async def send_json(self, value):
        self.messages.append(value)


class FakePubSub:
    def __init__(self):
        self.subscriptions: list[str] = []
        self.unsubscriptions: list[str] = []

    async def subscribe(self, *channels: str):
        self.subscriptions.extend(channels)

    async def unsubscribe(self, *channels: str):
        self.unsubscriptions.extend(channels)

    async def get_message(self, ignore_subscribe_messages=True, timeout=1):
        return None


class FakeRedis:
    def __init__(self, pubsub: FakePubSub):
        self._pubsub = pubsub

    def pubsub(self):
        return self._pubsub


class FakeRepo:
    def __init__(self, lobby: schemas.Lobby | None = None):
        self.lobby = lobby
        self.lock = asyncio.Lock()
        self.created_player: schemas.Player | None = None
        self.set_lobby_calls: list[tuple[str, dict]] = []
        self.status_updates: list[tuple[str, str, schemas.ConnectionStatus]] = []
        self.applied_ttls: list[tuple[str, int]] = []
        self.connected_players = 0
        self.players: list[schemas.Player] = []

    def mutation_lock(self, game_id):
        return self.lock

    async def create_player(self, player: schemas.Player):
        self.created_player = player

    async def get_lobby_meta(self, game_id: str):
        return self.lobby

    async def set_lobby_fields(self, game_id: str, **fields):
        self.set_lobby_calls.append((game_id, fields))

    async def set_player_status(
        self, game_id: str, player_id: str, status: schemas.ConnectionStatus
    ):
        self.status_updates.append((game_id, player_id, status))

    async def apply_game_ttl(self, game_id: str, ttl_seconds: int):
        self.applied_ttls.append((game_id, ttl_seconds))

    async def count_connected_players(self, game_id: str) -> int:
        return self.connected_players

    async def get_players(self, game_id: str) -> list[schemas.Player]:
        return [player for player in self.players if player.game_id == game_id]

    async def get_player(self, game_id: str, player_id: str):
        if self.created_player is not None and self.created_player.id == player_id:
            return self.created_player
        return None

    async def remove_player(self, game_id: str, player_id: str):
        if self.created_player is not None and self.created_player.id == player_id:
            self.created_player = None


@pytest.mark.asyncio
async def test_create_assigns_first_host_and_publishes_display_events(monkeypatch):
    lobby = schemas.Lobby(id="g1", join_code="ABCDE", host_enabled=True)
    repo = FakeRepo(lobby)
    published: list[tuple[str, object]] = []

    async def fake_publish(redis, channel, payload):
        published.append((channel, payload))

    monkeypatch.setattr(player_service, "GameStateRepository", lambda redis: repo)
    monkeypatch.setattr(player_service, "publish", fake_publish)

    player = await player_service.create(
        redis=object(),
        join_request=schemas.JoinRequest(
            join_code="ABCDE",
            player_name="Alice",
            avatar_kind="preset",
            avatar_preset_key="fox",
        ),
        game_id="g1",
    )

    assert repo.created_player == player
    assert player.avatar_kind == "preset"
    assert player.avatar_preset_key == "fox"
    assert repo.set_lobby_calls == [("g1", {"starter_id": player.id, "host_id": player.id})]
    assert repo.applied_ttls == [("g1", 3600)]
    assert published == [
        (
            GameKeyFactory.display_channel("g1"),
            schemas.PlayerJoinedEvent(player=player),
        ),
        (
            GameKeyFactory.display_channel("g1"),
            schemas.SetHostEvent(player_id=player.id),
        ),
        (
            GameKeyFactory.player_channel("g1", player.id),
            schemas.SetHostEvent(player_id=player.id),
        ),
    ]


@pytest.mark.asyncio
async def test_create_assigns_starter_without_host_in_hostless_lobby(monkeypatch):
    lobby = schemas.Lobby(id="g1", join_code="ABCDE", host_enabled=False)
    repo = FakeRepo(lobby)
    published: list[tuple[str, object]] = []

    async def fake_publish(redis, channel, payload):
        published.append((channel, payload))

    monkeypatch.setattr(player_service, "GameStateRepository", lambda redis: repo)
    monkeypatch.setattr(player_service, "publish", fake_publish)

    player = await player_service.create(
        redis=object(),
        join_request=schemas.JoinRequest(
            join_code="ABCDE",
            player_name="Alice",
            avatar_kind="preset",
            avatar_preset_key="fox",
        ),
        game_id="g1",
    )

    assert repo.created_player == player
    assert repo.set_lobby_calls == [("g1", {"starter_id": player.id})]
    assert published == [
        (
            GameKeyFactory.display_channel("g1"),
            schemas.PlayerJoinedEvent(player=player),
        )
    ]


@pytest.mark.asyncio
async def test_host_controller_subscribes_to_command_channel(monkeypatch):
    lobby = schemas.Lobby(id="g1", join_code="ABCDE", host_id="p1")
    player = schemas.Player(id="p1", game_id="g1", name="Host")
    pubsub = FakePubSub()
    redis = FakeRedis(pubsub)
    repo = FakeRepo(lobby)
    websocket = FakeWebSocket()
    published: list[tuple[str, object]] = []

    async def fake_publish(redis, channel, payload):
        published.append((channel, payload))

    snapshot = schemas.RuntimeSnapshotEvent(
        lobby=schemas.RuntimeLobbyState(
            id=lobby.id,
            join_code=lobby.join_code,
            host_enabled=lobby.host_enabled,
            host_id=lobby.host_id,
            state=lobby.state,
            phase=lobby.phase,
            current_step=lobby.current_step,
        )
    )

    def fake_create_task(coroutine):
        coroutine.close()
        return DummyTask()

    monkeypatch.setattr(player_service, "publish", fake_publish)
    monkeypatch.setattr(player_service.asyncio, "create_task", fake_create_task)

    controller = player_service.ClientController(websocket, redis, lobby, player)
    controller.repo = repo

    async def sync_lobby(_lobby):
        return snapshot

    async def submissions(_lobby):
        return schemas.SubmissionsUpdatedEvent()

    async def build_snapshot(_lobby):
        return snapshot

    controller.runtime = SimpleNamespace(
        sync_lobby=sync_lobby,
        build_submissions_event=submissions,
        build_snapshot=build_snapshot,
    )

    await controller.connect()

    assert websocket.accepted is True
    assert pubsub.subscriptions == [
        GameKeyFactory.player_channel("g1", "p1"),
        GameKeyFactory.host_channel("g1"),
    ]
    assert published == [
        (
            GameKeyFactory.display_channel("g1"),
            schemas.PlayerConnectedEvent(player_id="p1"),
        )
    ]
    assert repo.applied_ttls == [("g1", 3600)]


@pytest.mark.asyncio
async def test_host_processes_own_commands_without_command_channel_roundtrip(monkeypatch):
    lobby = schemas.Lobby(id="g1", join_code="ABCDE", host_id="p1")
    player = schemas.Player(id="p1", game_id="g1", name="Host")
    websocket = FakeWebSocket()
    controller = player_service.ClientController(
        websocket, redis=object(), lobby=lobby, player=player
    )

    called = {"refresh": 0, "process": []}

    async def refresh_lobby():
        called["refresh"] += 1

    async def process_controller(message: str):
        called["process"].append(message)

    async def fake_publish(redis, channel, payload):
        raise AssertionError("host commands should not be published to redis")

    monkeypatch.setattr(controller, "refresh_lobby", refresh_lobby)
    monkeypatch.setattr(controller, "process_controller", process_controller)
    monkeypatch.setattr(player_service, "publish", fake_publish)

    await controller.process_input({"type_": "start_game"})

    assert called["refresh"] == 1
    assert called["process"] == ['{"type_": "start_game"}']


@pytest.mark.asyncio
async def test_hostless_starter_processes_start_game_without_command_channel_roundtrip(
    monkeypatch,
):
    lobby = schemas.Lobby(id="g1", join_code="ABCDE", host_enabled=False, starter_id="p1")
    player = schemas.Player(id="p1", game_id="g1", name="Starter")
    websocket = FakeWebSocket()
    controller = player_service.ClientController(
        websocket, redis=object(), lobby=lobby, player=player
    )

    called = {"refresh": 0, "process": []}

    async def refresh_lobby():
        called["refresh"] += 1

    async def process_controller(message: str):
        called["process"].append(message)

    async def fake_publish(redis, channel, payload):
        raise AssertionError("hostless starter start commands should not be published to redis")

    monkeypatch.setattr(controller, "refresh_lobby", refresh_lobby)
    monkeypatch.setattr(controller, "process_controller", process_controller)
    monkeypatch.setattr(player_service, "publish", fake_publish)

    await controller.process_input({"type_": "start_game"})

    assert called["refresh"] == 1
    assert called["process"] == ['{"type_": "start_game"}']


@pytest.mark.asyncio
async def test_hostless_starter_processes_info_slide_controls_without_command_roundtrip(
    monkeypatch,
):
    lobby = schemas.Lobby(id="g1", join_code="ABCDE", host_enabled=False, starter_id="p1")
    player = schemas.Player(id="p1", game_id="g1", name="Starter")
    websocket = FakeWebSocket()
    controller = player_service.ClientController(
        websocket, redis=object(), lobby=lobby, player=player
    )

    called = {"refresh": 0, "process": []}

    async def refresh_lobby():
        called["refresh"] += 1

    async def process_controller(message: str):
        called["process"].append(message)

    async def get_current_step(_lobby):
        return SimpleNamespace(
            player_input=SimpleNamespace(kind="none"),
            evaluation=SimpleNamespace(type_="none"),
        )

    async def fake_publish(redis, channel, payload):
        raise AssertionError("hostless info-slide controls should not be published to redis")

    monkeypatch.setattr(controller, "refresh_lobby", refresh_lobby)
    monkeypatch.setattr(controller, "process_controller", process_controller)
    monkeypatch.setattr(player_service, "publish", fake_publish)
    controller.runtime = SimpleNamespace(
        get_current_step=get_current_step,
        is_information_slide=lambda step: True,
    )

    await controller.process_input({"type_": "close_step"})

    assert called["refresh"] == 1
    assert called["process"] == ['{"type_": "close_step"}']


@pytest.mark.asyncio
async def test_hostless_player_submission_processes_without_command_roundtrip(monkeypatch):
    lobby = schemas.Lobby(id="g1", join_code="ABCDE", host_enabled=False, starter_id="p1")
    player = schemas.Player(id="p2", game_id="g1", name="Player")
    websocket = FakeWebSocket()
    controller = player_service.ClientController(
        websocket, redis=object(), lobby=lobby, player=player
    )

    called = {"refresh": 0, "process": []}

    async def refresh_lobby():
        called["refresh"] += 1

    async def process_controller(message: str):
        called["process"].append(message)

    async def fake_publish(redis, channel, payload):
        raise AssertionError("hostless player submissions should not be published to redis")

    monkeypatch.setattr(controller, "refresh_lobby", refresh_lobby)
    monkeypatch.setattr(controller, "process_controller", process_controller)
    monkeypatch.setattr(player_service, "publish", fake_publish)

    await controller.process_input({"type_": "player_input_submitted", "value": "ok"})

    assert called["refresh"] == 1
    assert json.loads(called["process"][0]) == {
        "type_": "player_input_submitted",
        "value": "ok",
        "player_id": "p2",
    }


@pytest.mark.asyncio
async def test_rejected_player_submission_sends_targeted_feedback(monkeypatch):
    lobby = schemas.Lobby(
        id="g1",
        join_code="ABCDE",
        host_id="host",
        phase="question_active",
    )
    host = schemas.Player(id="host", game_id="g1", name="Host")
    controller = player_service.ClientController(
        FakeWebSocket(), redis=object(), lobby=lobby, player=host
    )
    controller.repo = FakeRepo(lobby)
    snapshot = schemas.RuntimeSnapshotEvent(
        lobby=schemas.RuntimeLobbyState(
            id=lobby.id,
            join_code=lobby.join_code,
            host_enabled=lobby.host_enabled,
            host_id=lobby.host_id,
            state=lobby.state,
            phase=lobby.phase,
            current_step=lobby.current_step,
        ),
        active_step=schemas.RuntimeStepState(
            id="drawing",
            title="Draw",
            input_enabled=True,
            input_kind=schemas.PlayerInputKind.DRAWING,
        ),
    )
    called = {"broadcasts": []}

    async def build_snapshot(_lobby):
        return snapshot

    async def submit_player_input(_lobby, _player_id, _value):
        return [], False

    async def broadcast(event, players=None, exclude=None):
        called["broadcasts"].append((event, players, exclude))

    async def relay_event(_event, players=None, exclude=None):
        raise AssertionError("rejected submissions should not be relayed broadly")

    async def emit_runtime_state(_before_snapshot, force_snapshot=False):
        raise AssertionError("rejected submissions should not emit runtime state")

    controller.runtime = SimpleNamespace(
        build_snapshot=build_snapshot,
        submit_player_input=submit_player_input,
    )
    monkeypatch.setattr(controller, "broadcast", broadcast)
    monkeypatch.setattr(controller, "relay_event", relay_event)
    monkeypatch.setattr(controller, "_emit_runtime_state", emit_runtime_state)

    await controller.process_controller(
        '{"type_": "player_input_submitted", "player_id": "p2", "value": {}}'
    )

    assert len(called["broadcasts"]) == 1
    event, players, exclude = called["broadcasts"][0]
    assert event == schemas.SubmissionRejectedEvent(player_id="p2", reason="invalid_drawing")
    assert players == ["p2"]
    assert exclude is None


@pytest.mark.asyncio
async def test_player_reaction_relays_without_runtime_snapshot(monkeypatch):
    lobby = schemas.Lobby(
        id="g1",
        join_code="ABCDE",
        host_id="p1",
        state=schemas.GameState.RUNNING,
        phase="question_active",
    )
    player = schemas.Player(id="p2", game_id="g1", name="Player")
    controller = player_service.ClientController(
        FakeWebSocket(), redis=object(), lobby=lobby, player=player
    )

    called = {"refresh": 0, "relayed": []}

    async def refresh_lobby():
        called["refresh"] += 1

    async def relay_event(event, players=None, exclude=None):
        called["relayed"].append((event, players, exclude))

    async def record_player_reaction(lobby, player_id, reaction):
        called["recorded"] = (lobby.id, player_id, reaction)

    controller.runtime = SimpleNamespace(
        build_snapshot=lambda _lobby: (_ for _ in ()).throw(
            AssertionError("runtime snapshot not expected")
        ),
        record_player_reaction=record_player_reaction,
    )
    monkeypatch.setattr(controller, "refresh_lobby", refresh_lobby)
    monkeypatch.setattr(controller, "relay_event", relay_event)

    await controller.process_input({"type_": "player_reaction", "reaction": "🔥"})

    assert called["refresh"] == 1
    assert len(called["relayed"]) == 1
    event, _players, _exclude = called["relayed"][0]
    assert event.type_ == "player_reaction"
    assert event.player_id == "p2"
    assert event.reaction == "🔥"
    assert event.instance_id
    assert called["recorded"] == ("g1", "p2", "🔥")


@pytest.mark.asyncio
async def test_finished_player_reaction_relays_through_runtime_guard(monkeypatch):
    lobby = schemas.Lobby(
        id="g1",
        join_code="ABCDE",
        host_id="p1",
        state=schemas.GameState.RUNNING,
        phase="finished",
    )
    player = schemas.Player(id="p2", game_id="g1", name="Player")
    controller = player_service.ClientController(
        FakeWebSocket(), redis=object(), lobby=lobby, player=player
    )

    called = {"refresh": 0, "relayed": 0, "recorded": 0}

    async def refresh_lobby():
        called["refresh"] += 1

    async def relay_event(event, players=None, exclude=None):
        called["relayed"] += 1

    async def record_player_reaction(lobby, player_id, reaction):
        called["recorded"] += 1

    controller.runtime = SimpleNamespace(record_player_reaction=record_player_reaction)
    monkeypatch.setattr(controller, "refresh_lobby", refresh_lobby)
    monkeypatch.setattr(controller, "relay_event", relay_event)

    await controller.process_input({"type_": "player_reaction", "reaction": "🤮"})

    assert called == {"refresh": 1, "relayed": 1, "recorded": 1}


@pytest.mark.asyncio
async def test_invalid_player_reaction_is_dropped(monkeypatch):
    lobby = schemas.Lobby(
        id="g1",
        join_code="ABCDE",
        state=schemas.GameState.RUNNING,
        phase="question_active",
    )
    player = schemas.Player(id="p2", game_id="g1", name="Player")
    controller = player_service.ClientController(
        FakeWebSocket(), redis=object(), lobby=lobby, player=player
    )

    called = {"refresh": 0, "relayed": 0}

    async def refresh_lobby():
        called["refresh"] += 1

    async def relay_event(_event, players=None, exclude=None):
        called["relayed"] += 1

    monkeypatch.setattr(controller, "refresh_lobby", refresh_lobby)
    monkeypatch.setattr(controller, "relay_event", relay_event)

    await controller.process_input({"type_": "player_reaction", "reaction": "NOPE"})

    assert called == {"refresh": 1, "relayed": 0}


@pytest.mark.asyncio
async def test_throttled_player_reaction_is_dropped(monkeypatch):
    lobby = schemas.Lobby(
        id="g1",
        join_code="ABCDE",
        state=schemas.GameState.RUNNING,
        phase="question_active",
    )
    player = schemas.Player(id="p2", game_id="g1", name="Player")
    controller = player_service.ClientController(
        FakeWebSocket(), redis=object(), lobby=lobby, player=player
    )

    called = {"refresh": 0, "relayed": 0}

    async def refresh_lobby():
        called["refresh"] += 1

    async def relay_event(_event, players=None, exclude=None):
        called["relayed"] += 1

    monkeypatch.setattr(controller, "refresh_lobby", refresh_lobby)
    monkeypatch.setattr(controller, "relay_event", relay_event)

    now = time()
    for _ in range(player_service.PLAYER_REACTION_BURST_LIMIT):
        controller.reaction_timestamps.append(now)

    await controller.process_input({"type_": "player_reaction", "reaction": "🤮"})

    assert called == {"refresh": 1, "relayed": 0}


@pytest.mark.asyncio
async def test_resync_request_sends_full_snapshot_without_command_roundtrip(monkeypatch):
    lobby = schemas.Lobby(id="g1", join_code="ABCDE", host_id="p1")
    player = schemas.Player(id="p1", game_id="g1", name="Host")
    websocket = FakeWebSocket()
    controller = player_service.ClientController(
        websocket, redis=object(), lobby=lobby, player=player
    )

    snapshot = schemas.RuntimeSnapshotEvent(
        revision=3,
        lobby=schemas.RuntimeLobbyState(
            id=lobby.id,
            join_code=lobby.join_code,
            host_enabled=lobby.host_enabled,
            host_id=lobby.host_id,
            state=lobby.state,
            phase=lobby.phase,
            current_step=lobby.current_step,
        ),
    )

    called = {"refresh": 0, "scheduled": 0}

    async def refresh_lobby():
        called["refresh"] += 1

    async def sync_lobby(_lobby):
        return snapshot

    async def schedule(_snapshot=None):
        called["scheduled"] += 1

    monkeypatch.setattr(controller, "refresh_lobby", refresh_lobby)
    monkeypatch.setattr(controller, "_schedule_timer_from_snapshot", schedule)
    controller.runtime = SimpleNamespace(sync_lobby=sync_lobby)

    await controller.process_input({"type_": "resync_request"})

    assert called["refresh"] == 1
    assert called["scheduled"] == 1
    assert websocket.messages == [snapshot.model_dump_json()]


@pytest.mark.asyncio
async def test_display_resync_refreshes_lobby_before_snapshot():
    stale_lobby = schemas.Lobby(id="g1", join_code="ABCDE")
    fresh_lobby = schemas.Lobby(
        id="g1",
        join_code="ABCDE",
        state=schemas.GameState.RUNNING,
        phase="question_active",
    )
    websocket = FakeWebSocket()
    controller = lobby_service.GameController(websocket, redis=object(), lobby=stale_lobby)
    controller.repo = FakeRepo(fresh_lobby)

    async def sync_lobby(lobby):
        return schemas.RuntimeSnapshotEvent(
            revision=4,
            lobby=schemas.RuntimeLobbyState(
                id=lobby.id,
                join_code=lobby.join_code,
                host_enabled=lobby.host_enabled,
                host_id=lobby.host_id,
                state=lobby.state,
                phase=lobby.phase,
                current_step=lobby.current_step,
            ),
        )

    controller.runtime = SimpleNamespace(sync_lobby=sync_lobby)

    await controller.process_input({"type_": "resync_request"})

    assert controller.lobby.state == schemas.GameState.RUNNING
    assert controller.lobby.phase == "question_active"
    assert len(websocket.messages) == 1
    snapshot = schemas.RuntimeSnapshotEvent.model_validate_json(websocket.messages[0])
    assert snapshot.lobby.state == schemas.GameState.RUNNING
    assert snapshot.lobby.phase == "question_active"


@pytest.mark.asyncio
async def test_hostless_advisory_timer_is_scheduled(monkeypatch):
    lobby = schemas.Lobby(
        id="g1",
        join_code="ABCDE",
        host_enabled=False,
        starter_id="p1",
        phase="question_active",
    )
    player = schemas.Player(id="p1", game_id="g1", name="Starter")
    controller = player_service.ClientController(
        FakeWebSocket(), redis=object(), lobby=lobby, player=player
    )

    snapshot = schemas.RuntimeSnapshotEvent(
        lobby=schemas.RuntimeLobbyState(
            id=lobby.id,
            join_code=lobby.join_code,
            host_enabled=lobby.host_enabled,
            starter_id=lobby.starter_id,
            state=lobby.state,
            phase="question_active",
            current_step=lobby.current_step,
        ),
        active_step=schemas.RuntimeStepState(
            id="step1",
            title="Question",
            evaluation_type="exact_text",
            evaluation_points=1,
            input_enabled=True,
            input_kind="text",
            input_options=[],
            timer=schemas.RuntimeTimerState(
                seconds=30,
                enforced=False,
                started_at=1.0,
                ends_at=time() + 30,
                remaining_seconds=30,
            ),
        ),
    )

    async def get_current_step(_lobby):
        return SimpleNamespace(id="step1")

    created = {"count": 0}

    def fake_create_task(coroutine):
        created["count"] += 1
        coroutine.close()
        return DummyTask()

    monkeypatch.setattr(player_service.asyncio, "create_task", fake_create_task)
    controller.runtime = SimpleNamespace(
        get_current_step=get_current_step,
        is_hostless_auto_progress_step=lambda _lobby, _step: True,
    )

    await controller._schedule_timer_from_snapshot(snapshot)

    assert created["count"] == 1


@pytest.mark.asyncio
async def test_round_intro_timer_is_scheduled(monkeypatch):
    lobby = schemas.Lobby(
        id="g1",
        join_code="ABCDE",
        host_enabled=True,
        phase="round_intro",
    )
    player = schemas.Player(id="p1", game_id="g1", name="Host")
    controller = player_service.ClientController(
        FakeWebSocket(), redis=object(), lobby=lobby, player=player
    )

    snapshot = schemas.RuntimeSnapshotEvent(
        lobby=schemas.RuntimeLobbyState(
            id=lobby.id,
            join_code=lobby.join_code,
            host_enabled=lobby.host_enabled,
            state=lobby.state,
            phase="round_intro",
            current_step=lobby.current_step,
        ),
        active_round=schemas.RuntimeRoundState(
            id="round1",
            title="Round One",
            number=1,
            total=2,
        ),
        active_item=schemas.RuntimeRoundIntroItemState(
            round=schemas.RuntimeRoundState(
                id="round1",
                title="Round One",
                number=1,
                total=2,
            ),
            duration_seconds=5.0,
        ),
    )

    created = {"count": 0}

    def fake_create_task(coroutine):
        created["count"] += 1
        coroutine.close()
        return DummyTask()

    monkeypatch.setattr(player_service.asyncio, "create_task", fake_create_task)

    await controller._schedule_timer_from_snapshot(snapshot)

    assert created["count"] == 1


@pytest.mark.asyncio
async def test_hostless_end_game_autoplay_is_scheduled(monkeypatch):
    lobby = schemas.Lobby(
        id="g1",
        join_code="ABCDE",
        host_enabled=False,
        starter_id="p1",
        phase="finished",
    )
    player = schemas.Player(id="p1", game_id="g1", name="Starter")
    controller = player_service.ClientController(
        FakeWebSocket(), redis=object(), lobby=lobby, player=player
    )

    snapshot = schemas.RuntimeSnapshotEvent(
        lobby=schemas.RuntimeLobbyState(
            id=lobby.id,
            join_code=lobby.join_code,
            host_enabled=lobby.host_enabled,
            starter_id=lobby.starter_id,
            state=lobby.state,
            phase="finished",
            current_step=lobby.current_step,
        ),
        end_game=schemas.EndGameState(
            revealed=True,
            autoplay_enabled=True,
            sequence_stage="third_place",
        ),
    )

    created = {"count": 0}

    def fake_create_task(coroutine):
        created["count"] += 1
        coroutine.close()
        return DummyTask()

    monkeypatch.setattr(player_service.asyncio, "create_task", fake_create_task)

    await controller._schedule_timer_from_snapshot(snapshot)

    assert created["count"] == 1


@pytest.mark.asyncio
async def test_collect_player_drafts_broadcasts_to_unsubmitted_players(monkeypatch):
    lobby = schemas.Lobby(
        id="g1",
        join_code="ABCDE",
        host_id="host",
        phase="question_active",
    )
    player = schemas.Player(id="host", game_id="g1", name="Host")
    controller = player_service.ClientController(
        FakeWebSocket(), redis=object(), lobby=lobby, player=player
    )
    repo = FakeRepo(lobby)
    repo.players = [
        player,
        schemas.Player(id="p1", game_id="g1", name="Alice"),
        schemas.Player(id="p2", game_id="g1", name="Bob"),
    ]
    controller.repo = repo
    published: list[tuple[str, object]] = []

    async def fake_publish(redis, channel, payload):
        published.append((channel, payload))

    async def fake_sleep(delay):
        assert delay == player_service.DRAFT_COLLECTION_GRACE_SECONDS

    monkeypatch.setattr(player_service, "publish", fake_publish)
    monkeypatch.setattr(player_service.asyncio, "sleep", fake_sleep)

    async def get_current_step(_lobby):
        return SimpleNamespace(
            id="step1",
            player_input=SimpleNamespace(kind=schemas.PlayerInputKind.TEXT),
        )

    async def get_step_state(_game_id):
        return {"answers": {"p2": "done"}}

    controller.runtime = SimpleNamespace(
        get_current_step=get_current_step,
        get_step_state=get_step_state,
    )

    collected = await controller._collect_player_drafts_before_close(reason="host_reveal")

    assert collected is True
    assert len(published) == 1
    channel, event = published[0]
    assert channel == GameKeyFactory.player_channel("g1", "p1")
    assert isinstance(event, schemas.CollectPlayerDraftsEvent)
    assert event.step_id == "step1"
    assert event.reason == "host_reveal"


@pytest.mark.asyncio
async def test_collect_player_drafts_sends_to_local_hostless_player(monkeypatch):
    lobby = schemas.Lobby(
        id="g1",
        join_code="ABCDE",
        host_enabled=False,
        starter_id="p1",
        phase="question_active",
    )
    player = schemas.Player(id="p1", game_id="g1", name="Starter")
    websocket = FakeWebSocket()
    controller = player_service.ClientController(
        websocket, redis=object(), lobby=lobby, player=player
    )
    repo = FakeRepo(lobby)
    repo.players = [
        player,
        schemas.Player(id="p2", game_id="g1", name="Bob"),
    ]
    controller.repo = repo
    published: list[tuple[str, object]] = []

    async def fake_publish(redis, channel, payload):
        published.append((channel, payload))

    async def fake_sleep(delay):
        assert delay == player_service.DRAFT_COLLECTION_GRACE_SECONDS

    monkeypatch.setattr(player_service, "publish", fake_publish)
    monkeypatch.setattr(player_service.asyncio, "sleep", fake_sleep)

    async def get_current_step(_lobby):
        return SimpleNamespace(
            id="step1",
            player_input=SimpleNamespace(kind=schemas.PlayerInputKind.TEXT),
        )

    async def get_step_state(_game_id):
        return {"answers": {}}

    controller.runtime = SimpleNamespace(
        get_current_step=get_current_step,
        get_step_state=get_step_state,
    )

    collected = await controller._collect_player_drafts_before_close(reason="timer_expired")

    assert collected is True
    assert len(websocket.messages) == 1
    local_event = schemas.CollectPlayerDraftsEvent.model_validate_json(websocket.messages[0])
    assert local_event.step_id == "step1"
    assert local_event.reason == "timer_expired"
    assert published == [
        (
            GameKeyFactory.player_channel("g1", "p2"),
            schemas.CollectPlayerDraftsEvent(step_id="step1", reason="timer_expired"),
        )
    ]


@pytest.mark.asyncio
async def test_remove_deletes_custom_avatar_asset(monkeypatch):
    lobby = schemas.Lobby(id="g1", join_code="ABCDE")
    repo = FakeRepo(lobby)
    repo.created_player = schemas.Player(
        id="p1",
        game_id="g1",
        name="Alice",
        avatar_kind="custom",
        avatar_url="/api/v1/media/a1",
        avatar_asset_id="a1",
    )
    deleted_assets: list[str] = []

    class FakeStorage:
        async def delete(self, asset_id: str):
            deleted_assets.append(asset_id)

    monkeypatch.setattr(player_service, "GameStateRepository", lambda redis: repo)
    monkeypatch.setattr(player_service, "get_media_storage", lambda: FakeStorage())

    await player_service.remove(redis=object(), lobby_id="g1", player_id="p1")

    assert deleted_assets == ["a1"]
    assert repo.created_player is None


@pytest.mark.asyncio
async def test_disconnect_refreshes_idle_ttl_when_last_player_leaves(monkeypatch):
    lobby = schemas.Lobby(id="g1", join_code="ABCDE", host_id="p1")
    player = schemas.Player(id="p1", game_id="g1", name="Host")
    websocket = FakeWebSocket()
    repo = FakeRepo(lobby)
    published: list[tuple[str, object]] = []

    async def fake_publish(redis, channel, payload):
        published.append((channel, payload))

    controller = player_service.ClientController(
        websocket, redis=object(), lobby=lobby, player=player
    )
    controller.repo = repo
    repo.connected_players = 0

    monkeypatch.setattr(player_service, "publish", fake_publish)

    await controller.disconnect()

    assert repo.status_updates == [("g1", "p1", schemas.ConnectionStatus.DISCONNECTED)]
    assert repo.applied_ttls == [("g1", 3600)]
    assert published == [
        (
            GameKeyFactory.display_channel("g1"),
            schemas.PlayerDisconnectedEvent(player_id="p1"),
        )
    ]


@pytest.mark.asyncio
async def test_finished_lobby_does_not_refresh_idle_ttl_on_connect_or_command(monkeypatch):
    lobby = schemas.Lobby(id="g1", join_code="ABCDE", host_id="p1", phase="finished")
    player = schemas.Player(id="p1", game_id="g1", name="Host")
    pubsub = FakePubSub()
    redis = FakeRedis(pubsub)
    repo = FakeRepo(lobby)
    websocket = FakeWebSocket()

    snapshot = schemas.RuntimeSnapshotEvent(
        lobby=schemas.RuntimeLobbyState(
            id=lobby.id,
            join_code=lobby.join_code,
            host_enabled=lobby.host_enabled,
            host_id=lobby.host_id,
            state=lobby.state,
            phase=lobby.phase,
            current_step=lobby.current_step,
        )
    )

    def fake_create_task(coroutine):
        coroutine.close()
        return DummyTask()

    async def sync_lobby(_lobby):
        return snapshot

    async def submissions(_lobby):
        return schemas.SubmissionsUpdatedEvent()

    async def build_snapshot(_lobby):
        return snapshot

    async def fake_publish(redis, channel, payload):
        return None

    monkeypatch.setattr(player_service, "publish", fake_publish)
    monkeypatch.setattr(player_service.asyncio, "create_task", fake_create_task)

    controller = player_service.ClientController(websocket, redis, lobby, player)
    controller.repo = repo
    controller.runtime = SimpleNamespace(
        sync_lobby=sync_lobby,
        build_submissions_event=submissions,
        build_snapshot=build_snapshot,
    )

    await controller.connect()

    async def fake_process_controller(_message: str):
        return None

    monkeypatch.setattr(controller, "process_controller", fake_process_controller)
    await controller.process_input({"type_": "start_game"})

    assert repo.applied_ttls == []


def test_start_game_event_is_exported_from_schemas():
    assert schemas.StartGameEvent().type_ == "start_game"


def test_player_reaction_event_is_exported_from_schemas():
    assert (
        schemas.PlayerReactionEvent(
            player_id="p1",
            reaction="😂",
            instance_id="reaction-1",
            emitted_at=1.0,
        ).type_
        == "player_reaction"
    )


def test_runtime_patch_redacts_host_only_fields_for_public_view():
    lobby = schemas.Lobby(id="g1", join_code="ABCDE", host_id="p1")
    player = schemas.Player(id="p1", game_id="g1", name="Host")
    controller = player_service.ClientController(
        FakeWebSocket(), redis=object(), lobby=lobby, player=player
    )

    before_snapshot = schemas.RuntimeSnapshotEvent(
        revision=1,
        lobby=schemas.RuntimeLobbyState(
            id=lobby.id,
            join_code=lobby.join_code,
            host_enabled=lobby.host_enabled,
            host_id=lobby.host_id,
            state=lobby.state,
            phase=lobby.phase,
            current_step=lobby.current_step,
        ),
        submissions=[],
    )
    after_snapshot = before_snapshot.model_copy(
        update={
            "revision": 2,
            "host_answer": schemas.RevealedAnswer(value="correct"),
            "submissions": [schemas.SubmissionItem(player_id="p2", value="buzz", reviewed=False)],
        }
    )

    host_patch = controller._patch_for_viewer(
        before_snapshot, after_snapshot, include_host_answer=True
    )
    public_patch = controller._patch_for_viewer(
        before_snapshot, after_snapshot, include_host_answer=False
    )

    assert host_patch is not None
    assert host_patch.changes["host_answer"] == {"value": "correct"}
    assert host_patch.changes["submissions"] == [
        {"player_id": "p2", "value": "buzz", "reviewed": False}
    ]
    assert public_patch is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "event",
    [
        "start_game",
        "update_score",
        "reset_step",
        "show_answer_reveal",
        "step_advanced",
        "review_submission",
    ],
)
async def test_ordinary_players_cannot_forward_host_commands(monkeypatch, event):
    lobby = schemas.Lobby(id="g1", join_code="ABCDE", host_id="host")
    controller = player_service.ClientController(
        FakeWebSocket(), object(), lobby, schemas.Player(id="p1", game_id="g1", name="Player")
    )
    controller.refresh_lobby = AsyncMock()
    controller.process_controller = AsyncMock()
    publish = AsyncMock()
    monkeypatch.setattr(player_service, "publish", publish)
    await controller.process_input({"type_": event, "player_id": "p1", "set_score": 999})
    publish.assert_not_awaited()
    controller.process_controller.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("hosted", [True, False])
@pytest.mark.parametrize("event", ["player_input_submitted", "drawing_vote_submitted"])
async def test_submission_identity_always_comes_from_connection(monkeypatch, hosted, event):
    lobby = schemas.Lobby(
        id="g1", join_code="ABCDE", host_enabled=hosted, host_id="host" if hosted else None
    )
    controller = player_service.ClientController(
        FakeWebSocket(), object(), lobby, schemas.Player(id="p1", game_id="g1", name="Player")
    )
    controller.refresh_lobby = AsyncMock()
    controller.process_controller = AsyncMock()
    publish = AsyncMock()
    monkeypatch.setattr(player_service, "publish", publish)
    await controller.process_input(
        {"type_": event, "player_id": "victim", "value": "answer", "drawing_id": "drawing:0"}
    )
    payload = (
        publish.call_args.args[2]
        if hosted
        else json.loads(controller.process_controller.call_args.args[0])
    )
    assert payload["player_id"] == "p1"


@pytest.mark.asyncio
async def test_lobby_host_transfer_moves_command_subscription():
    lobby = schemas.Lobby(id="g1", join_code="ABCDE", host_id="old")
    repo = FakeRepo(lobby)
    controllers = []
    for player_id in ["old", "new"]:
        controller = player_service.ClientController(
            FakeWebSocket(),
            object(),
            lobby.model_copy(),
            schemas.Player(id=player_id, game_id="g1", name=player_id),
        )
        controller.repo = repo
        controller.pubsub = FakePubSub()
        await controller.refresh_lobby()
        controllers.append(controller)
    lobby.host_id = "new"
    for controller in controllers:
        await controller.refresh_lobby()
    old, new = controllers
    assert old.command_channel in old.pubsub.unsubscriptions
    assert not old.command_subscribed
    assert new.command_channel in new.pubsub.subscriptions
    assert new.command_subscribed


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "state,can_manage,host_enabled,exists,allowed",
    [
        ("waiting_for_players", True, True, True, True),
        ("running", True, True, True, False),
        ("paused", True, True, True, False),
        ("waiting_for_players", False, True, True, False),
        ("waiting_for_players", True, False, True, False),
        ("waiting_for_players", True, True, False, False),
    ],
)
async def test_host_selection_is_owned_and_lobby_only(
    state, can_manage, host_enabled, exists, allowed
):
    persisted = schemas.Lobby(
        id="g1", join_code="ABCDE", state=state, host_enabled=host_enabled, host_id="old"
    )
    stale = persisted.model_copy(update={"state": schemas.GameState.WAITING_FOR_PLAYERS})
    controller = lobby_service.GameController(
        FakeWebSocket(), object(), stale, can_manage=can_manage
    )
    controller.repo = FakeRepo(persisted)
    controller.repo.get_player = AsyncMock(
        return_value=schemas.Player(id="new", game_id="g1", name="New") if exists else None
    )
    controller._set_host = AsyncMock()
    await controller.set_host(schemas.SetHostEvent(player_id="new"))
    assert controller._set_host.await_count == int(allowed)


@pytest.mark.asyncio
async def test_concurrent_hostless_submissions_keep_both_answers(monkeypatch):
    import copy

    from partygame.service.game import GameRuntimeService
    from tests.test_game_runtime import FakeRepo as RuntimeRepo

    class Repo(RuntimeRepo):
        def __init__(self):
            super().__init__()
            self.lock = asyncio.Lock()
            self.lobby = schemas.Lobby(id="g1", join_code="ABCDE", host_enabled=False)

        def mutation_lock(self, game_id):
            return self.lock

        async def get_lobby_meta(self, game_id):
            return self.lobby.model_copy()

        async def set_lobby_fields(self, game_id, **fields):
            await super().set_lobby_fields(game_id, **fields)
            self.lobby = self.lobby.model_copy(update=fields)

        async def get_step_cache(self, game_id):
            state = copy.deepcopy(await super().get_step_cache(game_id))
            await asyncio.sleep(0)
            return state

    repo = Repo()
    provider = AsyncMock()
    provider.load.return_value = schemas.GameDefinition(
        id="test",
        title="Test",
        rounds=[
            schemas.RoundDefinition(
                id="r",
                steps=[
                    schemas.StepDefinition(
                        id="s",
                        title="Question",
                        player_input=schemas.PlayerInputDefinition(kind="text"),
                        evaluation=schemas.EvaluationRule(
                            type_="exact_text", answer="yes", points=1
                        ),
                    )
                ],
            )
        ],
    )
    runtime = GameRuntimeService(repo, definition_provider=provider, archive_game_stats=False)
    await runtime.start_game(repo.lobby)
    controllers = []
    for player_id in ["p1", "p2"]:
        controller = player_service.ClientController(
            FakeWebSocket(),
            object(),
            repo.lobby.model_copy(),
            schemas.Player(id=player_id, game_id="g1", name=player_id),
        )
        controller.repo = repo
        controller.runtime = GameRuntimeService(
            repo, definition_provider=provider, archive_game_stats=False
        )
        controller._relay_non_snapshot_events = AsyncMock()
        controller._emit_runtime_state = AsyncMock()
        controllers.append(controller)
    await asyncio.gather(
        *(c.process_input({"type_": "player_input_submitted", "value": "yes"}) for c in controllers)
    )
    state = await repo.get_step_cache("g1")
    assert state["answers"] == {"p1": "yes", "p2": "yes"}
    assert repo.scores == {"p1": 1, "p2": 6}
    assert state["evaluated"] is True


@pytest.mark.asyncio
async def test_hostless_controller_patch_does_not_expose_host_answer():
    lobby = schemas.Lobby(id="g1", join_code="ABCDE", host_enabled=False)
    controller = player_service.ClientController(
        FakeWebSocket(), object(), lobby, schemas.Player(id="p1", game_id="g1", name="Player")
    )
    before = schemas.RuntimeSnapshotEvent(
        lobby=schemas.RuntimeLobbyState(
            id="g1",
            join_code="ABCDE",
            host_enabled=False,
            state="running",
            phase="question_active",
            current_step=0,
        )
    )
    after = before.model_copy(
        update={"revision": 1, "host_answer": schemas.RevealedAnswer(value="secret")}
    )
    controller.send = AsyncMock()
    controller._broadcast_runtime_patch = AsyncMock()
    await controller._send_runtime_patch(before, after)
    controller.send.assert_not_awaited()
