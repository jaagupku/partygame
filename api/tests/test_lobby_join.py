import pytest
from fastapi import HTTPException

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

    result = await join_lobby(
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
            redis=redis,
            join_request=schemas.JoinRequest(
                join_code="ABCDE",
                player_name="Bob",
                player_id="missing",
            ),
        )

    assert error.value.status_code == 403
