from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .chunk import (
    BLOCK_AIR,
    BLOCK_DIRT,
    BLOCK_GLASS,
    BLOCK_GRASS,
    BLOCK_LEAVES,
    BLOCK_LOG,
    BLOCK_SAND,
    BLOCK_SNOW,
    BLOCK_STONE,
    BLOCK_WATER,
)
from .items import get_definition, is_item_id


@dataclass(slots=True)
class ItemStack:
    block_id: int = BLOCK_AIR
    count: int = 0
    durability: int = 0

    def is_empty(self) -> bool:
        return self.block_id == BLOCK_AIR or self.count <= 0

    def max_stack(self) -> int:
        if self.block_id == BLOCK_AIR:
            return 1
        if is_item_id(self.block_id):
            def_ = get_definition(self.block_id)
            return def_.max_stack
        return 64

    def can_merge_with(self, other: ItemStack) -> bool:
        return self.block_id == other.block_id and self.block_id != BLOCK_AIR

    def copy(self) -> ItemStack:
        return ItemStack(self.block_id, self.count, self.durability)


class Inventory:
    """Minecraft-style inventory with hotbar + main storage + crafting grid."""

    HOTBAR_SIZE = 9
    MAIN_ROWS = 3
    MAIN_COLS = 9
    MAIN_SIZE = MAIN_ROWS * MAIN_COLS  # 27
    CRAFT_SIZE = 2  # 2x2 grid
    CRAFT_SIZE_3X3 = 3  # 3x3 grid

    def __init__(self):
        # Hotbar (slots 0-8)
        self.hotbar: List[ItemStack] = [ItemStack() for _ in range(self.HOTBAR_SIZE)]
        # Main inventory (slots 9-35)
        self.main: List[ItemStack] = [ItemStack() for _ in range(self.MAIN_SIZE)]
        # Crafting grid (2x2)
        self.craft_grid: List[ItemStack] = [ItemStack() for _ in range(self.CRAFT_SIZE * self.CRAFT_SIZE)]
        # Crafting result
        self.craft_result = ItemStack()
        # 3x3 crafting grid (crafting table)
        self.craft_grid_3x3: List[ItemStack] = [ItemStack() for _ in range(self.CRAFT_SIZE_3X3 * self.CRAFT_SIZE_3X3)]
        # 3x3 crafting result
        self.craft_result_3x3 = ItemStack()
        # Equipped armor: [helmet, chestplate, leggings, boots] (ARMOR_HEAD..ARMOR_FEET)
        self.armor: List[ItemStack] = [ItemStack() for _ in range(4)]
        # Active hotbar slot index
        self.active_slot = 0
        # Hotbar starts empty for both survival and creative — player gathers
        # their own resources. Use cheats/creative inventory UI to add items.

    @property
    def all_slots(self) -> List[ItemStack]:
        """Return all slots: hotbar + main (for UI iteration)."""
        return self.hotbar + self.main

    def active_stack(self) -> ItemStack:
        return self.hotbar[self.active_slot]

    def active_block_id(self) -> int:
        s = self.active_stack()
        return s.block_id if not s.is_empty() else BLOCK_AIR

    def consume_active(self, amount: int = 1) -> bool:
        s = self.active_stack()
        if s.is_empty() or s.count < amount:
            return False
        s.count -= amount
        if s.count <= 0:
            s.block_id = BLOCK_AIR
            s.count = 0
        return True

    def add_item(self, block_id: int, count: int = 1) -> int:
        """Try to add items. Returns how many could NOT be added (0 = full success)."""
        if block_id == BLOCK_AIR or count <= 0:
            return count

        defn = get_definition(block_id)
        init_dur = defn.max_durability  # 0 for non-tools

        remaining = count

        # First, try to stack with existing non-full stacks (tools never stack: max_stack=1)
        for slot in self.all_slots:
            if slot.block_id == block_id and slot.count < slot.max_stack():
                space = slot.max_stack() - slot.count
                add = min(remaining, space)
                slot.count += add
                remaining -= add
                if remaining <= 0:
                    return 0

        # Then, fill empty slots
        for slot in self.all_slots:
            if slot.is_empty():
                add = min(remaining, 64)
                slot.block_id = block_id
                slot.count = add
                slot.durability = init_dur
                remaining -= add
                if remaining <= 0:
                    return 0

        return remaining

    def remove_item(self, block_id: int, count: int = 1) -> bool:
        """Remove items. Returns True if fully satisfied."""
        if block_id == BLOCK_AIR or count <= 0:
            return True

        to_remove = count
        for slot in self.all_slots:
            if slot.block_id == block_id:
                rm = min(to_remove, slot.count)
                slot.count -= rm
                to_remove -= rm
                if slot.count <= 0:
                    slot.block_id = BLOCK_AIR
                    slot.count = 0
                if to_remove <= 0:
                    return True
        return False

    def count_item(self, block_id: int) -> int:
        total = 0
        for slot in self.all_slots:
            if slot.block_id == block_id:
                total += slot.count
        return total

    def get_slot(self, index: int) -> ItemStack:
        """Index 0-35 for hotbar+main. Raises IndexError for crafting."""
        if index < 0 or index >= self.HOTBAR_SIZE + self.MAIN_SIZE:
            raise IndexError(index)
        return self.all_slots[index]

    def set_slot(self, index: int, stack: ItemStack) -> None:
        if index < 0 or index >= self.HOTBAR_SIZE + self.MAIN_SIZE:
            raise IndexError(index)
        if index < self.HOTBAR_SIZE:
            self.hotbar[index] = stack
        else:
            self.main[index - self.HOTBAR_SIZE] = stack

    def get_craft_slot(self, row: int, col: int) -> ItemStack:
        idx = row * self.CRAFT_SIZE + col
        return self.craft_grid[idx]

    def set_craft_slot(self, row: int, col: int, stack: ItemStack) -> None:
        idx = row * self.CRAFT_SIZE + col
        self.craft_grid[idx] = stack

    def get_craft_pattern(self) -> Tuple[Tuple[int, ...], ...]:
        """Return 2x2 pattern of block_ids."""
        return tuple(
            tuple(self.craft_grid[r * self.CRAFT_SIZE + c].block_id for c in range(self.CRAFT_SIZE))
            for r in range(self.CRAFT_SIZE)
        )

    def total_armor_points(self) -> int:
        """Sum the Minecraft defense points of all equipped armor pieces."""
        total = 0
        for slot in self.armor:
            if not slot.is_empty():
                total += get_definition(slot.block_id).armor_points
        return total


