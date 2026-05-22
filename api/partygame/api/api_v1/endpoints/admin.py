from datetime import UTC, date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from partygame.api import deps
from partygame.db.postgres import get_async_session
from partygame.schemas import GameStatSummary, GameStatSummaryList
from partygame.service.stats import GameStatsService

router = APIRouter(dependencies=[Depends(deps.get_current_admin_user)])


@router.get("/game-stats", response_model=GameStatSummaryList)
async def list_game_stats(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    definition_id: str | None = Query(default=None, min_length=1),
    host_enabled: bool | None = Query(default=None),
    finished_from: date | None = Query(default=None),
    finished_to: date | None = Query(default=None),
    session: AsyncSession = Depends(get_async_session),
):
    finished_from_datetime = (
        datetime.combine(finished_from, time.min, tzinfo=UTC) if finished_from is not None else None
    )
    finished_to_datetime = (
        datetime.combine(finished_to + timedelta(days=1), time.min, tzinfo=UTC)
        if finished_to is not None
        else None
    )
    return await GameStatsService(session).list_summaries(
        limit=limit,
        offset=offset,
        definition_id=definition_id,
        host_enabled=host_enabled,
        finished_from=finished_from_datetime,
        finished_to=finished_to_datetime,
    )


@router.get("/game-stats/{game_id}", response_model=GameStatSummary)
async def get_game_stats(
    game_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    summary = await GameStatsService(session).get_summary(game_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Game stats were not found")
    return summary
