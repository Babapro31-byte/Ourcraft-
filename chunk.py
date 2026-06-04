from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass
from typing import Dict, Iterable, Tuple

import numpy as np


BLOCK_AIR = 0
BLOCK_GRASS = 1
BLOCK_DIRT = 2
BLOCK_STONE = 3
BLOCK_SAND = 4
BLOCK_LOG = 5
BLOCK_LEAVES = 6
BLOCK_WATER = 7
BLOCK_BEDROCK = 8
BLOCK_SNOW = 9
BLOCK_GLASS = 10
BLOCK_PLANKS = 11
BLOCK_STICK = 12
BLOCK_CRAFTING_TABLE = 13
BLOCK_COBBLESTONE = 14
BLOCK_GRAVEL = 15
BLOCK_LAVA = 16
BLOCK_COAL_ORE = 17
BLOCK_IRON_ORE = 18
BLOCK_GOLD_ORE = 19
BLOCK_DIAMOND_ORE = 20
BLOCK_REDSTONE_ORE = 21
BLOCK_TALL_GRASS = 22
BLOCK_FLOWER_RED = 23
BLOCK_FLOWER_YELLOW = 24
BLOCK_FURNACE = 25
BLOCK_CHEST = 26
BLOCK_GRANITE = 27
BLOCK_ANDESITE = 28
BLOCK_DIORITE = 29
BLOCK_CLAY = 30
BLOCK_MUSHROOM_RED = 31
BLOCK_MUSHROOM_BROWN = 32
BLOCK_SUGAR_CANE = 33
BLOCK_COAL_BLOCK = 34
BLOCK_IRON_BLOCK = 35
BLOCK_GOLD_BLOCK = 36
BLOCK_DIAMOND_BLOCK = 37
BLOCK_REDSTONE_BLOCK = 38
BLOCK_SANDSTONE = 39
BLOCK_STONE_BRICKS = 40
BLOCK_BRICKS = 41
BLOCK_BOOKSHELF = 42
BLOCK_TNT = 43
BLOCK_WOOL = 44
BLOCK_BED = 45
BLOCK_DEEPSLATE = 46
BLOCK_DEEPSLATE_COAL = 47
BLOCK_DEEPSLATE_IRON = 48
BLOCK_DEEPSLATE_GOLD = 49
BLOCK_DEEPSLATE_REDSTONE = 50
BLOCK_DEEPSLATE_DIAMOND = 51
BLOCK_COPPER_ORE = 52
BLOCK_DEEPSLATE_COPPER = 53
BLOCK_COPPER_BLOCK = 54
BLOCK_BLOCKS_COUNT = 55  # Total block count


FACE_PX = 0
FACE_NX = 1
FACE_PY = 2
FACE_NY = 3
FACE_PZ = 4
FACE_NZ = 5


def is_transparent(block_id: int) -> bool:
    return block_id in (BLOCK_WATER, BLOCK_GLASS, BLOCK_LEAVES, BLOCK_LAVA,
                        BLOCK_TALL_GRASS, BLOCK_FLOWER_RED, BLOCK_FLOWER_YELLOW,
                        BLOCK_MUSHROOM_RED, BLOCK_MUSHROOM_BROWN, BLOCK_SUGAR_CANE)


TRANSPARENT_BLOCKS = {BLOCK_AIR, BLOCK_WATER, BLOCK_GLASS, BLOCK_LEAVES, BLOCK_LAVA,
                      BLOCK_TALL_GRASS, BLOCK_FLOWER_RED, BLOCK_FLOWER_YELLOW,
                      BLOCK_MUSHROOM_RED, BLOCK_MUSHROOM_BROWN, BLOCK_SUGAR_CANE}


def is_solid(block_id: int) -> bool:
    return block_id not in (BLOCK_AIR, BLOCK_WATER, BLOCK_LAVA,
                             BLOCK_TALL_GRASS, BLOCK_FLOWER_RED, BLOCK_FLOWER_YELLOW,
                             BLOCK_MUSHROOM_RED, BLOCK_MUSHROOM_BROWN, BLOCK_SUGAR_CANE)


