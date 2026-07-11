from __future__ import annotations

from pathlib import Path

import nbtlib
from litemapy import BlockState as LiteBlockState
from litemapy import Region, Schematic
from nbtlib import ByteArray, Compound, File, Int, IntArray, List, Short, String

from schem_nbt_converter.parsers import decode_varints, load_litematic, load_sponge
from schem_nbt_converter.writer import convert_file


def encode_varints(values: list[int]) -> ByteArray:
    output: list[int] = []
    for value in values:
        while True:
            byte = value & 0x7F
            value >>= 7
            if value:
                output.append(byte | 0x80)
            else:
                output.append(byte)
                break
    signed = [v - 256 if v >= 128 else v for v in output]
    return ByteArray(signed)


def save_file(path: Path, root: dict) -> None:
    File(root, gzipped=True).save(path, gzipped=True)


def test_varints_over_127() -> None:
    values = [0, 1, 127, 128, 129, 255, 300, 16384]
    assert decode_varints(encode_varints(values), len(values)) == values


def test_sponge_v2_to_vanilla(tmp_path: Path) -> None:
    source = tmp_path / "simple.schem"
    root = {
        "Version": Int(2),
        "DataVersion": Int(3465),
        "Width": Short(2),
        "Height": Short(1),
        "Length": Short(1),
        "Offset": IntArray([0, 0, 0]),
        "Palette": Compound({
            "minecraft:stone": Int(0),
            "minecraft:oak_log[axis=x]": Int(1),
        }),
        "PaletteMax": Int(2),
        "BlockData": encode_varints([0, 1]),
        "BlockEntities": List[Compound](),
        "Entities": List[Compound](),
    }
    save_file(source, root)

    parsed = load_sponge(source)
    assert parsed.size == (2, 1, 1)
    assert parsed.blocks[(1, 0, 0)].state.name == "minecraft:oak_log"
    assert parsed.blocks[(1, 0, 0)].state.properties_dict == {"axis": "x"}

    output = tmp_path / "out"
    files = convert_file(source, output)
    assert files == [output / "simple.nbt"]
    result = nbtlib.load(files[0], gzipped=True)
    assert [int(v) for v in result["size"]] == [2, 1, 1]
    assert len(result["palette"]) == 2
    assert len(result["blocks"]) == 2


def test_sponge_v3_block_entity(tmp_path: Path) -> None:
    source = tmp_path / "v3.schem"
    schematic = Compound({
        "Version": Int(3),
        "DataVersion": Int(3700),
        "Width": Short(1),
        "Height": Short(1),
        "Length": Short(1),
        "Offset": IntArray([5, 6, 7]),
        "Blocks": Compound({
            "Palette": Compound({"minecraft:chest[facing=north,type=single,waterlogged=false]": Int(0)}),
            "Data": encode_varints([0]),
            "BlockEntities": List[Compound]([
                Compound({
                    "Pos": IntArray([0, 0, 0]),
                    "Id": String("minecraft:chest"),
                    "Data": Compound({"CustomName": String('{"text":"Test"}')})
                })
            ]),
        }),
        "Entities": List[Compound](),
    })
    save_file(source, {"Schematic": schematic})

    files = convert_file(source, tmp_path / "out")
    result = nbtlib.load(files[0], gzipped=True)
    block = result["blocks"][0]
    assert str(block["nbt"]["id"]) == "minecraft:chest"
    assert "CustomName" in block["nbt"]
    assert "x" not in block["nbt"]


def test_litematic_multiple_regions(tmp_path: Path) -> None:
    region_a = Region(0, 0, 0, 2, 1, 1)
    region_a[0, 0, 0] = LiteBlockState("minecraft:stone")
    region_a[1, 0, 0] = LiteBlockState("minecraft:dirt")
    region_b = Region(3, 0, 0, 1, 1, 1)
    region_b[0, 0, 0] = LiteBlockState("minecraft:gold_block")
    schematic = Schematic(
        name="multi",
        author="test",
        regions={"A": region_a, "B": region_b},
        mc_version=3700,
    )
    source = tmp_path / "multi.litematic"
    schematic.save(source)

    parsed = load_litematic(source)
    assert parsed.size == (4, 1, 1)
    assert parsed.blocks[(0, 0, 0)].state.name == "minecraft:stone"
    assert parsed.blocks[(3, 0, 0)].state.name == "minecraft:gold_block"

    files = convert_file(source, tmp_path / "out")
    result = nbtlib.load(files[0], gzipped=True)
    assert [int(v) for v in result["size"]] == [4, 1, 1]
    positions = {tuple(int(v) for v in block["pos"]) for block in result["blocks"]}
    assert (0, 0, 0) in positions
    assert (3, 0, 0) in positions
    assert (2, 0, 0) not in positions


def test_split_large_structure(tmp_path: Path) -> None:
    source = tmp_path / "large.schem"
    root = {
        "Version": Int(2),
        "DataVersion": Int(3700),
        "Width": Short(50),
        "Height": Short(1),
        "Length": Short(1),
        "Offset": IntArray([0, 0, 0]),
        "Palette": Compound({"minecraft:stone": Int(0)}),
        "PaletteMax": Int(1),
        "BlockData": encode_varints([0] * 50),
        "BlockEntities": List[Compound](),
        "Entities": List[Compound](),
    }
    save_file(source, root)

    files = convert_file(source, tmp_path / "out", max_size=48, split_large=True)
    nbt_files = [p for p in files if p.suffix == ".nbt"]
    assert len(nbt_files) == 2
    sizes = [tuple(int(v) for v in nbtlib.load(p, gzipped=True)["size"]) for p in nbt_files]
    assert sizes == [(48, 1, 1), (2, 1, 1)]
    assert any(p.name.endswith("_manifest.json") for p in files)


def test_preserve_imported_folder_tree(tmp_path: Path) -> None:
    source_root = tmp_path / "worldpainter-trees-main"
    source = source_root / "rocks" / "granite" / "stone01.schem"
    source.parent.mkdir(parents=True)
    root = {
        "Version": Int(2),
        "DataVersion": Int(3700),
        "Width": Short(1),
        "Height": Short(1),
        "Length": Short(1),
        "Offset": IntArray([0, 0, 0]),
        "Palette": Compound({"minecraft:stone": Int(0)}),
        "PaletteMax": Int(1),
        "BlockData": encode_varints([0]),
        "BlockEntities": List[Compound](),
        "Entities": List[Compound](),
    }
    save_file(source, root)

    output_root = tmp_path / "out"
    files = convert_file(source, output_root, source_root=source_root)

    assert files == [output_root / "rocks" / "granite" / "stone01.nbt"]
    assert files[0].is_file()
