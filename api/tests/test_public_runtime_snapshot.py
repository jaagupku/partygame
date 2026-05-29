import partygame.schemas as schemas
from partygame.service.player import public_runtime_snapshot


def _snapshot(*, input_kind: schemas.PlayerInputKind, evaluation_type: schemas.EvaluationType):
    return schemas.RuntimeSnapshotEvent(
        revision=1,
        lobby=schemas.RuntimeLobbyState(
            id="game-1",
            join_code="ABC123",
            state=schemas.GameState.RUNNING,
        ),
        active_step=schemas.RuntimeStepState(
            id="step-1",
            title="Question",
            input_kind=input_kind,
            evaluation_type=evaluation_type,
        ),
        display_phase="answer_reveal",
        host_answer=schemas.RevealedAnswer(value="secret"),
        submissions=[
            schemas.SubmissionItem(
                player_id="player-1",
                value={"lat": 58.37, "lng": 26.72},
            )
        ],
    )


def test_public_runtime_snapshot_keeps_map_reveal_submissions():
    snapshot = _snapshot(
        input_kind=schemas.PlayerInputKind.MAP,
        evaluation_type=schemas.EvaluationType.MAP_DISTANCE,
    )

    public_snapshot = public_runtime_snapshot(snapshot)

    assert public_snapshot.host_answer is None
    assert public_snapshot.submissions == snapshot.submissions


def test_public_runtime_snapshot_hides_non_map_reveal_submissions():
    snapshot = _snapshot(
        input_kind=schemas.PlayerInputKind.TEXT,
        evaluation_type=schemas.EvaluationType.EXACT_TEXT,
    )

    public_snapshot = public_runtime_snapshot(snapshot)

    assert public_snapshot.host_answer is None
    assert public_snapshot.submissions == []


def test_public_runtime_snapshot_sets_viewer_own_drawing_id_without_owner_order():
    snapshot = _snapshot(
        input_kind=schemas.PlayerInputKind.DRAWING,
        evaluation_type=schemas.EvaluationType.FAVORITE_VOTE,
    ).model_copy(
        update={
            "display_phase": "drawing_vote",
            "drawing_owner_ids": ["player-1", "player-2"],
            "drawing_items": [
                schemas.DrawingVoteItem(id="drawing:0", label="Drawing A", value={}),
                schemas.DrawingVoteItem(id="drawing:1", label="Drawing B", value={}),
            ],
        }
    )

    public_snapshot = public_runtime_snapshot(snapshot, viewer_player_id="player-2")

    assert public_snapshot.own_drawing_id == "drawing:1"
    assert public_snapshot.drawing_owner_ids == []


def test_public_runtime_snapshot_keeps_drawing_vote_rubric():
    snapshot = _snapshot(
        input_kind=schemas.PlayerInputKind.DRAWING,
        evaluation_type=schemas.EvaluationType.FAVORITE_VOTE,
    ).model_copy(
        update={
            "display_phase": "drawing_vote",
            "active_step": schemas.RuntimeStepState(
                id="drawing-step",
                title="Draw a cat",
                input_kind=schemas.PlayerInputKind.DRAWING,
                evaluation_type=schemas.EvaluationType.FAVORITE_VOTE,
                evaluation_points=2,
                evaluation_answer="Cats should have visible whiskers.",
            ),
        }
    )

    public_snapshot = public_runtime_snapshot(snapshot)

    assert public_snapshot.host_answer is None
    assert public_snapshot.active_step is not None
    assert public_snapshot.active_step.evaluation_answer == "Cats should have visible whiskers."