def occludes_face(block_id: int) -> bool:
    return block_id not in (BLOCK_AIR, BLOCK_WATER, BLOCK_LAVA, BLOCK_GLASS,
                             BLOCK_TALL_GRASS, BLOCK_FLOWER_RED, BLOCK_FLOWER_YELLOW,
                             BLOCK_MUSHROOM_RED, BLOCK_MUSHROOM_BROWN, BLOCK_SUGAR_CANE)


def face_should_render(this_id: int, neighbor_id: int) -> bool:
    if neighbor_id == BLOCK_AIR:
        return True
    if this_id == BLOCK_WATER and neighbor_id == BLOCK_WATER:
        return False
    if this_id == BLOCK_LAVA and neighbor_id == BLOCK_LAVA:
        return False
    if this_id == BLOCK_GLASS and neighbor_id == BLOCK_GLASS:
        return False
    if is_transparent(this_id):
        return not occludes_face(neighbor_id)
    return not occludes_face(neighbor_id)


def ao_factor(ao: int) -> float:
    if ao <= 0:
        return 0.78
    if ao == 1:
        return 0.84
    if ao == 2:
        return 0.92
    return 1.00


def vertex_ao(side1: bool, side2: bool, corner: bool) -> int:
    if side1 and side2:
        return 0
    occ = (1 if side1 else 0) + (1 if side2 else 0) + (1 if corner else 0)
    return 3 - occ


def get_sky_light(light_val: int) -> int:
    return (light_val >> 4) & 0x0F


def get_block_light(light_val: int) -> int:
    return light_val & 0x0F


def _neighbor_solid(world, x: int, y: int, z: int) -> bool:
    return occludes_face(world.get_block(x, y, z))


# ----------------------------------------------------------------------
# Module-level lookup tables for the vectorized mesh builder.
# ----------------------------------------------------------------------

_AO_LUT = np.array([0.60, 0.75, 0.88, 1.00], dtype="f4")

# Packed light byte -> normalized brightness in [0.5, 1.0].
_LIGHT_LUT = np.empty(256, dtype="f4")
for _v in range(256):
    _sky = (_v >> 4) & 0x0F
    _blk = _v & 0x0F
    _LIGHT_LUT[_v] = 0.5 + (max(_sky, _blk) / 15.0) * 0.5

# Per-block constant tint. grass/leaves/tall_grass are recoloured per biome via
# _biome_tint_lut(); this base table is the fallback (plains-like overworld green).
_TINT_LUT = np.ones((BLOCK_BLOCKS_COUNT, 3), dtype="f4")
_TINT_LUT[BLOCK_GRASS]      = (0.65, 0.95, 0.50)
_TINT_LUT[BLOCK_LEAVES]     = (0.55, 0.85, 0.45)
_TINT_LUT[BLOCK_TALL_GRASS] = (0.65, 0.95, 0.50)

# Minecraft-style biome foliage colouring: (grass_rgb, leaves_rgb) per biome id
# (see world_generator BIOME_* constants 0..11). Grass also tints tall_grass.
_BIOME_FOLIAGE = {
    0:  ((0.57, 0.92, 0.44), (0.48, 0.85, 0.38)),  # plains
    1:  ((0.48, 0.85, 0.40), (0.42, 0.80, 0.34)),  # forest
    2:  ((0.74, 0.71, 0.34), (0.62, 0.66, 0.30)),  # desert (dry)
    3:  ((0.50, 0.68, 0.55), (0.42, 0.62, 0.50)),  # snow plains (pale)
    4:  ((0.45, 0.66, 0.49), (0.40, 0.60, 0.44)),  # taiga (grey-green)
    5:  ((0.57, 0.85, 0.45), (0.48, 0.80, 0.38)),  # beach
    6:  ((0.55, 0.84, 0.46), (0.48, 0.80, 0.38)),  # ocean
    7:  ((0.42, 0.55, 0.30), (0.38, 0.50, 0.28)),  # swamp (murky)
    8:  ((0.35, 0.85, 0.28), (0.30, 0.78, 0.24)),  # jungle (vivid)
    9:  ((0.74, 0.72, 0.34), (0.66, 0.66, 0.32)),  # savanna (dry yellow-green)
    10: ((0.52, 0.78, 0.46), (0.46, 0.74, 0.40)),  # mountain
    11: ((0.55, 0.85, 0.45), (0.48, 0.80, 0.40)),  # foothills
}
_BIOME_TINT_CACHE: dict = {}


