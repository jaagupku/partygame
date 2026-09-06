import pytest
from fastapi import HTTPException, Request, Response
from partygame.service.connection_access import connection_cookie_name

from partygame import schemas
from partygame.api.api_v1.endpoints.lobby import join_lobby
from partygame.state import GameStateRepository
from tests.test_state_repo_cleanup import FakeRedis


@pytest.mark.asyncio
async def test_existing_player_can_rejoin_running_game():
    redis = FakeRedis()
    repo = GameStateRepository(redis)
    lobby = schemas.Lobby(
        id="g1",
        join_code="ABCDE",
        state=schemas.GameState.RUNNING,
    )
    player = schemas.Player(id="p1", game_id="g1", name="Alice")
    await repo.create_lobby(lobby)
    await repo.create_player(player)

    token = await repo.issue_connection_token("g1", "p1")
    result = await join_lobby(
        request=join_request_http(token),
        response=Response(),
        redis=redis,
        join_request=schemas.JoinRequest(
            join_code="abcde",
            player_name="Alice",
            player_id="p1",
        ),
    )

    assert result.player.id == "p1"
    assert result.player.game_id == "g1"
    assert result.lobby.id == "g1"


@pytest.mark.asyncio
async def test_unknown_player_cannot_join_running_game():
    redis = FakeRedis()
    repo = GameStateRepository(redis)
    await repo.create_lobby(
        schemas.Lobby(
            id="g1",
            join_code="ABCDE",
            state=schemas.GameState.RUNNING,
        )
    )

    with pytest.raises(HTTPException) as error:
        await join_lobby(
            request=join_request_http(),
            response=Response(),
            redis=redis,
            join_request=schemas.JoinRequest(
                join_code="ABCDE",
                player_name="Bob",
                player_id="missing",
            ),
        )

    assert error.value.status_code == 403


def join_request_http(token: str = "") -> Request:
    return Request(
        {
            "type": "http",
            "scheme": "http",
            "path": "/api/v1/lobby/join",
            "headers": [
                (b"cookie", f"{connection_cookie_name('g1', player=True)}={token}".encode())
            ],
        }
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("token", ["", "wrong-token"])
async def test_public_player_id_cannot_be_used_to_rejoin(token):
    redis = FakeRedis()
    repo = GameStateRepository(redis)
    await repo.create_lobby(schemas.Lobby(id="g1", join_code="ABCDE"))
    await repo.create_player(schemas.Player(id="p1", game_id="g1", name="Alice"))
    await repo.issue_connection_token("g1", "p1")
    with pytest.raises(HTTPException) as error:
        await join_lobby(
            request=join_request_http(token),
            response=Response(),
            redis=redis,
            join_request=schemas.JoinRequest(
                join_code="ABCDE", player_name="Alice", player_id="p1"
            ),
        )
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_join_issues_private_cookie_without_leaking_token(monkeypatch):
    from partygame.service import player as player_service
    from unittest.mock import AsyncMock

    redis = FakeRedis()
    repo = GameStateRepository(redis)
    await repo.create_lobby(schemas.Lobby(id="g1", join_code="ABCDE"))
    monkeypatch.setattr(player_service, "publish", AsyncMock())
    response = Response()
    result = await join_lobby(
        request=join_request_http(),
        response=response,
        redis=redis,
        join_request=schemas.JoinRequest(join_code="ABCDE", player_name="Alice"),
    )
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=strict" in cookie
    token = cookie.split(";", 1)[0].split("=", 1)[1]
    assert await repo.verify_connection_token("g1", token, result.player.id)
    assert token not in result.model_dump_json()
    assert token not in (await repo.get_player("g1", result.player.id)).model_dump_json()
    assert token not in (await repo.get_lobby_meta("g1")).model_dump_json()
