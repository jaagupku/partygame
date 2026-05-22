import os
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from partygame import schemas
from partygame.api import deps
from partygame.db.postgres import Base
from partygame.service.game import GameRuntimeService
from partygame.service.stats import GameStatsArchiver, GameStatsService
from partygame.state.auth_models import UserRecord, UserRole
from partygame.state.stats_models import GameStatSummaryRecord
from tests.test_game_runtime import FakeRepo, MixedDefinitionProvider


def _admin_user() -> UserRecord:
    return UserRecord(
        id="admin-1",
        email="admin@example.com",
        display_name="Admin",
        password_hash="hash",
        role=UserRole.ADMIN.value,
    )


def _regular_user() -> UserRecord:
    return UserRecord(
        id="user-1",
        email="user@example.com",
        display_name="User",
        password_hash="hash",
        role=UserRole.USER.value,
    )


@pytest_asyncio.fixture()
async def stats_sessionmaker():
    database_url = os.environ.get("POSTGRES_TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("POSTGRES_TEST_DATABASE_URL is not configured")

    engine = create_async_engine(database_url)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

    try:
        yield sessionmaker
    finally:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest.mark.asyncio
async def test_admin_dependency_rejects_regular_user():
    with pytest.raises(HTTPException) as error:
        await deps.get_current_admin_user(_regular_user())

    assert error.value.status_code == 403
    assert (await deps.get_current_admin_user(_admin_user())).role == UserRole.ADMIN.value


@pytest.mark.asyncio
async def test_finished_game_archives_idempotent_summary(stats_sessionmaker):
    repo = FakeRepo()
    archiver = GameStatsArchiver(
        repo,
        definition_provider=MixedDefinitionProvider(),
        sessionmaker=stats_sessionmaker,
    )
    service = GameRuntimeService(
        repo=repo,
        definition_provider=MixedDefinitionProvider(),
        stats_archiver=archiver,
    )
    lobby = schemas.Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=True)

    await service.start_game(lobby)
    await service.submit_player_input(lobby, "p1", "buzz")
    await service.review_submission(
        lobby,
        schemas.ReviewSubmissionEvent(player_id="p1", accepted=True),
    )
    await service.advance_step(lobby)
    await service.submit_player_input(lobby, "p1", 27)
    await service.submit_player_input(lobby, "p2", 10)
    await service.close_step(lobby)
    await service.advance_step(lobby)
    await archiver.archive_finished_game(lobby)

    async with stats_sessionmaker() as session:
        records = (await session.scalars(select(GameStatSummaryRecord))).all()
        listed = await GameStatsService(session).list_summaries()

    assert len(records) == 1
    assert listed.total == 1
    summary = listed.items[0]
    assert summary.game_id == "g1"
    assert summary.player_count == 2
    assert summary.summary["answers"]["correct_count"] >= 1
    assert summary.summary["buzzers"]["buzz_count"] == 1


@pytest.mark.asyncio
async def test_game_stats_service_filters_by_finished_date(stats_sessionmaker):
    now = datetime.now(tz=UTC)
    async with stats_sessionmaker() as session:
        session.add_all(
            [
                GameStatSummaryRecord(
                    game_id="old",
                    join_code="OLD11",
                    definition_id="quiz_demo",
                    definition_title="Quiz",
                    host_enabled=True,
                    started_at=now - timedelta(days=3),
                    finished_at=now - timedelta(days=2),
                    player_count=2,
                    round_count=1,
                    step_count=1,
                    summary={},
                ),
                GameStatSummaryRecord(
                    game_id="new",
                    join_code="NEW11",
                    definition_id="quiz_demo",
                    definition_title="Quiz",
                    host_enabled=True,
                    started_at=now - timedelta(hours=1),
                    finished_at=now,
                    player_count=2,
                    round_count=1,
                    step_count=1,
                    summary={},
                ),
            ]
        )
        await session.commit()

        listed = await GameStatsService(session).list_summaries(
            finished_from=now - timedelta(days=1),
            finished_to=now + timedelta(days=1),
        )

    assert [item.game_id for item in listed.items] == ["new"]


@pytest.mark.asyncio
async def test_runtime_can_disable_game_stats_archiver():
    repo = FakeRepo()
    service = GameRuntimeService(
        repo=repo,
        definition_provider=MixedDefinitionProvider(),
        archive_game_stats=False,
    )
    lobby = schemas.Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=True)

    await service.start_game(lobby)

    assert service.stats_archiver is None
    assert "game_stats_context" not in repo.components.get("g1", {})


@pytest.mark.asyncio
async def test_game_stats_service_returns_none_for_missing_summary(stats_sessionmaker):
    async with stats_sessionmaker() as session:
        summary = await GameStatsService(session).get_summary("missing")

    assert summary is None
