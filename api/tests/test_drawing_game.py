import json
from copy import deepcopy
from time import time
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException, Response

from partygame import schemas
from partygame.api.api_v1.endpoints.lobby import get_drawing_artwork
from partygame.schemas.drawing_game import DrawingCommand, DrawingSettings, PreparedDrawingSession
from partygame.schemas.lobby import ContinueGame
from partygame.service import continuation
from partygame.service.drawing.rules import allocate_points, assignments
from partygame.service.drawing.runtime import COMPONENT, DrawingError, DrawingRuntime
from partygame.service.game_sessions import prepare_session
from partygame.service.player import ClientController, public_runtime_snapshot
from partygame.service.stats import GameStatsArchiver
from partygame.state import GameKeyFactory, GameStateRepository
from tests.test_game_runtime import valid_drawing
from tests.test_lobby_continuation import ReplayRedis, request


def test_balanced_assignments():
    for count in range(3, 33):
        for seed in range(50):
            criteria, artists = assignments(count, seed)
            k = 2 if count < 5 else 3
            assert sorted(criteria) == list(range(count))
            assert all(t != c for t, c in enumerate(criteria))
            for topic, players in enumerate(artists):
                assert len(set(players)) == k
                assert topic not in players
                if count >= 4:
                    assert criteria[topic] not in players
            assert [sum(p in a for a in artists) for p in range(count)] == [k] * count
            assert assignments(count, seed) == (criteria, artists)


@pytest.mark.parametrize(
    "votes,points,reason",
    [
        ([], [], "empty"),
        ([0], [1000], "uncontested"),
        ([4], [1000], "uncontested"),
        ([3, 1], [750, 250], "votes"),
        ([1, 1, 1], [334, 333, 333], "votes"),
        ([0, 0, 0], [334, 333, 333], "no_votes"),
        ([0, 0], [500, 500], "no_votes"),
        ([0, 2, 1], [0, 667, 333], "votes"),
    ],
)
def test_point_pool(votes, points, reason):
    assert allocate_points(votes) == (points, reason)
    if votes:
        assert sum(points) == 1000


@pytest_asyncio.fixture
async def room(monkeypatch):
    repo = GameStateRepository(ReplayRedis())
    lobby = schemas.Lobby(
        id="g1",
        run_id="g1",
        join_code="ABCDE",
        game_type="drawing_mashup",
        session_version=2,
        host_enabled=False,
        starter_id="p0",
        definition_title="Drawing Mashup",
    )
    await repo.create_lobby(lobby)
    for i in range(5):
        await repo.create_player(
            schemas.Player(id=f"p{i}", game_id="g1", name=f"Player {i}", status="connected")
        )
    prepared = PreparedDrawingSession(session_id="g1", seed=42)
    await repo.set_component_state(
        "g1", "prepared_session", {"snapshot": prepared.model_dump(mode="json")}
    )
    await repo.set_component_state(
        "g1",
        "game_setup",
        {"settings": schemas.CreateGame(game_type="drawing_mashup").model_dump(mode="json")},
    )
    monkeypatch.setattr(GameStatsArchiver, "archive_finished_game", AsyncMock())
    runtime = DrawingRuntime(repo)
    await runtime.start(lobby, "p0")
    return repo, lobby, runtime


async def act(room, player, action, **kwargs):
    repo, lobby, runtime = room
    state = await runtime.load(lobby)
    command = DrawingCommand(
        action=action,
        run_id=lobby.run_id,
        phase_id=state["phase_id"],
        request_id=uuid4().hex,
        **kwargs,
    )
    async with repo.mutation_lock(lobby.id):
        return await runtime.command(lobby, player, command)


async def draw_phase(room):
    for i in range(5):
        await act(
            room, f"p{i}", "prompt", topic=f"Secret topic {i}", criterion=f"Secret criterion {i}"
        )
        await act(room, f"p{i}", "ready")
    return await room[2].load(room[1])


async def vote_phase(room):
    state = await draw_phase(room)
    for aid, art in state["artworks"].items():
        await act(room, art["owner"], "draw", assignment_id=aid, value=valid_drawing())
    for p in state["roster"]:
        await act(room, p, "ready")
    return await room[2].load(room[1])