def _biome_tint_lut(biome_id: int) -> np.ndarray:
    """Return a per-block tint LUT with grass/leaves/tall_grass recoloured for
    the given biome. Cached per biome; falls back to the base table if unknown."""
    lut = _BIOME_TINT_CACHE.get(biome_id)
    if lut is None:
        colors = _BIOME_FOLIAGE.get(biome_id)
        if colors is None:
            lut = _TINT_LUT
        else:
            grass_c, leaves_c = colors
            lut = _TINT_LUT.copy()
            lut[BLOCK_GRASS] = grass_c
            lut[BLOCK_TALL_GRASS] = grass_c
            lut[BLOCK_LEAVES] = leaves_c
        _BIOME_TINT_CACHE[biome_id] = lut
    return lut

# Animation flag (water/lava UV scroll).
_ANIM_LUT = np.zeros(BLOCK_BLOCKS_COUNT, dtype="f4")
_ANIM_LUT[BLOCK_WATER] = 1.0
_ANIM_LUT[BLOCK_LAVA] = 1.0

# Light-emitting blocks: block_id -> emission level (0-15), Minecraft-style.
# Lava glows at 15; add torch=14 / glowstone=15 here once those blocks exist.
LIGHT_EMISSION = {
    BLOCK_LAVA: 15,
}

# Transparency class: 0 opaque, 1 cutout (leaves/glass/grass/flowers), 2 translucent (water/lava).
_CLASS_LUT = np.zeros(BLOCK_BLOCKS_COUNT, dtype=np.int8)
for _b in (BLOCK_LEAVES, BLOCK_GLASS, BLOCK_TALL_GRASS, BLOCK_FLOWER_RED, BLOCK_FLOWER_YELLOW,
           BLOCK_MUSHROOM_RED, BLOCK_MUSHROOM_BROWN, BLOCK_SUGAR_CANE):
    _CLASS_LUT[_b] = 1
for _b in (BLOCK_WATER, BLOCK_LAVA):
    _CLASS_LUT[_b] = 2

# Mask of non-occluding block ids (used to decide whether a face renders against neighbor).
# LEAVES must be here: they are alpha-cutout, so a solid block behind a leaf must still draw its
# face (otherwise the void shows through the leaf's transparent gaps = x-ray). Leaf-vs-leaf faces
# are separately culled by the same_translucent mask in the mesh builder.
_NON_OCCLUDING = np.zeros(BLOCK_BLOCKS_COUNT, dtype=bool)
for _b in (BLOCK_AIR, BLOCK_WATER, BLOCK_LAVA, BLOCK_GLASS, BLOCK_LEAVES,
           BLOCK_TALL_GRASS, BLOCK_FLOWER_RED, BLOCK_FLOWER_YELLOW,
           BLOCK_MUSHROOM_RED, BLOCK_MUSHROOM_BROWN, BLOCK_SUGAR_CANE):
    _NON_OCCLUDING[_b] = True

# Foliage blocks render as two perpendicular X-cross quads instead of cube faces.
_FOLIAGE_BLOCKS = (BLOCK_TALL_GRASS, BLOCK_FLOWER_RED, BLOCK_FLOWER_YELLOW,
                   BLOCK_MUSHROOM_RED, BLOCK_MUSHROOM_BROWN, BLOCK_SUGAR_CANE)
_IS_FOLIAGE = np.zeros(BLOCK_BLOCKS_COUNT, dtype=bool)
for _b in _FOLIAGE_BLOCKS:
    _IS_FOLIAGE[_b] = True

