from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


class ItemType(StrEnum):
    NOTE = "note"
    IMAGE = "image"
    PIN = "pin"
    TEXT = "text"
    GROUP = "group"


@dataclass(slots=True)
class BoardItemModel:
    type: ItemType
    x: float
    y: float
    width: float = 220
    height: float = 150
    rotation: float = 0
    z: float = 0
    status: str = "Nowe"
    tags: list[str] = field(default_factory=list)
    locked: bool = False
    payload: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=now_iso)
    modified_at: str = field(default_factory=now_iso)

    def copy(self, *, offset: float = 24) -> "BoardItemModel":
        return BoardItemModel(
            type=self.type, x=self.x + offset, y=self.y + offset,
            width=self.width, height=self.height, rotation=self.rotation,
            z=self.z + 1, status=self.status, tags=list(self.tags),
            locked=self.locked, payload=dict(self.payload),
        )

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["type"] = self.type.value
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BoardItemModel":
        values = dict(data)
        values["type"] = ItemType(values["type"])
        return cls(**values)


@dataclass(slots=True)
class ConnectionModel:
    source_id: str
    target_id: str
    color: str = "#60a5fa"
    width: float = 2
    style: str = "solid"
    label: str = ""
    direction: str = "forward"
    relation_type: str = "jest powiązany z"
    confidence: str = "nieznany"
    branch_from_id: str = ""
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CaseMetadata:
    name: str
    description: str = ""
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=now_iso)
    modified_at: str = field(default_factory=now_iso)
    camera_x: float = 0
    camera_y: float = 0
    zoom: float = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AnalysisRecord:
    kind: str
    title: str
    data: dict[str, Any] = field(default_factory=dict)
    item_ids: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    status: str = ""
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=now_iso)
    modified_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
