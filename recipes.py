from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
# SMELT_RECIPES and FUEL_VALUES are defined at bottom of this module

from .chunk import (
    BLOCK_AIR,
    BLOCK_BED,
    BLOCK_BOOKSHELF,
    BLOCK_BRICKS,
    BLOCK_CHEST,
    BLOCK_CLAY,
    BLOCK_COAL_BLOCK,
    BLOCK_COBBLESTONE,
    BLOCK_COPPER_BLOCK,
    BLOCK_COPPER_ORE,
    BLOCK_DIAMOND_BLOCK,
    BLOCK_DIRT,
    BLOCK_FURNACE,
    BLOCK_GLASS,
    BLOCK_GOLD_BLOCK,
    BLOCK_GOLD_ORE,
    BLOCK_GRASS,
    BLOCK_IRON_BLOCK,
    BLOCK_IRON_ORE,
    BLOCK_LEAVES,
    BLOCK_LOG,
    BLOCK_MUSHROOM_BROWN,
    BLOCK_MUSHROOM_RED,
    BLOCK_PLANKS,
    BLOCK_REDSTONE_BLOCK,
    BLOCK_SAND,
    BLOCK_SANDSTONE,
    BLOCK_SNOW,
    BLOCK_STICK,
    BLOCK_STONE,
    BLOCK_STONE_BRICKS,
    BLOCK_SUGAR_CANE,
    BLOCK_TNT,
    BLOCK_WATER,
    BLOCK_WOOL,
)
from .items import (
    ITEM_APPLE,
    ITEM_BONE,
    ITEM_BONE_MEAL,
    ITEM_BOOK,
    ITEM_BOWL,
    ITEM_BRICK,
    ITEM_BUCKET,
    ITEM_CHICKEN,
    ITEM_CLAY_BALL,
    ITEM_COAL,
    ITEM_COOKED_BEEF,
    ITEM_COPPER_INGOT,
    ITEM_DIAMOND,
    ITEM_DIAMOND_AXE,
    ITEM_DIAMOND_HOE,
    ITEM_DIAMOND_PICKAXE,
    ITEM_DIAMOND_SHOVEL,
    ITEM_DIAMOND_SWORD,
    ITEM_FLINT_AND_STEEL,
    ITEM_GOLD_INGOT,
    ITEM_GOLDEN_APPLE,
    ITEM_GUNPOWDER,
    ITEM_IRON_AXE,
    ITEM_IRON_HOE,
    ITEM_IRON_INGOT,
    ITEM_IRON_PICKAXE,
    ITEM_IRON_SHOVEL,
    ITEM_IRON_SWORD,
    ITEM_MUSHROOM_STEW,
    ITEM_PAPER,
    ITEM_PORKCHOP,
    ITEM_RAW_BEEF,
    ITEM_RAW_COPPER,
    ITEM_RAW_GOLD,
    ITEM_RAW_IRON,
    ITEM_REDSTONE,
    ITEM_SHEARS,
    ITEM_STONE_AXE,
    ITEM_STONE_HOE,
    ITEM_STONE_PICKAXE,
    ITEM_STONE_SHOVEL,
    ITEM_STONE_SWORD,
    ITEM_SUGAR,
    ITEM_WOODEN_AXE,
    ITEM_WOODEN_HOE,
    ITEM_WOODEN_PICKAXE,
    ITEM_WOODEN_SHOVEL,
    ITEM_WOODEN_SWORD,
    ITEM_WOOL,
)
from .items import (
    ITEM_LEATHER,
    ITEM_LEATHER_HELMET, ITEM_LEATHER_CHESTPLATE, ITEM_LEATHER_LEGGINGS, ITEM_LEATHER_BOOTS,
    ITEM_IRON_HELMET, ITEM_IRON_CHESTPLATE, ITEM_IRON_LEGGINGS, ITEM_IRON_BOOTS,
    ITEM_GOLD_HELMET, ITEM_GOLD_CHESTPLATE, ITEM_GOLD_LEGGINGS, ITEM_GOLD_BOOTS,
    ITEM_DIAMOND_HELMET, ITEM_DIAMOND_CHESTPLATE, ITEM_DIAMOND_LEGGINGS, ITEM_DIAMOND_BOOTS,
)