def block_id_to_name(block_id: int) -> str:
    from .chunk import (
        BLOCK_CHEST, BLOCK_COAL_ORE, BLOCK_COBBLESTONE, BLOCK_CRAFTING_TABLE,
        BLOCK_DIAMOND_ORE, BLOCK_FLOWER_RED, BLOCK_FLOWER_YELLOW,
        BLOCK_FURNACE, BLOCK_GOLD_ORE, BLOCK_GRAVEL, BLOCK_IRON_ORE, BLOCK_LAVA,
        BLOCK_PLANKS, BLOCK_REDSTONE_ORE, BLOCK_STICK, BLOCK_TALL_GRASS,
    )
    return {
        BLOCK_AIR: "air",
        BLOCK_GRASS: "grass",
        BLOCK_DIRT: "dirt",
        BLOCK_STONE: "stone",
        BLOCK_SAND: "sand",
        BLOCK_LOG: "wood_log",
        BLOCK_LEAVES: "leaves",
        BLOCK_WATER: "water",
        BLOCK_GLASS: "glass",
        BLOCK_SNOW: "snow",
        BLOCK_PLANKS: "planks",
        BLOCK_STICK: "stick",
        BLOCK_CRAFTING_TABLE: "crafting_table",
        BLOCK_COBBLESTONE: "cobblestone",
        BLOCK_GRAVEL: "gravel",
        BLOCK_LAVA: "lava",
        BLOCK_COAL_ORE: "coal_ore",
        BLOCK_IRON_ORE: "iron_ore",
        BLOCK_GOLD_ORE: "gold_ore",
        BLOCK_DIAMOND_ORE: "diamond_ore",
        BLOCK_REDSTONE_ORE: "redstone_ore",
        BLOCK_TALL_GRASS: "tall_grass",
        BLOCK_FLOWER_RED: "flower_red",
        BLOCK_FLOWER_YELLOW: "flower_yellow",
        BLOCK_FURNACE: "furnace",
        BLOCK_CHEST: "chest",
    }.get(block_id, f"block_{block_id}")
