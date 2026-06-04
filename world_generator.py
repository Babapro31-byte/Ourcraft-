from __future__ import annotations

import random
from typing import Tuple

import numpy as np
from noise import pnoise2, pnoise3

from .chunk import (
    BLOCK_AIR,
    BLOCK_ANDESITE,
    BLOCK_BEDROCK,
    BLOCK_CLAY,
    BLOCK_COAL_ORE,
    BLOCK_COBBLESTONE,
    BLOCK_COPPER_ORE,
    BLOCK_DEEPSLATE,
    BLOCK_DEEPSLATE_COAL,
    BLOCK_DEEPSLATE_COPPER,
    BLOCK_DEEPSLATE_DIAMOND,
    BLOCK_DEEPSLATE_GOLD,
    BLOCK_DEEPSLATE_IRON,
    BLOCK_DEEPSLATE_REDSTONE,
    BLOCK_DIAMOND_ORE,
    BLOCK_DIORITE,
    BLOCK_DIRT,
    BLOCK_FLOWER_RED,
    BLOCK_FLOWER_YELLOW,
    BLOCK_GLASS,
    BLOCK_GOLD_ORE,
    BLOCK_GRANITE,
    BLOCK_GRASS,
    BLOCK_GRAVEL,
    BLOCK_IRON_ORE,
    BLOCK_LAVA,
    BLOCK_LEAVES,
    BLOCK_LOG,
    BLOCK_MUSHROOM_BROWN,
    BLOCK_MUSHROOM_RED,
    BLOCK_PLANKS,
    BLOCK_REDSTONE_ORE,
    BLOCK_SAND,
    BLOCK_SNOW,
    BLOCK_STONE,
    BLOCK_SUGAR_CANE,
    BLOCK_TALL_GRASS,
    BLOCK_WATER,
    Chunk,
)

# Map regular ore -> deepslate variant.
_DEEPSLATE_ORE_MAP = {
    BLOCK_COAL_ORE:     BLOCK_DEEPSLATE_COAL,
    BLOCK_IRON_ORE:     BLOCK_DEEPSLATE_IRON,
    BLOCK_GOLD_ORE:     BLOCK_DEEPSLATE_GOLD,
    BLOCK_REDSTONE_ORE: BLOCK_DEEPSLATE_REDSTONE,
    BLOCK_DIAMOND_ORE:  BLOCK_DEEPSLATE_DIAMOND,
    BLOCK_COPPER_ORE:   BLOCK_DEEPSLATE_COPPER,
}

# ---------------------------------------------------------------------------
# Biome constants — now distinct integers (old code aliased all to 0).
# ---------------------------------------------------------------------------
BIOME_PLAINS      = 0
BIOME_FOREST      = 1
BIOME_DESERT      = 2
BIOME_SNOW_PLAINS = 3
BIOME_TAIGA       = 4
BIOME_BEACH       = 5
BIOME_OCEAN       = 6
BIOME_SWAMP       = 7
BIOME_JUNGLE      = 8
BIOME_SAVANNA     = 9
BIOME_MOUNTAIN    = 10
BIOME_FOOTHILLS   = 11
# Legacy aliases kept so external imports don't crash.
BIOME_SNOW        = BIOME_SNOW_PLAINS
BIOME_RIVER       = BIOME_SWAMP

# ---------------------------------------------------------------------------
# Biome parameter table.
# Keys: base_height, height_variation, surface, subsurface,
#       tree_density, tree_type ('oak'|'spruce'|'birch'|'none'),
#       veg_density, sand_layers
# ---------------------------------------------------------------------------
_BP = {
    BIOME_PLAINS: dict(
        base_height=68, height_variation=8,
        surface=BLOCK_GRASS, subsurface=BLOCK_DIRT,
        tree_density=0.003, tree_type='oak',
        veg_density=0.18, sand_layers=0,
    ),
    BIOME_FOREST: dict(
        base_height=72, height_variation=12,
        surface=BLOCK_GRASS, subsurface=BLOCK_DIRT,
        tree_density=0.06, tree_type='oak',
        veg_density=0.12, sand_layers=0,
    ),
    BIOME_DESERT: dict(
        base_height=66, height_variation=6,
        surface=BLOCK_SAND, subsurface=BLOCK_SAND,
        tree_density=0.0, tree_type='none',
        veg_density=0.0, sand_layers=4,
    ),
    BIOME_SNOW_PLAINS: dict(
        base_height=68, height_variation=8,
        surface=BLOCK_SNOW, subsurface=BLOCK_DIRT,
        tree_density=0.002, tree_type='spruce',
        veg_density=0.0, sand_layers=0,
    ),
    BIOME_TAIGA: dict(
        base_height=70, height_variation=14,
        surface=BLOCK_GRASS, subsurface=BLOCK_DIRT,
        tree_density=0.055, tree_type='spruce',
        veg_density=0.05, sand_layers=0,
    ),
    BIOME_BEACH: dict(
        base_height=63, height_variation=2,
        surface=BLOCK_SAND, subsurface=BLOCK_SAND,
        tree_density=0.0, tree_type='none',
        veg_density=0.0, sand_layers=2,
    ),
    BIOME_OCEAN: dict(
        base_height=42, height_variation=10,
        surface=BLOCK_SAND, subsurface=BLOCK_GRAVEL,
        tree_density=0.0, tree_type='none',
        veg_density=0.0, sand_layers=0,
    ),
    BIOME_SWAMP: dict(
        base_height=62, height_variation=4,
        surface=BLOCK_GRASS, subsurface=BLOCK_DIRT,
        tree_density=0.015, tree_type='oak',
        veg_density=0.08, sand_layers=0,
    ),
    BIOME_JUNGLE: dict(
        base_height=74, height_variation=10,
        surface=BLOCK_GRASS, subsurface=BLOCK_DIRT,
        tree_density=0.12, tree_type='oak_tall',
        veg_density=0.30, sand_layers=0,
    ),
    BIOME_SAVANNA: dict(
        base_height=70, height_variation=5,
        surface=BLOCK_GRASS, subsurface=BLOCK_DIRT,
        tree_density=0.008, tree_type='oak',
        veg_density=0.04, sand_layers=0,
    ),
    BIOME_MOUNTAIN: dict(
        base_height=82, height_variation=22,
        surface=BLOCK_STONE, subsurface=BLOCK_STONE,
        tree_density=0.01, tree_type='spruce',
        veg_density=0.0, sand_layers=0,
    ),
    BIOME_FOOTHILLS: dict(
        base_height=76, height_variation=14,
        surface=BLOCK_GRASS, subsurface=BLOCK_DIRT,
        tree_density=0.04, tree_type='spruce',
        veg_density=0.03, sand_layers=0,
    ),
}

# ---------------------------------------------------------------------------
# Ore specs: (ore_id, peak_y, spread, veins_per_chunk, sz_min, sz_max)
# peak_y and spread use positive y only (no negative y in this engine).
# ---------------------------------------------------------------------------
_ORE_SPECS = [
    # Ore Y-distributions remapped onto this engine's compressed column (bedrock
    # ~y0, sea ~y64, deepslate <y8) to mirror Minecraft 1.18 shapes.
    (BLOCK_COAL_ORE,     72, 40, 20, 4, 13),  # MC: most common, abundant from surface down
    (BLOCK_COPPER_ORE,   48, 30, 16, 6, 14),  # MC 1.18: triangle peak ~48, large veins
    (BLOCK_IRON_ORE,     16, 24, 18, 4,  8),  # MC: main low-band triangle peak ~16
    (BLOCK_IRON_ORE,    100, 30,  4, 3,  6),  # MC 1.18 second batch: sparse iron up in mountains
    (BLOCK_GOLD_ORE,     26, 18,  3, 3,  6),  # MC: deep triangle, below the iron band
    (BLOCK_DIAMOND_ORE,   8,  8,  1, 2,  4),  # MC: near bedrock, increasing downward
    (BLOCK_REDSTONE_ORE, 14, 14,  5, 4,  8),  # MC: bottom-weighted, common deep
    (BLOCK_GRANITE,      60, 40,  3, 18, 28),
    (BLOCK_ANDESITE,     60, 40,  3, 18, 28),
    (BLOCK_DIORITE,      60, 40,  3, 18, 28),
]