# Re-export block IDs for backward compatibility
BLOCK_PLANKS = 11
BLOCK_STICK = 12
BLOCK_CRAFTING_TABLE = 13
BLOCK_COBBLESTONE = 14
BLOCK_GRAVEL = 15

_B = BLOCK_AIR        # Empty slot shorthand
_P = BLOCK_PLANKS
_S = BLOCK_STICK
_C = BLOCK_COBBLESTONE
_L = BLOCK_LOG
_I = ITEM_IRON_INGOT
_G = ITEM_GOLD_INGOT
_D = ITEM_DIAMOND
_CU = ITEM_COPPER_INGOT
_LE = ITEM_LEATHER
_COAL = ITEM_COAL
_SAND = BLOCK_SAND
_STONE = BLOCK_STONE
_BRICK = ITEM_BRICK
_GP = ITEM_GUNPOWDER
_REDSTONE = ITEM_REDSTONE
_APPLE = ITEM_APPLE
_PAPER = ITEM_PAPER
_BOOK = ITEM_BOOK
_BOWL = ITEM_BOWL
_SC = BLOCK_SUGAR_CANE
_MR = BLOCK_MUSHROOM_RED
_MB = BLOCK_MUSHROOM_BROWN
_BONE = ITEM_BONE


@dataclass(slots=True)
class Recipe:
    """A shaped crafting recipe."""
    pattern: Tuple[Tuple[int, ...], ...]  # 2x2 or 3x3 grid of block_ids (0 = empty)
    result_id: int
    result_count: int = 1


@dataclass(slots=True)
class ShapelessRecipe:
    """A shapeless crafting recipe — position of ingredients doesn't matter."""
    ingredients: Tuple[int, ...]
    result_id: int
    result_count: int = 1


def _normalize_pattern(pattern: Tuple[Tuple[int, ...], ...]) -> Tuple[Tuple[int, ...], ...]:
    """Remove empty rows/cols from pattern to allow compact matching."""
    # Find non-empty rows
    rows = [r for r in pattern if any(c != BLOCK_AIR for c in r)]
    if not rows:
        return ((BLOCK_AIR,),)
    # Find non-empty cols
    min_col = min(i for r in rows for i, c in enumerate(r) if c != BLOCK_AIR)
    max_col = max(i for r in rows for i, c in enumerate(r) if c != BLOCK_AIR)
    return tuple(tuple(r[i] for i in range(min_col, max_col + 1)) for r in rows)


def match_recipe(pattern: Tuple[Tuple[int, ...], ...], recipes: List[Recipe],
                 shapeless_recipes: Optional[List[ShapelessRecipe]] = None) -> Optional[object]:
    """Try to match a crafting grid pattern against shaped recipes first, then shapeless."""
    # Normalize input pattern (trim empty rows/cols)
    norm = _normalize_pattern(pattern)
    norm_rows = len(norm)
    norm_cols = len(norm[0]) if norm else 0

    for recipe in recipes:
        rpat = _normalize_pattern(recipe.pattern)
        if len(rpat) != norm_rows or len(rpat[0]) != norm_cols:
            continue
        if all(norm[r][c] == rpat[r][c] for r in range(norm_rows) for c in range(norm_cols)):
            return recipe

    if shapeless_recipes:
        contents = tuple(sorted(c for r in pattern for c in r if c != BLOCK_AIR))
        if contents:
            for sr in shapeless_recipes:
                if tuple(sorted(sr.ingredients)) == contents:
                    return sr

    return None


