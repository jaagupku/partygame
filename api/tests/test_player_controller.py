from types import SimpleNamespace
from time import time

import pytest

from partygame import schemas
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
        self.created_player: schemas.Player | None = None
        self.set_lobby_calls: list[tuple[str, dict]] = []
        self.status_updates: list[tuple[str, str, schemas.ConnectionStatus]] = []
        self.applied_ttls: list[tuple[str, int]] = []
        self.connected_players = 0

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
        _is_information_slide=lambda step: True,
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
    assert called["process"] == ['{"type_": "player_input_submitted", "value": "ok"}']


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
        _is_hostless_auto_progress_step=lambda _lobby, _step: True,
    )

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
