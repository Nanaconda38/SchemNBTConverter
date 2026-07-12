from __future__ import annotations

from collections.abc import Mapping

from .errors import ConversionError
from .model import BlockState

LEGACY_DATA_VERSION = 1343  # Minecraft Java 1.12.2

# Legacy IDs are stable; names are the 1.12 registry names used by .schematic.
LEGACY_BLOCK_NAMES = {
    0: "air", 1: "stone", 2: "grass", 3: "dirt", 4: "cobblestone", 5: "planks",
    6: "sapling", 7: "bedrock", 8: "flowing_water", 9: "water", 10: "flowing_lava",
    11: "lava", 12: "sand", 13: "gravel", 14: "gold_ore", 15: "iron_ore",
    16: "coal_ore", 17: "log", 18: "leaves", 19: "sponge", 20: "glass",
    21: "lapis_ore", 22: "lapis_block", 23: "dispenser", 24: "sandstone",
    25: "noteblock", 26: "bed", 27: "golden_rail", 28: "detector_rail",
    29: "sticky_piston", 30: "web", 31: "tallgrass", 32: "deadbush", 33: "piston",
    34: "piston_head", 35: "wool", 36: "piston_extension", 37: "yellow_flower",
    38: "red_flower", 39: "brown_mushroom", 40: "red_mushroom", 41: "gold_block",
    42: "iron_block", 43: "double_stone_slab", 44: "stone_slab", 45: "brick_block",
    46: "tnt", 47: "bookshelf", 48: "mossy_cobblestone", 49: "obsidian", 50: "torch",
    51: "fire", 52: "mob_spawner", 53: "oak_stairs", 54: "chest", 55: "redstone_wire",
    56: "diamond_ore", 57: "diamond_block", 58: "crafting_table", 59: "wheat",
    60: "farmland", 61: "furnace", 62: "lit_furnace", 63: "standing_sign",
    64: "wooden_door", 65: "ladder", 66: "rail", 67: "stone_stairs", 68: "wall_sign",
    69: "lever", 70: "stone_pressure_plate", 71: "iron_door", 72: "wooden_pressure_plate",
    73: "redstone_ore", 74: "lit_redstone_ore", 75: "unlit_redstone_torch",
    76: "redstone_torch", 77: "stone_button", 78: "snow_layer", 79: "ice", 80: "snow",
    81: "cactus", 82: "clay", 83: "reeds", 84: "jukebox", 85: "fence", 86: "pumpkin",
    87: "netherrack", 88: "soul_sand", 89: "glowstone", 90: "portal", 91: "lit_pumpkin",
    92: "cake", 93: "unpowered_repeater", 94: "powered_repeater", 95: "stained_glass",
    96: "trapdoor", 97: "monster_egg", 98: "stonebrick", 99: "brown_mushroom_block",
    100: "red_mushroom_block", 101: "iron_bars", 102: "glass_pane", 103: "melon_block",
    104: "pumpkin_stem", 105: "melon_stem", 106: "vine", 107: "fence_gate",
    108: "brick_stairs", 109: "stone_brick_stairs", 110: "mycelium", 111: "waterlily",
    112: "nether_brick", 113: "nether_brick_fence", 114: "nether_brick_stairs",
    115: "nether_wart", 116: "enchanting_table", 117: "brewing_stand", 118: "cauldron",
    119: "end_portal", 120: "end_portal_frame", 121: "end_stone", 122: "dragon_egg",
    123: "redstone_lamp", 124: "lit_redstone_lamp", 125: "double_wooden_slab",
    126: "wooden_slab", 127: "cocoa", 128: "sandstone_stairs", 129: "emerald_ore",
    130: "ender_chest", 131: "tripwire_hook", 132: "tripwire", 133: "emerald_block",
    134: "spruce_stairs", 135: "birch_stairs", 136: "jungle_stairs", 137: "command_block",
    138: "beacon", 139: "cobblestone_wall", 140: "flower_pot", 141: "carrots",
    142: "potatoes", 143: "wooden_button", 144: "skull", 145: "anvil", 146: "trapped_chest",
    147: "light_weighted_pressure_plate", 148: "heavy_weighted_pressure_plate",
    149: "unpowered_comparator", 150: "powered_comparator", 151: "daylight_detector",
    152: "redstone_block", 153: "quartz_ore", 154: "hopper", 155: "quartz_block",
    156: "quartz_stairs", 157: "activator_rail", 158: "dropper", 159: "stained_hardened_clay",
    160: "stained_glass_pane", 161: "leaves2", 162: "log2", 163: "acacia_stairs",
    164: "dark_oak_stairs", 165: "slime", 166: "barrier", 167: "iron_trapdoor",
    168: "prismarine", 169: "sea_lantern", 170: "hay_block", 171: "carpet",
    172: "hardened_clay", 173: "coal_block", 174: "packed_ice", 175: "double_plant",
    176: "standing_banner", 177: "wall_banner", 178: "daylight_detector_inverted",
    179: "red_sandstone", 180: "red_sandstone_stairs", 181: "double_stone_slab2",
    182: "stone_slab2", 183: "spruce_fence_gate", 184: "birch_fence_gate",
    185: "jungle_fence_gate", 186: "dark_oak_fence_gate", 187: "acacia_fence_gate",
    188: "spruce_fence", 189: "birch_fence", 190: "jungle_fence", 191: "dark_oak_fence",
    192: "acacia_fence", 193: "spruce_door", 194: "birch_door", 195: "jungle_door",
    196: "acacia_door", 197: "dark_oak_door", 198: "end_rod", 199: "chorus_plant",
    200: "chorus_flower", 201: "purpur_block", 202: "purpur_pillar", 203: "purpur_stairs",
    204: "purpur_double_slab", 205: "purpur_slab", 206: "end_bricks", 207: "beetroots",
    208: "grass_path", 209: "end_gateway", 210: "repeating_command_block",
    211: "chain_command_block", 212: "frosted_ice", 213: "magma", 214: "nether_wart_block",
    215: "red_nether_brick", 216: "bone_block", 217: "structure_void", 218: "observer",
    219: "white_shulker_box", 220: "orange_shulker_box", 221: "magenta_shulker_box",
    222: "light_blue_shulker_box", 223: "yellow_shulker_box", 224: "lime_shulker_box",
    225: "pink_shulker_box", 226: "gray_shulker_box", 227: "light_gray_shulker_box",
    228: "cyan_shulker_box", 229: "purple_shulker_box", 230: "blue_shulker_box",
    231: "brown_shulker_box", 232: "green_shulker_box", 233: "red_shulker_box",
    234: "black_shulker_box", 235: "white_glazed_terracotta", 236: "orange_glazed_terracotta",
    237: "magenta_glazed_terracotta", 238: "light_blue_glazed_terracotta",
    239: "yellow_glazed_terracotta", 240: "lime_glazed_terracotta", 241: "pink_glazed_terracotta",
    242: "gray_glazed_terracotta", 243: "light_gray_glazed_terracotta",
    244: "cyan_glazed_terracotta", 245: "purple_glazed_terracotta", 246: "blue_glazed_terracotta",
    247: "brown_glazed_terracotta", 248: "green_glazed_terracotta",
    249: "red_glazed_terracotta", 250: "black_glazed_terracotta", 251: "concrete",
    252: "concrete_powder", 255: "structure_block",
}