@pytest.mark.asyncio
async def test_privacy_drafts_and_reconnect(room):
    repo, lobby, runtime = room
    await act(room, "p0", "prompt", topic="Secret topic", criterion="Hidden criterion")
    raw = await runtime.snapshot(lobby)
    assert "Secret topic" not in public_runtime_snapshot(raw).model_dump_json()
    assert (
        "Hidden criterion"
        not in public_runtime_snapshot(raw, viewer_player_id="p1").model_dump_json()
    )
    assert (
        public_runtime_snapshot(raw, viewer_player_id="p0").drawing_game.prompt["topic"]
        == "Secret topic"
    )
    assert public_runtime_snapshot(raw, viewer_player_id="p0").drawing_private == {}
    await act(room, "p0", "advance")
    state = await runtime.load(lobby)
    aid, art = next(iter(state["artworks"].items()))
    await act(room, art["owner"], "draw", assignment_id=aid, value=valid_drawing())
    restored = DrawingRuntime(repo)
    own = public_runtime_snapshot(await restored.snapshot(lobby), viewer_player_id=art["owner"])
    assert next(a for a in own.drawing_game.assignments if a.id == aid).value == valid_drawing()
    assert "Hidden criterion" not in own.model_dump_json()
    assert not public_runtime_snapshot(await restored.snapshot(lobby)).drawing_game.assignments
    other = next(p for p in state["roster"] if p != art["owner"])
    with pytest.raises(DrawingError, match="forbidden"):
        await act(room, other, "draw", assignment_id=aid, value=valid_drawing())
    with pytest.raises(DrawingError, match="conflict"):
        await act(room, art["owner"], "draw", assignment_id=aid, value=valid_drawing("#ef4444"))
    assert await act(room, art["owner"], "draw", assignment_id=aid, value=valid_drawing()) == 1
    await act(room, "p0", "advance")
    assert (await runtime.load(lobby))["artworks"][aid]["value"] == valid_drawing()


@pytest.mark.asyncio
async def test_voting_revision_commendations_and_exactly_once(room):
    _, lobby, runtime = room
    state = await vote_phase(room)
    match = state["matchups"][0]
    ids = match["drawings"]
    artist = state["artworks"][ids[0]]["owner"]
    with pytest.raises(DrawingError, match="invalid_vote"):
        await act(room, artist, "ballot", matchup_id=match["id"], ballot={"drawing_id": ids[0]})
    for ballot in ({"drawing_id": ids[1]}, {"topic": True}, {"criterion": True}, {}):
        with pytest.raises(DrawingError, match="invalid_vote"):
            await act(room, artist, "ballot", matchup_id=match["id"], ballot=ballot)
    with pytest.raises(DrawingError, match="invalid_vote"):
        await act(
            room, match["topic_author"], "ballot", matchup_id=match["id"], ballot={"topic": True}
        )
    outsider = next(
        p for p in state["roster"] if p not in [state["artworks"][a]["owner"] for a in ids]
    )
    await act(room, outsider, "ballot", matchup_id=match["id"], ballot={"drawing_id": ids[0]})
    await act(
        room,
        outsider,
        "ballot",
        matchup_id=match["id"],
        ballot={
            "drawing_id": ids[1],
            "topic": outsider != match["topic_author"],
            "criterion": outsider != match["criterion_author"],
        },
    )
    before = public_runtime_snapshot(await runtime.snapshot(lobby))
    assert before.drawing_game.matchup.revealed_votes == []
    assert before.drawing_game.reveal_duration is None
    for player_id in state["roster"]:
        private = public_runtime_snapshot(await runtime.snapshot(lobby), viewer_player_id=player_id)
        assert private.drawing_game.matchup.revealed_votes == []
    assert all(
        a.player_id is None and a.vote_count == 0 for a in before.drawing_game.matchup.drawings
    )
    await act(room, "p0", "advance")
    state = await runtime.load(lobby)
    result = state["matchups"][0]["result"]
    assert result["points"][ids[1]] == 1000
    assert result["votes"][ids[0]] == 0
    expected_votes = [
        {
            "voter_id": outsider,
            "voter_name": state["roster"][outsider]["name"],
            "drawing_id": ids[1],
        }
    ]
    assert result["revealed_votes"] == expected_votes
    for viewer in (None, *state["roster"]):
        revealed = public_runtime_snapshot(await runtime.snapshot(lobby), viewer_player_id=viewer)
        assert [
            v.model_dump() for v in revealed.drawing_game.matchup.revealed_votes
        ] == expected_votes
        assert revealed.drawing_game.reveal_duration == 12
        assert revealed.drawing_game.server_time is not None
    assert (
        sum(state["scores"].values()) == 1000 + result["topic_points"] + result["criterion_points"]
    )
    copy = deepcopy(state)
    runtime.score(state)
    assert state == copy
    assert all(a.player_id for a in runtime.view(state).matchup.drawings)
    state["ballots"].clear()
    assert [v.model_dump() for v in runtime.view(state).matchup.revealed_votes] == expected_votes


