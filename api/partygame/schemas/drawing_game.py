"""Drawing Mashup preparation and viewer-specific wire contracts."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class DrawingSettings(BaseModel):
    writing_seconds: int = Field(default=90, ge=30, le=300)
    drawing_seconds: int = Field(default=90, ge=30, le=300)
    voting_seconds: int = Field(default=30, ge=10, le=120)
    language: Literal["en", "et"] = "en"


class DrawingMetadata(BaseModel):
    id: Literal["drawing_mashup"] = "drawing_mashup"
    title: str = "Drawing Mashup"
    theme: None = None


class PreparedDrawingSession(BaseModel):
    version: Literal[2] = 2
    session_id: str
    definition: DrawingMetadata = Field(default_factory=DrawingMetadata)
    settings: DrawingSettings = Field(default_factory=DrawingSettings)
    seed: int
    fallback_version: Literal[1] = 1


class DrawingText(BaseModel):
    text: str = ""
    fallback: int | None = None


class MashupArtwork(BaseModel):
    id: str
    topic: DrawingText
    criterion: DrawingText | None = None
    value: Any = None
    revision: int = 0
    player_id: str | None = None
    player_name: str | None = None
    vote_count: int = 0
    points: int = 0
    own: bool = False


class MashupBallot(BaseModel):
    drawing_id: str | None = None
    topic: bool = False
    criterion: bool = False


class MashupRevealedVote(BaseModel):
    voter_id: str
    voter_name: str
    drawing_id: str


class MashupMatchup(BaseModel):
    id: str
    topic: DrawingText
    # Withheld during the showcase so phones cannot read it before the reveal.
    criterion: DrawingText | None = None
    drawings: list[MashupArtwork] = Field(default_factory=list)
    can_commend_topic: bool = False
    can_commend_criterion: bool = False
    topic_author: str | None = None
    criterion_author: str | None = None
    topic_points: int = 0
    criterion_points: int = 0
    allocation: Literal["votes", "uncontested", "no_votes", "empty"] | None = None
    revealed_votes: list[MashupRevealedVote] = Field(default_factory=list)


class DrawingGameView(BaseModel):
    phase: Literal[
        "waiting",
        "writing",
        "drawing",
        "showcase",
        "criterion_reveal",
        "voting",
        "results",
        "finished",
    ] = "waiting"
    phase_id: int = 0
    deadline: float | None = None
    remaining_seconds: float | None = None
    server_time: float | None = None
    reveal_duration: float | None = None
    paused: bool = False
    language: Literal["en", "et"] = "en"
    participant_ids: list[str] = Field(default_factory=list)
    ready_ids: list[str] = Field(default_factory=list)
    # Players whose action still holds the phase open; artists never vote on their matchup.
    waiting_ids: list[str] = Field(default_factory=list)
    is_participant: bool = False
    # Drawing phase pacing: each player has this many drawings, each budgeted this long.
    drawing_count: int = 0
    drawing_seconds: int | None = None
    prompt: dict[str, Any] | None = None
    assignments: list[MashupArtwork] = Field(default_factory=list)
    matchup: MashupMatchup | None = None
    matchup_number: int = 0
    matchup_count: int = 0
    ballot: MashupBallot | None = None
    gallery: list[MashupArtwork] = Field(default_factory=list)


class DrawingCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type_: Literal["drawing_command"] = "drawing_command"
    action: Literal["start", "prompt", "draw", "ready", "ballot", "pause", "resume", "advance"]
    run_id: str
    phase_id: int = 0
    request_id: str = Field(min_length=1, max_length=100)
    assignment_id: str | None = None
    revision: int = Field(default=0, ge=0)
    topic: str = Field(default="", max_length=160)
    criterion: str = Field(default="", max_length=240)
    value: Any = None
    ballot: MashupBallot | None = None
    matchup_id: str | None = None
