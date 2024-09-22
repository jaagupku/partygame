from typing import List

from pydantic import BaseModel

from .lobby import ControllerComponent, DisplayComponent

class QuestionSchema(BaseModel):
    type_: DisplayComponent
    title: str
    data: str | None


class PlaySchema(BaseModel):
    controller: ControllerComponent
    questions: List[QuestionSchema]


class GameSchema(BaseModel):
    id: str
    games: List[PlaySchema]
