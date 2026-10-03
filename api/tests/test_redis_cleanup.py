"""Exercise redis-py pool ownership; REDIS_CLEANUP_TEST_URL opts into real Valkey."""

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from redis.asyncio import ConnectionPool, Redis
from redis.asyncio.connection import Connection

from partygame import schemas
from partygame.api import deps
from partygame.api.api_v1.endpoints import game as endpoints
from partygame.service import realtime
from partygame.service.lobby import GameController
from partygame.service.player import ClientController
from tests.test_player_controller import FakeRepo, FakeWebSocket


class NoIOConnection(Connection):
    async def connect(self):
        pass

    async def send_command(self, *args, **kwargs):
        pass

    async def read_response(self, **kwargs):
        return "PONG"


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["display", "player"])
async def test_repeated_websocket_connections_return_pubsub_to_small_pool(
    kind, monkeypatch
):
    if url := os.environ.get("REDIS_CLEANUP_TEST_URL"):
        pool = ConnectionPool.from_url(url, max_connections=2)
    else:
        pool = ConnectionPool(connection_class=NoIOConnection, max_connections=2)
        # Keep actual pool accounting, PubSub subscription, close, and release code.
        monkeypatch.setattr(pool, "ensure_connection", AsyncMock())
    redis = Redis(connection_pool=pool)
    lobby = schemas.Lobby(id="cleanup", join_code="CLEAN", host_id="p1")
    player = schemas.Player(id="p1", game_id=lobby.id, name="Player")
    try:
        for _ in range(125):
            if kind == "display":
                controller = GameController(FakeWebSocket(), redis, lobby)
            else:
                controller = ClientController(FakeWebSocket(), redis, lobby, player)
                controller._schedule_timer_from_snapshot = AsyncMock()
            controller.repo = FakeRepo(lobby)
            controller.runtime = SimpleNamespace(sync_lobby=AsyncMock(return_value={}))
            controller.publish_websocket = asyncio.Event().wait
            await controller.connect()
            reader = controller.send_task
            subscription = controller.pubsub
            assert len(pool._in_use_connections) == 1
            await controller.disconnect()
            assert reader.done()
            assert subscription.connection is None
            assert not pool._in_use_connections
            assert (
                await redis.ping()
            )  # Scheduler/commands can immediately borrow again.
        assert not realtime.get_displays(lobby.id)
        assert not realtime.get_players(lobby.id)
    finally:
        await redis.aclose()
        await pool.aclose()


@pytest.mark.asyncio
async def test_player_releases_resources_before_failing_status_update(monkeypatch):
    lobby = schemas.Lobby(id="failed-cleanup", join_code="CLEAN")
    player = schemas.Player(id="p1", game_id=lobby.id, name="Player")
    controller = ClientController(FakeWebSocket(), AsyncMock(), lobby, player)
    controller.refresh_lobby = AsyncMock(side_effect=RuntimeError("Redis unavailable"))
    subscription = controller.pubsub = AsyncMock()
    controller.send_task = asyncio.create_task(asyncio.Event().wait())
    controller.timer_task = asyncio.create_task(asyncio.Event().wait())
    tasks = [controller.send_task, controller.timer_task]
    realtime.register_player(lobby.id, player.id, controller)
    with pytest.raises(RuntimeError, match="Redis unavailable"):
        await controller.disconnect()
    subscription.aclose.assert_awaited_once()
    assert all(task.done() for task in tasks)
    assert not realtime.get_players(lobby.id)
    assert controller.pubsub is None


@pytest.mark.asyncio
async def test_reader_stops_before_subscription_is_closed_even_if_reader_failed():
    stopped = asyncio.Event()

    async def reader():
        try:
            await asyncio.Event().wait()
        finally:
            stopped.set()
            raise RuntimeError("reader failed")

    async def close():
        assert stopped.is_set()

    subscription = SimpleNamespace(aclose=AsyncMock(side_effect=close))
    task = asyncio.create_task(reader())
    await asyncio.sleep(0)
    await realtime.close_subscription(subscription, task)
    subscription.aclose.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["display", "player"])
@pytest.mark.parametrize("cancelled", [False, True])
async def test_endpoint_cleans_up_partial_connect(kind, cancelled, monkeypatch):
    lobby = schemas.Lobby(id="g1", join_code="CLEAN")
    player = schemas.Player(id="p1", game_id=lobby.id, name="Player")
    controller = AsyncMock()
    controller.connect.side_effect = (
        asyncio.CancelledError() if cancelled else RuntimeError("sync failed")
    )
    monkeypatch.setattr(endpoints, "GameController", lambda *args, **kwargs: controller)
    monkeypatch.setattr(
        endpoints, "ClientController", lambda *args, **kwargs: controller
    )
    monkeypatch.setattr(endpoints.service.lobby, "get", AsyncMock(return_value=lobby))
    monkeypatch.setattr(endpoints.service.player, "get", AsyncMock(return_value=player))
    monkeypatch.setattr(
        endpoints,
        "GameStateRepository",
        lambda redis: SimpleNamespace(
            verify_connection_token=AsyncMock(return_value=True)
        ),
    )
    socket = AsyncMock()
    socket.cookies = {}
    call = (
        endpoints.game_websocket_host(socket, "g1", object())
        if kind == "display"
        else endpoints.game_websocket_controller(socket, "g1", "p1", object())
    )
    if cancelled:
        with pytest.raises(asyncio.CancelledError):
            await call
    else:
        await call
    controller.disconnect.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("cancelled", [False, True])
async def test_dependency_closes_client_when_request_raises(cancelled, monkeypatch):
    client = AsyncMock()
    monkeypatch.setattr(deps, "get_connection", lambda: client)
    dependency = deps.get_redis()
    assert await anext(dependency) is client
    error = asyncio.CancelledError if cancelled else RuntimeError
    with pytest.raises(error):
        await dependency.athrow(error())
    client.aclose.assert_awaited_once()
