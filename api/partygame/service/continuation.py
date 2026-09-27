"""Prepare the next game without replacing the lobby or its connections."""

from uuid import uuid4

from fastapi import HTTPException, Request

from partygame import schemas
from partygame.core.config import settings
from partygame.schemas.game_session import PreparedSession
from partygame.schemas.lobby import ContinueGame, LobbySetup
from partygame.service.connection_access import connection_cookie_name
from partygame.service.definitions import get_default_definition_provider
from partygame.service.game import GameRuntimeService
from partygame.service.game_sessions import SESSION_COMPONENT_ID, prepare_session
from partygame.service.player import public_runtime_snapshot
from partygame.service.stats import GameStatsArchiver
from partygame.state import GameKeyFactory, GameStateRepository


async def require_manager(repo: GameStateRepository, game_id: str, request: Request):
    lobby = await repo.get_lobby_meta(game_id)
    if lobby is None:
        raise HTTPException(404, "Lobby data not found")
    if await repo.verify_connection_token(
        game_id, request.cookies.get(connection_cookie_name(game_id))
    ):
        return lobby
    manager_id = lobby.host_id if lobby.host_enabled else lobby.starter_id
    if manager_id and await repo.verify_connection_token(
        game_id, request.cookies.get(connection_cookie_name(game_id, player=True)), manager_id
    ):
        return lobby
    raise HTTPException(403, "Only the lobby manager can configure the next game")


async def read_setup(repo: GameStateRepository, lobby: schemas.Lobby) -> LobbySetup:
    record = await repo.get_component_state(lobby.id, "game_setup")
    saved = record.get("settings")
    payload = (
        schemas.CreateGame.model_validate(saved)
        if saved
        else schemas.CreateGame(
            game_type=lobby.game_type,
            definition_id=lobby.definition_id or "quiz_demo",
            host_enabled=lobby.host_enabled,
        )
    )
    return LobbySetup(
        run_id=lobby.run_id or lobby.id,
        settings=payload,
        settings_complete=bool(saved) or lobby.game_type != "price_guessing",
        definition_title=lobby.definition_title,
    )


async def continue_game(repo, game_id: str, request: Request, payload: ContinueGame, user=None):
    lobby = await require_manager(repo, game_id, request)
    check_finished(lobby, payload.expected_run_id)
    setup = payload.settings
    # Replaying a frozen quiz remains possible after its source is edited or removed.
    frozen = None
    if (
        setup.game_type == lobby.game_type == "trivia"
        and setup.definition_id == lobby.definition_id
    ):
        frozen = await repo.get_component_state(game_id, SESSION_COMPONENT_ID)
        if lobby.session_version is not None and (lobby.session_version != 1 or not frozen):
            raise HTTPException(409, "game_content_unavailable")
    prepared = (
        PreparedSession.model_validate(frozen["snapshot"])
        if frozen
        else await prepare_session(setup, user, get_default_definition_provider())
    )
    async with repo.mutation_lock(game_id):
        lobby = await require_manager(repo, game_id, request)
        check_finished(lobby, payload.expected_run_id)
        try:
            await GameStatsArchiver(repo).archive_finished_game(lobby, strict=True)
        except Exception as error:
            raise HTTPException(503, "game_archive_failed") from error
        next_lobby = lobby.model_copy(
            update={
                "run_id": prepared.session_id or uuid4().hex,
                "game_type": setup.game_type,
                "definition_id": prepared.definition.id,
                "definition_title": prepared.definition.title,
                "session_version": prepared.version,
                "host_enabled": setup.host_enabled,
                "host_id": (lobby.host_id or lobby.starter_id) if setup.host_enabled else None,
                "active_game": None,
                "state": schemas.GameState.WAITING_FOR_PLAYERS,
                "phase": "waiting",
                "current_step": 0,
            }
        )
        # Frozen trivia snapshots may originate from an older generated session.
        if next_lobby.run_id == (lobby.run_id or lobby.id):
            next_lobby.run_id = uuid4().hex
        await repo.replace_run(next_lobby, prepared, setup, settings.GAME_IDLE_TTL_SECONDS)
        next_lobby.players = await repo.get_players(game_id)
        snapshot = await GameRuntimeService(repo).build_snapshot(next_lobby)
        public = public_runtime_snapshot(snapshot).model_dump_json()
        await repo.publish_many(
            [
                (GameKeyFactory.display_channel(game_id), public),
                *[
                    (GameKeyFactory.player_channel(game_id, player.id), public)
                    for player in next_lobby.players
                ],
            ]
        )
        return next_lobby


def check_finished(lobby, expected_run_id):
    if lobby.phase != "finished" or (lobby.run_id or lobby.id) != expected_run_id:
        raise HTTPException(409, "game_run_changed")