COLORS = (
    "white", "orange", "magenta", "light_blue", "yellow", "lime", "pink", "gray",
    "light_gray", "cyan", "purple", "blue", "brown", "green", "red", "black",
)
WOOD = ("oak", "spruce", "birch", "jungle", "acacia", "dark_oak")
STAIR_FACING = ("east", "west", "south", "north")
STAIR_IDS = {
    53: "oak_stairs", 67: "stone_stairs", 108: "brick_stairs", 109: "stone_brick_stairs",
    114: "nether_brick_stairs", 128: "sandstone_stairs", 134: "spruce_stairs",
    135: "birch_stairs", 136: "jungle_stairs", 156: "quartz_stairs", 163: "acacia_stairs",
    164: "dark_oak_stairs", 180: "red_sandstone_stairs", 203: "purpur_stairs",
}


def _state(name: str, **properties: str) -> BlockState:
    return BlockState.from_parts(name if ":" in name else f"minecraft:{name}", properties)


def _color_state(suffix: str, metadata: int) -> BlockState:
    return _state(f"{COLORS[metadata & 15]}_{suffix}")


def read_schematica_mapping(root: Mapping[str, object]) -> dict[int, str]:
    raw = root.get("SchematicaMapping")
    if not isinstance(raw, Mapping):
        return {}
    result: dict[int, str] = {}
    for key, value in raw.items():
        try:
            if ":" in str(key):
                result[int(value)] = str(key)
            elif ":" in str(value):
                result[int(key)] = str(value)
        except (TypeError, ValueError):
            continue
    return result


