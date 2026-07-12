from __future__ import annotations

import copy
import math
from pathlib import Path
from typing import Iterable

import nbtlib
from litemapy import Schematic
from nbtlib import Compound, List

from .errors import ConversionError
from .legacy import LEGACY_DATA_VERSION, legacy_block_state, read_nibble, read_schematica_mapping
from .model import BlockRecord, BlockState, EntityRecord, Structure


def _load_gzipped_nbt(path: Path):
    try:
        return nbtlib.load(path, gzipped=True)
    except Exception as gzip_error:
        try:
            return nbtlib.load(path, gzipped=False)
        except Exception as plain_error:
            raise ConversionError(
                f"Unable to read NBT file {path.name}: {plain_error}"
            ) from gzip_error


def _unsigned_short(value: int) -> int:
    value = int(value)
    return value & 0xFFFF if value < 0 else value


def decode_varints(raw: Iterable[int], expected_count: int | None = None) -> list[int]:
    """Decode the Sponge VarInt array (signed or unsigned bytes)."""
    values: list[int] = []
    value = 0
    shift = 0
    for item in raw:
        byte = int(item) & 0xFF
        value |= (byte & 0x7F) << shift
        if byte & 0x80:
            shift += 7
            if shift > 35:
                raise ConversionError("Invalid Sponge VarInt (more than 5 bytes).")
        else:
            values.append(value)
            value = 0
            shift = 0
    if shift != 0:
        raise ConversionError("Truncated Sponge VarInt array.")
    if expected_count is not None and len(values) != expected_count:
        raise ConversionError(
            f"Invalid block index count: {len(values)} instead of {expected_count}."
        )
    return values


def _parse_state_identifier(identifier: str) -> BlockState:
    identifier = str(identifier)
    if "[" not in identifier:
        return BlockState.from_parts(identifier)
    name, raw_props = identifier.split("[", 1)
    raw_props = raw_props.rsplit("]", 1)[0]
    props: dict[str, str] = {}
    if raw_props:
        for entry in raw_props.split(","):
            if "=" not in entry:
                raise ConversionError(f"Invalid block property: {identifier}")
            key, value = entry.split("=", 1)
            props[key] = value
    return BlockState.from_parts(name, props)


def _compound_without_keys(source: Compound, excluded: set[str]) -> Compound:
    result = Compound()
    for key, value in source.items():
        if str(key) not in excluded:
            result[str(key)] = copy.deepcopy(value)
    return result


def _extract_block_entity(entry: Compound) -> tuple[tuple[int, int, int], Compound]:
    if "Pos" in entry:
        pos = tuple(int(v) for v in entry["Pos"])
    elif all(k in entry for k in ("x", "y", "z")):
        pos = (int(entry["x"]), int(entry["y"]), int(entry["z"]))
    else:
        raise ConversionError("Block entity has no position (Pos or x/y/z).")

    data = Compound()
    nested = entry.get("Data")
    if isinstance(nested, Compound):
        for key, value in nested.items():
            data[str(key)] = copy.deepcopy(value)

    for key, value in entry.items():
        key = str(key)
        if key not in {"Pos", "Id", "Data", "x", "y", "z"}:
            data[key] = copy.deepcopy(value)

    if "Id" in entry and "id" not in data:
        data["id"] = nbtlib.String(str(entry["Id"]))
    elif "id" in entry and "id" not in data:
        data["id"] = nbtlib.String(str(entry["id"]))

    for key in ("x", "y", "z"):
        data.pop(key, None)
    return pos, data


def _extract_entity(entry: Compound) -> EntityRecord:
    nested = entry.get("Data")
    data = Compound()
    if isinstance(nested, Compound):
        for key, value in nested.items():
            data[str(key)] = copy.deepcopy(value)
    for key, value in entry.items():
        key = str(key)
        if key not in {"Id", "Data"}:
            data[key] = copy.deepcopy(value)
    if "Id" in entry and "id" not in data:
        data["id"] = nbtlib.String(str(entry["Id"]))
    elif "id" in entry and "id" not in data:
        data["id"] = nbtlib.String(str(entry["id"]))

    raw_pos = entry.get("Pos", data.get("Pos"))
    if raw_pos is None:
        raise ConversionError("Sponge entity has no Pos position.")
    position = tuple(float(v) for v in raw_pos)
    data["Pos"] = List[nbtlib.Double]([nbtlib.Double(v) for v in position])
    block_position = tuple(math.floor(v) for v in position)
    return EntityRecord(position, block_position, data)


