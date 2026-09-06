import pytest

from partygame import schemas
from partygame.service.runtime.end_game import EndGameRuntime
from partygame.service.runtime.timing import TimingState


def build_cards():
    runtime = EndGameRuntime(None, TimingState())
    standings = [
        schemas.FinalStandingEntry(player_id="p1", name="Alice", score=20, place=1),
        schemas.FinalStandingEntry(player_id="p2", name="Bob", score=18, place=2),
        schemas.FinalStandingEntry(player_id="p3", name="Chris", score=10, place=3),
    ]
    metrics = {
        "p1": {"correct_count": 6, "answered_count": 10, "fastest_buzz_seconds": 0.5},
        "p2": {"correct_count": 5, "answered_count": 5, "wrong_count": 0},
        "p3": {
            "correct_count": 1,
            "answered_count": 1,
            "reaction_count": 12,
            "reaction_counts": {"😂": 6, "🔥": 4, "👏": 2},
        },
        "host": {"correct_count": 999, "answered_count": 999},
    }
    return runtime, runtime._build_end_game_stats(standings, metrics)


def test_highlights_vary_between_games_but_stay_stable_within_game():
    runtime, cards = build_cards()
    selections = set()
    for index in range(20):
        seed = f"game-{index}"
        selected = runtime._select_highlights(cards, seed)
        assert selected == runtime._select_highlights(cards, seed)
        assert len(selected) == 3
        assert "most_wrong" not in selected
        selections.add(tuple(selected))
        winners = []
        for card in cards:
            if card.id in selected:
                winners.extend(card.winner_player_ids)
        assert len(winners) == len(set(winners))
        assert (
            len(
                set(selected)
                & {"most_reactions", "signature_reaction", "game_mood", "reaction_variety"}
            )
            <= 1
        )
    assert len(selections) > 1
    assert len({frozenset(selection) for selection in selections}) > 1


def test_accuracy_requires_five_answers_and_includes_the_fraction():
    _, cards = build_cards()
    accuracy = next(card for card in cards if card.id == "highest_accuracy")
    assert accuracy.winner_player_ids == ["p2"]
    assert accuracy.value == 100
    assert accuracy.answer_counts == {"p2": 5}
    assert accuracy.correct_counts == {"p2": 5}


def test_room_facts_are_derived_from_players_and_exclude_host():
    _, cards = build_cards()
    facts = {card.id: card for card in cards}
    assert facts["team_correct"].value == 12
    assert facts["reaction_variety"].value == 3
    assert facts["photo_finish"].value == 2
    assert facts["photo_finish"].winner_player_ids == ["p1"]


def test_tied_champions_share_a_card_and_empty_games_have_no_invented_facts():
    runtime = EndGameRuntime(None, TimingState())
    assert runtime._select_highlights([], "empty") == []
    standings = [
        schemas.FinalStandingEntry(player_id=id_, name=id_, score=10, place=1)
        for id_ in ["p1", "p2"]
    ]
    cards = runtime._build_end_game_stats(standings, {})
    assert [card.id for card in cards] == ["shared_crown"]
    assert cards[0].winner_player_ids == ["p1", "p2"]


@pytest.mark.asyncio
async def test_stats_autoplay_allows_time_to_read_three_awards():
    from partygame.service.runtime.scheduler import RuntimeTransitionScheduler

    lobby = schemas.Lobby(id="g1", join_code="ABCDE", host_enabled=False, phase="finished")
    snapshot = schemas.RuntimeSnapshotEvent(
        lobby=schemas.RuntimeLobbyState(
            id=lobby.id,
            join_code=lobby.join_code,
            host_enabled=False,
            state=schemas.GameState.RUNNING,
            phase="finished",
            current_step=0,
        ),
        end_game=schemas.EndGameState(revealed=True, autoplay_enabled=True, sequence_stage="stats"),
    )
    scheduler = RuntimeTransitionScheduler()
    transition = await scheduler.next_transition(lobby=lobby, snapshot=snapshot, runtime=None)
    assert transition.kind == "hostless_end_game_stage"
    assert transition.delay_seconds == 12
    snapshot.end_game.sequence_stage = "first_place"
    transition = await scheduler.next_transition(lobby=lobby, snapshot=snapshot, runtime=None)
    assert transition.delay_seconds == 4.5