def read_nibble(raw: object, index: int) -> int:
    try:
        byte = int(raw[index // 2]) & 0xFF  # type: ignore[index]
    except (IndexError, TypeError, ValueError) as exc:
        raise ConversionError("Invalid legacy nibble array.") from exc
    return (byte >> (4 * (index & 1))) & 0x0F


def legacy_block_state(
    block_id: int,
    metadata: int,
    mapping: Mapping[int, str] | None = None,
) -> BlockState:
    if mapping and block_id in mapping:
        identifier = mapping[block_id]
        return _state(identifier if ":" in identifier else f"minecraft:{identifier}")

    if block_id not in LEGACY_BLOCK_NAMES:
        raise ConversionError(
            f"Unknown legacy block ID {block_id}. A SchematicaMapping entry is required for custom blocks."
        )

    metadata &= 15
    if block_id == 1:
        variants = ("stone", "granite", "polished_granite", "diorite", "polished_diorite", "andesite", "polished_andesite")
        return _state(variants[metadata % len(variants)])
    if block_id == 3:
        variants = ("dirt", "coarse_dirt", "podzol")
        return _state(variants[metadata % len(variants)])
    if block_id == 5:
        return _state(f"{WOOD[metadata % 6]}_planks")
    if block_id == 6:
        return _state(f"{WOOD[metadata % 6]}_sapling")
    if block_id in {8, 9}:
        return _state("water", level=str(metadata if block_id == 8 else 0))
    if block_id in {10, 11}:
        return _state("lava", level=str(metadata if block_id == 10 else 0))
    if block_id in {12}:
        return _state(("sand", "red_sand")[metadata & 1])
    if block_id in {17, 162}:
        names = ("oak", "spruce", "birch", "jungle") if block_id == 17 else ("acacia", "dark_oak")
        axis = {0: "y", 4: "x", 8: "z"}.get(metadata & 12, "y")
        return _state(f"{names[(metadata & 3) % len(names)]}_log", axis=axis)
    if block_id in {18, 161}:
        names = ("oak", "spruce", "birch", "jungle") if block_id == 18 else ("acacia", "dark_oak")
        return _state(f"{names[(metadata & 3) % len(names)]}_leaves")
    if block_id == 24:
        variants = ("sandstone", "chiseled_sandstone", "cut_sandstone")
        return _state(variants[metadata % len(variants)])
    if block_id == 31:
        variants = ("dead_bush", "short_grass", "fern")
        return _state(variants[metadata % len(variants)])
    if block_id == 35:
        return _color_state("wool", metadata)
    if block_id == 37:
        return _state("dandelion")
    if block_id == 38:
        variants = ("poppy", "blue_orchid", "allium", "azure_bluet", "red_tulip", "orange_tulip", "white_tulip", "pink_tulip", "oxeye_daisy")
        return _state(variants[metadata % len(variants)])
    if block_id in {43, 44, 181, 182, 204, 205}:
        names = (
            "stone_slab", "sandstone_slab", "petrified_oak_slab", "cobblestone_slab",
            "brick_slab", "stone_brick_slab", "nether_brick_slab", "quartz_slab",
        )
        if block_id in {181, 182}:
            names = ("red_sandstone_slab",)
        if block_id in {204, 205}:
            names = ("purpur_slab",)
        double = block_id in {43, 125, 181, 204}
        return _state(names[metadata & (len(names) - 1)] if len(names) > 1 else names[0], type="double" if double else ("top" if metadata & 8 else "bottom"))
    if block_id == 45:
        return _state("bricks")
    if block_id in {50}:
        if metadata == 5:
            return _state("torch")
        facing = {1: "east", 2: "west", 3: "south", 4: "north"}.get(metadata)
        return _state("wall_torch", facing=facing) if facing else _state("torch")
    if block_id in STAIR_IDS:
        return _state(
            STAIR_IDS[block_id],
            facing=STAIR_FACING[metadata & 3],
            half="top" if metadata & 4 else "bottom",
            shape="straight",
            waterlogged="false",
        )
    if block_id == 52:
        return _state("spawner")
    if block_id in {63, 68}:
        return _state("oak_sign" if block_id == 63 else "oak_wall_sign")
    if block_id in {62, 74, 91, 124, 149, 150}:
        return _state({62: "furnace", 74: "redstone_ore", 91: "jack_o_lantern", 124: "redstone_lamp", 149: "comparator", 150: "comparator"}[block_id])
    if block_id == 64:
        return _state("oak_door")
    if block_id == 71:
        return _state("iron_door")
    if block_id in {75, 76}:
        return _state("redstone_torch")
    if block_id == 83:
        return _state("sugar_cane")
    if block_id == 85:
        return _state("oak_fence")
    if block_id == 95:
        return _color_state("stained_glass", metadata)
    if block_id == 97:
        variants = ("infested_stone", "infested_cobblestone", "infested_stone_bricks", "infested_mossy_stone_bricks", "infested_cracked_stone_bricks", "infested_chiseled_stone_bricks")
        return _state(variants[metadata % len(variants)])
    if block_id == 98:
        variants = ("stone_bricks", "mossy_stone_bricks", "cracked_stone_bricks", "chiseled_stone_bricks")
        return _state(variants[metadata % len(variants)])
    if block_id == 107:
        return _state("oak_fence_gate")
    if block_id == 111:
        return _state("lily_pad")
    if block_id == 116:
        return _state("enchanting_table")
    if block_id in {125, 126}:
        return _state(f"{WOOD[metadata % 6]}_slab", type="double" if block_id == 125 else ("top" if metadata & 8 else "bottom"))
    if block_id == 139:
        return _state("mossy_cobblestone_wall" if metadata & 1 else "cobblestone_wall")
    if block_id == 143:
        return _state("oak_button")
    if block_id == 144:
        variants = ("skeleton_skull", "wither_skeleton_skull", "zombie_head", "player_head", "creeper_head", "dragon_head")
        return _state(variants[metadata % len(variants)])
    if block_id in {155}:
        variants = ("quartz_block", "chiseled_quartz_block", "quartz_pillar")
        return _state(variants[metadata % len(variants)])
    if block_id == 159:
        return _color_state("terracotta", metadata)
    if block_id == 160:
        return _color_state("stained_glass_pane", metadata)
    if block_id == 168:
        variants = ("prismarine", "prismarine_bricks", "dark_prismarine")
        return _state(variants[metadata % len(variants)])
    if block_id == 171:
        return _color_state("carpet", metadata)
    if block_id == 172:
        return _state("terracotta")
    if block_id == 175:
        variants = ("sunflower", "lilac", "tall_grass", "large_fern", "rose_bush", "peony")
        return _state(variants[metadata % len(variants)])
    if block_id == 176:
        return _color_state("banner", metadata)
    if block_id == 177:
        return _color_state("wall_banner", metadata)
    if block_id == 178:
        return _state("daylight_detector", inverted="true")
    if block_id == 251:
        return _color_state("concrete", metadata)
    if block_id == 252:
        return _color_state("concrete_powder", metadata)

    name = LEGACY_BLOCK_NAMES[block_id]
    overrides = {
        "brick_block": "bricks", "enchanting_table": "enchanting_table", "fence": "oak_fence",
        "fence_gate": "oak_fence_gate", "flowing_lava": "lava", "flowing_water": "water",
        "lit_furnace": "furnace", "mob_spawner": "spawner", "noteblock": "note_block",
        "piston_extension": "moving_piston", "portal": "nether_portal",
        "powered_repeater": "repeater", "reeds": "sugar_cane", "standing_banner": "white_banner",
        "unpowered_repeater": "repeater", "waterlily": "lily_pad", "web": "cobweb",
        "grass_path": "dirt_path",
        "wooden_button": "oak_button", "wooden_door": "oak_door",
        "wooden_pressure_plate": "oak_pressure_plate", "yellow_flower": "dandelion",
    }
    return _state(overrides.get(name, name))
