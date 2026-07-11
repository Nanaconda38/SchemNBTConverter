from __future__ import annotations

import copy
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import nbtlib
from nbtlib import Compound, File, List

from .errors import ConversionError
from .model import BlockRecord, BlockState, EntityRecord, Structure


@dataclass(slots=True)
class OutputChunk:
    origin: tuple[int, int, int]
    size: tuple[int, int, int]
    blocks: list[BlockRecord]
    entities: list[EntityRecord]


def _state_to_nbt(state: BlockState) -> Compound:
    tag = Compound({"Name": nbtlib.String(state.name)})
    if state.properties:
        tag["Properties"] = Compound(
            {key: nbtlib.String(value) for key, value in state.properties}
        )
    return tag


def _adjust_entity(entity: EntityRecord, origin: tuple[int, int, int]) -> EntityRecord:
    pos = tuple(float(v - o) for v, o in zip(entity.position, origin))
    block_pos = tuple(int(v - o) for v, o in zip(entity.block_position, origin))
    data = copy.deepcopy(entity.nbt)
    data["Pos"] = List[nbtlib.Double]([nbtlib.Double(v) for v in pos])
    return EntityRecord(pos, block_pos, data)


def split_structure(
    structure: Structure,
    max_size: int = 48,
    include_air: bool = True,
    force_split: bool = True,
) -> list[OutputChunk]:
    if max_size < 1:
        raise ConversionError("Chunk size must be greater than zero.")
    sx, sy, sz = structure.size
    if min(sx, sy, sz) <= 0:
        raise ConversionError(f"Invalid structure dimensions: {structure.size}")

    chunk_size = max_size if force_split else max(sx, sy, sz)
    nx = math.ceil(sx / chunk_size)
    ny = math.ceil(sy / chunk_size)
    nz = math.ceil(sz / chunk_size)

    grouped_blocks: dict[tuple[int, int, int], list[BlockRecord]] = {}
    for record in structure.blocks.values():
        if not include_air and record.state.is_air and record.nbt is None:
            continue
        x, y, z = record.position
        if not (0 <= x < sx and 0 <= y < sy and 0 <= z < sz):
            continue
        key = (x // chunk_size, y // chunk_size, z // chunk_size)
        grouped_blocks.setdefault(key, []).append(record)

    grouped_entities: dict[tuple[int, int, int], list[EntityRecord]] = {}
    for entity in structure.entities:
        bx = min(max(entity.block_position[0], 0), sx - 1)
        by = min(max(entity.block_position[1], 0), sy - 1)
        bz = min(max(entity.block_position[2], 0), sz - 1)
        key = (bx // chunk_size, by // chunk_size, bz // chunk_size)
        grouped_entities.setdefault(key, []).append(entity)

    chunks: list[OutputChunk] = []
    for cy in range(ny):
        for cz in range(nz):
            for cx in range(nx):
                key = (cx, cy, cz)
                origin = (cx * chunk_size, cy * chunk_size, cz * chunk_size)
                size = (
                    min(chunk_size, sx - origin[0]),
                    min(chunk_size, sy - origin[1]),
                    min(chunk_size, sz - origin[2]),
                )
                source_blocks = grouped_blocks.get(key, [])
                source_entities = grouped_entities.get(key, [])
                if not include_air and not source_blocks and not source_entities:
                    continue
                blocks = [
                    BlockRecord(
                        tuple(v - o for v, o in zip(record.position, origin)),
                        record.state,
                        copy.deepcopy(record.nbt),
                    )
                    for record in source_blocks
                ]
                entities = [_adjust_entity(entity, origin) for entity in source_entities]
                chunks.append(OutputChunk(origin, size, blocks, entities))
    return chunks


def build_vanilla_nbt(chunk: OutputChunk, data_version: int) -> File:
    palette: list[BlockState] = []
    palette_index: dict[BlockState, int] = {}
    block_tags = List[Compound]()

    for record in sorted(chunk.blocks, key=lambda r: (r.position[1], r.position[2], r.position[0])):
        index = palette_index.get(record.state)
        if index is None:
            index = len(palette)
            palette_index[record.state] = index
            palette.append(record.state)
        tag = Compound(
            {
                "pos": List[nbtlib.Int]([nbtlib.Int(v) for v in record.position]),
                "state": nbtlib.Int(index),
            }
        )
        if record.nbt is not None:
            block_nbt = copy.deepcopy(record.nbt)
            for key in ("x", "y", "z", "Pos"):
                block_nbt.pop(key, None)
            tag["nbt"] = block_nbt
        block_tags.append(tag)

    entity_tags = List[Compound]()
    for entity in chunk.entities:
        entity_tags.append(
            Compound(
                {
                    "pos": List[nbtlib.Double]([nbtlib.Double(v) for v in entity.position]),
                    "blockPos": List[nbtlib.Int]([nbtlib.Int(v) for v in entity.block_position]),
                    "nbt": copy.deepcopy(entity.nbt),
                }
            )
        )

    return File(
        {
            "DataVersion": nbtlib.Int(int(data_version)),
            "size": List[nbtlib.Int]([nbtlib.Int(v) for v in chunk.size]),
            "palette": List[Compound]([_state_to_nbt(state) for state in palette]),
            "blocks": block_tags,
            "entities": entity_tags,
        },
        gzipped=True,
        byteorder="big",
        root_name="",
    )


def safe_stem(name: str) -> str:
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
    cleaned = "".join(ch if ch in allowed else "_" for ch in name.strip())
    cleaned = cleaned.strip("_")
    return cleaned or "structure"


def resolve_output_directory(
    input_path: str | Path,
    output_root: str | Path,
    source_root: str | Path | None = None,
) -> Path:
    """Resolve the output directory while optionally preserving the source tree.

    ``source_root`` must be the folder imported by the user.
    For ``source_root/rocks/stone.schem``, the result is
    ``output_root/rocks``. If the file is not contained within that root,
    the conversion intentionally falls back to ``output_root``.
    """

    input_path = Path(input_path).expanduser().resolve()
    output_root = Path(output_root).expanduser()
    if source_root is None:
        return output_root

    try:
        relative_parent = input_path.parent.relative_to(Path(source_root).expanduser().resolve())
    except ValueError:
        return output_root
    return output_root / relative_parent


def convert_file(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    max_size: int = 48,
    split_large: bool = True,
    include_air: bool = True,
    overwrite: bool = False,
    source_root: str | Path | None = None,
    progress: Callable[[str], None] | None = None,
) -> list[Path]:
    from .parsers import load_structure

    input_path = Path(input_path).expanduser().resolve()
    output_dir = resolve_output_directory(input_path, output_dir, source_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    notify = progress or (lambda _message: None)

    notify(f"Reading {input_path.name}…")
    structure = load_structure(input_path)
    should_split = split_large and any(dim > max_size for dim in structure.size)
    chunks = split_structure(
        structure,
        max_size=max_size,
        include_air=include_air,
        force_split=should_split,
    )
    if not chunks:
        raise ConversionError("No blocks or entities are available to export with the selected options.")

    stem = safe_stem(input_path.stem)
    multiple = len(chunks) > 1
    outputs: list[Path] = []
    manifest_chunks: list[dict[str, object]] = []
    planned: list[tuple[OutputChunk, Path]] = []

    for chunk in chunks:
        if multiple:
            cx = chunk.origin[0] // max_size
            cy = chunk.origin[1] // max_size
            cz = chunk.origin[2] // max_size
            filename = f"{stem}_x{cx:02d}_y{cy:02d}_z{cz:02d}.nbt"
        else:
            filename = f"{stem}.nbt"
        planned.append((chunk, output_dir / filename))

    manifest_path = output_dir / f"{stem}_manifest.json" if multiple else None
    conflicts = [path for _, path in planned if path.exists()]
    if manifest_path is not None and manifest_path.exists():
        conflicts.append(manifest_path)
    if conflicts and not overwrite:
        names = ", ".join(path.name for path in conflicts[:5])
        suffix = "…" if len(conflicts) > 5 else ""
        raise ConversionError(f"Output file(s) already exist: {names}{suffix}")

    for index, (chunk, output_path) in enumerate(planned, start=1):
        filename = output_path.name
        notify(f"Writing {filename} ({index}/{len(chunks)})…")
        build_vanilla_nbt(chunk, structure.data_version).save(output_path, gzipped=True, byteorder="big")
        outputs.append(output_path)
        manifest_chunks.append(
            {
                "file": filename,
                "origin": list(chunk.origin),
                "size": list(chunk.size),
                "blocks": len(chunk.blocks),
                "entities": len(chunk.entities),
            }
        )

    if multiple and manifest_path is not None:
        manifest = {
            "source": input_path.name,
            "source_size": list(structure.size),
            "source_offset": list(structure.source_offset),
            "data_version": structure.data_version,
            "chunk_size": max_size,
            "coordinate_system": "origin relative to the complete structure, X/Y/Z axes",
            "chunks": manifest_chunks,
            "warnings": structure.warnings,
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        outputs.append(manifest_path)

    return outputs
