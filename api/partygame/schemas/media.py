from pathlib import Path
from enum import StrEnum, auto

from pydantic import BaseModel


class MediaKind(StrEnum):
    IMAGE = auto()
    AUDIO = auto()
    VIDEO = auto()


class MediaAsset(BaseModel):
    id: str
    kind: MediaKind
    storage_path: str
    original_filename: str
    content_type: str
    size_bytes: int
    public_url: str

    @property
    def storage_path_obj(self) -> Path:
        return Path(self.storage_path)
