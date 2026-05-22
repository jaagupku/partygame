from __future__ import annotations

import logging
from datetime import UTC, datetime
from statistics import median
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from partygame import schemas
from partygame.db.postgres import AsyncSessionLocal
from partygame.service.definitions import DefinitionProvider, get_default_definition_provider
from partygame.service.runtime.end_game import PLAYER_METRICS_COMPONENT_ID
from partygame.state import GameStateRepository
from partygame.state.stats_models import GameStatSummaryRecord

log = logging.getLogger(__name__)

GAME_STATS_CONTEXT_COMPONENT_ID = "game_stats_context"
CLOSE_BUZZ_SECONDS = 0.1


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except TypeError, ValueError:
        return None


def _to_datetime(value: Any) -> datetime | None:
    timestamp = _to_float(value)
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, tz=UTC)


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except TypeError, ValueError:
        return 0


def _record_to_schema(record: GameStatSummaryRecord) -> schemas.GameStatSummary:
    return schemas.GameStatSummary(
        game_id=record.game_id,
        join_code=record.join_code,
        definition_id=record.definition_id,
        definition_title=record.definition_title,
        host_enabled=record.host_enabled,
        started_at=record.started_at,
        finished_at=record.finished_at,
        player_count=record.player_count,
        round_count=record.round_count,
        step_count=record.step_count,
        summary=record.summary,
    )


class GameStatsArchiver:
    def __init__(
        self,
        repo: GameStateRepository,
        *,
        definition_provider: DefinitionProvider | None = None,
        sessionmaker: async_sessionmaker[AsyncSession] = AsyncSessionLocal,
    ):
        self.repo = repo
        self.definition_provider = definition_provider or get_default_definition_provider()
        self.sessionmaker = sessionmaker

    async def mark_started(self, lobby_id: str):
        await self.repo.set_component_state(
            lobby_id,
            GAME_STATS_CONTEXT_COMPONENT_ID,
            {"started_at": datetime.now(tz=UTC).timestamp()},
        )

    async def archive_finished_game(self, lobby: schemas.Lobby):
        try:
            record_values = await self._build_record_values(lobby)
            async with self.sessionmaker() as session:
                statement = insert(GameStatSummaryRecord).values(**record_values)
                update_values = {
                    key: value
                    for key, value in record_values.items()
                    if key not in {"game_id", "created_at"}
                }
                statement = statement.on_conflict_do_update(
                    index_elements=[GameStatSummaryRecord.game_id],
                    set_=update_values | {"updated_at": func.now()},
                )
                await session.execute(statement)
                await session.commit()
        except Exception:
            log.exception("Failed to archive game stats for game %s", lobby.id)

    async def _build_record_values(self, lobby: schemas.Lobby) -> dict[str, Any]:
        definition = None
        definition_id = lobby.definition_id or "quiz_demo"
        try:
            definition = await self.definition_provider.load(definition_id)
        except Exception:
            log.exception("Failed to load definition %s for game stats", definition_id)

        players = await self.repo.get_players(lobby.id)
        scoreboard = self._build_scoreboard(players, lobby.host_id)
        metrics = await self._get_player_metrics(lobby.id)
        step_states = await self._get_step_states(lobby, definition)
        started_at = _to_datetime(
            (await self.repo.get_component_state(lobby.id, GAME_STATS_CONTEXT_COMPONENT_ID)).get(
                "started_at"
            )
        )
        finished_at = datetime.now(tz=UTC)

        summary = {
            "version": 1,
            "scoreboard": scoreboard,
            "answers": self._build_answer_summary(metrics, step_states),
            "buzzers": self._build_buzzer_summary(step_states),
            "reactions": self._build_reaction_summary(metrics),
        }
        return {
            "game_id": lobby.id,
            "join_code": lobby.join_code,
            "definition_id": definition_id,
            "definition_title": definition.title if definition is not None else None,
            "host_enabled": bool(lobby.host_enabled),
            "started_at": started_at,
            "finished_at": finished_at,
            "player_count": len(scoreboard),
            "round_count": len(definition.rounds) if definition is not None else 0,
            "step_count": (
                sum(len(round_definition.steps) for round_definition in definition.rounds)
                if definition is not None
                else len(step_states)
            ),
            "summary": summary,
        }

    async def _get_player_metrics(self, lobby_id: str) -> dict[str, dict[str, Any]]:
        state = await self.repo.get_component_state(lobby_id, PLAYER_METRICS_COMPONENT_ID)
        metrics = state.get("metrics")
        return metrics if isinstance(metrics, dict) else {}

    async def _get_step_states(
        self,
        lobby: schemas.Lobby,
        definition: schemas.GameDefinition | None,
    ) -> list[dict[str, Any]]:
        step_count = (
            sum(len(round_definition.steps) for round_definition in definition.rounds)
            if definition is not None
            else max(0, lobby.current_step)
        )
        states: list[dict[str, Any]] = []
        for step_index in range(step_count):
            state = await self.repo.get_component_state(lobby.id, f"step_archive:{step_index}")
            if state:
                states.append(state)
        current_state = await self.repo.get_step_cache(lobby.id)
        current_index = _safe_int(current_state.get("step_index"))
        if current_state and current_index >= len(states):
            states.append(current_state)
        return states

    def _build_scoreboard(
        self,
        players: list[schemas.Player],
        host_id: str | None,
    ) -> list[dict[str, Any]]:
        ranked = [player for player in players if player.id != host_id]
        ranked.sort(key=lambda player: (-player.score, player.name.casefold(), player.id))
        scoreboard: list[dict[str, Any]] = []
        last_score: int | None = None
        last_place = 0
        for index, player in enumerate(ranked, start=1):
            if player.score != last_score:
                last_place = index
                last_score = player.score
            scoreboard.append(
                {
                    "player_id": player.id,
                    "name": player.name,
                    "score": player.score,
                    "place": last_place,
                }
            )
        return scoreboard

    def _build_answer_summary(
        self,
        metrics: dict[str, dict[str, Any]],
        step_states: list[dict[str, Any]],
    ) -> dict[str, Any]:
        answered_counts = [_safe_int(data.get("answered_count")) for data in metrics.values()]
        correct_counts = [_safe_int(data.get("correct_count")) for data in metrics.values()]
        wrong_counts = [_safe_int(data.get("wrong_count")) for data in metrics.values()]
        reviewed_player_ids = {
            player_id
            for state in step_states
            for player_id in state.get("reviewed_player_ids", [])
            if isinstance(player_id, str)
        }
        accuracy_values = [
            round(correct / answered * 100, 2)
            for answered, correct in zip(answered_counts, correct_counts, strict=False)
            if answered > 0
        ]
        return {
            "submitted_count": sum(
                len(answers)
                for state in step_states
                if isinstance((answers := state.get("answers")), dict)
            ),
            "reviewed_count": len(reviewed_player_ids),
            "answered_count": sum(answered_counts),
            "correct_count": sum(correct_counts),
            "wrong_count": sum(wrong_counts),
            "average_accuracy_percent": (
                round(sum(accuracy_values) / len(accuracy_values), 2) if accuracy_values else None
            ),
        }

    def _build_buzzer_summary(self, step_states: list[dict[str, Any]]) -> dict[str, Any]:
        reaction_times: list[float] = []
        for state in step_states:
            if not state.get("buzzed_player_id"):
                continue
            reaction_time = _to_float(state.get("buzz_reaction_seconds"))
            if reaction_time is not None:
                reaction_times.append(reaction_time)
        return {
            "buzz_count": len(reaction_times),
            "fastest_reaction_seconds": round(min(reaction_times), 3) if reaction_times else None,
            "median_reaction_seconds": round(median(reaction_times), 3) if reaction_times else None,
            "close_call_count": sum(
                1 for reaction_time in reaction_times if reaction_time <= CLOSE_BUZZ_SECONDS
            ),
            "close_call_threshold_seconds": CLOSE_BUZZ_SECONDS,
        }

    def _build_reaction_summary(self, metrics: dict[str, dict[str, Any]]) -> dict[str, Any]:
        reaction_counts: dict[str, int] = {}
        for data in metrics.values():
            counts = data.get("reaction_counts", {})
            if not isinstance(counts, dict):
                continue
            for reaction, count in counts.items():
                reaction_counts[str(reaction)] = reaction_counts.get(str(reaction), 0) + _safe_int(
                    count
                )
        most_used_reaction = None
        if reaction_counts:
            most_used_reaction = sorted(
                reaction_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )[0][0]
        return {
            "total_reactions": sum(reaction_counts.values()),
            "most_used_reaction": most_used_reaction,
            "reaction_counts": reaction_counts,
        }


class GameStatsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_summaries(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        definition_id: str | None = None,
        host_enabled: bool | None = None,
        finished_from: datetime | None = None,
        finished_to: datetime | None = None,
    ) -> schemas.GameStatSummaryList:
        conditions = []
        if definition_id:
            conditions.append(GameStatSummaryRecord.definition_id == definition_id)
        if host_enabled is not None:
            conditions.append(GameStatSummaryRecord.host_enabled == host_enabled)
        if finished_from is not None:
            conditions.append(GameStatSummaryRecord.finished_at >= finished_from)
        if finished_to is not None:
            conditions.append(GameStatSummaryRecord.finished_at < finished_to)

        base = select(GameStatSummaryRecord)
        count_query = select(func.count()).select_from(GameStatSummaryRecord)
        for condition in conditions:
            base = base.where(condition)
            count_query = count_query.where(condition)
        rows = await self.session.scalars(
            base.order_by(GameStatSummaryRecord.finished_at.desc()).limit(limit).offset(offset)
        )
        total = int(await self.session.scalar(count_query) or 0)
        return schemas.GameStatSummaryList(
            items=[_record_to_schema(record) for record in rows],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def get_summary(self, game_id: str) -> schemas.GameStatSummary | None:
        record = await self.session.get(GameStatSummaryRecord, game_id)
        if record is None:
            return None
        return _record_to_schema(record)