def _clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


class WorldGenerator:
    def __init__(self, seed: int, sea_level: int = 64):
        self.seed = int(seed)
        self.sea_level = sea_level
        # Village placement is delegated to a separate builder for clarity.
        from .village import VillageBuilder
        self._village_builder = VillageBuilder(self.seed)
        self.world = None  # back-ref wired in generate_chunk

    # ------------------------------------------------------------------
    # Climate sampling — single source of truth.
    # Returns (temperature, humidity, continentalness), each in ~[-1, 1].
    # ------------------------------------------------------------------

    def _sample_climate(self, wx: float, wz: float) -> Tuple[float, float, float]:
        s = self.seed
        # Domain warp for continentalness (same as old terrain_height).
        _wx = pnoise2((wx + s * 7.1) * 0.005, (wz + s * 7.3) * 0.005,
                      octaves=2, persistence=0.5, lacunarity=2.0) * 30.0
        _wz = pnoise2((wx + s * 8.7) * 0.005, (wz + s * 8.9) * 0.005,
                      octaves=2, persistence=0.5, lacunarity=2.0) * 30.0
        sx = wx + _wx
        sz = wz + _wz
        cont = pnoise2((sx + s * 1.1) * 0.0025, (sz + s * 1.3) * 0.0025,
                       octaves=2, persistence=0.5, lacunarity=2.0)
        temp = pnoise2((wx + s * 11.1) * 0.0028, (wz + s * 11.3) * 0.0028,
                       octaves=3, persistence=0.5, lacunarity=2.0)
        humid = pnoise2((wx + s * 13.7) * 0.0032, (wz + s * 13.9) * 0.0032,
                        octaves=3, persistence=0.5, lacunarity=2.0)
        return temp, humid, cont

    # ------------------------------------------------------------------
    # Biome classification — pure function, no noise calls.
    # ------------------------------------------------------------------

    @staticmethod
    def _classify_biome(temp: float, humid: float, cont: float) -> int:
        if cont < -0.35:
            return BIOME_OCEAN
        if cont < -0.15:
            return BIOME_BEACH
        if cont > 0.40:
            return BIOME_MOUNTAIN
        if cont > 0.20:
            return BIOME_FOOTHILLS
        if temp < -0.3:
            return BIOME_SNOW_PLAINS if humid < 0.0 else BIOME_TAIGA
        # Warm biomes: jungle (warm + humid), savanna (warm + dry), desert (very dry),
        # swamp (very humid).
        if temp > 0.35:
            if humid > 0.4:
                return BIOME_JUNGLE
            if humid < -0.1:
                return BIOME_SAVANNA
        if temp > 0.2:
            return BIOME_DESERT if humid < 0.0 else BIOME_SWAMP
        return BIOME_FOREST if humid >= 0.1 else BIOME_PLAINS

    # ------------------------------------------------------------------
    # Public API: get_biome — now returns meaningful 0-7.
    # ------------------------------------------------------------------

    def get_biome(self, x: int, z: int) -> int:
        temp, humid, cont = self._sample_climate(x, z)
        return self._classify_biome(temp, humid, cont)

    # ------------------------------------------------------------------
    # Terrain height — biome-parameterised.
    # ------------------------------------------------------------------

    def _terrain_height_biome(self, wx: float, wz: float, bp: dict, cont: float) -> int:
        s = self.seed
        # Domain warp to get warped coords (reuse warp from _sample_climate
        # without re-computing — but this is called independently too).
        _wx = pnoise2((wx + s * 7.1) * 0.005, (wz + s * 7.3) * 0.005,
                      octaves=2, persistence=0.5, lacunarity=2.0) * 30.0
        _wz = pnoise2((wx + s * 8.7) * 0.005, (wz + s * 8.9) * 0.005,
                      octaves=2, persistence=0.5, lacunarity=2.0) * 30.0
        sx = wx + _wx
        sz = wz + _wz
        ero = pnoise2((sx + s * 2.1) * 0.003, (sz + s * 2.3) * 0.003,
                      octaves=2, persistence=0.5, lacunarity=2.0)
        n = 0.0
        amp = bp['height_variation'] * 0.7
        freq = 0.008
        for i in range(5):
            n += pnoise2((sx + s * (3 + i)) * freq, (sz + s * (4 + i)) * freq,
                         octaves=1, persistence=0.5, lacunarity=2.0) * amp
            amp *= 0.5
            freq *= 2.0
        base = bp['base_height'] + cont * bp['height_variation'] * 1.8
        detail = n * (1.0 - 0.75 * max(0.0, ero))
        h = base + detail
        return int(_clamp(round(h), 1, 200))

    def _terrain_height_fast(self, wx: float, wz: float, bp: dict, cont: float,
                              sx: float, sz: float,
                              blended_base: float = None,
                              blended_variation: float = None) -> int:
        """Like _terrain_height_biome but accepts pre-warped coords (sx, sz).
        blended_base and blended_variation are bilinearly-blended corner-biome values
        that smooth biome boundaries (kill coliseum rims)."""
        s = self.seed
        ero = pnoise2((sx + s * 2.1) * 0.003, (sz + s * 2.3) * 0.003,
                      octaves=1, persistence=0.5, lacunarity=2.0)
        n = 0.0
        hv = blended_variation if blended_variation is not None else bp['height_variation']
        amp = hv * 0.7
        freq = 0.008
        for i in range(5):
            n += pnoise2((sx + s * (3 + i)) * freq, (sz + s * (4 + i)) * freq,
                         octaves=1, persistence=0.5, lacunarity=2.0) * amp
            amp *= 0.5
            freq *= 2.0
        if blended_base is not None:
            base = blended_base
        else:
            base = bp['base_height'] + cont * hv * 1.8
        detail = n * (1.0 - 0.75 * max(0.0, ero))
        h = base + detail
        return int(_clamp(round(h), 1, 200))

    # ------------------------------------------------------------------
    # Public API: terrain_height — biome-aware, same int return range.
    # ------------------------------------------------------------------

    def terrain_height(self, x: int, z: int) -> int:
        temp, humid, cont = self._sample_climate(x, z)
        biome = self._classify_biome(temp, humid, cont)
        return self._terrain_height_biome(x, z, _BP[biome], cont)

    # ------------------------------------------------------------------
    # Biome blending — sample 4 chunk corners, bilinear interpolation.
    # Returns three (16,16) float32 arrays: temps, humids, conts.
    # ------------------------------------------------------------------

    def _biome_blended_params(self, cx: int, cz: int):
        ox = cx * 16
        oz = cz * 16
        corners = [
            self._sample_climate(ox,      oz),
            self._sample_climate(ox + 15, oz),
            self._sample_climate(ox,      oz + 15),
            self._sample_climate(ox + 15, oz + 15),
        ]
        # corners[i] = (temp, humid, cont) at (NW, NE, SW, SE)
        t00, h00, c00 = corners[0]
        t10, h10, c10 = corners[1]
        t01, h01, c01 = corners[2]
        t11, h11, c11 = corners[3]

        tx = np.linspace(0.0, 1.0, 16, dtype=np.float32)  # x weight
        tz = np.linspace(0.0, 1.0, 16, dtype=np.float32)  # z weight
        wx_g, wz_g = np.meshgrid(tx, tz, indexing='ij')   # (16,16)

        def _lerp(v00, v10, v01, v11):
            return (v00 * (1 - wx_g) * (1 - wz_g)
                    + v10 * wx_g       * (1 - wz_g)
                    + v01 * (1 - wx_g) * wz_g
                    + v11 * wx_g       * wz_g).astype(np.float32)

        temps = _lerp(t00, t10, t01, t11)
        humids = _lerp(h00, h10, h01, h11)
        conts = _lerp(c00, c10, c01, c11)

        # Per-corner biome reference heights and height_variation: bilinearly blended
        # so biome boundaries don't cause sudden cliffs or coliseum rims.
        def _ref_height(t, h, c):
            bp = _BP[self._classify_biome(t, h, c)]
            return bp['base_height'] + c * bp['height_variation'] * 1.8
        def _ref_variation(t, h, c):
            return _BP[self._classify_biome(t, h, c)]['height_variation']
        bh00 = _ref_height(t00, h00, c00)
        bh10 = _ref_height(t10, h10, c10)
        bh01 = _ref_height(t01, h01, c01)
        bh11 = _ref_height(t11, h11, c11)
        base_heights = _lerp(bh00, bh10, bh01, bh11)
        vh00 = _ref_variation(t00, h00, c00)
        vh10 = _ref_variation(t10, h10, c10)
        vh01 = _ref_variation(t01, h01, c01)
        vh11 = _ref_variation(t11, h11, c11)
        height_variations = _lerp(vh00, vh10, vh01, vh11)
        return temps, humids, conts, base_heights, height_variations

    # ------------------------------------------------------------------
    # 3D density column — returns (256,) bool array where True = solid.
    # Only calls pnoise3 in the ~±48-block transition zone around h2d.
    # ------------------------------------------------------------------

    def _build_density_column(self, wx: int, wz: int,
                               h2d: int, cont: float) -> np.ndarray:
        s = self.seed
        y_arr = np.arange(256, dtype=np.float32)

        # 2D height bias: positive below h2d (solid), negative above (air).
        base_bias = (h2d - y_arr) / 32.0 + cont * 0.5

        # Vertical squeeze to enforce hard floor/ceiling.
        squeeze = np.zeros(256, dtype=np.float32)
        squeeze[181:] = (y_arr[181:] - 180.0) / 24.0
        squeeze[1:8] = (8.0 - y_arr[1:8]) / 8.0

        # Default solid = sign of 2D bias (no noise needed outside uncertain zone).
        solid = (base_bias - squeeze) > 0.0
        solid[0] = True  # bedrock always solid

        # Find the uncertain zone where 3D noise could flip the sign.
        # d3 max amplitude = 0.5, so only rows with |bias| < 0.5 can flip.
        y_lo = max(1, h2d - 17)
        y_hi = min(254, h2d + 17)

        STEP = 12  # sample every 12 y-levels — fewer pnoise3 calls
        xf = (wx + s * 20.1) * 0.018
        yf_base = s * 20.3 * 0.018
        zf = (wz + s * 20.7) * 0.018

        # Coarse samples at STEP-spaced y values in the uncertain window.
        sample_ys = list(range(y_lo, y_hi + 1, STEP))
        if not sample_ys or sample_ys[-1] < y_hi:
            sample_ys.append(y_hi)

        d3v = [pnoise3(xf, y * 0.018 + yf_base, zf,
                       octaves=1, persistence=0.5, lacunarity=2.0) * 0.5
               for y in sample_ys]

        # Linear interpolation between knots (tight inner loop).
        d3_full = np.empty(256, dtype=np.float32)
        for i in range(len(sample_ys) - 1):
            ya, yb = sample_ys[i], sample_ys[i + 1]
            da, db = d3v[i], d3v[i + 1]
            inv_n = 1.0 / (yb - ya)
            for j in range(yb - ya + 1):
                d3_full[ya + j] = da + j * (db - da) * inv_n

        # Apply the 3D detail in the uncertain window.
        solid[y_lo:y_hi + 1] = (base_bias[y_lo:y_hi + 1]
                                 + d3_full[y_lo:y_hi + 1]
                                 - squeeze[y_lo:y_hi + 1]) > 0.0
        solid[0] = True
        return solid

    # ------------------------------------------------------------------
    # Caves — blob carving + worm-tube double-noise (unchanged)
    # ------------------------------------------------------------------

    def cave_carve(self, x: int, y: int, z: int) -> bool:
        if y < 5 or y > 96:
            return False
        n = pnoise3(
            (x + self.seed * 1.2) * 0.030,
            (y + self.seed * 1.4) * 0.030,
            (z + self.seed * 1.6) * 0.030,
            octaves=1, persistence=0.55, lacunarity=2.0,
        )
        n2 = pnoise3(
            (x + self.seed * 1.8) * 0.060,
            (y + self.seed * 2.1) * 0.060,
            (z + self.seed * 2.4) * 0.060,
            octaves=1, persistence=0.5, lacunarity=2.0,
        )
        v = 0.65 * n + 0.35 * n2
        return v < -0.36

    def cave_worm(self, x: int, y: int, z: int) -> bool:
        if y < 5 or y > 60:
            return False
        na = pnoise3(
            (x + self.seed * 2.3) * 0.012,
            (y + self.seed * 1.1) * 0.012,
            (z + self.seed * 1.7) * 0.012,
            octaves=1, persistence=0.5, lacunarity=2.0,
        )
        nb = pnoise3(
            (x + self.seed * 3.1) * 0.012,
            (y + self.seed * 2.9) * 0.012,
            (z + self.seed * 0.8) * 0.012,
            octaves=1, persistence=0.5, lacunarity=2.0,
        )
        return (na * na + nb * nb) < 0.018

    # ------------------------------------------------------------------
    # Aquifer — fill underground air pockets below y=40 with water.
    # Runs after lava pools so lava takes priority.
    # ------------------------------------------------------------------

    def _fill_aquifer(self, c: Chunk, lx: int, lz: int,
                      wx: int, wz: int) -> None:
        s = self.seed
        # Single 2D noise sample per column — "is this column in a wet aquifer zone?"
        # Avoids 40 pnoise3 calls per column while still producing patchy underground water.
        aq = pnoise2((wx + s * 30.1) * 0.035, (wz + s * 30.7) * 0.035,
                     octaves=2, persistence=0.5, lacunarity=2.0)
        if aq <= 0.25:
            return
        for y in range(1, 40):
            if c.blocks[lx, y, lz] == BLOCK_AIR:
                c.blocks[lx, y, lz] = BLOCK_WATER

    # ------------------------------------------------------------------
    # Surface rules — applied after 3D density fill.
    # ------------------------------------------------------------------

    def _apply_surface_rules(self, c: Chunk, lx: int, lz: int,
                              top_y: int, bp: dict, biome_id: int,
                              heights_2d: np.ndarray) -> None:
        if top_y <= 0:
            return

        # Steep-slope detection (in-chunk neighbors only).
        height_delta = 0
        for ddx, ddz in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nlx, nlz = lx + ddx, lz + ddz
            if 0 <= nlx < 16 and 0 <= nlz < 16:
                height_delta = max(height_delta,
                                   abs(int(top_y) - int(heights_2d[nlx, nlz])))
        if height_delta >= 4:
            # Exposed cliff — leave as STONE (already STONE from density fill).
            return

        # High-altitude snow cap on mountain peaks.
        if top_y > 130:
            c.blocks[lx, top_y, lz] = BLOCK_SNOW
            for dy in range(1, 3):
                y2 = top_y - dy
                if y2 > 0 and c.blocks[lx, y2, lz] == BLOCK_STONE:
                    c.blocks[lx, y2, lz] = BLOCK_STONE
            return

        # High-altitude stone (mountain peaks).
        if top_y > 115:
            # c.blocks[lx, top_y, lz] is already BLOCK_STONE.
            return

        # Ocean floor.
        if biome_id == BIOME_OCEAN:
            c.blocks[lx, top_y, lz] = BLOCK_SAND
            for dy in range(1, 3):
                y2 = top_y - dy
                if y2 > 0:
                    c.blocks[lx, y2, lz] = BLOCK_GRAVEL
            return

        # Beach.
        if biome_id == BIOME_BEACH:
            c.blocks[lx, top_y, lz] = BLOCK_SAND
            for dy in range(1, 3):
                y2 = top_y - dy
                if y2 > 0:
                    c.blocks[lx, y2, lz] = BLOCK_SAND
            return

        # Desert — thick sand layers.
        if bp['sand_layers'] > 0:
            c.blocks[lx, top_y, lz] = BLOCK_SAND
            for dy in range(1, bp['sand_layers'] + 1):
                y2 = top_y - dy
                if y2 > 0:
                    c.blocks[lx, y2, lz] = BLOCK_SAND
            return

        # Snow biome.
        if bp['surface'] == BLOCK_SNOW:
            c.blocks[lx, top_y, lz] = BLOCK_SNOW
            for dy in range(1, 4):
                y2 = top_y - dy
                if y2 > 0:
                    c.blocks[lx, y2, lz] = BLOCK_DIRT
            return

        # Swamp at/below sea level — waterlogged feel, use dirt not grass.
        if biome_id == BIOME_SWAMP and top_y <= self.sea_level:
            c.blocks[lx, top_y, lz] = BLOCK_DIRT
            for dy in range(1, 4):
                y2 = top_y - dy
                if y2 > 0:
                    c.blocks[lx, y2, lz] = BLOCK_DIRT
            return

        # Shore beach: any grass-surface land sitting right at the waterline turns
        # to sand, the way Minecraft forms beaches wherever land meets ocean. This
        # softens the hard grass→water edge across every biome (steep coastal cliffs
        # already returned as STONE above, so they stay rocky like MC).
        sl = self.sea_level
        if bp['surface'] == BLOCK_GRASS and sl - 1 <= top_y <= sl + 2:
            c.blocks[lx, top_y, lz] = BLOCK_SAND
            for dy in range(1, 3):
                y2 = top_y - dy
                if y2 > 0:
                    c.blocks[lx, y2, lz] = BLOCK_SAND
            return

        # Standard biome surface.
        c.blocks[lx, top_y, lz] = bp['surface']
        for dy in range(1, 4):
            y2 = top_y - dy
            if y2 > 0:
                c.blocks[lx, y2, lz] = bp['subsurface']

    # ------------------------------------------------------------------
    # Ore placement — triangular distribution centred on peak_y.
    # ------------------------------------------------------------------

    def _place_ore_vein_triangular(self, c: Chunk, rng: random.Random,
                                    ore_id: int, peak_y: int, spread: int,
                                    size: int) -> None:
        lo = max(5, peak_y - spread)
        hi = min(250, peak_y + spread)
        # Average of two uniforms gives triangular PDF peaked at midpoint.
        oy = int((rng.uniform(lo, hi) + rng.uniform(lo, hi)) / 2.0)
        ox_ = rng.randint(0, 15)
        oz_ = rng.randint(0, 15)
        deepslate_variant = _DEEPSLATE_ORE_MAP.get(ore_id)
        for _ in range(size):
            dx = rng.randint(-2, 2)
            dy = rng.randint(-1, 1)
            dz = rng.randint(-2, 2)
            lx2, y2, lz2 = ox_ + dx, oy + dy, oz_ + dz
            if 0 <= lx2 < 16 and 0 <= y2 < 256 and 0 <= lz2 < 16:
                cur = c.blocks[lx2, y2, lz2]
                if cur == BLOCK_STONE:
                    c.blocks[lx2, y2, lz2] = ore_id
                elif cur == BLOCK_DEEPSLATE and deepslate_variant is not None:
                    c.blocks[lx2, y2, lz2] = deepslate_variant

    # ------------------------------------------------------------------
    # Ravine carver — long vertical fissures, ~2% of chunks.
    # ------------------------------------------------------------------

    def _carve_ravine(self, c: Chunk, cx: int, cz: int) -> None:
        rh = (cx * 7919) ^ (cz * 6571) ^ self.seed
        rh = (rh ^ (rh >> 13)) & 0xFFFFFFFF
        if (rh % 100) >= 2:
            return
        r = random.Random(rh)
        # Ravine starts at random position within chunk
        sx = r.randint(2, 13)
        sz = r.randint(2, 13)
        # Direction in radians
        heading = r.uniform(0.0, 2.0 * 3.14159)
        segments = r.randint(12, 20)
        seg_len = r.uniform(2.0, 3.5)
        top_y = r.randint(60, 75)
        bottom_y = r.randint(18, 25)

        import math as _m
        px = float(sx)
        pz = float(sz)
        for seg in range(segments):
            heading += r.uniform(-0.3, 0.3)
            dx = _m.cos(heading) * seg_len
            dz = _m.sin(heading) * seg_len
            px += dx
            pz += dz
            # Cross-section: oval, narrower at top, wider at bottom
            for y in range(bottom_y, top_y + 1):
                # Width tapers: narrow at top
                t = (y - bottom_y) / max(1, top_y - bottom_y)
                width = 2.0 + (1.0 - t) * 3.5  # 5.5 at bottom -> 2.0 at top
                depth = 1.5 + (1.0 - t) * 1.5  # in z slightly thinner
                # Carve oval centered at (px, y, pz)
                x0 = int(max(0, _m.floor(px - width)))
                x1 = int(min(15, _m.ceil(px + width)))
                z0 = int(max(0, _m.floor(pz - depth)))
                z1 = int(min(15, _m.ceil(pz + depth)))
                for lx in range(x0, x1 + 1):
                    for lz in range(z0, z1 + 1):
                        ddx = (lx - px) / width
                        ddz = (lz - pz) / depth
                        if ddx * ddx + ddz * ddz <= 1.0:
                            cur = c.blocks[lx, y, lz]
                            # Carve through stone/dirt/grass/gravel/sand/snow but skip deepslate/bedrock/ore
                            if cur in (BLOCK_STONE, BLOCK_DIRT, BLOCK_GRASS,
                                       BLOCK_GRAVEL, BLOCK_SAND, BLOCK_SNOW):
                                c.blocks[lx, y, lz] = BLOCK_AIR
            # Optional lava pool at bottom
            if bottom_y < 15 and r.random() < 0.3:
                lavax = int(_m.floor(px))
                lavaz = int(_m.floor(pz))
                if 0 <= lavax < 16 and 0 <= lavaz < 16:
                    if c.blocks[lavax, bottom_y, lavaz] == BLOCK_AIR:
                        c.blocks[lavax, bottom_y, lavaz] = BLOCK_LAVA

    # Legacy method kept for API compat.
    def _place_ore_vein(self, c: Chunk, rng: random.Random,
                        ore_id: int, ox: int, oy: int, oz: int, size: int) -> None:
        for _ in range(size):
            dx = rng.randint(-2, 2)
            dy = rng.randint(-1, 1)
            dz = rng.randint(-2, 2)
            lx, y, lz = ox + dx, oy + dy, oz + dz
            if 0 <= lx < 16 and 0 <= y < 256 and 0 <= lz < 16:
                if c.blocks[lx, y, lz] == BLOCK_STONE:
                    c.blocks[lx, y, lz] = ore_id

    # ------------------------------------------------------------------
    # Tree generation helpers (unchanged)
    # ------------------------------------------------------------------

    def _place_tree_oak(self, c: Chunk, lx: int, h: int, lz: int,
                        trunk_h: int, r: random.Random) -> None:
        for i in range(trunk_h):
            y = h + 1 + i
            if y >= 256:
                break
            c.set_block(lx, y, lz, BLOCK_LOG)
        top_y = min(h + trunk_h, 255)
        for dy in range(-2, 3):
            y = top_y + dy
            if y < 0 or y >= 256:
                continue
            rad = 2 if dy <= 0 else 1
            for dx in range(-rad, rad + 1):
                for dz in range(-rad, rad + 1):
                    if abs(dx) + abs(dz) > rad + 1:
                        continue
                    if c.get_local(lx + dx, y, lz + dz) == BLOCK_AIR:
                        c.set_block(lx + dx, y, lz + dz, BLOCK_LEAVES)

    def _place_tree_oak_tall(self, c: Chunk, lx: int, h: int, lz: int,
                              trunk_h: int, r: random.Random) -> None:
        """Tall jungle-style oak — longer trunk, wider 3-tier leaf cap."""
        for i in range(trunk_h):
            y = h + 1 + i
            if y >= 256:
                break
            c.set_block(lx, y, lz, BLOCK_LOG)
        top_y = min(h + trunk_h, 255)
        # Wider canopy: top tier r=2, middle r=3, lower r=2
        tiers = (
            (1,  2),  # top
            (0,  3),  # middle
            (-1, 3),  # widest layer
            (-2, 2),
        )
        for dy, rad in tiers:
            y = top_y + dy
            if y < 0 or y >= 256:
                continue
            for dx in range(-rad, rad + 1):
                for dz in range(-rad, rad + 1):
                    if dx * dx + dz * dz > rad * rad + 1:
                        continue
                    if c.get_local(lx + dx, y, lz + dz) == BLOCK_AIR:
                        c.set_block(lx + dx, y, lz + dz, BLOCK_LEAVES)

    def _place_tree_spruce(self, c: Chunk, lx: int, h: int, lz: int,
                           trunk_h: int, r: random.Random) -> None:
        for i in range(trunk_h):
            y = h + 1 + i
            if y >= 256:
                break
            c.set_block(lx, y, lz, BLOCK_LOG)
        top_y = min(h + trunk_h, 255)
        for dy in range(-trunk_h + 1, 2):
            y = top_y + dy
            if y < 0 or y >= 256:
                continue
            rad = max(0, 2 - (dy + trunk_h - 1) // 2)
            for dx in range(-rad, rad + 1):
                for dz in range(-rad, rad + 1):
                    if abs(dx) + abs(dz) > rad + 1:
                        continue
                    if c.get_local(lx + dx, y, lz + dz) == BLOCK_AIR:
                        c.set_block(lx + dx, y, lz + dz, BLOCK_LEAVES)

    def _place_tree_birch(self, c: Chunk, lx: int, h: int, lz: int,
                          trunk_h: int, r: random.Random) -> None:
        for i in range(trunk_h):
            y = h + 1 + i
            if y >= 256:
                break
            c.set_block(lx, y, lz, BLOCK_LOG)
        top_y = min(h + trunk_h, 255)
        for dy in range(-1, 3):
            y = top_y + dy
            if y < 0 or y >= 256:
                continue
            rad = 1 if dy >= 1 else 2
            for dx in range(-rad, rad + 1):
                for dz in range(-rad, rad + 1):
                    if abs(dx) + abs(dz) > rad:
                        continue
                    if c.get_local(lx + dx, y, lz + dz) == BLOCK_AIR:
                        c.set_block(lx + dx, y, lz + dz, BLOCK_LEAVES)

    # ------------------------------------------------------------------
    # Feature placement — biome-aware, per column.
    # ------------------------------------------------------------------

    def _place_features(self, c: Chunk, lx: int, lz: int,
                        top_y: int, bp: dict, biome_id: int,
                        wx: int, wz: int, s: int) -> None:
        # Trees.
        if (bp['tree_type'] != 'none'
                and top_y >= self.sea_level + 2
                and top_y <= 130
                and c.blocks[lx, top_y, lz] in (BLOCK_GRASS, BLOCK_DIRT, BLOCK_SNOW)):
            hb = (wx * 374761393) ^ (wz * 668265263) ^ s
            hb = ((hb ^ (hb >> 13)) * 1274126177) & 0xFFFFFFFF

            density = bp['tree_density']
            # Forest biome gets noise-modulated density like old code.
            if biome_id == BIOME_FOREST:
                forest_n = pnoise2((wx + s * 6.1) * 0.012,
                                   (wz + s * 6.3) * 0.012,
                                   octaves=2, persistence=0.5)
                density = 0.004 + max(0.0, forest_n + 0.15) * 0.060

            if (hb / 0xFFFFFFFF) < density:
                r = random.Random(hb)
                tt = bp['tree_type']
                if tt == 'spruce':
                    trunk_h = 6 + r.randrange(4)
                    self._place_tree_spruce(c, lx, top_y, lz, trunk_h, r)
                elif tt == 'oak_tall':
                    trunk_h = 8 + r.randrange(5)  # 8..12 — jungle
                    self._place_tree_oak_tall(c, lx, top_y, lz, trunk_h, r)
                elif tt == 'birch' or (tt == 'oak' and r.random() < 0.3
                                       and biome_id == BIOME_PLAINS):
                    trunk_h = 5 + r.randrange(3)
                    self._place_tree_birch(c, lx, top_y, lz, trunk_h, r)
                else:
                    trunk_h = 4 + r.randrange(3)
                    self._place_tree_oak(c, lx, top_y, lz, trunk_h, r)

        # Tall grass and flowers (biome veg_density).
        if (bp['veg_density'] > 0.0
                and top_y + 1 < 256
                and c.blocks[lx, top_y, lz] == BLOCK_GRASS
                and c.blocks[lx, top_y + 1, lz] == BLOCK_AIR):
            hb2 = (wx * 2246822519) ^ (wz * 3266489917) ^ s
            hb2 = ((hb2 ^ (hb2 >> 13)) * 1274126177) & 0xFFFFFFFF
            fv = hb2 / 0xFFFFFFFF
            if fv < bp['veg_density']:
                if fv < bp['veg_density'] * 0.88:
                    c.blocks[lx, top_y + 1, lz] = BLOCK_TALL_GRASS
                else:
                    c.blocks[lx, top_y + 1, lz] = (
                        BLOCK_FLOWER_RED if ((hb2 >> 17) & 1) else BLOCK_FLOWER_YELLOW
                    )

        # Sugar cane — water-adjacent, biome-agnostic.
        if top_y + 1 < 256:
            surface = int(c.blocks[lx, top_y, lz])
            if (surface in (BLOCK_GRASS, BLOCK_SAND, BLOCK_DIRT)
                    and c.blocks[lx, top_y + 1, lz] == BLOCK_AIR):
                adj_water = False
                for ddx, ddz in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nlx, nlz = lx + ddx, lz + ddz
                    if 0 <= nlx < 16 and 0 <= nlz < 16:
                        if c.blocks[nlx, top_y, nlz] == BLOCK_WATER:
                            adj_water = True
                            break
                if adj_water:
                    hb3 = (wx * 1597334677) ^ (wz * 2246822519) ^ (s * 3266489917)
                    hb3 = (hb3 ^ (hb3 >> 13)) & 0xFFFFFFFF
                    if (hb3 / 0xFFFFFFFF) < 0.55:
                        stalks = 2 + ((hb3 >> 16) & 0x3)
                        for sy in range(stalks):
                            yy = top_y + 1 + sy
                            if 0 <= yy < 256 and c.blocks[lx, yy, lz] == BLOCK_AIR:
                                c.blocks[lx, yy, lz] = BLOCK_SUGAR_CANE

        # Clay near water — sand at beach/sea level.
        if (c.blocks[lx, top_y, lz] == BLOCK_SAND
                and self.sea_level - 3 <= top_y <= self.sea_level + 1):
            adj_water = False
            for ddx, ddz in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nlx, nlz = lx + ddx, lz + ddz
                if 0 <= nlx < 16 and 0 <= nlz < 16:
                    if (c.blocks[nlx, top_y + 1, nlz] == BLOCK_WATER
                            or c.blocks[nlx, top_y, nlz] == BLOCK_WATER):
                        adj_water = True
                        break
            if adj_water:
                hb4 = (wx * 2654435761) ^ (wz * 1597334677) ^ s
                hb4 = (hb4 ^ (hb4 >> 13)) & 0xFFFFFFFF
                if (hb4 / 0xFFFFFFFF) < 0.30:
                    c.blocks[lx, top_y, lz] = BLOCK_CLAY

    # ------------------------------------------------------------------
    # Chunk generation
    # ------------------------------------------------------------------

    def generate_chunk(self, cx: int, cz: int, world) -> Chunk:
        import time
        t0 = time.perf_counter()

        c = Chunk(cx, cz, world=world)
        ox = cx * 16
        oz = cz * 16
        rng = random.Random(self.seed ^ (cx * 341873128712) ^ (cz * 132897987541))
        s = self.seed

        # --- Steps 1+2: Climate/biome grid and 2D height in one pass ---
        temps_grid, humids_grid, cont_grid, base_heights_grid, height_variations_grid = self._biome_blended_params(cx, cz)
        biome_grid = np.zeros((16, 16), dtype=np.int8)

        # Biome classification: pure Python, no noise calls.
        for lx in range(16):
            for lz in range(16):
                biome_grid[lx, lz] = self._classify_biome(
                    float(temps_grid[lx, lz]),
                    float(humids_grid[lx, lz]),
                    float(cont_grid[lx, lz]),
                )

        # Vectorised warp + terrain height.
        # All noise functions are sampled on a coarse 5×5 grid and bilinearly
        # interpolated to 16×16.  Cuts ~2 000 pnoise2 calls to ~200 with no
        # visible quality loss (warp/terrain frequencies are low vs. 16-block chunk).
        _CRS = [0, 4, 8, 12, 15]   # five sample indices spanning [0, 15]
        _FINE = np.arange(16, dtype=np.float64)

        def _c2f(c5):
            """Bilinear interp: (5,5) coarse → (16,16) fine numpy array."""
            mid = np.vstack([np.interp(_FINE, _CRS, c5[i]) for i in range(5)])
            return np.vstack([np.interp(_FINE, _CRS, mid[:, j]) for j in range(16)]).T

        # Warp noise (freq 0.005): 2 × 25 = 50 calls.
        _wx2_c = np.empty((5, 5), dtype=np.float32)
        _wz2_c = np.empty((5, 5), dtype=np.float32)
        for _ci, _lx in enumerate(_CRS):
            for _cj, _lz in enumerate(_CRS):
                _wcx = ox + _lx; _wcz = oz + _lz
                _wx2_c[_ci, _cj] = pnoise2(
                    (_wcx + s * 7.1) * 0.005, (_wcz + s * 7.3) * 0.005,
                    octaves=1, persistence=0.5, lacunarity=2.0) * 30.0
                _wz2_c[_ci, _cj] = pnoise2(
                    (_wcx + s * 8.7) * 0.005, (_wcz + s * 8.9) * 0.005,
                    octaves=1, persistence=0.5, lacunarity=2.0) * 30.0

        sx_grid = (ox + np.arange(16, dtype=np.float32)[:, np.newaxis]
                   + _c2f(_wx2_c).astype(np.float32))   # (16,16) warped x
        sz_grid = (oz + np.arange(16, dtype=np.float32)[np.newaxis, :]
                   + _c2f(_wz2_c).astype(np.float32))   # (16,16) warped z

        # Erosion noise (freq 0.003): 25 calls.
        _ero_c = np.empty((5, 5), dtype=np.float32)
        for _ci, _lx in enumerate(_CRS):
            for _cj, _lz in enumerate(_CRS):
                _ex = float(sx_grid[_lx, _lz]); _ez = float(sz_grid[_lx, _lz])
                _ero_c[_ci, _cj] = pnoise2(
                    (_ex + s * 2.1) * 0.003, (_ez + s * 2.3) * 0.003,
                    octaves=1, persistence=0.5, lacunarity=2.0)
        ero_grid = _c2f(_ero_c).astype(np.float32)   # (16,16)

        # Terrain octaves (freqs 0.008→0.128): 5 × 25 = 125 calls.
        hv_grid = height_variations_grid.astype(np.float32)
        amp_grid = hv_grid * 0.7   # per-column amplitude; halved each octave
        n_grid = np.zeros((16, 16), dtype=np.float32)
        _freq = 0.008
        for _oi in range(5):
            _oct_c = np.empty((5, 5), dtype=np.float32)
            for _ci, _lx in enumerate(_CRS):
                for _cj, _lz in enumerate(_CRS):
                    _ex = float(sx_grid[_lx, _lz]); _ez = float(sz_grid[_lx, _lz])
                    _oct_c[_ci, _cj] = pnoise2(
                        (_ex + s * (3 + _oi)) * _freq, (_ez + s * (4 + _oi)) * _freq,
                        octaves=1, persistence=0.5, lacunarity=2.0)
            n_grid += _c2f(_oct_c).astype(np.float32) * amp_grid
            amp_grid = amp_grid * 0.5
            _freq *= 2.0

        # Assemble heights (same formula as _terrain_height_fast with blended_base).
        # base_heights_grid already encodes base_height + cont * hv * 1.8.
        _detail = n_grid * (1.0 - 0.75 * np.maximum(0.0, ero_grid))
        _h_raw = base_heights_grid.astype(np.float32) + _detail
        heights_2d = np.clip(np.round(_h_raw), 1, 200).astype(np.int32)

        # --- Step 3: 3D density fill + bedrock ---
        top_y_grid = np.zeros((16, 16), dtype=np.int32)
        for lx in range(16):
            wx = ox + lx
            for lz in range(16):
                wz = oz + lz
                h2d = int(heights_2d[lx, lz])
                cont_val = float(cont_grid[lx, lz])
                solid = self._build_density_column(wx, wz, h2d, cont_val)
                c.blocks[lx, :, lz] = np.where(solid, BLOCK_STONE, BLOCK_AIR)

                # Bedrock layer.
                c.blocks[lx, 0, lz] = BLOCK_BEDROCK
                for y in range(1, 3):
                    if rng.random() < 0.15:
                        c.blocks[lx, y, lz] = BLOCK_BEDROCK

                # Cache top solid y for later steps.
                nz_ys = np.where(solid)[0]
                top_y_grid[lx, lz] = int(nz_ys[-1]) if len(nz_ys) > 0 else 0

        # --- Step 4: Cave carving — vectorised bulk evaluation ---
        # Sample cave blob noise on a coarse 4×4×4-block grid, trilinearly
        # interpolate to full 16×74×16, then carve where value < threshold.
        _CAVE_Y_MAX = 74   # covers y 0..73 (matches old max_y logic)
        _CAVE_Y_MIN = 5
        _STEP = 8
        # Coarse grid axes.
        cx_pts = [ox + _STEP // 2 + i * _STEP for i in range(2)]   # 2 x-points
        cz_pts = [oz + _STEP // 2 + i * _STEP for i in range(2)]   # 2 z-points
        cy_pts = list(range(0, _CAVE_Y_MAX + 1, _STEP))             # ~10 y-points

        def _cave_noise_coarse():
            # Returns (4, len(cy_pts), 4) array of blob cave noise values.
            arr = np.empty((4, len(cy_pts), 4), dtype=np.float32)
            for xi, wxc in enumerate(cx_pts):
                for yi, yc in enumerate(cy_pts):
                    for zi, wzc in enumerate(cz_pts):
                        n = pnoise3(
                            (wxc + s * 1.2) * 0.030,
                            (yc  + s * 1.4) * 0.030,
                            (wzc + s * 1.6) * 0.030,
                            octaves=1, persistence=0.55, lacunarity=2.0,
                        )
                        n2 = pnoise3(
                            (wxc + s * 1.8) * 0.060,
                            (yc  + s * 2.1) * 0.060,
                            (wzc + s * 2.4) * 0.060,
                            octaves=1, persistence=0.5, lacunarity=2.0,
                        )
                        arr[xi, yi, zi] = 0.65 * n + 0.35 * n2
            return arr

        def _worm_noise_coarse():
            # Returns two (4, len(cy_pts), 4) arrays for worm detection (y<=46).
            cy_worm = [y for y in cy_pts if y <= 46]
            ny = len(cy_worm)
            a = np.empty((4, ny, 4), dtype=np.float32)
            b = np.empty((4, ny, 4), dtype=np.float32)
            for xi, wxc in enumerate(cx_pts):
                for yi, yc in enumerate(cy_worm):
                    for zi, wzc in enumerate(cz_pts):
                        a[xi, yi, zi] = pnoise3(
                            (wxc + s * 2.3) * 0.012,
                            (yc  + s * 1.1) * 0.012,
                            (wzc + s * 1.7) * 0.012,
                            octaves=1, persistence=0.5, lacunarity=2.0,
                        )
                        b[xi, yi, zi] = pnoise3(
                            (wxc + s * 3.1) * 0.012,
                            (yc  + s * 2.9) * 0.012,
                            (wzc + s * 0.8) * 0.012,
                            octaves=1, persistence=0.5, lacunarity=2.0,
                        )
            return a, b, cy_worm

        cave_coarse = _cave_noise_coarse()

        def _trilinear_upsample(coarse, out_x, out_y, out_z):
            # coarse shape: (cx, cy, cz). Upsample to (out_x, out_y, out_z) via
            # linear interpolation along each axis using numpy.
            cx_n, cy_n, cz_n = coarse.shape
            # Interpolate x axis: (cx_n -> out_x)
            tx = np.linspace(0, cx_n - 1, out_x)
            xi = np.clip(tx.astype(int), 0, cx_n - 2)
            xf = (tx - xi).reshape(-1, 1, 1)
            tmp = coarse[xi] * (1 - xf) + coarse[xi + 1] * xf  # (out_x, cy_n, cz_n)
            # Interpolate y axis: (cy_n -> out_y)
            ty = np.linspace(0, cy_n - 1, out_y)
            yi = np.clip(ty.astype(int), 0, cy_n - 2)
            yf = (ty - yi).reshape(1, -1, 1)
            tmp = tmp[:, yi, :] * (1 - yf) + tmp[:, yi + 1, :] * yf  # (out_x, out_y, cz_n)
            # Interpolate z axis: (cz_n -> out_z)
            tz = np.linspace(0, cz_n - 1, out_z)
            zi = np.clip(tz.astype(int), 0, cz_n - 2)
            zf = (tz - zi).reshape(1, 1, -1)
            result = tmp[:, :, zi] * (1 - zf) + tmp[:, :, zi + 1] * zf
            return result.astype(np.float32)

        # Trilinearly interpolate to full 16×_CAVE_Y_MAX×16 volume.
        cave_vol = _trilinear_upsample(cave_coarse, 16, _CAVE_Y_MAX, 16)

        # Worm noise (lower frequency).
        wa, wb, cy_worm = _worm_noise_coarse()
        nyw = len(cy_worm)
        if nyw >= 2:
            worm_vol_a = _trilinear_upsample(wa, 16, 46, 16)
            worm_vol_b = _trilinear_upsample(wb, 16, 46, 16)
            worm_vol = np.clip(
                worm_vol_a.astype(np.float64) ** 2 + worm_vol_b.astype(np.float64) ** 2,
                0.0, np.finfo(np.float32).max
            ).astype(np.float32)
        else:
            worm_vol = np.ones((16, 46, 16), dtype=np.float32)

        # Carve: cave blob threshold < -0.36, worm threshold < 0.018.
        # Fully vectorised — no per-cell Python loop.
        cave_mask = cave_vol < -0.36   # (16, _CAVE_Y_MAX, 16) bool

        # Worm mask padded to same shape as cave_mask.
        worm_mask_full = np.zeros((_CAVE_Y_MAX, 16, 16), dtype=bool)
        worm_mask_full[:46] = (worm_vol < 0.018).transpose(1, 0, 2)  # (46,16,16)
        worm_mask_full = worm_mask_full.transpose(1, 0, 2)  # back to (16,74,16)

        carve_mask = cave_mask | worm_mask_full  # (16,74,16)

        # Solid surface buffer: no carving within 10 y of the column surface.
        cap = np.maximum(heights_2d - 10, 0).astype(np.int32)           # (16,16)
        y_idx = np.arange(_CAVE_Y_MAX, dtype=np.int32)[None, :, None]   # (1,74,1)
        carve_mask &= (y_idx < cap[:, None, :])

        # Restrict to STONE blocks in y 5..73.
        stone_slice = c.blocks[:, _CAVE_Y_MIN:_CAVE_Y_MAX, :] == BLOCK_STONE
        carve_slice = carve_mask[:, _CAVE_Y_MIN:_CAVE_Y_MAX, :] & stone_slice
        c.blocks[:, _CAVE_Y_MIN:_CAVE_Y_MAX, :][carve_slice] = BLOCK_AIR

        # Worm tube: also carve the block above each worm-carved cell.
        worm_only = worm_mask_full[:, _CAVE_Y_MIN:_CAVE_Y_MAX - 1, :] & stone_slice[:, :-1]
        # The "above" y = y+1 in the chunk: shift slice up by 1.
        above_stone = c.blocks[:, _CAVE_Y_MIN + 1:_CAVE_Y_MAX, :] == BLOCK_STONE
        c.blocks[:, _CAVE_Y_MIN + 1:_CAVE_Y_MAX, :][worm_only & above_stone] = BLOCK_AIR

        # Cave rooms.
        for lx in range(16):
            for lz in range(16):
                h = int(heights_2d[lx, lz])
                if h < 50:
                    continue
                if rng.random() < 0.03:
                    cy_center = rng.randint(10, 40)
                    rad = rng.randint(4, 5)  # capped at 5 to avoid worst-case O(n^3)
                    # Vectorised sphere carve.
                    x0 = max(0, lx - rad); x1 = min(16, lx + rad + 1)
                    y0 = max(0, cy_center - rad); y1 = min(256, cy_center + rad + 1)
                    z0 = max(0, lz - rad); z1 = min(16, lz + rad + 1)
                    xs = np.arange(x0, x1) - lx
                    ys = np.arange(y0, y1) - cy_center
                    zs = np.arange(z0, z1) - lz
                    xx, yy, zz = np.meshgrid(xs, ys, zs, indexing='ij')
                    in_sphere = (xx**2 + yy**2 + zz**2) <= rad * rad
                    stone_sub = c.blocks[x0:x1, y0:y1, z0:z1] == BLOCK_STONE
                    c.blocks[x0:x1, y0:y1, z0:z1][in_sphere & stone_sub] = BLOCK_AIR

        # --- Step 4b: Deepslate layer (Minecraft 1.18+) ---
        # y 0-3: full deepslate. y 4-7: noise-driven transition.
        # Only converts existing stone (preserves bedrock, ores, air, etc.)
        stone_layer = c.blocks[:, 0:8, :] == BLOCK_STONE
        # Bottom 4 rows: hard deepslate
        c.blocks[:, 0:4, :][stone_layer[:, 0:4, :]] = BLOCK_DEEPSLATE
        # Transition zone y 4..7: vectorised noise evaluation.
        # Build one 16×16 noise grid per y-level (4 total = 256 calls instead of
        # 1024) then apply as a mask.  Coordinates are the same regardless of y
        # (the noise is 2D), so we only need 256 evaluations total.
        _ds_xs = np.array([(ox + lx + s * 17.1) * 0.08 for lx in range(16)],
                          dtype=np.float64)
        _ds_zs = np.array([(oz + lz + s * 17.3) * 0.08 for lz in range(16)],
                          dtype=np.float64)
        _ds_noise = np.empty((16, 16), dtype=np.float32)
        for lx in range(16):
            for lz in range(16):
                _ds_noise[lx, lz] = pnoise2(_ds_xs[lx], _ds_zs[lz],
                                             octaves=1, persistence=0.5,
                                             lacunarity=2.0)
        for ty_off in range(4, 8):
            threshold = (ty_off - 4) / 4.0 - 0.5  # -0.5 .. 0.25
            is_stone = c.blocks[:, ty_off, :] == BLOCK_STONE   # (16,16)
            convert = is_stone & (_ds_noise > threshold)
            c.blocks[:, ty_off, :][convert] = BLOCK_DEEPSLATE

        # --- Step 4c: Ravine carving (~2% of chunks) ---
        self._carve_ravine(c, cx, cz)

        # --- Step 5: Lava pools (below y=10) — vectorised ---
        # Fill air that sits on a non-air block in y=1..9.
        lava_slice = c.blocks[:, 1:10, :]   # (16,9,16) view
        below_slice = c.blocks[:, 0:9, :]
        lava_mask = (lava_slice == BLOCK_AIR) & (below_slice != BLOCK_AIR)
        c.blocks[:, 1:10, :][lava_mask] = BLOCK_LAVA

        # --- Step 6: Aquifer fill (y 1-39, after lava) ---
        for lx in range(16):
            wx = ox + lx
            for lz in range(16):
                wz = oz + lz
                self._fill_aquifer(c, lx, lz, wx, wz)

        # --- Step 7: Surface rules ---
        # Recompute top_y vectorised: highest non-air block per (lx,lz).
        # c.blocks shape: (16,256,16). Find last nonzero y per column.
        non_air = (c.blocks > 0)  # (16,256,16)
        # Reverse along y, argmax finds first True = last non-air in original.
        top_y_grid = (255 - np.argmax(non_air[:, ::-1, :], axis=1)).astype(np.int32)
        # Columns that are all-air: argmax returns 0 → 255-0=255; clamp to 0.
        all_air_cols = ~non_air.any(axis=1)
        top_y_grid[all_air_cols] = 0

        for lx in range(16):
            for lz in range(16):
                top_y = int(top_y_grid[lx, lz])
                biome_id = int(biome_grid[lx, lz])
                bp = _BP[biome_id]
                self._apply_surface_rules(c, lx, lz, top_y, bp, biome_id, heights_2d)

        # --- Step 8: Sea water fill — vectorised ---
        sl = self.sea_level
        air_sea = c.blocks[:, 1:sl + 1, :] == BLOCK_AIR  # (16, sl, 16)
        # Only fill columns where top_y < sea_level.
        col_mask = top_y_grid < sl  # (16,16)
        col_mask_3d = col_mask[:, np.newaxis, :]  # (16,1,16) broadcasts
        c.blocks[:, 1:sl + 1, :][air_sea & col_mask_3d] = BLOCK_WATER

        # --- Step 9: Ore placement (triangular distribution) ---
        for ore_id, peak_y, spread, veins, sz_min, sz_max in _ORE_SPECS:
            for _ in range(veins):
                size = rng.randint(sz_min, sz_max)
                self._place_ore_vein_triangular(c, rng, ore_id, peak_y, spread, size)

        # --- Step 10: Features (trees, vegetation, clay, sugar cane) ---
        for lx in range(16):
            wx = ox + lx
            for lz in range(16):
                wz = oz + lz
                top_y = int(top_y_grid[lx, lz])
                biome_id = int(biome_grid[lx, lz])
                bp = _BP[biome_id]
                self._place_features(c, lx, lz, top_y, bp, biome_id, wx, wz, s)

        # Mushrooms in caves — world-coord hash, dim regions.
        for lx in range(16):
            wx = ox + lx
            for lz in range(16):
                wz = oz + lz
                for y in range(10, 50):
                    if c.blocks[lx, y, lz] != BLOCK_AIR:
                        continue
                    if y == 0:
                        continue
                    below = c.blocks[lx, y - 1, lz]
                    if below != BLOCK_STONE:
                        continue
                    hb = (wx * 374761393) ^ (y * 2246822519) ^ (wz * 668265263) ^ s
                    hb = (hb ^ (hb >> 13)) & 0xFFFFFFFF
                    if (hb / 0xFFFFFFFF) < 0.012:
                        c.blocks[lx, y, lz] = (
                            BLOCK_MUSHROOM_RED if ((hb >> 17) & 1) else BLOCK_MUSHROOM_BROWN
                        )

        # --- Step 11: Village placement (cross-chunk via pending_block_writes) ---
        self.world = world  # ensure VillageBuilder can reach world.pending_block_writes
        try:
            self._village_builder.maybe_place_village(self, c.blocks, cx, cz)
        except Exception as _e:
            print(f"  village placement skipped at ({cx},{cz}): {_e}")

        c.dirty = True
        t1 = time.perf_counter()
        if t1 - t0 > 0.010:
            print(f"  chunk ({cx},{cz}) generated in {(t1 - t0) * 1000:.1f}ms")
        return c