# 2x2 crafting recipes (inventory crafting grid)
CRAFT_RECIPES: List[Recipe] = [
    # Planks from log
    Recipe(
        pattern=((_L, _B),
                 (_B, _B)),
        result_id=BLOCK_PLANKS,
        result_count=4,
    ),
    # Sticks from planks (vertical 2x1)
    Recipe(
        pattern=((_P, _B),
                 (_P, _B)),
        result_id=BLOCK_STICK,
        result_count=4,
    ),
    # Crafting table from planks (2x2)
    Recipe(
        pattern=((_P, _P),
                 (_P, _P)),
        result_id=BLOCK_CRAFTING_TABLE,
        result_count=1,
    ),
    # Sandstone from sand (2x2)
    Recipe(
        pattern=((_SAND, _SAND),
                 (_SAND, _SAND)),
        result_id=BLOCK_SANDSTONE,
        result_count=1,
    ),
    # Stone bricks (2x2)
    Recipe(
        pattern=((_STONE, _STONE),
                 (_STONE, _STONE)),
        result_id=BLOCK_STONE_BRICKS,
        result_count=4,
    ),
    # Bricks block from 4 bricks (2x2)
    Recipe(
        pattern=((_BRICK, _BRICK),
                 (_BRICK, _BRICK)),
        result_id=BLOCK_BRICKS,
        result_count=1,
    ),
]

# Bed recipe (3 wool top + 3 planks middle) — added to 3x3 list below.