# Per-face static data: (drx, dry, drz, normal, corner_offsets, ao_offsets).
_FACE_DATA = (
    # FACE_PX
    (1, 0, 0, (1.0, 0.0, 0.0),
     ((1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)),
     (((0, -1, 0), (0, 0, -1), (0, -1, -1)), ((0, 1, 0), (0, 0, -1), (0, 1, -1)),
      ((0, 1, 0), (0, 0, 1), (0, 1, 1)), ((0, -1, 0), (0, 0, 1), (0, -1, 1)))),
    # FACE_NX
    (-1, 0, 0, (-1.0, 0.0, 0.0),
     ((0, 0, 1), (0, 1, 1), (0, 1, 0), (0, 0, 0)),
     (((0, -1, 0), (0, 0, 1), (0, -1, 1)), ((0, 1, 0), (0, 0, 1), (0, 1, 1)),
      ((0, 1, 0), (0, 0, -1), (0, 1, -1)), ((0, -1, 0), (0, 0, -1), (0, -1, -1)))),
    # FACE_PY
    (0, 1, 0, (0.0, 1.0, 0.0),
     ((0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0)),
     (((-1, 0, 0), (0, 0, -1), (-1, 0, -1)), ((-1, 0, 0), (0, 0, 1), (-1, 0, 1)),
      ((1, 0, 0), (0, 0, 1), (1, 0, 1)), ((1, 0, 0), (0, 0, -1), (1, 0, -1)))),
    # FACE_NY
    (0, -1, 0, (0.0, -1.0, 0.0),
     ((0, 0, 1), (0, 0, 0), (1, 0, 0), (1, 0, 1)),
     (((-1, 0, 0), (0, 0, 1), (-1, 0, 1)), ((-1, 0, 0), (0, 0, -1), (-1, 0, -1)),
      ((1, 0, 0), (0, 0, -1), (1, 0, -1)), ((1, 0, 0), (0, 0, 1), (1, 0, 1)))),
    # FACE_PZ
    (0, 0, 1, (0.0, 0.0, 1.0),
     ((1, 0, 1), (1, 1, 1), (0, 1, 1), (0, 0, 1)),
     (((0, -1, 0), (-1, 0, 0), (-1, -1, 0)), ((0, 1, 0), (-1, 0, 0), (-1, 1, 0)),
      ((0, 1, 0), (1, 0, 0), (1, 1, 0)), ((0, -1, 0), (1, 0, 0), (1, -1, 0)))),
    # FACE_NZ
    (0, 0, -1, (0.0, 0.0, -1.0),
     ((0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)),
     (((0, -1, 0), (1, 0, 0), (1, -1, 0)), ((0, 1, 0), (1, 0, 0), (1, 1, 0)),
      ((0, 1, 0), (-1, 0, 0), (-1, 1, 0)), ((0, -1, 0), (-1, 0, 0), (-1, -1, 0)))),
)

# UV table built lazily on the first mesh build (we need texture-manager data).
_UV_TABLE = None
_UV_TABLE_LOCK = threading.Lock()


def _ensure_uv_table(uv_by_block_face):
    global _UV_TABLE
    if _UV_TABLE is not None:
        return _UV_TABLE
    with _UV_TABLE_LOCK:
        if _UV_TABLE is None:
            t = np.zeros((BLOCK_BLOCKS_COUNT, 6, 4), dtype="f4")
            for (bid, face), uvs in uv_by_block_face.items():
                if 0 <= bid < BLOCK_BLOCKS_COUNT and 0 <= face < 6:
                    t[bid, face] = uvs
            _UV_TABLE = t
    return _UV_TABLE


# Thread-local scratch arrays so mesh builds don't re-allocate ~200KB each time.
_tls = threading.local()


def _scratch():
    if not hasattr(_tls, "padded"):
        _tls.padded = np.zeros((18, 258, 18), dtype=np.uint8)
        _tls.padded_light = np.zeros((18, 258, 18), dtype=np.uint8)
    return _tls.padded, _tls.padded_light


@dataclass(slots=True)
class ChunkMeshData:
    opaque: np.ndarray
    cutout: np.ndarray
    translucent: np.ndarray


