from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class BlockState:
    name: str
    properties: tuple[tuple[str, str], ...] = ()

    @classmethod
    def from_parts(cls, name: str, properties: dict[str, str] | None = None) -> "BlockState":
        props = tuple(sorted((str(k), str(v)) for k, v in (properties or {}).items()))
        return cls(str(name), props)

    @property
    def properties_dict(self) -> dict[str, str]:
        return dict(self.properties)

    @property
    def is_air(self) -> bool:
        return self.name in {"minecraft:air", "minecraft:cave_air", "minecraft:void_air"}


@dataclass(slots=True)
class BlockRecord:
    position: tuple[int, int, int]
    state: BlockState
    nbt: Any | None = None


@dataclass(slots=True)
class EntityRecord:
    position: tuple[float, float, float]
    block_position: tuple[int, int, int]
    nbt: Any


@dataclass(slots=True)
class Structure:
    size: tuple[int, int, int]
    data_version: int
    blocks: dict[tuple[int, int, int], BlockRecord] = field(default_factory=dict)
    entities: list[EntityRecord] = field(default_factory=list)
    source_offset: tuple[int, int, int] = (0, 0, 0)
    warnings: list[str] = field(default_factory=list)