@pytest.mark.asyncio
async def test_missing_drawings_and_no_votes(room):
    _, lobby, runtime = room
    state = await draw_phase(room)
    match = state["matchups"][0]
    aid = match["drawings"][0]
    await act(
        room, state["artworks"][aid]["owner"], "draw", assignment_id=aid, value=valid_drawing()
    )
    await act(room, "p0", "advance")
    assert (await runtime.load(lobby))["phase"] == "voting"
    await act(room, "p0", "advance")
    state = await runtime.load(lobby)
    assert state["matchups"][0]["result"]["points"] == {aid: 1000}
    assert state["matchups"][0]["result"]["reveal_duration"] == 12
    await act(room, "p0", "advance")
    state = await runtime.load(lobby)
    assert state["phase"] == "results"
    assert state["matchups"][1]["result"]["allocation"] == "empty"
    assert state["matchups"][1]["result"]["reveal_duration"] == 12


@pytest.mark.asyncio
async def test_reveal_pause_resume_and_legacy_results(room, monkeypatch):
    _, lobby, runtime = room
    await vote_phase(room)
    monkeypatch.setattr("partygame.service.drawing.runtime.time", lambda: 1000)
    await act(room, "p0", "advance")
    state = await runtime.load(lobby)
    assert state["deadline"] == 1012
    monkeypatch.setattr("partygame.service.drawing.runtime.time", lambda: 1004)
    await act(room, "p0", "pause")
    paused = runtime.view(await runtime.load(lobby))
    assert paused.reveal_duration == 12
    assert paused.remaining_seconds == 8
    assert paused.deadline is None
    monkeypatch.setattr("partygame.service.drawing.runtime.time", lambda: 1100)
    await act(room, "p0", "resume")
    state = await runtime.load(lobby)
    assert state["deadline"] == 1108
    assert runtime.view(state).server_time == 1100
    result = state["matchups"][0]["result"]
    del result["reveal_duration"]
    del result["revealed_votes"]
    legacy = runtime.view(state)
    assert legacy.reveal_duration is None
    assert legacy.matchup.revealed_votes == []
    assert sum(a.points for a in legacy.matchup.drawings) == 1000


@pytest.mark.asyncio
@pytest.mark.parametrize("count,duration", [(0, 12), (1, 12), (4, 12.6), (20, 18), (61, 18)])
async def test_reveal_duration_order_and_abstentions(room, monkeypatch, count, duration):
    _, _, runtime = room
    state = await vote_phase(room)
    aid = state["matchups"][0]["drawings"][0]
    for i in range(count):
        pid = f"voter{i}"
        state["roster"][pid] = {"name": f"Voter {i}"}
    # Submission order must not change the presentation order.
    state["ballots"] = {
        f"voter{i}": {"drawing_id": aid, "topic": False, "criterion": False}
        for i in reversed(range(count))
    }
    state["ballots"]["p0"] = {"drawing_id": None, "topic": False, "criterion": False}
    monkeypatch.setattr("partygame.service.drawing.runtime.time", lambda: 1000)
    runtime.open_results(state)
    result = state["matchups"][0]["result"]
    assert result["reveal_duration"] == duration
    assert state["deadline"] == 1000 + duration
    assert [v["voter_id"] for v in result["revealed_votes"]] == [f"voter{i}" for i in range(count)]
    assert all(set(v) == {"voter_id", "voter_name", "drawing_id"} for v in result["revealed_votes"])