# 3x3 crafting recipes (crafting table)
CRAFT_RECIPES_3x3: List[Recipe] = [
    # ---- Pickaxes ----
    Recipe(pattern=((_P, _P, _P),
                    (_B, _S, _B),
                    (_B, _S, _B)), result_id=ITEM_WOODEN_PICKAXE, result_count=1),
    Recipe(pattern=((_C, _C, _C),
                    (_B, _S, _B),
                    (_B, _S, _B)), result_id=ITEM_STONE_PICKAXE, result_count=1),
    Recipe(pattern=((_I, _I, _I),
                    (_B, _S, _B),
                    (_B, _S, _B)), result_id=ITEM_IRON_PICKAXE, result_count=1),
    Recipe(pattern=((_D, _D, _D),
                    (_B, _S, _B),
                    (_B, _S, _B)), result_id=ITEM_DIAMOND_PICKAXE, result_count=1),
    # ---- Axes ----
    Recipe(pattern=((_P, _P, _B),
                    (_P, _S, _B),
                    (_B, _S, _B)), result_id=ITEM_WOODEN_AXE, result_count=1),
    Recipe(pattern=((_C, _C, _B),
                    (_C, _S, _B),
                    (_B, _S, _B)), result_id=ITEM_STONE_AXE, result_count=1),
    Recipe(pattern=((_I, _I, _B),
                    (_I, _S, _B),
                    (_B, _S, _B)), result_id=ITEM_IRON_AXE, result_count=1),
    Recipe(pattern=((_D, _D, _B),
                    (_D, _S, _B),
                    (_B, _S, _B)), result_id=ITEM_DIAMOND_AXE, result_count=1),
    # ---- Shovels ----
    Recipe(pattern=((_B, _P, _B),
                    (_B, _S, _B),
                    (_B, _S, _B)), result_id=ITEM_WOODEN_SHOVEL, result_count=1),
    Recipe(pattern=((_B, _C, _B),
                    (_B, _S, _B),
                    (_B, _S, _B)), result_id=ITEM_STONE_SHOVEL, result_count=1),
    Recipe(pattern=((_B, _I, _B),
                    (_B, _S, _B),
                    (_B, _S, _B)), result_id=ITEM_IRON_SHOVEL, result_count=1),
    Recipe(pattern=((_B, _D, _B),
                    (_B, _S, _B),
                    (_B, _S, _B)), result_id=ITEM_DIAMOND_SHOVEL, result_count=1),
    # ---- Swords ----
    Recipe(pattern=((_B, _P, _B),
                    (_B, _P, _B),
                    (_B, _S, _B)), result_id=ITEM_WOODEN_SWORD, result_count=1),
    Recipe(pattern=((_B, _C, _B),
                    (_B, _C, _B),
                    (_B, _S, _B)), result_id=ITEM_STONE_SWORD, result_count=1),
    Recipe(pattern=((_B, _I, _B),
                    (_B, _I, _B),
                    (_B, _S, _B)), result_id=ITEM_IRON_SWORD, result_count=1),
    Recipe(pattern=((_B, _D, _B),
                    (_B, _D, _B),
                    (_B, _S, _B)), result_id=ITEM_DIAMOND_SWORD, result_count=1),
    # ---- Hoes ----
    Recipe(pattern=((_P, _P, _B),
                    (_B, _S, _B),
                    (_B, _S, _B)), result_id=ITEM_WOODEN_HOE, result_count=1),
    Recipe(pattern=((_C, _C, _B),
                    (_B, _S, _B),
                    (_B, _S, _B)), result_id=ITEM_STONE_HOE, result_count=1),
    Recipe(pattern=((_I, _I, _B),
                    (_B, _S, _B),
                    (_B, _S, _B)), result_id=ITEM_IRON_HOE, result_count=1),
    Recipe(pattern=((_D, _D, _B),
                    (_B, _S, _B),
                    (_B, _S, _B)), result_id=ITEM_DIAMOND_HOE, result_count=1),
    # ---- Axes (mirror / right-handed) ----
    Recipe(pattern=((_B, _P, _P),
                    (_B, _S, _P),
                    (_B, _S, _B)), result_id=ITEM_WOODEN_AXE, result_count=1),
    Recipe(pattern=((_B, _C, _C),
                    (_B, _S, _C),
                    (_B, _S, _B)), result_id=ITEM_STONE_AXE, result_count=1),
    Recipe(pattern=((_B, _I, _I),
                    (_B, _S, _I),
                    (_B, _S, _B)), result_id=ITEM_IRON_AXE, result_count=1),
    Recipe(pattern=((_B, _D, _D),
                    (_B, _S, _D),
                    (_B, _S, _B)), result_id=ITEM_DIAMOND_AXE, result_count=1),
    # ---- Hoes (mirror / right-handed) ----
    Recipe(pattern=((_B, _P, _P),
                    (_B, _S, _B),
                    (_B, _S, _B)), result_id=ITEM_WOODEN_HOE, result_count=1),
    Recipe(pattern=((_B, _C, _C),
                    (_B, _S, _B),
                    (_B, _S, _B)), result_id=ITEM_STONE_HOE, result_count=1),
    Recipe(pattern=((_B, _I, _I),
                    (_B, _S, _B),
                    (_B, _S, _B)), result_id=ITEM_IRON_HOE, result_count=1),
    Recipe(pattern=((_B, _D, _D),
                    (_B, _S, _B),
                    (_B, _S, _B)), result_id=ITEM_DIAMOND_HOE, result_count=1),
    # ---- Chest (8 planks ring) ----
    Recipe(pattern=((_P, _P, _P),
                    (_P, _B, _P),
                    (_P, _P, _P)), result_id=BLOCK_CHEST, result_count=1),
    # ---- Furnace (8 cobblestone ring) ----
    Recipe(pattern=((_C, _C, _C),
                    (_C, _B, _C),
                    (_C, _C, _C)), result_id=BLOCK_FURNACE, result_count=1),
    # ---- Storage blocks (9 material full grid) ----
    Recipe(pattern=((_COAL, _COAL, _COAL),
                    (_COAL, _COAL, _COAL),
                    (_COAL, _COAL, _COAL)), result_id=BLOCK_COAL_BLOCK, result_count=1),
    Recipe(pattern=((_I, _I, _I),
                    (_I, _I, _I),
                    (_I, _I, _I)), result_id=BLOCK_IRON_BLOCK, result_count=1),
    Recipe(pattern=((_G, _G, _G),
                    (_G, _G, _G),
                    (_G, _G, _G)), result_id=BLOCK_GOLD_BLOCK, result_count=1),
    Recipe(pattern=((_D, _D, _D),
                    (_D, _D, _D),
                    (_D, _D, _D)), result_id=BLOCK_DIAMOND_BLOCK, result_count=1),
    Recipe(pattern=((_REDSTONE, _REDSTONE, _REDSTONE),
                    (_REDSTONE, _REDSTONE, _REDSTONE),
                    (_REDSTONE, _REDSTONE, _REDSTONE)), result_id=BLOCK_REDSTONE_BLOCK, result_count=1),
    Recipe(pattern=((_CU, _CU, _CU),
                    (_CU, _CU, _CU),
                    (_CU, _CU, _CU)), result_id=BLOCK_COPPER_BLOCK, result_count=1),
    # ---- Paper from sugar cane (3 horizontal middle) ----
    Recipe(pattern=((_B, _B, _B),
                    (_SC, _SC, _SC),
                    (_B, _B, _B)), result_id=ITEM_PAPER, result_count=3),
    # ---- Bowl from planks (V shape) ----
    Recipe(pattern=((_B, _B, _B),
                    (_P, _B, _P),
                    (_B, _P, _B)), result_id=ITEM_BOWL, result_count=4),
    # ---- Bookshelf (6 planks + 3 books middle row) ----
    Recipe(pattern=((_P, _P, _P),
                    (_BOOK, _BOOK, _BOOK),
                    (_P, _P, _P)), result_id=BLOCK_BOOKSHELF, result_count=1),
    # ---- Golden apple (8 gold ring + apple center) ----
    Recipe(pattern=((_G, _G, _G),
                    (_G, _APPLE, _G),
                    (_G, _G, _G)), result_id=ITEM_GOLDEN_APPLE, result_count=1),
    # ---- TNT (5 gunpowder + 4 sand alternating) ----
    Recipe(pattern=((_GP, _SAND, _GP),
                    (_SAND, _GP, _SAND),
                    (_GP, _SAND, _GP)), result_id=BLOCK_TNT, result_count=1),
    # ---- Shears (2 iron diagonal) ----
    Recipe(pattern=((_B, _I, _B),
                    (_I, _B, _B),
                    (_B, _B, _B)), result_id=ITEM_SHEARS, result_count=1),
    # ---- Flint and steel (iron + coal diagonal) ----
    Recipe(pattern=((_I, _B, _B),
                    (_B, _COAL, _B),
                    (_B, _B, _B)), result_id=ITEM_FLINT_AND_STEEL, result_count=1),
    # ---- Bucket (3 iron V-shape) ----
    Recipe(pattern=((_B, _B, _B),
                    (_I, _B, _I),
                    (_B, _I, _B)), result_id=ITEM_BUCKET, result_count=1),
    # ---- Bed (3 wool top + 3 planks middle row) ----
    Recipe(pattern=((BLOCK_WOOL, BLOCK_WOOL, BLOCK_WOOL),
                    (_P, _P, _P),
                    (_B, _B, _B)), result_id=BLOCK_BED, result_count=1),
]

