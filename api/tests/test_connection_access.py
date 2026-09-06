from unittest.mock import AsyncMock

import pytest
from fastapi import Request, Response

from partygame import schemas
from partygame.api.api_v1.endpoints import game as endpoints
from partygame.service.connection_access import connection_cookie_name, set_connection_cookie
from partygame.state import GameStateRepository
from tests.test_state_repo_cleanup import FakeRedis


@pytest.mark.asyncio
async def test_tokens_are_scoped_to_game_player_and_role():
    redis = FakeRedis()
    repo = GameStateRepository(redis)
    await repo.create_lobby(schemas.Lobby(id="g1", join_code="ABCDE"))
    await repo.create_player(schemas.Player(id="p1", game_id="g1", name="One"))
    display = await repo.issue_connection_token("g1")
    player = await repo.issue_connection_token("g1", "p1")
    assert await repo.verify_connection_token("g1", display)
    assert await repo.verify_connection_token("g1", player, "p1")
    assert not await repo.verify_connection_token("g1", player)
    assert not await repo.verify_connection_token("g1", display, "p1")
    assert not await repo.verify_connection_token("g1", player, "p2")
    assert not await repo.verify_connection_token("g2", player, "p1")
    assert display not in (await repo.get_lobby_meta("g1")).model_dump_json()
    assert player not in (await repo.get_player("g1", "p1")).model_dump_json()


@pytest.mark.asyncio
async def test_websocket_rejects_public_ids_without_cookie(monkeypatch):
    socket = AsyncMock()
    socket.cookies = {}
    get_player = AsyncMock()
    monkeypatch.setattr(endpoints.service.player, "get", get_player)
    await endpoints.game_websocket_controller(socket, "g1", "p1", FakeRedis())
    socket.close.assert_awaited_once_with(code=1008)
    get_player.assert_not_awaited()


def test_https_cookie_is_secure_and_http_only():
    response = Response()
    request = Request(
        {"type": "http", "scheme": "https", "path": "/", "headers": [(b"host", b"localhost")]}
    )
    set_connection_cookie(response, request, "g1", "secret", player=True)
    cookie = response.headers["set-cookie"]
    assert connection_cookie_name("g1", player=True) in cookie
    assert "Secure" in cookie and "HttpOnly" in cookie and "SameSite=strict" in cookie