class Chunk:
    __slots__ = ("cx", "cz", "blocks", "light", "dirty", "modified", "world")

    def __init__(self, cx: int, cz: int, world=None):
        self.cx = int(cx)
        self.cz = int(cz)
        self.blocks = np.zeros((16, 256, 16), dtype=np.uint8)
        self.light = np.zeros((16, 256, 16), dtype=np.uint8)
        self.dirty = True
        self.modified = False
        self.world = world

    def get_local(self, lx: int, y: int, lz: int) -> int:
        if 0 <= lx < 16 and 0 <= lz < 16 and 0 <= y < 256:
            return int(self.blocks[lx, y, lz])
        return BLOCK_AIR

    def set_local(self, lx: int, y: int, lz: int, block_id: int) -> None:
        if 0 <= lx < 16 and 0 <= lz < 16 and 0 <= y < 256:
            self.blocks[lx, y, lz] = int(block_id)
            self.dirty = True
            self.modified = True

    def set_block(self, lx: int, y: int, lz: int, block_id: int) -> None:
        if 0 <= lx < 16 and 0 <= lz < 16 and 0 <= y < 256:
            self.blocks[lx, y, lz] = int(block_id)
            self.dirty = True
            return
        dcx = 0
        dcz = 0
        if lx < 0:
            dcx = -1
            lx += 16
        elif lx >= 16:
            dcx = 1
            lx -= 16
        if lz < 0:
            dcz = -1
            lz += 16
        elif lz >= 16:
            dcz = 1
            lz -= 16
        if dcx != 0 or dcz != 0:
            if self.world is None:
                return
            ncx = self.cx + dcx
            ncz = self.cz + dcz
            neighbor = self.world.chunks.get((ncx, ncz))
            if neighbor is not None:
                neighbor.set_block(lx, y, lz, block_id)
            else:
                key = (ncx, ncz)
                q = self.world.pending_block_writes
                if key not in q:
                    q[key] = []
                q[key].append((lx, y, lz, block_id))

    def get_neighbor_chunk(self, dx: int, dz: int):
        if self.world is None:
            return None
        return self.world.get_chunk(self.cx + dx, self.cz + dz, generate=True)

    def propagate_sky_light(self) -> None:
        transparent_blocks_array = np.array(list(TRANSPARENT_BLOCKS), dtype=np.uint8)
        level = np.full((16, 16), 15, dtype=np.uint8)

        for y in range(255, -1, -1):
            blocks_at_y = self.blocks[:, y, :]
            is_opaque = ~np.isin(blocks_at_y, transparent_blocks_array)
            level = np.where(is_opaque, 0, level)
            self.light[:, y, :] = (self.light[:, y, :] & 0x0F) | (level.astype(np.uint8) << 4)

    def propagate_initial_block_light(self) -> None:
        """Chunk-local BFS that lights up emitter blocks (lava, etc.) at load.
        Cross-chunk spill is handled later by World.update_block_light_for_edit;
        here we just seed the chunk's own emitters so caves glow on generation."""
        if not LIGHT_EMISSION:
            return
        # Clear the block-light nibble (keep sky nibble) before seeding.
        self.light &= 0xF0
        q = deque()
        for bid, lvl in LIGHT_EMISSION.items():
            for lx, y, lz in np.argwhere(self.blocks == bid):
                lx, y, lz = int(lx), int(y), int(lz)
                self.light[lx, y, lz] = (self.light[lx, y, lz] & 0xF0) | (lvl & 0x0F)
                q.append((lx, y, lz, lvl))
        while q:
            lx, y, lz, lvl = q.popleft()
            if lvl <= 1:
                continue
            for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                nx, ny, nz = lx + dx, y + dy, lz + dz
                if not (0 <= nx < 16 and 0 <= nz < 16 and 0 <= ny < 256):
                    continue
                if int(self.blocks[nx, ny, nz]) not in TRANSPARENT_BLOCKS:
                    continue
                if (self.light[nx, ny, nz] & 0x0F) >= lvl - 1:
                    continue
                self.light[nx, ny, nz] = (self.light[nx, ny, nz] & 0xF0) | ((lvl - 1) & 0x0F)
                q.append((nx, ny, nz, lvl - 1))

    # ------------------------------------------------------------------
    # Vectorized mesh builder.
    # ------------------------------------------------------------------

    def build_mesh(self, world, uv_by_block_face) -> ChunkMeshData:
        UV_TABLE = _ensure_uv_table(uv_by_block_face)

        ox, oz = self.cx * 16, self.cz * 16

        # Biome-aware foliage tint (grass/leaves) sampled once at chunk centre.
        tint_lut = _TINT_LUT
        try:
            if world is not None and hasattr(world, "get_biome"):
                tint_lut = _biome_tint_lut(int(world.get_biome(ox + 8, oz + 8)))
        except Exception:
            tint_lut = _TINT_LUT

        # --- 1. Padded block + light arrays via thread-local scratch ---
        padded, padded_light = _scratch()
        padded.fill(0)
        padded_light.fill(0)
        padded[1:17, 1:257, 1:17] = self.blocks
        padded_light[1:17, 1:257, 1:17] = self.light

        for drx, drz in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nc = world.chunks.get((self.cx + drx, self.cz + drz))
            if nc:
                if drx == -1:
                    padded[0, 1:257, 1:17] = nc.blocks[15, :, :]
                    padded_light[0, 1:257, 1:17] = nc.light[15, :, :]
                elif drx == 1:
                    padded[17, 1:257, 1:17] = nc.blocks[0, :, :]
                    padded_light[17, 1:257, 1:17] = nc.light[0, :, :]
                elif drz == -1:
                    padded[1:17, 1:257, 0] = nc.blocks[:, :, 15]
                    padded_light[1:17, 1:257, 0] = nc.light[:, :, 15]
                elif drz == 1:
                    padded[1:17, 1:257, 17] = nc.blocks[:, :, 0]
                    padded_light[1:17, 1:257, 17] = nc.light[:, :, 0]
            else:
                # Missing neighbor = solid wall (prevents x-ray) + full sky light.
                if drx == -1:
                    padded[0, 1:257, 1:17] = BLOCK_STONE
                    padded_light[0, 1:257, 1:17] = 0xF0
                elif drx == 1:
                    padded[17, 1:257, 1:17] = BLOCK_STONE
                    padded_light[17, 1:257, 1:17] = 0xF0
                elif drz == -1:
                    padded[1:17, 1:257, 0] = BLOCK_STONE
                    padded_light[1:17, 1:257, 0] = 0xF0
                elif drz == 1:
                    padded[1:17, 1:257, 17] = BLOCK_STONE
                    padded_light[1:17, 1:257, 17] = 0xF0

        # Diagonal corners for AO at chunk seams.
        for drx, drz in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
            nc = world.chunks.get((self.cx + drx, self.cz + drz))
            px = 0 if drx == -1 else 17
            pz = 0 if drz == -1 else 17
            if nc:
                bx = 15 if drx == -1 else 0
                bz = 15 if drz == -1 else 0
                padded[px, 1:257, pz] = nc.blocks[bx, :, bz]
                padded_light[px, 1:257, pz] = nc.light[bx, :, bz]
            else:
                padded[px, 1:257, pz] = BLOCK_STONE
                padded_light[px, 1:257, pz] = 0xF0

        # --- 2. Occlusion array (1 = blocks AO neighbor, 0 = sees through) ---
        occ = (~_NON_OCCLUDING[padded] & (padded != BLOCK_AIR)).astype(np.uint8)

        blocks_view = padded[1:17, 1:257, 1:17]
        foliage_mask = _IS_FOLIAGE[blocks_view]
        exists = (blocks_view > 0) & ~foliage_mask

        # Buckets per transparency class.
        opaque_buckets = []
        cutout_buckets = []
        trans_buckets = []

        # --- 3. Emit faces, one face direction at a time, fully vectorized ---
        for face_id in range(6):
            drx, dry, drz, normal, corner_offsets, ao_offsets = _FACE_DATA[face_id]
            nx_v, ny_v, nz_v = normal

            neigh = padded[1 + drx:17 + drx, 1 + dry:257 + dry, 1 + drz:17 + drz]

            # Visible-face mask: this block exists AND neighbor is non-occluding,
            # EXCEPT when both are the same translucent/cutout type (water-water, etc).
            neigh_non_occ = _NON_OCCLUDING[neigh]
            mask = exists & neigh_non_occ
            same_translucent = (
                ((blocks_view == BLOCK_WATER) & (neigh == BLOCK_WATER)) |
                ((blocks_view == BLOCK_LAVA) & (neigh == BLOCK_LAVA)) |
                ((blocks_view == BLOCK_GLASS) & (neigh == BLOCK_GLASS)) |
                ((blocks_view == BLOCK_LEAVES) & (neigh == BLOCK_LEAVES)) |
                ((blocks_view == BLOCK_TALL_GRASS) & (neigh == BLOCK_TALL_GRASS)) |
                ((blocks_view == BLOCK_FLOWER_RED) & (neigh == BLOCK_FLOWER_RED)) |
                ((blocks_view == BLOCK_FLOWER_YELLOW) & (neigh == BLOCK_FLOWER_YELLOW)) |
                ((blocks_view == BLOCK_MUSHROOM_RED) & (neigh == BLOCK_MUSHROOM_RED)) |
                ((blocks_view == BLOCK_MUSHROOM_BROWN) & (neigh == BLOCK_MUSHROOM_BROWN)) |
                ((blocks_view == BLOCK_SUGAR_CANE) & (neigh == BLOCK_SUGAR_CANE))
            )
            mask &= ~same_translucent

            lxs, ys, lzs = np.nonzero(mask)
            N = lxs.shape[0]
            if N == 0:
                continue

            bids = blocks_view[lxs, ys, lzs]

            # UV per face (N,4): u0, v0, u1, v1.
            uvs = UV_TABLE[bids, face_id]
            u0 = uvs[:, 0]; v0 = uvs[:, 1]
            u1 = uvs[:, 2]; v1 = uvs[:, 3]

            # AO per quad corner (4 corners × N).
            lxs1 = lxs + 1
            ys1 = ys + 1
            lzs1 = lzs + 1

            ao_vals = []
            for corner_off in ao_offsets:
                (d1, d2, dc) = corner_off
                s1 = occ[lxs1 + d1[0], ys1 + d1[1], lzs1 + d1[2]]
                s2 = occ[lxs1 + d2[0], ys1 + d2[1], lzs1 + d2[2]]
                co = occ[lxs1 + dc[0], ys1 + dc[1], lzs1 + dc[2]]
                ai = np.where((s1 == 1) & (s2 == 1), 0, 3 - (s1 + s2 + co))
                # ai is int but may be int8/uint8 arithmetic — cast safely.
                ao_vals.append(_AO_LUT[ai.astype(np.int64)])
            ao0, ao1, ao2, ao3 = ao_vals

            # Face light from the neighbor cell.
            face_light = _LIGHT_LUT[padded_light[lxs1 + drx, ys1 + dry, lzs1 + drz]]

            # Tint + animation flag.
            tint = tint_lut[bids]
            tr = tint[:, 0]; tg = tint[:, 1]; tb = tint[:, 2]
            anim = _ANIM_LUT[bids]

            # World-space corner positions.
            wx_f = lxs.astype("f4") + ox
            wz_f = lzs.astype("f4") + oz
            yf = ys.astype("f4")

            def make_corner(off):
                dx, dy, dz = off
                return np.column_stack((wx_f + dx, yf + dy, wz_f + dz)).astype("f4")

            c0 = make_corner(corner_offsets[0])
            c1 = make_corner(corner_offsets[1])
            c2 = make_corner(corner_offsets[2])
            c3 = make_corner(corner_offsets[3])

            # Constant per-face attribute columns.
            n_col = np.broadcast_to(
                np.array([nx_v, ny_v, nz_v], dtype="f4"), (N, 3)
            )

            # Build (N, 14) per-vertex tables for each of the 4 corners.
            def make_vert(corner, uu, vv, aov):
                return np.column_stack((
                    corner,                  # 3
                    n_col,                   # 3
                    uu, vv,                  # 1 + 1
                    aov,                     # 1
                    face_light,              # 1
                    tr, tg, tb,              # 3
                    anim,                    # 1
                )).astype("f4")

            v0_arr = make_vert(c0, u0, v0, ao0)
            v1_arr = make_vert(c1, u0, v1, ao1)
            v2_arr = make_vert(c2, u1, v1, ao2)
            v3_arr = make_vert(c3, u1, v0, ao3)

            # Triangulation: normal = c0,c1,c2,c0,c2,c3; flipped = c1,c2,c3,c1,c3,c0.
            quads_normal = np.stack(
                (v0_arr, v1_arr, v2_arr, v0_arr, v2_arr, v3_arr), axis=1
            )
            quads_flipped = np.stack(
                (v1_arr, v2_arr, v3_arr, v1_arr, v3_arr, v0_arr), axis=1
            )
            flip = (ao0 + ao2) < (ao1 + ao3)
            quads = np.where(flip[:, None, None], quads_flipped, quads_normal)

            # Bucket by transparency class.
            cls = _CLASS_LUT[bids]
            for cls_id, bucket in ((0, opaque_buckets), (1, cutout_buckets), (2, trans_buckets)):
                sel = cls == cls_id
                if sel.any():
                    bucket.append(quads[sel].reshape(-1, 14))

        # --- 4. Foliage: emit two perpendicular cross-quads instead of cube faces.
        flxs, fys, flzs = np.nonzero(foliage_mask)
        if flxs.size:
            fbids = blocks_view[flxs, fys, flzs]
            # Use the +X face UV; tall_grass/flowers/etc. have the same UV on all six faces.
            fuvs = UV_TABLE[fbids, FACE_PX]
            fu0 = fuvs[:, 0]; fv0 = fuvs[:, 1]
            fu1 = fuvs[:, 2]; fv1 = fuvs[:, 3]

            fN = flxs.shape[0]
            fwx = flxs.astype("f4") + ox
            fwz = flzs.astype("f4") + oz
            fyf = fys.astype("f4")

            ftint = tint_lut[fbids]
            ftr = ftint[:, 0]; ftg = ftint[:, 1]; ftb = ftint[:, 2]
            fface_light = _LIGHT_LUT[padded_light[flxs + 1, fys + 1, flzs + 1]]
            # Foliage uses flat lighting; AO disabled so plants look bright.
            fao = np.full(fN, 1.00, dtype="f4")
            fn_col = np.broadcast_to(np.array([0.0, 1.0, 0.0], dtype="f4"), (fN, 3))
            fanim = _ANIM_LUT[fbids]

            def _foliage_vert(cx, cy, cz, uu, vv):
                return np.column_stack((
                    fwx + cx, fyf + cy, fwz + cz,   # position 3
                    fn_col,                          # normal 3
                    uu, vv,                          # uv 2
                    fao,                             # ao 1
                    fface_light,                     # light 1
                    ftr, ftg, ftb,                   # tint 3
                    fanim,                           # anim 1
                )).astype("f4")

            def _emit_cross_quad(corners):
                # corners[0,1] = bottom pair (y=0), corners[2,3] = top pair (y=1).
                # v0 < v1 in atlas; OpenGL V increases upward → bottom uses v0, top uses v1.
                v0 = _foliage_vert(corners[0][0], corners[0][1], corners[0][2], fu0, fv0)
                v1 = _foliage_vert(corners[1][0], corners[1][1], corners[1][2], fu1, fv0)
                v2 = _foliage_vert(corners[2][0], corners[2][1], corners[2][2], fu1, fv1)
                v3 = _foliage_vert(corners[3][0], corners[3][1], corners[3][2], fu0, fv1)
                # Double-sided: front (v0,v1,v2,v0,v2,v3) + back (v0,v2,v1,v0,v3,v2)
                front = np.stack((v0, v1, v2, v0, v2, v3), axis=1)
                back  = np.stack((v0, v2, v1, v0, v3, v2), axis=1)
                return np.concatenate((front, back), axis=1).reshape(-1, 14)

            # Quad 1: SW(0.15,0,0.15) -> NE(0.85,*,0.85) diagonal.
            q1 = _emit_cross_quad([
                (0.15, 0.0, 0.15),
                (0.85, 0.0, 0.85),
                (0.85, 1.0, 0.85),
                (0.15, 1.0, 0.15),
            ])
            # Quad 2: NW(0.15,0,0.85) -> SE(0.85,*,0.15) diagonal.
            q2 = _emit_cross_quad([
                (0.15, 0.0, 0.85),
                (0.85, 0.0, 0.15),
                (0.85, 1.0, 0.15),
                (0.15, 1.0, 0.85),
            ])
            cutout_buckets.append(q1)
            cutout_buckets.append(q2)

        def concat(buckets):
            if not buckets:
                return np.zeros((0,), dtype="f4")
            return np.concatenate(buckets, axis=0).astype("f4").ravel()

        self.dirty = False
        return ChunkMeshData(
            opaque=concat(opaque_buckets),
            cutout=concat(cutout_buckets),
            translucent=concat(trans_buckets),
        )
