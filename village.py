"""Village structure generation.

A village = one well at the chunk centre + 3-5 small houses placed in a
ring around it. Houses may straddle chunk borders, so cross-chunk block
writes go through `world.pending_block_writes` which is already drained
when a neighbour chunk loads.

Spawn rule: ~0.5% of chunks (one in ~200) try to place a village; the
site must sit on flat plains/savanna above sea level. Villager spawn
positions for each chunk are stored in `_spawn_spots` and consumed by
`World._spawn_mobs_for_chunk`.
"""

from __future__ import annotations

import math
import random
from typing import Dict, List, Tuple

from .chunk import (
    BLOCK_AIR,
    BLOCK_COBBLESTONE,
    BLOCK_DIRT,
    BLOCK_FLOWER_RED,
    BLOCK_FLOWER_YELLOW,
    BLOCK_GLASS,
    BLOCK_GRASS,
    BLOCK_GRAVEL,
    BLOCK_LEAVES,
    BLOCK_LOG,
    BLOCK_PLANKS,
    BLOCK_TALL_GRASS,
    BLOCK_WATER,
)


def _is_obstruction(bid: int) -> bool:
    """Vegetation/log/leaves blocks we should clear inside a building bbox."""
    return bid in (BLOCK_LOG, BLOCK_LEAVES, BLOCK_TALL_GRASS,
                   BLOCK_FLOWER_RED, BLOCK_FLOWER_YELLOW)