@pytest.mark.asyncio
async def test_timeouts_pause_failover_and_old_commands(room):
    repo, lobby, runtime = room
    await act(room, "p0", "pause")
    state = await runtime.load(lobby)
    assert state["deadline"] is None
    with pytest.raises(DrawingError, match="closed"):
        await act(room, "p1", "prompt", topic="x")
    await repo.set_player_status(lobby.id, "p0", schemas.ConnectionStatus.DISCONNECTED)
    await runtime.tick(lobby, now=100)
    await runtime.tick(lobby, now=116)
    assert lobby.starter_id == "p1"
    await act(room, "p1", "resume")
    state = await runtime.load(lobby)
    assert state["deadline"] > time()
    old = DrawingCommand(
        action="ready", request_id="old", run_id=lobby.run_id, phase_id=state["phase_id"]
    )
    await runtime.tick(lobby, now=state["deadline"] + 1)
    assert (await runtime.load(lobby))["phase"] == "drawing"
    with pytest.raises(DrawingError, match="stale"):
        await runtime.command(lobby, "p1", old)
    state = await runtime.load(lobby)
    assert all(
        m["topic_author"] is None and m["criterion_author"] is None for m in state["matchups"]
    )


@pytest.mark.asyncio
async def test_finish_gallery_history_cleanup_and_rematch(room):
    repo, lobby, runtime = room
    await vote_phase(room)
    while (await runtime.load(lobby))["phase"] != "finished":
        await act(room, "p0", "advance")
    snapshot = public_runtime_snapshot(await runtime.snapshot(lobby))
    assert len(snapshot.drawing_game.gallery) == 15
    assert all(a.value is None for a in snapshot.drawing_game.gallery)
    assert sum(p.score for p in snapshot.end_game.final_standings) == 5000
    stats = await GameStatsArchiver(repo)._drawing_record(lobby)
    assert stats["summary"]["drawing"]
    assert "answers" not in stats["summary"]
    aid = snapshot.drawing_game.gallery[0].id
    await repo.issue_connection_token("g1")
    token = await repo.issue_connection_token("g1", "p0")
    assert (
        await get_drawing_artwork(
            "g1", "g1", aid, request(token, player=True), Response(), "p0", repo.redis
        )
        == valid_drawing()
    )
    with pytest.raises(HTTPException) as error:
        await get_drawing_artwork(
            "g1", "old-run", aid, request(token, player=True), Response(), "p0", repo.redis
        )
    assert error.value.status_code == 404
    old = await runtime.load(lobby)
    next_lobby = await continuation.continue_game(
        repo,
        "g1",
        request(token, player=True),
        ContinueGame(expected_run_id="g1", settings=schemas.CreateGame(game_type="drawing_mashup")),
    )
    assert next_lobby.run_id != old["run_id"]
    assert await runtime.load(next_lobby) is None
    assert all(p.score == 0 for p in await repo.get_players("g1"))
    await repo.delete_game("g1")
    assert await repo.get_component_state("g1", COMPONENT) == {}


@pytest.mark.asyncio
async def test_preparation_validation():
    prepared = await prepare_session(
        schemas.CreateGame(game_type="drawing_mashup"), None, AsyncMock()
    )
    assert prepared.version == 2
    assert not hasattr(prepared.definition, "rounds")
    with pytest.raises(HTTPException):
        await prepare_session(
            schemas.CreateGame(game_type="drawing_mashup", host_enabled=True), None, AsyncMock()
        )
    with pytest.raises(ValueError):
        DrawingSettings(voting_seconds=0)


@pytest.mark.asyncio
async def test_private_draft_commits_do_not_broadcast(room):
    repo, _, _ = room
    repo.redis.published.clear()
    await act(room, "p1", "prompt", topic="Private", criterion="Private criterion")
    assert not repo.redis.published
    await act(room, "p1", "ready")
    frames = [
        json.loads(p) for c, p in repo.redis.published if c == GameKeyFactory.display_channel("g1")
    ]
    assert frames and "Private criterion" not in json.dumps(frames)


@pytest.mark.asyncio
async def test_minimum_connected_players(room):
    repo, lobby, runtime = room
    lobby.state = schemas.GameState.WAITING_FOR_PLAYERS
    for p in ("p2", "p3", "p4"):
        await repo.set_player_status("g1", p, schemas.ConnectionStatus.DISCONNECTED)
    with pytest.raises(DrawingError, match="needs_three_players"):
        await runtime.start(lobby, "p0")