def load_sponge(path: Path) -> Structure:
    nbt = _load_gzipped_nbt(path)
    root = nbt.get("Schematic", nbt)
    if not isinstance(root, Compound):
        raise ConversionError("Missing or invalid Sponge Schematic root.")

    version = int(root.get("Version", 2))
    width = _unsigned_short(root.get("Width", 0))
    height = _unsigned_short(root.get("Height", 0))
    length = _unsigned_short(root.get("Length", 0))
    if min(width, height, length) <= 0:
        raise ConversionError(f"Invalid Sponge dimensions: {width}×{height}×{length}.")

    if version >= 3 and "Blocks" in root:
        container = root["Blocks"]
        palette_tag = container.get("Palette")
        data_tag = container.get("Data", container.get("BlockData"))
        block_entities = container.get("BlockEntities", List[Compound]())
    else:
        container = root
        palette_tag = root.get("Palette", root.get("BlockPalette"))
        data_tag = root.get("BlockData", root.get("Data"))
        block_entities = root.get("BlockEntities", root.get("TileEntities", List[Compound]()))

    if palette_tag is None or data_tag is None:
        raise ConversionError("The .schem file is missing its palette or block data.")

    palette: dict[int, BlockState] = {}
    for identifier, index in palette_tag.items():
        palette[int(index)] = _parse_state_identifier(str(identifier))

    volume = width * height * length
    try:
        indices = decode_varints(data_tag, volume)
    except ConversionError:
        raw = [int(v) & 0xFF for v in data_tag]
        if len(raw) == volume:
            indices = raw
        else:
            raise

    be_by_pos: dict[tuple[int, int, int], Compound] = {}
    for entry in block_entities:
        pos, data = _extract_block_entity(entry)
        be_by_pos[pos] = data

    blocks: dict[tuple[int, int, int], BlockRecord] = {}
    for flat_index, palette_index in enumerate(indices):
        try:
            state = palette[palette_index]
        except KeyError as exc:
            raise ConversionError(f"Unknown palette index: {palette_index}.") from exc
        x = flat_index % width
        z = (flat_index // width) % length
        y = flat_index // (width * length)
        pos = (x, y, z)
        blocks[pos] = BlockRecord(pos, state, be_by_pos.get(pos))

    entities: list[EntityRecord] = []
    for entry in root.get("Entities", List[Compound]()):
        entities.append(_extract_entity(entry))

    offset_raw = root.get("Offset", [0, 0, 0])
    offset = tuple(int(v) for v in offset_raw)
    warnings: list[str] = []
    if version not in {2, 3}:
        warnings.append(f"Non-standard Sponge version {version}; best-effort conversion was used.")

    return Structure(
        size=(width, height, length),
        data_version=int(root.get("DataVersion", 0)),
        blocks=blocks,
        entities=entities,
        source_offset=offset,
        warnings=warnings,
    )


def load_legacy_schematic(path: Path) -> Structure:
    nbt = _load_gzipped_nbt(path)
    root = nbt.get("Schematic", nbt)
    if not isinstance(root, Compound):
        raise ConversionError("Missing or invalid legacy schematic root.")

    width = _unsigned_short(root.get("Width", 0))
    height = _unsigned_short(root.get("Height", 0))
    length = _unsigned_short(root.get("Length", 0))
    if min(width, height, length) <= 0:
        raise ConversionError(f"Invalid legacy schematic dimensions: {width}×{height}×{length}.")

    block_ids = root.get("Blocks")
    metadata = root.get("Data")
    if block_ids is None or metadata is None:
        raise ConversionError("The .schematic file is missing its Blocks or Data array.")

    volume = width * height * length
    if len(block_ids) != volume or len(metadata) * 2 < volume:
        raise ConversionError("The .schematic block arrays do not match its dimensions.")

    add_blocks = root.get("AddBlocks")
    if add_blocks is not None and len(add_blocks) * 2 < volume:
        raise ConversionError("The .schematic AddBlocks array is too short.")

    block_entities = root.get("TileEntities", root.get("BlockEntities", List[Compound]()))
    be_by_pos: dict[tuple[int, int, int], Compound] = {}
    for entry in block_entities:
        pos, data = _extract_block_entity(entry)
        be_by_pos[pos] = data

    mapping = read_schematica_mapping(root)
    blocks: dict[tuple[int, int, int], BlockRecord] = {}
    for flat_index in range(volume):
        block_id = int(block_ids[flat_index]) & 0xFF
        if add_blocks is not None:
            block_id |= read_nibble(add_blocks, flat_index) << 8
        state = legacy_block_state(block_id, read_nibble(metadata, flat_index), mapping)
        x = flat_index % width
        z = (flat_index // width) % length
        y = flat_index // (width * length)
        pos = (x, y, z)
        blocks[pos] = BlockRecord(pos, state, be_by_pos.get(pos))

    entities = [_extract_entity(entry) for entry in root.get("Entities", List[Compound]())]
    warnings = [
        "Legacy .schematic block IDs and metadata were converted from the 1.12 format.",
    ]
    materials = str(root.get("Materials", "Alpha"))
    if materials.lower() != "alpha":
        warnings.append(f"Unexpected legacy Materials value: {materials}.")

    return Structure(
        size=(width, height, length),
        data_version=int(root.get("DataVersion", LEGACY_DATA_VERSION)),
        blocks=blocks,
        entities=entities,
        source_offset=(0, 0, 0),
        warnings=warnings,
    )


def load_litematic(path: Path) -> Structure:
    try:
        schematic = Schematic.load(path)
    except Exception as exc:
        raise ConversionError(f"Unable to read .litematic file {path.name}: {exc}") from exc
    if not schematic.regions:
        raise ConversionError("The .litematic file does not contain any regions.")

    min_x = min(region.min_schem_x() for region in schematic.regions.values())
    min_y = min(region.min_schem_y() for region in schematic.regions.values())
    min_z = min(region.min_schem_z() for region in schematic.regions.values())
    max_x = max(region.max_schem_x() for region in schematic.regions.values())
    max_y = max(region.max_schem_y() for region in schematic.regions.values())
    max_z = max(region.max_schem_z() for region in schematic.regions.values())
    size = (max_x - min_x + 1, max_y - min_y + 1, max_z - min_z + 1)

    blocks: dict[tuple[int, int, int], BlockRecord] = {}
    entities: list[EntityRecord] = []
    warnings: list[str] = []

    # Region order is preserved: when regions overlap, the last one wins.
    for region_name, region in schematic.regions.items():
        tile_entities: dict[tuple[int, int, int], Compound] = {}
        for tile in region.tile_entities:
            local = tuple(int(v) for v in tile.position)
            data = _compound_without_keys(tile.data, {"x", "y", "z"})
            tile_entities[local] = data

        for local_x, local_y, local_z in region.block_positions():
            block = region[local_x, local_y, local_z]
            global_pos = (
                region.x + local_x - min_x,
                region.y + local_y - min_y,
                region.z + local_z - min_z,
            )
            state = BlockState.from_parts(block.id, dict(block.properties()))
            local_pos = (local_x, local_y, local_z)
            blocks[global_pos] = BlockRecord(global_pos, state, tile_entities.get(local_pos))

        for entity in region.entities:
            global_position = (
                float(region.x + entity.position[0] - min_x),
                float(region.y + entity.position[1] - min_y),
                float(region.z + entity.position[2] - min_z),
            )
            data = copy.deepcopy(entity.data)
            data["Pos"] = List[nbtlib.Double]([nbtlib.Double(v) for v in global_position])
            entities.append(
                EntityRecord(
                    global_position,
                    tuple(math.floor(v) for v in global_position),
                    data,
                )
            )

        if region.tile_entities and len(tile_entities) != len(region.tile_entities):
            warnings.append(f"Some block entities from region {region_name!r} were ignored.")

    return Structure(
        size=size,
        data_version=int(schematic.mc_version),
        blocks=blocks,
        entities=entities,
        source_offset=(min_x, min_y, min_z),
        warnings=warnings,
    )


def load_structure(path: str | Path) -> Structure:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".schem":
        return load_sponge(path)
    if suffix == ".schematic":
        return load_legacy_schematic(path)
    if suffix == ".litematic":
        return load_litematic(path)
    raise ConversionError(f"Unsupported file extension: {path.suffix}")