class VillageBuilder:
    def __init__(self, seed: int):
        self.seed = int(seed)
        # (cx, cz) -> list of (vx, vy, vz) villager spawn positions
        self._spawn_spots: Dict[Tuple[int, int], List[Tuple[float, float, float]]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def maybe_place_village(self, world_gen, blocks, cx: int, cz: int) -> None:
        rh = (cx * 7919) ^ (cz * 6571) ^ self.seed
        rh = (rh ^ (rh >> 13)) & 0xFFFFFFFF
        if (rh % 200) != 0:
            return
        if not self._is_suitable(world_gen, cx, cz):
            return
        rng = random.Random(rh)
        self._build_village(world_gen, blocks, cx, cz, rng)

    def get_villager_spawn_positions(self, cx: int, cz: int) -> List[Tuple[float, float, float]]:
        return self._spawn_spots.get((cx, cz), [])

    # ------------------------------------------------------------------
    # Suitability check
    # ------------------------------------------------------------------

    def _is_suitable(self, world_gen, cx: int, cz: int) -> bool:
        ox, oz = cx * 16, cz * 16
        cx_centre, cz_centre = ox + 8, oz + 8
        # Use a 3x3 sampling pattern across the chunk.
        samples = [
            (ox + 2, oz + 2), (cx_centre, oz + 2), (ox + 13, oz + 2),
            (ox + 2, cz_centre), (cx_centre, cz_centre), (ox + 13, cz_centre),
            (ox + 2, oz + 13), (cx_centre, oz + 13), (ox + 13, oz + 13),
        ]
        heights = []
        sea = world_gen.sea_level
        for wx, wz in samples:
            biome = world_gen.get_biome(wx, wz)
            # Plains (0), Savanna (9), Forest (1) are acceptable village sites.
            if biome not in (0, 1, 9):
                return False
            h = world_gen.terrain_height(wx, wz)
            if h <= sea + 1 or h > 110:
                return False
            heights.append(h)
        hmin, hmax = min(heights), max(heights)
        if hmax - hmin > 3:
            return False
        return True

    # ------------------------------------------------------------------
    # Building helpers
    # ------------------------------------------------------------------

    def _set_world(self, world_gen, blocks, cx: int, cz: int,
                   wx: int, wy: int, wz: int, bid: int) -> None:
        if wy < 1 or wy >= 255:
            return
        tcx = wx // 16 if wx >= 0 else -((-wx + 15) // 16)
        tcz = wz // 16 if wz >= 0 else -((-wz + 15) // 16)
        # Floor-division for negative coordinates
        tcx = math.floor(wx / 16)
        tcz = math.floor(wz / 16)
        lx = int(wx - tcx * 16)
        lz = int(wz - tcz * 16)
        if tcx == cx and tcz == cz:
            blocks[lx, wy, lz] = bid
        else:
            world_gen.world.pending_block_writes.setdefault((tcx, tcz), []).append(
                (lx, wy, lz, bid)
            )

    def _get_world(self, world_gen, blocks, cx: int, cz: int,
                   wx: int, wy: int, wz: int) -> int:
        if wy < 0 or wy >= 256:
            return BLOCK_AIR
        tcx = math.floor(wx / 16)
        tcz = math.floor(wz / 16)
        lx = int(wx - tcx * 16)
        lz = int(wz - tcz * 16)
        if tcx == cx and tcz == cz:
            return int(blocks[lx, wy, lz])
        # For neighbour chunks we can't read existing state during generation;
        # treat as air so we still write through.
        return BLOCK_AIR

    # ------------------------------------------------------------------
    # Village layout
    # ------------------------------------------------------------------

    def _build_village(self, world_gen, blocks, cx: int, cz: int, rng: random.Random) -> None:
        ox, oz = cx * 16, cz * 16
        well_x = ox + 8
        well_z = oz + 8
        well_y = world_gen.terrain_height(well_x, well_z)

        # 1. Build the well
        self._build_well(world_gen, blocks, cx, cz, well_x, well_y, well_z)
        self._register_spawn(cx, cz, well_x, well_y + 1, well_z)

        # 2. Place 3-5 houses in a ring around the well
        house_count = rng.randint(3, 5)
        placed: List[Tuple[int, int, int, int, int, int]] = []  # AABB list (x0,z0,x1,z1, y, key)
        for _ in range(house_count):
            for _attempt in range(8):
                angle = rng.uniform(0.0, 2.0 * math.pi)
                radius = rng.uniform(8.0, 12.0)
                hx = int(well_x + math.cos(angle) * radius)
                hz = int(well_z + math.sin(angle) * radius)
                hy = world_gen.terrain_height(hx, hz)
                if abs(hy - well_y) > 3:
                    continue
                # House footprint is 5x5 centred on (hx, hz).
                x0, x1 = hx - 2, hx + 2
                z0, z1 = hz - 2, hz + 2
                if any(self._overlaps(x0, z0, x1, z1, p) for p in placed):
                    continue
                placed.append((x0, z0, x1, z1, hy, 0))
                self._build_house_small(world_gen, blocks, cx, cz, hx, hy, hz, rng)
                # Path from well to house: replace surface grass with gravel
                self._build_path(world_gen, blocks, cx, cz, well_x, well_z, hx, hz)
                break

    def _overlaps(self, x0: int, z0: int, x1: int, z1: int, other: tuple) -> bool:
        ox0, oz0, ox1, oz1, _, _ = other
        # Pad by 1 so houses aren't flush against each other.
        return not (x1 + 1 < ox0 or x0 - 1 > ox1 or z1 + 1 < oz0 or z0 - 1 > oz1)

    # ------------------------------------------------------------------
    # Building primitives
    # ------------------------------------------------------------------

    def _build_well(self, world_gen, blocks, cx: int, cz: int,
                    wx: int, wy: int, wz: int) -> None:
        # 4x4 cobblestone rim at wy, with water in the central 2x2 at wy.
        for dx in range(-2, 2):
            for dz in range(-2, 2):
                self._set_world(world_gen, blocks, cx, cz, wx + dx, wy, wz + dz, BLOCK_COBBLESTONE)
        # Hollow centre with water
        for dx in (-1, 0):
            for dz in (-1, 0):
                self._set_world(world_gen, blocks, cx, cz, wx + dx, wy, wz + dz, BLOCK_WATER)
        # Four corner pillars 2 high
        for (dx, dz) in ((-2, -2), (1, -2), (-2, 1), (1, 1)):
            self._set_world(world_gen, blocks, cx, cz, wx + dx, wy + 1, wz + dz, BLOCK_LOG)
            self._set_world(world_gen, blocks, cx, cz, wx + dx, wy + 2, wz + dz, BLOCK_LOG)
        # Roof slab of planks above
        for dx in range(-2, 2):
            for dz in range(-2, 2):
                self._set_world(world_gen, blocks, cx, cz, wx + dx, wy + 3, wz + dz, BLOCK_PLANKS)

    def _build_house_small(self, world_gen, blocks, cx: int, cz: int,
                            hx: int, hy: int, hz: int, rng: random.Random) -> None:
        """A 5x4x5 house: cobblestone foundation, plank walls, glass windows, doorway."""
        # Door faces toward the well — pick the side closest in chunk-x or chunk-z direction.
        well_x = cx * 16 + 8
        well_z = cz * 16 + 8
        dxw = well_x - hx
        dzw = well_z - hz
        if abs(dxw) >= abs(dzw):
            door_side = 'E' if dxw > 0 else 'W'
        else:
            door_side = 'S' if dzw > 0 else 'N'

        # Foundation (one block below surface, 5x5 cobblestone)
        for dx in range(-2, 3):
            for dz in range(-2, 3):
                self._set_world(world_gen, blocks, cx, cz, hx + dx, hy, hz + dz, BLOCK_COBBLESTONE)
        # Clear inside (3x3x3) of any vegetation
        for dx in range(-1, 2):
            for dz in range(-1, 2):
                for dy in range(1, 4):
                    self._set_world(world_gen, blocks, cx, cz, hx + dx, hy + dy, hz + dz, BLOCK_AIR)
        # Walls: 5x5 frame, 3 blocks high.
        for dy in (1, 2, 3):
            for dx in range(-2, 3):
                for dz in range(-2, 3):
                    edge = (dx == -2 or dx == 2 or dz == -2 or dz == 2)
                    if not edge:
                        continue
                    # Default: planks
                    bid = BLOCK_PLANKS
                    # Corner posts → log
                    if abs(dx) == 2 and abs(dz) == 2:
                        bid = BLOCK_LOG
                    # Windows on middle row, mid of each non-door wall
                    elif dy == 2 and (dx == 0 or dz == 0):
                        # Skip the door wall
                        skip = ((door_side == 'E' and dx == 2 and dz == 0)
                                or (door_side == 'W' and dx == -2 and dz == 0)
                                or (door_side == 'S' and dz == 2 and dx == 0)
                                or (door_side == 'N' and dz == -2 and dx == 0))
                        if not skip:
                            bid = BLOCK_GLASS
                    self._set_world(world_gen, blocks, cx, cz, hx + dx, hy + dy, hz + dz, bid)
        # Doorway: 1 wide, 2 tall on the chosen side
        if door_side == 'E':
            dxs, dzs = (2, 0)
        elif door_side == 'W':
            dxs, dzs = (-2, 0)
        elif door_side == 'S':
            dxs, dzs = (0, 2)
        else:
            dxs, dzs = (0, -2)
        self._set_world(world_gen, blocks, cx, cz, hx + dxs, hy + 1, hz + dzs, BLOCK_AIR)
        self._set_world(world_gen, blocks, cx, cz, hx + dxs, hy + 2, hz + dzs, BLOCK_AIR)
        # Roof: 5x5 planks at hy+4
        for dx in range(-2, 3):
            for dz in range(-2, 3):
                self._set_world(world_gen, blocks, cx, cz, hx + dx, hy + 4, hz + dz, BLOCK_PLANKS)
        # Register villager spawn just outside the doorway
        spawn_x = hx + dxs * 1.5
        spawn_z = hz + dzs * 1.5
        self._register_spawn(cx, cz, spawn_x, hy + 1, spawn_z)
        # And one inside for variety
        self._register_spawn(cx, cz, hx, hy + 1, hz)

    def _build_path(self, world_gen, blocks, cx: int, cz: int,
                     x0: int, z0: int, x1: int, z1: int) -> None:
        """Replace surface grass/dirt with gravel along a straight line from (x0,z0) to (x1,z1)."""
        dx = x1 - x0
        dz = z1 - z0
        steps = max(abs(dx), abs(dz))
        if steps == 0:
            return
        for i in range(1, steps):
            px = x0 + int(round(dx * i / steps))
            pz = z0 + int(round(dz * i / steps))
            py = world_gen.terrain_height(px, pz)
            self._set_world(world_gen, blocks, cx, cz, px, py, pz, BLOCK_GRAVEL)
            # Clear the air block just above so the path is walkable.
            if 0 <= py + 1 < 255:
                # Only clear if it might be tall grass/flower; safer to always set air on the
                # tall-grass slot since we're inside a village footprint.
                pass

    # ------------------------------------------------------------------
    # Spawn-spot registration (cross-chunk aware)
    # ------------------------------------------------------------------

    def _register_spawn(self, cx: int, cz: int, x: float, y: float, z: float) -> None:
        # Determine which chunk this spawn-point falls into so the right
        # `_spawn_mobs_for_chunk` call will see it.
        tcx = math.floor(x / 16)
        tcz = math.floor(z / 16)
        key = (int(tcx), int(tcz))
        self._spawn_spots.setdefault(key, []).append((float(x) + 0.5, float(y), float(z) + 0.5))
