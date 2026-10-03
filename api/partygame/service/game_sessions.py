"""Prepare once, then resolve private session content independently of its source."""

from secrets import randbits
from typing import Protocol
from uuid import uuid4

from fastapi import HTTPException

from partygame.schemas.calorie_game import CalorieGameSettings
from partygame.schemas.drawing_game import DrawingMetadata, DrawingSettings, PreparedDrawingSession
from partygame.schemas.game_definition import GameDefinition
from partygame.schemas.game_session import PreparedSession, RoundBundle, RoundOrigin, SourceMetadata
from partygame.schemas.lobby import CreateGame, Lobby
from partygame.schemas.price_game import PriceGameSettings
from partygame.service.calories.datasets import CalorieDatasets
from partygame.service.calories.generator import InsufficientCalorieData
from partygame.service.definitions import (
    DefinitionProvider,
    PostgresDefinitionProvider,
    validate_definition,
)
from partygame.service.game_catalog import require_game_type
from partygame.service.prices.datasets import PriceDatasets
from partygame.service.prices.generator import InsufficientPriceData
from partygame.state import GameStateRepository
from partygame.state.auth_models import UserRecord

SESSION_COMPONENT_ID = "prepared_session"


def compose_rounds(
    bundles: list[RoundBundle], *, definition_id: str, title: str, description: str | None = None
) -> PreparedSession:
    rounds = []
    origins = []
    for bundle_index, bundle in enumerate(bundles):
        for round_index, source_round in enumerate(bundle.rounds):
            round_definition = source_round.model_copy(deep=True)
            round_definition.id = f"b{bundle_index}-r{round_index}"
            step_ids = {}
            for step_index, step in enumerate(round_definition.steps):
                runtime_id = f"{round_definition.id}-s{step_index}"
                step_ids[runtime_id] = step.id
                step.id = runtime_id
            rounds.append(round_definition)
            origins.append(
                RoundOrigin(
                    runtime_round_id=round_definition.id,
                    source_round_id=source_round.id,
                    step_ids=step_ids,
                    source=bundle.source.model_copy(deep=True),
                )
            )
    definition = GameDefinition(
        id=definition_id,
        title=title,
        description=description,
        theme=bundles[0].theme.model_copy(deep=True) if bundles and bundles[0].theme else None,
        rounds=rounds,
    )
    validate_definition(definition)
    return PreparedSession(definition=definition, origins=origins)


class SessionBuilder[Settings](Protocol):
    async def prepare(self, settings: Settings, user: UserRecord | None) -> PreparedSession: ...


class TriviaSessionBuilder:
    def __init__(self, provider: DefinitionProvider):
        self.provider = provider

    async def prepare(self, settings: CreateGame, user: UserRecord | None) -> PreparedSession:
        if isinstance(self.provider, PostgresDefinitionProvider):
            definition = await self.provider.require_playable(settings.definition_id, user)
        else:
            definition = await self.provider.load(settings.definition_id)
        return compose_rounds(
            [
                RoundBundle(
                    rounds=definition.rounds,
                    theme=definition.theme,
                    source=SourceMetadata(source_id=definition.id),
                )
            ],
            definition_id=definition.id,
            title=definition.title,
            description=definition.description,
        )


class PriceSessionBuilder:
    async def prepare(self, settings: CreateGame, user: UserRecord | None) -> PreparedSession:
        session_id = uuid4().hex
        try:
            bundles, datasets = await PriceDatasets().prepare(
                settings.price_settings or PriceGameSettings(), randbits(32), session_id
            )
        except InsufficientPriceData as error:
            raise HTTPException(status_code=409, detail="price_content_unavailable") from error
        prepared = compose_rounds(bundles, definition_id="price_guessing", title="Price Guessing")
        prepared.session_id = session_id
        prepared.datasets = [SourceMetadata.model_validate(item) for item in datasets]
        return PreparedSession.model_validate(prepared.model_dump())


class CalorieSessionBuilder:
    async def prepare(self, settings: CreateGame, user: UserRecord | None) -> PreparedSession:
        session_id = uuid4().hex
        try:
            bundles, datasets = await CalorieDatasets().prepare(
                settings.calorie_settings or CalorieGameSettings(), randbits(32), session_id
            )
        except InsufficientCalorieData as error:
            raise HTTPException(status_code=409, detail="calorie_content_unavailable") from error
        prepared = compose_rounds(
            bundles, definition_id="calorie_guessing", title="Calorie Guessing"
        )
        prepared.session_id = session_id
        prepared.datasets = [SourceMetadata.model_validate(item) for item in datasets]
        return PreparedSession.model_validate(prepared.model_dump())


async def prepare_session(
    settings: CreateGame, user: UserRecord | None, provider: DefinitionProvider
) -> PreparedSession | PreparedDrawingSession:
    require_game_type(settings.game_type, host_enabled=settings.host_enabled)
    if settings.game_type == "drawing_mashup":
        options = settings.drawing_settings or DrawingSettings()
        return PreparedDrawingSession(
            session_id=uuid4().hex,
            seed=randbits(32),
            settings=options,
            definition=DrawingMetadata(
                title="Joonistussegadus" if options.language == "et" else "Drawing Mashup"
            ),
        )
    builders: dict[str, SessionBuilder[CreateGame]] = {
        "trivia": TriviaSessionBuilder(provider),
        "price_guessing": PriceSessionBuilder(),
        "calorie_guessing": CalorieSessionBuilder(),
    }
    try:
        return await builders[settings.game_type].prepare(settings, user)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error


async def load_session_definition(
    repo: GameStateRepository, lobby: Lobby, provider: DefinitionProvider
) -> GameDefinition:
    if lobby.session_version is None:
        return await provider.load(lobby.definition_id or "quiz_demo")
    if lobby.session_version != 1:
        raise RuntimeError("Unsupported prepared session version")
    record = await repo.get_component_state(lobby.id, SESSION_COMPONENT_ID)
    if not record:
        raise RuntimeError("Prepared session is missing")
    return PreparedSession.model_validate(record["snapshot"]).definition