# ---- Armor: helmet / chestplate / leggings / boots per material (Minecraft shapes) ----
# Helmet  XXX / X.X       Chestplate  X.X / XXX / XXX
# Leggings XXX / X.X / X.X   Boots  X.X / X.X
_ARMOR_TIERS = [
    (_LE, ITEM_LEATHER_HELMET, ITEM_LEATHER_CHESTPLATE, ITEM_LEATHER_LEGGINGS, ITEM_LEATHER_BOOTS),
    (_I,  ITEM_IRON_HELMET,    ITEM_IRON_CHESTPLATE,    ITEM_IRON_LEGGINGS,    ITEM_IRON_BOOTS),
    (_G,  ITEM_GOLD_HELMET,    ITEM_GOLD_CHESTPLATE,    ITEM_GOLD_LEGGINGS,    ITEM_GOLD_BOOTS),
    (_D,  ITEM_DIAMOND_HELMET, ITEM_DIAMOND_CHESTPLATE, ITEM_DIAMOND_LEGGINGS, ITEM_DIAMOND_BOOTS),
]
for _x, _helm, _chest, _legs, _boots in _ARMOR_TIERS:
    CRAFT_RECIPES_3x3.extend([
        Recipe(pattern=((_x, _x, _x), (_x, _B, _x), (_B, _B, _B)), result_id=_helm),
        Recipe(pattern=((_x, _B, _x), (_x, _x, _x), (_x, _x, _x)), result_id=_chest),
        Recipe(pattern=((_x, _x, _x), (_x, _B, _x), (_x, _B, _x)), result_id=_legs),
        Recipe(pattern=((_B, _B, _B), (_x, _B, _x), (_x, _B, _x)), result_id=_boots),
    ])


