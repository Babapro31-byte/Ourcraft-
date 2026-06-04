"""Top-down minimap that samples the world around the player."""

from __future__ import annotations

import numpy as np

from .chunk import (
    BLOCK_AIR, BLOCK_BEDROCK, BLOCK_CHEST, BLOCK_COAL_ORE, BLOCK_COBBLESTONE,
    BLOCK_CRAFTING_TABLE, BLOCK_DIAMOND_ORE, BLOCK_DIRT, BLOCK_FLOWER_RED,
    BLOCK_FLOWER_YELLOW, BLOCK_FURNACE, BLOCK_GLASS, BLOCK_GOLD_ORE,
    BLOCK_GRASS, BLOCK_GRAVEL, BLOCK_IRON_ORE, BLOCK_LAVA, BLOCK_LEAVES,
    BLOCK_LOG, BLOCK_PLANKS, BLOCK_REDSTONE_ORE, BLOCK_SAND, BLOCK_SNOW,
    BLOCK_STONE, BLOCK_TALL_GRASS, BLOCK_WATER,
)


_BLOCK_COLORS = {
    BLOCK_AIR:            (45, 60, 100),
    BLOCK_GRASS:          (70, 170, 75),
    BLOCK_DIRT:           (130, 90, 60),
    BLOCK_STONE:          (135, 135, 135),
    BLOCK_COBBLESTONE:    (115, 115, 115),
    BLOCK_SAND:           (225, 205, 140),
    BLOCK_LOG:            (95, 65, 35),
    BLOCK_LEAVES:         (45, 110, 35),
    BLOCK_WATER:          (55, 100, 200),
    BLOCK_LAVA:           (220, 100, 30),
    BLOCK_GLASS:          (200, 220, 230),
    BLOCK_SNOW:           (240, 245, 250),
    BLOCK_PLANKS:         (165, 125, 75),
    BLOCK_GRAVEL:         (160, 160, 160),
    BLOCK_COAL_ORE:       (60, 60, 60),
    BLOCK_IRON_ORE:       (180, 160, 130),
    BLOCK_GOLD_ORE:       (220, 200, 90),
    BLOCK_DIAMOND_ORE:    (130, 220, 220),
    BLOCK_REDSTONE_ORE:   (180, 60, 60),
    BLOCK_TALL_GRASS:     (85, 165, 65),
    BLOCK_FLOWER_RED:     (200, 70, 70),
    BLOCK_FLOWER_YELLOW:  (220, 200, 70),
    BLOCK_BEDROCK:        (40, 40, 40),
    BLOCK_CRAFTING_TABLE: (140, 100, 50),
    BLOCK_FURNACE:        (80, 80, 80),
    BLOCK_CHEST:          (180, 130, 70),
}


class Minimap:
    """A persistent 64x64 RGBA minimap surface, refilled on player movement."""

    SIZE = 64

    def __init__(self):
        self.pixels = np.zeros((self.SIZE, self.SIZE, 4), dtype=np.uint8)
        self.pixels[..., 3] = 230
        self._last_px = None
        self._last_pz = None
        self._timer = 0.0

    def _sample_color(self, world, wx: int, wz: int) -> tuple:
        h = world.terrain_height(wx, wz)
        # Walk down at most a few blocks until we hit something solid (cheap).
        for dy in range(0, 6):
            y = h + 2 - dy
            if y < 0 or y >= 256:
                continue
            bid = int(world.get_block(wx, y, wz))
            if bid != BLOCK_AIR:
                color = _BLOCK_COLORS.get(bid, (110, 100, 80))
                # Tint by elevation so terrain reads as terrain.
                shade = 0.55 + min(0.45, max(0.0, (h - 50) / 80.0))
                return (
                    int(color[0] * shade),
                    int(color[1] * shade),
                    int(color[2] * shade),
                )
        # Sky / unloaded fallback
        return (45, 60, 100)

    def update(self, world, player_pos, dt: float):
        """Refresh the minimap if the player moved or after a short interval."""
        self._timer += dt
        px = int(player_pos[0])
        pz = int(player_pos[2])
        moved = (px != self._last_px) or (pz != self._last_pz)
        if not moved and self._timer < 1.0:
            return
        self._timer = 0.0
        self._last_px = px
        self._last_pz = pz

        half = self.SIZE // 2
        for row in range(self.SIZE):
            wz = pz - half + row
            for col in range(self.SIZE):
                wx = px - half + col
                r, g, b = self._sample_color(world, wx, wz)
                self.pixels[row, col, 0] = r
                self.pixels[row, col, 1] = g
                self.pixels[row, col, 2] = b

    def to_bytes(self) -> bytes:
        return self.pixels.tobytes()