@pytest.mark.asyncio
async def test_continuous_saves_do_not_postpone_worker(room):
    repo, lobby, _ = room
    token = f"{lobby.id}:{lobby.run_id}"
    due = await repo.redis.zscore("drawing_mashup:due", token)
    for revision in range(10):
        await act(room, "p0", "prompt", topic=f"Topic {revision}", revision=revision)
    assert await repo.redis.zscore("drawing_mashup:due", token) <= due
    # A fresh runtime instance recovers the saved deadline without a controller.
    restored = DrawingRuntime(repo)
    state = await restored.load(lobby)
    await restored.tick(lobby, now=state["deadline"] + 1)
    assert (await restored.load(lobby))["phase"] == "drawing"


@pytest.mark.asyncio
async def test_concurrent_readiness_closes_vote_once(room):
    import asyncio

    repo, lobby, runtime = room
    state = await vote_phase(room)
    eligible = set(state["roster"]) - runtime.matchup_artists(state)
    await asyncio.gather(*(act(room, p, "ready") for p in eligible))
    state = await runtime.load(lobby)
    assert state["phase"] == "results"
    assert sum(state["scores"].values()) == 1000
    assert sum(p.score for p in await repo.get_players(lobby.id)) == 1000


@pytest.mark.asyncio
async def test_gallery_is_unavailable_before_finish_or_without_credentials(room):
    repo, _, _ = room
    state = await draw_phase(room)
    aid, art = next(iter(state["artworks"].items()))
    await act(room, art["owner"], "draw", assignment_id=aid, value=valid_drawing())
    token = await repo.issue_connection_token("g1", "p0")
    with pytest.raises(HTTPException) as error:
        await get_drawing_artwork(
            "g1", "g1", aid, request(token, player=True), Response(), "p0", repo.redis
        )
    assert error.value.status_code == 404
    with pytest.raises(HTTPException) as error:
        await get_drawing_artwork(
            "g1", "g1", aid, request("wrong", player=True), Response(), "p0", repo.redis
        )
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_invalid_artwork_preserves_previous_draft(room):
    _, lobby, runtime = room
    state = await draw_phase(room)
    aid, art = next(iter(state["artworks"].items()))
    await act(room, art["owner"], "draw", assignment_id=aid, value=valid_drawing())
    for invalid in (
        {"w": 512, "h": 384, "s": []},
        {"w": 512, "h": 384, "s": [[0, 8, {}, [1, 1]]]},
        valid_drawing() | {"padding": "x" * 240_000},
    ):
        with pytest.raises(DrawingError, match="invalid_drawing"):
            await act(room, art["owner"], "draw", assignment_id=aid, revision=1, value=invalid)
    assert (await runtime.load(lobby))["artworks"][aid]["value"] == valid_drawing()


@pytest.mark.asyncio
async def test_organizer_failover_still_runs_at_final_scoreboard(room):
    repo, lobby, runtime = room
    await act(room, "p0", "advance")
    await act(room, "p0", "advance")
    while (await runtime.load(lobby))["phase"] != "finished":
        await act(room, "p0", "advance")
    state = await runtime.load(lobby)
    state.update(finale_stage="scoreboard", deadline=None, archived=True)
    await runtime.commit(lobby, state)
    assert await repo.redis.zscore("drawing_mashup:due", "g1:g1") is not None
    await repo.set_player_status(lobby.id, "p0", schemas.ConnectionStatus.DISCONNECTED)
    await runtime.tick(lobby, now=100)
    await runtime.tick(lobby, now=116)
    assert (await repo.get_lobby_meta(lobby.id)).starter_id == "p1"


@pytest.mark.asyncio
async def test_organizer_failover_before_start(room):
    repo, lobby, runtime = room
    await repo.redis.delete(GameKeyFactory.game_component(lobby.id, COMPONENT))
    lobby.state = schemas.GameState.WAITING_FOR_PLAYERS
    lobby.phase = "waiting"
    await repo.set_lobby_fields(lobby.id, state="waiting_for_players", phase="waiting")
    await repo.set_player_status(lobby.id, "p0", schemas.ConnectionStatus.DISCONNECTED)
    await runtime.tick(lobby, now=100)
    await runtime.tick(lobby, now=114)
    assert lobby.starter_id == "p0"
    await runtime.tick(lobby, now=116)
    assert (await repo.get_lobby_meta(lobby.id)).starter_id == "p1"