# ---------------------------------------------------------------------------
# Shapeless recipes — ingredient position doesn't matter.
# match_recipe() falls back to these when no shaped recipe matches.
# ---------------------------------------------------------------------------

SHAPELESS_RECIPES_2x2: List[ShapelessRecipe] = [
    # 1 log anywhere in 2x2 grid → 4 planks (QoL: log in any slot, not just top-left)
    ShapelessRecipe(ingredients=(_L,), result_id=BLOCK_PLANKS, result_count=4),
]

SHAPELESS_RECIPES_3x3: List[ShapelessRecipe] = [
    # 1 log anywhere in 3x3 grid → 4 planks
    ShapelessRecipe(ingredients=(_L,), result_id=BLOCK_PLANKS, result_count=4),
    # 3 paper → 1 book (shapeless)
    ShapelessRecipe(ingredients=(_PAPER, _PAPER, _PAPER), result_id=ITEM_BOOK, result_count=1),
    # 1 mushroom_red + 1 mushroom_brown + 1 bowl → mushroom stew
    ShapelessRecipe(ingredients=(_MR, _MB, _BOWL), result_id=ITEM_MUSHROOM_STEW, result_count=1),
    # 1 sugar_cane → 1 sugar
    ShapelessRecipe(ingredients=(_SC,), result_id=ITEM_SUGAR, result_count=1),
    # 1 bone → 3 bone meal
    ShapelessRecipe(ingredients=(_BONE,), result_id=ITEM_BONE_MEAL, result_count=3),
    # Reverse storage blocks: 1 X_block → 9 X
    ShapelessRecipe(ingredients=(BLOCK_COAL_BLOCK,), result_id=ITEM_COAL, result_count=9),
    ShapelessRecipe(ingredients=(BLOCK_IRON_BLOCK,), result_id=ITEM_IRON_INGOT, result_count=9),
    ShapelessRecipe(ingredients=(BLOCK_GOLD_BLOCK,), result_id=ITEM_GOLD_INGOT, result_count=9),
    ShapelessRecipe(ingredients=(BLOCK_DIAMOND_BLOCK,), result_id=ITEM_DIAMOND, result_count=9),
    ShapelessRecipe(ingredients=(BLOCK_REDSTONE_BLOCK,), result_id=ITEM_REDSTONE, result_count=9),
    ShapelessRecipe(ingredients=(BLOCK_COPPER_BLOCK,), result_id=ITEM_COPPER_INGOT, result_count=9),
    # 1 wool item → 1 placeable wool block
    ShapelessRecipe(ingredients=(ITEM_WOOL,), result_id=BLOCK_WOOL, result_count=1),
]


# ---------------------------------------------------------------------------
# Smelting recipes: input_block_id → (result_id, result_count, smelt_seconds)
# ---------------------------------------------------------------------------

SMELT_RECIPES: Dict[int, Tuple[int, int, float]] = {
    BLOCK_IRON_ORE:    (ITEM_IRON_INGOT, 1, 10.0),
    BLOCK_GOLD_ORE:    (ITEM_GOLD_INGOT, 1, 10.0),
    BLOCK_COPPER_ORE:  (ITEM_COPPER_INGOT, 1, 10.0),
    BLOCK_SAND:        (BLOCK_GLASS, 1, 10.0),
    BLOCK_COBBLESTONE: (BLOCK_STONE, 1, 10.0),
    ITEM_RAW_BEEF:     (ITEM_COOKED_BEEF, 1, 10.0),
    ITEM_RAW_IRON:     (ITEM_IRON_INGOT, 1, 10.0),
    ITEM_RAW_GOLD:     (ITEM_GOLD_INGOT, 1, 10.0),
    ITEM_RAW_COPPER:   (ITEM_COPPER_INGOT, 1, 10.0),
    ITEM_CLAY_BALL:    (ITEM_BRICK, 1, 10.0),
}

# Fuel values in seconds of burn time
FUEL_VALUES: Dict[int, float] = {
    ITEM_COAL:    80.0,
    BLOCK_COAL_BLOCK: 800.0,
    BLOCK_LOG:    15.0,
    BLOCK_PLANKS:  7.5,
    BLOCK_STICK:   2.5,
}
