"""Item system: item IDs (64+), registry, tool tiers, and helpers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Dict, Tuple


# ---------------------------------------------------------------------------
# Tool type / tier enums
# ---------------------------------------------------------------------------

class ToolType(IntEnum):
    NONE = 0
    PICKAXE = 1
    AXE = 2
    SHOVEL = 3
    SWORD = 4
    HOE = 5


class ToolTier(IntEnum):
    NONE = 0
    WOODEN = 1
    STONE = 2
    IRON = 3
    DIAMOND = 4


# Armor equipment slots (index into Inventory.armor). -1 = not armor.
ARMOR_HEAD = 0
ARMOR_CHEST = 1
ARMOR_LEGS = 2
ARMOR_FEET = 3


# ---------------------------------------------------------------------------
# Item IDs (64+ to avoid collision with block IDs 0-63)
# ---------------------------------------------------------------------------

ITEM_WOODEN_PICKAXE = 64
ITEM_STONE_PICKAXE = 65
ITEM_IRON_PICKAXE = 66
ITEM_DIAMOND_PICKAXE = 67
ITEM_WOODEN_AXE = 68
ITEM_STONE_AXE = 69
ITEM_IRON_AXE = 70
ITEM_DIAMOND_AXE = 71
ITEM_WOODEN_SHOVEL = 72
ITEM_STONE_SHOVEL = 73
ITEM_IRON_SHOVEL = 74
ITEM_DIAMOND_SHOVEL = 75
ITEM_WOODEN_SWORD = 76
ITEM_STONE_SWORD = 77
ITEM_IRON_SWORD = 78
ITEM_DIAMOND_SWORD = 79
ITEM_WOODEN_HOE = 80
ITEM_STONE_HOE = 81
ITEM_IRON_HOE = 82
ITEM_DIAMOND_HOE = 83
ITEM_COAL = 84
ITEM_IRON_INGOT = 85
ITEM_GOLD_INGOT = 86
ITEM_DIAMOND = 87
ITEM_RAW_BEEF = 88
ITEM_COOKED_BEEF = 89
ITEM_APPLE = 90
ITEM_CHICKEN = 91
ITEM_PORKCHOP = 92
ITEM_WOOL = 93
ITEM_BONE = 94
ITEM_STRING = 95
ITEM_ROTTEN_FLESH = 96
ITEM_GUNPOWDER = 97
ITEM_RAW_IRON = 98
ITEM_RAW_GOLD = 99
ITEM_REDSTONE = 100
ITEM_CLAY_BALL = 101
ITEM_BRICK = 102
ITEM_PAPER = 103
ITEM_BOOK = 104
ITEM_BOWL = 105
ITEM_MUSHROOM_STEW = 106
ITEM_GOLDEN_APPLE = 107
ITEM_SUGAR = 108
ITEM_BONE_MEAL = 109
ITEM_SHEARS = 110
ITEM_FLINT_AND_STEEL = 111
ITEM_BUCKET = 112
ITEM_WATER_BUCKET = 113
ITEM_LAVA_BUCKET = 114
ITEM_LEATHER = 115
ITEM_FEATHER = 116
ITEM_RAW_COPPER = 117
ITEM_COPPER_INGOT = 118
# Armor (119-134): leather / iron / gold / diamond × helmet / chestplate / leggings / boots
ITEM_LEATHER_HELMET = 119
ITEM_LEATHER_CHESTPLATE = 120
ITEM_LEATHER_LEGGINGS = 121
ITEM_LEATHER_BOOTS = 122
ITEM_IRON_HELMET = 123
ITEM_IRON_CHESTPLATE = 124
ITEM_IRON_LEGGINGS = 125
ITEM_IRON_BOOTS = 126
ITEM_GOLD_HELMET = 127
ITEM_GOLD_CHESTPLATE = 128
ITEM_GOLD_LEGGINGS = 129
ITEM_GOLD_BOOTS = 130
ITEM_DIAMOND_HELMET = 131
ITEM_DIAMOND_CHESTPLATE = 132
ITEM_DIAMOND_LEGGINGS = 133
ITEM_DIAMOND_BOOTS = 134

# Spawn eggs (135-143): creative-only, right-click to spawn the mob.
ITEM_SPAWN_EGG_COW = 135
ITEM_SPAWN_EGG_PIG = 136
ITEM_SPAWN_EGG_CHICKEN = 137
ITEM_SPAWN_EGG_SHEEP = 138
ITEM_SPAWN_EGG_ZOMBIE = 139
ITEM_SPAWN_EGG_SKELETON = 140
ITEM_SPAWN_EGG_SPIDER = 141
ITEM_SPAWN_EGG_CREEPER = 142
ITEM_SPAWN_EGG_VILLAGER = 143


# ---------------------------------------------------------------------------
# Item definition
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class ItemDef:
    name: str
    max_stack: int = 64
    max_durability: int = 0          # 0 = unbreakable / not a tool
    texture_name: str = ""
    tool_type: ToolType = ToolType.NONE
    tool_tier: ToolTier = ToolTier.NONE
    weapon_damage: float = 0.0       # bonus damage for swords (hand=1)
    armor_points: int = 0            # Minecraft defense points (full diamond set = 20)
    armor_slot: int = -1             # ARMOR_HEAD/CHEST/LEGS/FEET, or -1 if not armor


ITEMS: Dict[int, ItemDef] = {
    # Pickaxes
    ITEM_WOODEN_PICKAXE: ItemDef("wooden_pickaxe", 1, 60, "wooden_pickaxe", ToolType.PICKAXE, ToolTier.WOODEN),
    ITEM_STONE_PICKAXE:  ItemDef("stone_pickaxe",  1, 132, "stone_pickaxe", ToolType.PICKAXE, ToolTier.STONE),
    ITEM_IRON_PICKAXE:   ItemDef("iron_pickaxe",   1, 251, "iron_pickaxe", ToolType.PICKAXE, ToolTier.IRON),
    ITEM_DIAMOND_PICKAXE: ItemDef("diamond_pickaxe", 1, 1562, "diamond_pickaxe", ToolType.PICKAXE, ToolTier.DIAMOND),
    # Axes
    ITEM_WOODEN_AXE: ItemDef("wooden_axe", 1, 60, "wooden_axe", ToolType.AXE, ToolTier.WOODEN),
    ITEM_STONE_AXE:  ItemDef("stone_axe",  1, 132, "stone_axe", ToolType.AXE, ToolTier.STONE),
    ITEM_IRON_AXE:   ItemDef("iron_axe",   1, 251, "iron_axe", ToolType.AXE, ToolTier.IRON),
    ITEM_DIAMOND_AXE: ItemDef("diamond_axe", 1, 1562, "diamond_axe", ToolType.AXE, ToolTier.DIAMOND),
    # Shovels
    ITEM_WOODEN_SHOVEL: ItemDef("wooden_shovel", 1, 60, "wooden_shovel", ToolType.SHOVEL, ToolTier.WOODEN),
    ITEM_STONE_SHOVEL:  ItemDef("stone_shovel",  1, 132, "stone_shovel", ToolType.SHOVEL, ToolTier.STONE),
    ITEM_IRON_SHOVEL:   ItemDef("iron_shovel",   1, 251, "iron_shovel", ToolType.SHOVEL, ToolTier.IRON),
    ITEM_DIAMOND_SHOVEL: ItemDef("diamond_shovel", 1, 1562, "diamond_shovel", ToolType.SHOVEL, ToolTier.DIAMOND),
    # Swords
    ITEM_WOODEN_SWORD: ItemDef("wooden_sword", 1, 60, "wooden_sword", ToolType.SWORD, ToolTier.WOODEN, weapon_damage=4.0),
    ITEM_STONE_SWORD:  ItemDef("stone_sword",  1, 132, "stone_sword", ToolType.SWORD, ToolTier.STONE, weapon_damage=5.0),
    ITEM_IRON_SWORD:   ItemDef("iron_sword",   1, 251, "iron_sword", ToolType.SWORD, ToolTier.IRON, weapon_damage=6.0),
    ITEM_DIAMOND_SWORD: ItemDef("diamond_sword", 1, 1562, "diamond_sword", ToolType.SWORD, ToolTier.DIAMOND, weapon_damage=7.0),
    # Hoes
    ITEM_WOODEN_HOE: ItemDef("wooden_hoe", 1, 60, "wooden_hoe", ToolType.HOE, ToolTier.WOODEN),
    ITEM_STONE_HOE:  ItemDef("stone_hoe",  1, 132, "stone_hoe", ToolType.HOE, ToolTier.STONE),
    ITEM_IRON_HOE:   ItemDef("iron_hoe",   1, 251, "iron_hoe", ToolType.HOE, ToolTier.IRON),
    ITEM_DIAMOND_HOE: ItemDef("diamond_hoe", 1, 1562, "diamond_hoe", ToolType.HOE, ToolTier.DIAMOND),
    # Materials
    ITEM_COAL:        ItemDef("coal", 64, texture_name="coal"),
    ITEM_IRON_INGOT:  ItemDef("iron_ingot", 64, texture_name="iron_ingot"),
    ITEM_GOLD_INGOT:  ItemDef("gold_ingot", 64, texture_name="gold_ingot"),
    ITEM_DIAMOND:     ItemDef("diamond", 64, texture_name="diamond"),
    # Food
    ITEM_RAW_BEEF:    ItemDef("raw_beef", 64, texture_name="raw_beef"),
    ITEM_COOKED_BEEF: ItemDef("cooked_beef", 64, texture_name="cooked_beef"),
    ITEM_APPLE:       ItemDef("apple", 64, texture_name="apple"),
    # Mob drops
    ITEM_CHICKEN:      ItemDef("chicken", 64, texture_name="chicken"),
    ITEM_PORKCHOP:     ItemDef("porkchop", 64, texture_name="porkchop"),
    ITEM_WOOL:         ItemDef("wool", 64, texture_name="wool"),
    ITEM_BONE:         ItemDef("bone", 64, texture_name="bone"),
    ITEM_STRING:       ItemDef("string", 64, texture_name="string"),
    ITEM_ROTTEN_FLESH: ItemDef("rotten_flesh", 64, texture_name="rotten_flesh"),
    ITEM_GUNPOWDER:    ItemDef("gunpowder", 64, texture_name="gunpowder"),
    ITEM_LEATHER:      ItemDef("leather", 64, texture_name="leather"),
    ITEM_FEATHER:      ItemDef("feather", 64, texture_name="feather"),
    # Raw ores
    ITEM_RAW_IRON:     ItemDef("raw_iron", 64, texture_name="raw_iron"),
    ITEM_RAW_GOLD:     ItemDef("raw_gold", 64, texture_name="raw_gold"),
    ITEM_RAW_COPPER:   ItemDef("raw_copper", 64, texture_name="raw_copper"),
    ITEM_COPPER_INGOT: ItemDef("copper_ingot", 64, texture_name="copper_ingot"),
    ITEM_REDSTONE:     ItemDef("redstone", 64, texture_name="redstone"),
    # Crafting materials
    ITEM_CLAY_BALL:    ItemDef("clay_ball", 64, texture_name="clay_ball"),
    ITEM_BRICK:        ItemDef("brick", 64, texture_name="brick"),
    ITEM_PAPER:        ItemDef("paper", 64, texture_name="paper"),
    ITEM_BOOK:         ItemDef("book", 64, texture_name="book"),
    ITEM_BOWL:         ItemDef("bowl", 64, texture_name="bowl"),
    ITEM_SUGAR:        ItemDef("sugar", 64, texture_name="sugar"),
    ITEM_BONE_MEAL:    ItemDef("bone_meal", 64, texture_name="bone_meal"),
    # Food
    ITEM_MUSHROOM_STEW: ItemDef("mushroom_stew", 1, texture_name="mushroom_stew"),
    ITEM_GOLDEN_APPLE:  ItemDef("golden_apple", 64, texture_name="golden_apple"),
    # Tools / utility
    ITEM_SHEARS:         ItemDef("shears", 1, 238, "shears"),
    ITEM_FLINT_AND_STEEL: ItemDef("flint_and_steel", 1, 64, "flint_and_steel"),
    ITEM_BUCKET:         ItemDef("bucket", 16, texture_name="bucket"),
    ITEM_WATER_BUCKET:   ItemDef("water_bucket", 1, texture_name="water_bucket"),
    ITEM_LAVA_BUCKET:    ItemDef("lava_bucket", 1, texture_name="lava_bucket"),
    # Armor (defense points & durability follow Minecraft Java). max_stack=1.
    ITEM_LEATHER_HELMET:     ItemDef("leather_helmet", 1, 55, "leather_helmet", armor_points=1, armor_slot=ARMOR_HEAD),
    ITEM_LEATHER_CHESTPLATE: ItemDef("leather_chestplate", 1, 80, "leather_chestplate", armor_points=3, armor_slot=ARMOR_CHEST),
    ITEM_LEATHER_LEGGINGS:   ItemDef("leather_leggings", 1, 75, "leather_leggings", armor_points=2, armor_slot=ARMOR_LEGS),
    ITEM_LEATHER_BOOTS:      ItemDef("leather_boots", 1, 65, "leather_boots", armor_points=1, armor_slot=ARMOR_FEET),
    ITEM_IRON_HELMET:        ItemDef("iron_helmet", 1, 165, "iron_helmet", armor_points=2, armor_slot=ARMOR_HEAD),
    ITEM_IRON_CHESTPLATE:    ItemDef("iron_chestplate", 1, 240, "iron_chestplate", armor_points=6, armor_slot=ARMOR_CHEST),
    ITEM_IRON_LEGGINGS:      ItemDef("iron_leggings", 1, 225, "iron_leggings", armor_points=5, armor_slot=ARMOR_LEGS),
    ITEM_IRON_BOOTS:         ItemDef("iron_boots", 1, 195, "iron_boots", armor_points=2, armor_slot=ARMOR_FEET),
    ITEM_GOLD_HELMET:        ItemDef("gold_helmet", 1, 77, "gold_helmet", armor_points=2, armor_slot=ARMOR_HEAD),
    ITEM_GOLD_CHESTPLATE:    ItemDef("gold_chestplate", 1, 112, "gold_chestplate", armor_points=5, armor_slot=ARMOR_CHEST),
    ITEM_GOLD_LEGGINGS:      ItemDef("gold_leggings", 1, 105, "gold_leggings", armor_points=3, armor_slot=ARMOR_LEGS),
    ITEM_GOLD_BOOTS:         ItemDef("gold_boots", 1, 91, "gold_boots", armor_points=1, armor_slot=ARMOR_FEET),
    ITEM_DIAMOND_HELMET:     ItemDef("diamond_helmet", 1, 363, "diamond_helmet", armor_points=3, armor_slot=ARMOR_HEAD),
    ITEM_DIAMOND_CHESTPLATE: ItemDef("diamond_chestplate", 1, 528, "diamond_chestplate", armor_points=8, armor_slot=ARMOR_CHEST),
    ITEM_DIAMOND_LEGGINGS:   ItemDef("diamond_leggings", 1, 495, "diamond_leggings", armor_points=6, armor_slot=ARMOR_LEGS),
    ITEM_DIAMOND_BOOTS:      ItemDef("diamond_boots", 1, 429, "diamond_boots", armor_points=3, armor_slot=ARMOR_FEET),
    # Spawn eggs (creative-only). Right-click to spawn the mob.
    ITEM_SPAWN_EGG_COW:      ItemDef("spawn_egg_cow", 64, texture_name="spawn_egg_cow"),
    ITEM_SPAWN_EGG_PIG:      ItemDef("spawn_egg_pig", 64, texture_name="spawn_egg_pig"),
    ITEM_SPAWN_EGG_CHICKEN:  ItemDef("spawn_egg_chicken", 64, texture_name="spawn_egg_chicken"),
    ITEM_SPAWN_EGG_SHEEP:    ItemDef("spawn_egg_sheep", 64, texture_name="spawn_egg_sheep"),
    ITEM_SPAWN_EGG_ZOMBIE:   ItemDef("spawn_egg_zombie", 64, texture_name="spawn_egg_zombie"),
    ITEM_SPAWN_EGG_SKELETON: ItemDef("spawn_egg_skeleton", 64, texture_name="spawn_egg_skeleton"),
    ITEM_SPAWN_EGG_SPIDER:   ItemDef("spawn_egg_spider", 64, texture_name="spawn_egg_spider"),
    ITEM_SPAWN_EGG_CREEPER:  ItemDef("spawn_egg_creeper", 64, texture_name="spawn_egg_creeper"),
    ITEM_SPAWN_EGG_VILLAGER: ItemDef("spawn_egg_villager", 64, texture_name="spawn_egg_villager"),
}

# Maps a spawn egg item ID -> mob type string (matches entity.MOB_* values).
# Plain strings used to avoid an items<->entity import cycle.
SPAWN_EGG_TO_MOB: Dict[int, str] = {
    ITEM_SPAWN_EGG_COW: "cow",
    ITEM_SPAWN_EGG_PIG: "pig",
    ITEM_SPAWN_EGG_CHICKEN: "chicken",
    ITEM_SPAWN_EGG_SHEEP: "sheep",
    ITEM_SPAWN_EGG_ZOMBIE: "zombie",
    ITEM_SPAWN_EGG_SKELETON: "skeleton",
    ITEM_SPAWN_EGG_SPIDER: "spider",
    ITEM_SPAWN_EGG_CREEPER: "creeper",
    ITEM_SPAWN_EGG_VILLAGER: "villager",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Food data: (hunger_restore, saturation)
FOODS: Dict[int, Tuple[float, float]] = {
    ITEM_RAW_BEEF: (3.0, 1.8),
    ITEM_COOKED_BEEF: (8.0, 12.8),
    ITEM_APPLE: (4.0, 2.4),
    ITEM_CHICKEN: (2.0, 1.2),
    ITEM_PORKCHOP: (3.0, 1.8),
    ITEM_ROTTEN_FLESH: (4.0, 0.8),
    ITEM_MUSHROOM_STEW: (6.0, 7.2),
    ITEM_GOLDEN_APPLE: (4.0, 9.6),
}


def is_block_id(id_: int) -> bool:
    """Return True if this ID refers to a placeable block (0-63)."""
    return 0 <= id_ < 64


def is_item_id(id_: int) -> bool:
    """Return True if this ID refers to a non-block item (64+)."""
    return id_ >= 64


def is_tool_id(id_: int) -> bool:
    """Return True if id_ is a tool item."""
    def_ = ITEMS.get(id_)
    return def_ is not None and def_.tool_type != ToolType.NONE


def is_spawn_egg(id_: int) -> bool:
    """Return True if id_ is a creative spawn egg item."""
    return id_ in SPAWN_EGG_TO_MOB


def get_definition(id_: int) -> ItemDef:
    """Return ItemDef for an item/block ID. Returns a generic block def for block IDs."""
    if is_item_id(id_):
        return ITEMS.get(id_, ItemDef(f"item_{id_}"))
    # Block IDs use a generic definition (max_stack=64, no durability)
    return ItemDef(f"block_{id_}", 64, 0, texture_name="dirt")


# ---------------------------------------------------------------------------
# Tool speed multipliers
# ---------------------------------------------------------------------------

_TOOL_SPEED = {
    ToolTier.WOODEN: 1.5,
    ToolTier.STONE: 2.0,
    ToolTier.IRON: 3.0,
    ToolTier.DIAMOND: 4.0,
}


def get_tool_multiplier(tool_type: ToolType, tool_tier: ToolTier) -> float:
    """Return the speed multiplier for a given tool type/tier combo.
    Default 1.0 for hand (no tool)."""
    if tool_tier == ToolTier.NONE:
        return 1.0
    return _TOOL_SPEED.get(tool_tier, 1.0)


# ---------------------------------------------------------------------------
# Block hardness -> (best_tool, min_tier) mapping for tool gating
# ---------------------------------------------------------------------------

from .chunk import (
    BLOCK_ANDESITE, BLOCK_BOOKSHELF, BLOCK_BRICKS, BLOCK_CLAY,
    BLOCK_COAL_BLOCK, BLOCK_COAL_ORE, BLOCK_COBBLESTONE,
    BLOCK_COPPER_BLOCK, BLOCK_COPPER_ORE,
    BLOCK_CRAFTING_TABLE, BLOCK_CHEST, BLOCK_DIAMOND_BLOCK,
    BLOCK_DIAMOND_ORE, BLOCK_DIORITE,
    BLOCK_DEEPSLATE_COAL, BLOCK_DEEPSLATE_COPPER, BLOCK_DEEPSLATE_DIAMOND,
    BLOCK_DEEPSLATE_GOLD, BLOCK_DEEPSLATE_IRON, BLOCK_DEEPSLATE_REDSTONE,
    BLOCK_DIRT, BLOCK_FURNACE, BLOCK_GLASS, BLOCK_GOLD_BLOCK,
    BLOCK_GOLD_ORE, BLOCK_GRANITE, BLOCK_GRASS, BLOCK_GRAVEL,
    BLOCK_IRON_BLOCK, BLOCK_IRON_ORE,
    BLOCK_LEAVES, BLOCK_LOG, BLOCK_PLANKS, BLOCK_REDSTONE_BLOCK,
    BLOCK_REDSTONE_ORE, BLOCK_SAND, BLOCK_SANDSTONE,
    BLOCK_SNOW, BLOCK_STONE, BLOCK_STONE_BRICKS, BLOCK_TNT,
)

# (base_hardness, best_tool_type, min_tool_tier)
# min_tier=None means any tier works, min_tier=ToolTier.STONE means stone+
BLOCK_TOOL_INFO: Dict[int, tuple] = {
    BLOCK_GRASS:         (0.50, ToolType.SHOVEL, ToolTier.NONE),
    BLOCK_DIRT:          (0.50, ToolType.SHOVEL, ToolTier.NONE),
    BLOCK_SAND:          (0.50, ToolType.SHOVEL, ToolTier.NONE),
    BLOCK_GRAVEL:        (0.50, ToolType.SHOVEL, ToolTier.NONE),
    BLOCK_SNOW:          (0.40, ToolType.SHOVEL, ToolTier.NONE),
    BLOCK_LEAVES:        (0.35, ToolType.NONE, ToolTier.NONE),
    BLOCK_GLASS:         (0.55, ToolType.NONE, ToolTier.NONE),
    BLOCK_LOG:           (1.00, ToolType.AXE, ToolTier.NONE),
    BLOCK_PLANKS:        (0.80, ToolType.AXE, ToolTier.NONE),
    BLOCK_CRAFTING_TABLE: (0.80, ToolType.AXE, ToolTier.NONE),
    BLOCK_STONE:         (1.50, ToolType.PICKAXE, ToolTier.NONE),
    BLOCK_COBBLESTONE:   (1.50, ToolType.PICKAXE, ToolTier.NONE),
    BLOCK_COAL_ORE:      (1.50, ToolType.PICKAXE, ToolTier.NONE),
    BLOCK_IRON_ORE:      (1.50, ToolType.PICKAXE, ToolTier.STONE),
    BLOCK_GOLD_ORE:      (1.50, ToolType.PICKAXE, ToolTier.IRON),
    BLOCK_REDSTONE_ORE:  (1.50, ToolType.PICKAXE, ToolTier.IRON),
    BLOCK_DIAMOND_ORE:   (3.00, ToolType.PICKAXE, ToolTier.IRON),
    BLOCK_COPPER_ORE:    (3.00, ToolType.PICKAXE, ToolTier.STONE),
    # Deepslate ore variants: same tool gate as their stone counterparts, a bit harder.
    BLOCK_DEEPSLATE_COAL:     (4.50, ToolType.PICKAXE, ToolTier.NONE),
    BLOCK_DEEPSLATE_IRON:     (4.50, ToolType.PICKAXE, ToolTier.STONE),
    BLOCK_DEEPSLATE_GOLD:     (4.50, ToolType.PICKAXE, ToolTier.IRON),
    BLOCK_DEEPSLATE_REDSTONE: (4.50, ToolType.PICKAXE, ToolTier.IRON),
    BLOCK_DEEPSLATE_DIAMOND:  (4.50, ToolType.PICKAXE, ToolTier.IRON),
    BLOCK_DEEPSLATE_COPPER:   (4.50, ToolType.PICKAXE, ToolTier.STONE),
    BLOCK_FURNACE:       (3.50, ToolType.PICKAXE, ToolTier.NONE),
    BLOCK_CHEST:         (2.50, ToolType.AXE, ToolTier.NONE),
    BLOCK_GRANITE:       (1.50, ToolType.PICKAXE, ToolTier.NONE),
    BLOCK_ANDESITE:      (1.50, ToolType.PICKAXE, ToolTier.NONE),
    BLOCK_DIORITE:       (1.50, ToolType.PICKAXE, ToolTier.NONE),
    BLOCK_CLAY:          (0.60, ToolType.SHOVEL, ToolTier.NONE),
    BLOCK_COAL_BLOCK:    (5.00, ToolType.PICKAXE, ToolTier.WOODEN),
    BLOCK_IRON_BLOCK:    (5.00, ToolType.PICKAXE, ToolTier.STONE),
    BLOCK_GOLD_BLOCK:    (3.00, ToolType.PICKAXE, ToolTier.IRON),
    BLOCK_DIAMOND_BLOCK: (5.00, ToolType.PICKAXE, ToolTier.IRON),
    BLOCK_REDSTONE_BLOCK: (5.00, ToolType.PICKAXE, ToolTier.IRON),
    BLOCK_COPPER_BLOCK:  (3.00, ToolType.PICKAXE, ToolTier.STONE),
    BLOCK_SANDSTONE:     (0.80, ToolType.PICKAXE, ToolTier.NONE),
    BLOCK_STONE_BRICKS:  (1.50, ToolType.PICKAXE, ToolTier.NONE),
    BLOCK_BRICKS:        (2.00, ToolType.PICKAXE, ToolTier.NONE),
    BLOCK_BOOKSHELF:     (1.50, ToolType.AXE, ToolTier.NONE),
    BLOCK_TNT:           (0.00, ToolType.NONE, ToolTier.NONE),
}


def get_block_hardness(block_id: int) -> float:
    """Return the base break time (seconds) for a block with best tool."""
    info = BLOCK_TOOL_INFO.get(block_id)
    if info is None:
        return 0.85
    return info[0]


def can_break(block_id: int, tool_type: ToolType, tool_tier: ToolTier) -> bool:
    """Return True if the given tool can break (and drop) this block."""
    info = BLOCK_TOOL_INFO.get(block_id)
    if info is None:
        return True  # generic blocks always breakable
    best_tool, min_tier = info[1], info[2]
    if min_tier == ToolTier.NONE:
        return True
    if tool_type != best_tool:
        return True  # wrong tool still breaks, just slower
    return tool_tier >= min_tier


def effective_hardness(block_id: int, tool_type: ToolType, tool_tier: ToolTier) -> float:
    """Return actual break time accounting for tool speed multiplier."""
    base = get_block_hardness(block_id)
    info = BLOCK_TOOL_INFO.get(block_id)
    if info is None:
        return base
    best_tool = info[1]
    if tool_type == best_tool and tool_type != ToolType.NONE:
        mult = get_tool_multiplier(tool_type, tool_tier)
        return base / mult
    return base