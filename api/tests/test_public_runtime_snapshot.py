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
