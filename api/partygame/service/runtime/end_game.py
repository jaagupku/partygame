from collections.abc import Awaitable, Callable
from hashlib import sha256
from uuid import uuid4
from typing import Any, TYPE_CHECKING

from partygame import schemas

if TYPE_CHECKING:
    from partygame.service.runtime.timing import TimingState
    from partygame.state.repo import GameStateRepository

BuildSnapshot = Callable[[schemas.Lobby], Awaitable[schemas.RuntimeSnapshotEvent]]

END_GAME_COMPONENT_ID = "end_game"
PLAYER_METRICS_COMPONENT_ID = "player_metrics"
REACTION_KEYS = {
    "😂": "laugh",
    "🔥": "fire",
    "👏": "clap",
    "😱": "shock",
    "💩": "poop",
    "🤮": "vomit",
}
END_GAME_SEQUENCE_STAGES = (
    "third_place",
    "second_place",
    "first_place",
    "stats",
    "scoreboard",
)


class EndGameRuntime:
    def __init__(self, repo: "GameStateRepository", timing: "TimingState") -> None:
        self.repo = repo
        self.timing = timing

    async def initialize_end_game_state(self, lobby_id: str, *, auto_reveal: bool) -> None:
        await self._initialize_end_game_state(lobby_id, auto_reveal=auto_reveal)

    async def set_end_game_state(self, lobby_id: str, updates: dict[str, Any]) -> None:
        await self._set_end_game_state(lobby_id, updates)

    async def apply_player_metric_updates(
        self,
        lobby_id: str,
        updates: dict[str, dict[str, Any]],
    ) -> None:
        await self._apply_player_metric_updates(lobby_id, updates)

    async def build_end_game_state(
        self,
        lobby: schemas.Lobby,
        players: list[schemas.Player],
    ) -> schemas.EndGameState | None:
        return await self._build_end_game_state(lobby, players)

    async def reveal_end_game(
        self, lobby: schemas.Lobby, build_snapshot: BuildSnapshot
    ) -> list[schemas.BaseEvent]:
        if lobby.phase != "finished":
            return []
        await self._set_end_game_state(
            lobby.id,
            {
                "revealed": True,
                "sequence_stage": END_GAME_SEQUENCE_STAGES[0],
            },
        )
        return [await build_snapshot(lobby)]

    async def advance_end_game_stage(
        self, lobby: schemas.Lobby, build_snapshot: BuildSnapshot
    ) -> list[schemas.BaseEvent]:
        if lobby.phase != "finished":
            return []
        end_game_state = await self._get_end_game_state(lobby.id)
        if not end_game_state.get("revealed"):
            return []
        stage = str(end_game_state.get("sequence_stage") or END_GAME_SEQUENCE_STAGES[0])
        try:
            next_index = min(
                END_GAME_SEQUENCE_STAGES.index(stage) + 1,
                len(END_GAME_SEQUENCE_STAGES) - 1,
            )
        except ValueError:
            next_index = 0
        await self._set_end_game_state(
            lobby.id,
            {"sequence_stage": END_GAME_SEQUENCE_STAGES[next_index]},
        )
        return [await build_snapshot(lobby)]

    async def toggle_end_game_autoplay(
        self,
        lobby: schemas.Lobby,
        enabled: bool,
        build_snapshot: BuildSnapshot,
    ) -> list[schemas.BaseEvent]:
        if lobby.phase != "finished":
            return []
        await self._set_end_game_state(lobby.id, {"autoplay_enabled": enabled})
        return [await build_snapshot(lobby)]

    async def record_player_reaction(
        self,
        lobby: schemas.Lobby,
        player_id: str,
        reaction: str,
    ) -> None:
        if lobby.phase == "finished":
            return
        await self._apply_player_metric_updates(
            lobby.id,
            {
                player_id: {
                    "reaction_count": 1,
                    "reaction_counts": {reaction: 1},
                }
            },
        )

    async def _initialize_end_game_state(self, lobby_id: str, *, auto_reveal: bool):
        await self.repo.set_component_state(
            lobby_id,
            END_GAME_COMPONENT_ID,
            {
                "state": {
                    "revealed": auto_reveal,
                    "sequence_stage": END_GAME_SEQUENCE_STAGES[0],
                    "autoplay_enabled": auto_reveal,
                    "showcase_seed": uuid4().hex,
                }
            },
        )
        await self.repo.set_component_state(
            lobby_id,
            PLAYER_METRICS_COMPONENT_ID,
            {"metrics": {}},
        )

    async def _get_end_game_state(self, lobby_id: str) -> dict[str, Any]:
        state = await self.repo.get_component_state(lobby_id, END_GAME_COMPONENT_ID)
        payload = state.get("state")
        if isinstance(payload, dict):
            return payload
        return {
            "revealed": False,
            "sequence_stage": END_GAME_SEQUENCE_STAGES[0],
            "autoplay_enabled": False,
        }

    async def _set_end_game_state(self, lobby_id: str, updates: dict[str, Any]):
        current = await self._get_end_game_state(lobby_id)
        current.update(updates)
        await self.repo.set_component_state(
            lobby_id,
            END_GAME_COMPONENT_ID,
            {"state": current},
        )

    async def _get_player_metrics(self, lobby_id: str) -> dict[str, dict[str, Any]]:
        state = await self.repo.get_component_state(lobby_id, PLAYER_METRICS_COMPONENT_ID)
        metrics = state.get("metrics")
        if isinstance(metrics, dict):
            return metrics
        return {}

    async def _apply_player_metric_updates(
        self,
        lobby_id: str,
        updates: dict[str, dict[str, Any]],
    ):
        if not updates:
            return
        metrics = await self._get_player_metrics(lobby_id)
        for player_id, changes in updates.items():
            current = metrics.setdefault(
                player_id,
                {
                    "answered_count": 0,
                    "correct_count": 0,
                    "wrong_count": 0,
                    "reaction_count": 0,
                    "reaction_counts": {},
                    "fastest_buzz_seconds": None,
                },
            )
            current["answered_count"] += int(changes.get("answered_count", 0))
            current["correct_count"] += int(changes.get("correct_count", 0))
            current["wrong_count"] += int(changes.get("wrong_count", 0))
            current["reaction_count"] = int(current.get("reaction_count", 0)) + int(
                changes.get("reaction_count", 0)
            )
            current_reactions = current.get("reaction_counts")
            if not isinstance(current_reactions, dict):
                current_reactions = {}
                current["reaction_counts"] = current_reactions
            reaction_changes = changes.get("reaction_counts", {})
            if isinstance(reaction_changes, dict):
                for reaction, count in reaction_changes.items():
                    current_reactions[str(reaction)] = int(
                        current_reactions.get(reaction, 0)
                    ) + int(count)
            next_fastest = self.timing.to_float(changes.get("fastest_buzz_seconds"))
            current_fastest = self.timing.to_float(current.get("fastest_buzz_seconds"))
            if next_fastest is not None and (
                current_fastest is None or next_fastest < current_fastest
            ):
                current["fastest_buzz_seconds"] = next_fastest
        await self.repo.set_component_state(
            lobby_id,
            PLAYER_METRICS_COMPONENT_ID,
            {"metrics": metrics},
        )

    async def _build_end_game_state(
        self,
        lobby: schemas.Lobby,
        players: list[schemas.Player],
    ) -> schemas.EndGameState | None:
        if lobby.phase != "finished":
            return None

        end_game_state = await self._get_end_game_state(lobby.id)
        metrics = await self._get_player_metrics(lobby.id)
        standings = self._build_final_standings(players, lobby.host_id)
        stats_cards = self._build_end_game_stats(standings, metrics)
        return schemas.EndGameState(
            revealed=bool(end_game_state.get("revealed")),
            sequence_stage=str(end_game_state.get("sequence_stage") or END_GAME_SEQUENCE_STAGES[0]),
            autoplay_enabled=bool(end_game_state.get("autoplay_enabled")),
            final_standings=standings,
            podium=standings[:3],
            stats_cards=stats_cards,
            highlight_card_ids=self._select_highlights(
                stats_cards, str(end_game_state.get("showcase_seed") or lobby.id)
            ),
        )

    def _build_final_standings(
        self,
        players: list[schemas.Player],
        host_id: str | None,
    ) -> list[schemas.FinalStandingEntry]:
        ranked_players = [player for player in players if player.id != host_id]
        ranked_players.sort(key=lambda player: (-player.score, player.name.casefold(), player.id))
        standings: list[schemas.FinalStandingEntry] = []
        last_score: int | None = None
        last_place = 0
        for index, player in enumerate(ranked_players, start=1):
            if player.score != last_score:
                last_place = index
                last_score = player.score
            standings.append(
                schemas.FinalStandingEntry(
                    player_id=player.id,
                    name=player.name,
                    score=player.score,
                    place=last_place,
                    avatar_kind=player.avatar_kind,
                    avatar_preset_key=player.avatar_preset_key,
                    avatar_url=player.avatar_url,
                )
            )
        return standings

    def _build_end_game_stats(
        self,
        standings: list[schemas.FinalStandingEntry],
        metrics: dict[str, dict[str, Any]],
    ) -> list[schemas.EndGameStatCard]:
        eligible_ids = {entry.player_id for entry in standings}
        filtered_metrics = {
            player_id: data for player_id, data in metrics.items() if player_id in eligible_ids
        }
        stats: list[schemas.EndGameStatCard] = []

        def add_stat(
            *,
            stat_id: str,
            label: str,
            description: str,
            values: dict[str, float | int],
            unit: str | None = None,
            higher_is_better: bool = True,
            require_positive: bool = True,
        ):
            if not values:
                return
            filtered_values = {
                player_id: value
                for player_id, value in values.items()
                if not require_positive or value > 0
            }
            if not filtered_values:
                return
            best_value = (
                max(filtered_values.values()) if higher_is_better else min(filtered_values.values())
            )
            winners = sorted(
                [player_id for player_id, value in filtered_values.items() if value == best_value]
            )
            stats.append(
                schemas.EndGameStatCard(
                    id=stat_id,
                    label=label,
                    winner_player_ids=winners,
                    value=round(best_value, 3) if isinstance(best_value, float) else best_value,
                    unit=unit,
                    description=description,
                )
            )

        add_stat(
            stat_id="most_correct",
            label="Most Correct Answers",
            description="Players with the most correct answers across the game.",
            values={
                player_id: int(data.get("correct_count", 0))
                for player_id, data in filtered_metrics.items()
            },
        )
        add_stat(
            stat_id="most_wrong",
            label="Most Wrong Answers",
            description="Players who collected the most incorrect reviewed or auto-judged answers.",
            values={
                player_id: int(data.get("wrong_count", 0))
                for player_id, data in filtered_metrics.items()
            },
        )
        add_stat(
            stat_id="fastest_buzz",
            label="Fastest Buzz",
            description="Quickest accepted buzzer reaction time.",
            values={
                player_id: float(data["fastest_buzz_seconds"])
                for player_id, data in filtered_metrics.items()
                if self.timing.to_float(data.get("fastest_buzz_seconds")) is not None
            },
            unit="seconds",
            higher_is_better=False,
        )
        add_stat(
            stat_id="highest_accuracy",
            label="Highest Accuracy",
            description="Best accuracy with at least five answers.",
            values={
                player_id: round(
                    int(data.get("correct_count", 0)) / int(data.get("answered_count", 0)) * 100,
                    2,
                )
                for player_id, data in filtered_metrics.items()
                if int(data.get("answered_count", 0)) >= 5
            },
            unit="percent",
        )
        add_stat(
            stat_id="most_reactions",
            label="Most Reactions",
            description="Certified button-mashing energy.",
            values={
                player_id: int(data.get("reaction_count", 0))
                for player_id, data in filtered_metrics.items()
            },
            unit="reactions",
        )

        signature_entries: list[tuple[int, str, str]] = []
        game_reaction_counts: dict[str, int] = {}
        for player_id, data in filtered_metrics.items():
            reaction_counts = data.get("reaction_counts", {})
            if not isinstance(reaction_counts, dict):
                continue
            for reaction, raw_count in reaction_counts.items():
                count = int(raw_count)
                if count <= 0:
                    continue
                reaction_key = str(reaction)
                signature_entries.append((count, reaction_key, player_id))
                game_reaction_counts[reaction_key] = (
                    game_reaction_counts.get(reaction_key, 0) + count
                )

        if signature_entries:
            best_signature_count = max(count for count, _reaction, _player_id in signature_entries)
            best_signature_reaction = sorted(
                {
                    reaction
                    for count, reaction, _player_id in signature_entries
                    if count == best_signature_count
                }
            )[0]
            signature_winners = sorted(
                player_id
                for count, reaction, player_id in signature_entries
                if count == best_signature_count and reaction == best_signature_reaction
            )
            stats.append(
                schemas.EndGameStatCard(
                    id="signature_reaction",
                    label="",
                    winner_player_ids=signature_winners,
                    value=best_signature_count,
                    unit="uses",
                    emoji=best_signature_reaction,
                    reaction_key=REACTION_KEYS.get(best_signature_reaction),
                )
            )

        if game_reaction_counts:
            best_game_count = max(game_reaction_counts.values())
            best_game_reaction = sorted(
                reaction
                for reaction, count in game_reaction_counts.items()
                if count == best_game_count
            )[0]
            stats.append(
                schemas.EndGameStatCard(
                    id="game_mood",
                    label="",
                    winner_player_ids=[],
                    value=best_game_count,
                    unit="uses",
                    emoji=best_game_reaction,
                    reaction_key=REACTION_KEYS.get(best_game_reaction),
                )
            )
        for card in stats:
            if card.id == "highest_accuracy":
                card.answer_counts = {
                    player_id: int(filtered_metrics[player_id].get("answered_count", 0))
                    for player_id in card.winner_player_ids
                }
                card.correct_counts = {
                    player_id: int(filtered_metrics[player_id].get("correct_count", 0))
                    for player_id in card.winner_player_ids
                }

        total_correct = sum(int(data.get("correct_count", 0)) for data in filtered_metrics.values())
        if total_correct > 0:
            stats.append(
                schemas.EndGameStatCard(
                    id="team_correct",
                    label="Team effort",
                    value=total_correct,
                    unit="answers",
                )
            )
        if len(game_reaction_counts) >= 3:
            stats.append(
                schemas.EndGameStatCard(
                    id="reaction_variety",
                    label="All the feels",
                    value=len(game_reaction_counts),
                    unit="reaction_types",
                    emoji="🎭",
                )
            )
        if len(standings) >= 2:
            margin = standings[0].score - standings[1].score
            if 0 < margin <= 5:
                stats.append(
                    schemas.EndGameStatCard(
                        id="photo_finish",
                        label="Photo finish",
                        value=margin,
                        unit="points",
                        winner_player_ids=[standings[0].player_id],
                        emoji="🏁",
                    )
                )
            elif margin == 0:
                tied = [entry.player_id for entry in standings if entry.place == 1]
                stats.append(
                    schemas.EndGameStatCard(
                        id="shared_crown",
                        label="Shared crown",
                        value=len(tied),
                        unit="champions",
                        winner_player_ids=tied,
                        emoji="👑",
                    )
                )
        return stats

    def _select_highlights(self, cards: list[schemas.EndGameStatCard], seed: str) -> list[str]:
        # Stable within one game, varied on every fresh start. Never invent an award
        # to fill a slot or put the same winners on multiple headline cards.
        candidates = [card for card in cards if card.id != "most_wrong"]
        candidates.sort(key=lambda card: sha256(f"{seed}:{card.id}".encode()).digest())
        selected: list[str] = []
        seen_winners: set[str] = set()
        reaction_selected = False
        reaction_ids = {"most_reactions", "signature_reaction", "game_mood", "reaction_variety"}
        performance_ids = {
            "most_correct",
            "highest_accuracy",
            "fastest_buzz",
            "photo_finish",
            "shared_crown",
        }
        # Lead with an earned gameplay award when one is available.
        candidates.sort(key=lambda card: card.id not in performance_ids)
        for card in candidates:
            if seen_winners.intersection(card.winner_player_ids):
                continue
            if card.id in reaction_ids and reaction_selected:
                continue
            selected.append(card.id)
            seen_winners.update(card.winner_player_ids)
            reaction_selected |= card.id in reaction_ids
            if len(selected) == 3:
                break
        return selected