@pytest.mark.asyncio
async def test_private_projection_applies_to_patches_even_with_host_flag(room):
    _, lobby, runtime = room
    controller = object.__new__(ClientController)
    before = await runtime.snapshot(lobby)
    await act(room, "p0", "prompt", topic="Private topic", criterion="Hidden criterion")
    await act(room, "p0", "ready")
    after = await runtime.snapshot(lobby)
    for viewer in (None, "p0", "p1", "outsider"):
        patch = controller._patch_for_viewer(
            before, after, include_host_answer=True, viewer_player_id=viewer
        )
        serialized = patch.model_dump_json()
        assert ("Private topic" in serialized) == (viewer == "p0")
        assert ("Hidden criterion" in serialized) == (viewer == "p0")
        assert "drawing_private" not in patch.changes


@pytest.mark.asyncio
@pytest.mark.parametrize("next_type", ["trivia", "price_guessing"])
async def test_continuation_between_drawing_and_existing_games(room, monkeypatch, next_type):
    from partygame.service.game import GameRuntimeService
    from partygame.service.game_sessions import compose_rounds
    from tests.test_game_sessions import bundle

    repo, lobby, runtime = room
    await act(room, "p0", "advance")
    await act(room, "p0", "advance")
    while (await runtime.load(lobby))["phase"] != "finished":
        await act(room, "p0", "advance")
    token = await repo.issue_connection_token("g1", "p0")
    prepared = compose_rounds([bundle()], definition_id="quiz_demo", title="Next game")
    with monkeypatch.context() as patch:
        patch.setattr(continuation, "prepare_session", AsyncMock(return_value=prepared))
        continued = await continuation.continue_game(
            repo,
            "g1",
            request(token, player=True),
            ContinueGame(expected_run_id="g1", settings=schemas.CreateGame(game_type=next_type)),
        )
    assert continued.game_type == next_type
    assert (await GameRuntimeService(repo).build_snapshot(continued)).drawing_game is None
    assert await repo.get_component_state("g1", COMPONENT) == {}
    await repo.set_lobby_fields("g1", phase="finished")
    back = await continuation.continue_game(
        repo,
        "g1",
        request(token, player=True),
        ContinueGame(
            expected_run_id=continued.run_id,
            settings=schemas.CreateGame(game_type="drawing_mashup"),
        ),
    )
    assert back.session_version == 2
    assert (await GameRuntimeService(repo).build_snapshot(back)).drawing_game.phase == "waiting"
    await runtime.start(back, "p0")
    assert (await runtime.load(back))["matchups"] == []


@pytest.mark.asyncio
async def test_background_worker_restores_deadline_and_discards_old_run_events(room, monkeypatch):
    import asyncio

    from partygame.service.drawing import scheduler

    repo, lobby, runtime = room
    state = await runtime.load(lobby)
    state["deadline"] = time() - 1
    await runtime.commit(lobby, state, publish=False)
    await repo.redis.zadd("drawing_mashup:due", {"g1:g1": 0, "g1:old-run": 0, "deleted:gone": 0})

    async def due(key, minimum, maximum, start=0, num=100):
        return [
            token for token, at in repo.redis.sorted_sets.get(key, {}).items() if at <= maximum
        ][start : start + num]

    async def stop(seconds):
        raise asyncio.CancelledError

    monkeypatch.setattr(repo.redis, "zrangebyscore", due, raising=False)
    monkeypatch.setattr(repo.redis, "aclose", AsyncMock(), raising=False)
    monkeypatch.setattr(scheduler, "get_connection", lambda: repo.redis)
    monkeypatch.setattr(scheduler.asyncio, "sleep", stop)
    for _ in range(2):
        with pytest.raises(asyncio.CancelledError):
            await scheduler.run_scheduler()
    restored = await runtime.load(lobby)
    assert restored["phase"] == "drawing"
    assert restored["phase_id"] == 2
    assert len(restored["artworks"]) == 15
    assert await repo.redis.zscore("drawing_mashup:due", "g1:old-run") is None
    assert await repo.redis.zscore("drawing_mashup:due", "deleted:gone") is None
