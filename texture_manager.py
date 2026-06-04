from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List, Tuple

import pygame

from .chunk import (
    BLOCK_ANDESITE,
    BLOCK_BEDROCK,
    BLOCK_BOOKSHELF,
    BLOCK_BRICKS,
    BLOCK_CHEST,
    BLOCK_CLAY,
    BLOCK_COAL_BLOCK,
    BLOCK_COAL_ORE,
    BLOCK_COBBLESTONE,
    BLOCK_COPPER_BLOCK,
    BLOCK_COPPER_ORE,
    BLOCK_CRAFTING_TABLE,
    BLOCK_DEEPSLATE,
    BLOCK_DEEPSLATE_COAL,
    BLOCK_DEEPSLATE_COPPER,
    BLOCK_DEEPSLATE_DIAMOND,
    BLOCK_DEEPSLATE_GOLD,
    BLOCK_DEEPSLATE_IRON,
    BLOCK_DEEPSLATE_REDSTONE,
    BLOCK_DIAMOND_BLOCK,
    BLOCK_DIAMOND_ORE,
    BLOCK_DIORITE,
    BLOCK_DIRT,
    BLOCK_FLOWER_RED,
    BLOCK_FLOWER_YELLOW,
    BLOCK_FURNACE,
    BLOCK_GLASS,
    BLOCK_GOLD_BLOCK,
    BLOCK_GOLD_ORE,
    BLOCK_GRANITE,
    BLOCK_GRASS,
    BLOCK_GRAVEL,
    BLOCK_IRON_BLOCK,
    BLOCK_IRON_ORE,
    BLOCK_LAVA,
    BLOCK_LEAVES,
    BLOCK_LOG,
    BLOCK_MUSHROOM_BROWN,
    BLOCK_MUSHROOM_RED,
    BLOCK_PLANKS,
    BLOCK_REDSTONE_BLOCK,
    BLOCK_REDSTONE_ORE,
    BLOCK_SAND,
    BLOCK_SANDSTONE,
    BLOCK_SNOW,
    BLOCK_STICK,
    BLOCK_STONE,
    BLOCK_STONE_BRICKS,
    BLOCK_SUGAR_CANE,
    BLOCK_TALL_GRASS,
    BLOCK_TNT,
    BLOCK_WATER,
    FACE_NX,
    FACE_NY,
    FACE_NZ,
    FACE_PX,
    FACE_PY,
    FACE_PZ,
)


@dataclass(slots=True)
class AtlasData:
    size: int
    rgba_bytes: bytes
    uv_by_name: Dict[str, Tuple[float, float, float, float]]
    ui_icons: Dict[str, pygame.Surface]


class TextureManager:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir

    def textures_dir(self) -> str:
        return os.path.join(self.base_dir, "textures")

    _TILE = 64  # target tile size; all textures are scaled to this on load

    def _load_surface(self, file_name: str) -> pygame.Surface:
        pack_path = os.path.join(self.textures_dir(), "pack", file_name)
        if os.path.isfile(pack_path):
            surf = pygame.image.load(pack_path).convert_alpha()
            w, h = surf.get_size()
            if h > w:
                # Animated strip — take the first frame
                cropped = pygame.Surface((w, w), flags=pygame.SRCALPHA, depth=32)
                cropped.blit(surf, (0, 0), (0, 0, w, w))
                surf = cropped
        else:
            path = os.path.join(self.textures_dir(), file_name)
            if not os.path.isfile(path):
                raise FileNotFoundError(path)
            surf = pygame.image.load(path).convert_alpha()
        w, h = surf.get_size()
        if w != self._TILE or h != self._TILE:
            surf = pygame.transform.scale(surf, (self._TILE, self._TILE))
        return surf

    def build_atlas(self, names: List[str]) -> AtlasData:
        tex = {}
        for n in names:
            tex[n] = self._load_surface(n + ".png")

        tile = self._TILE
        PAD = 1                      # 1-pixel border prevents mipmap bleeding
        padded = tile + 2 * PAD      # 18px per cell
        count = len(names)
        grid = 1
        while grid * grid < count:
            grid += 1
        size = grid * padded

        atlas = pygame.Surface((size, size), flags=pygame.SRCALPHA, depth=32)
        uv_by_name: Dict[str, Tuple[float, float, float, float]] = {}
        ui_icons: Dict[str, pygame.Surface] = {}

        for i, n in enumerate(names):
            row = i // grid
            col = i % grid
            x = col * padded + PAD
            y = row * padded + PAD
            atlas.blit(tex[n], (x, y))

            src = tex[n]
            atlas.blit(src, (x - PAD, y), (0, 0, PAD, tile))
            atlas.blit(src, (x + tile, y), (tile - PAD, 0, PAD, tile))
            atlas.blit(src, (x, y - PAD), (0, 0, tile, PAD))
            atlas.blit(src, (x, y + tile), (0, tile - PAD, tile, PAD))
            atlas.blit(src, (x - PAD, y - PAD), (0, 0, PAD, PAD))
            atlas.blit(src, (x + tile, y - PAD), (tile - PAD, 0, PAD, PAD))
            atlas.blit(src, (x - PAD, y + tile), (0, tile - PAD, PAD, PAD))
            atlas.blit(src, (x + tile, y + tile), (tile - PAD, tile - PAD, PAD, PAD))

            u0 = x / size
            u1 = (x + tile) / size
            v0_img = y / size
            v1_img = (y + tile) / size
            v0 = 1.0 - v1_img
            v1 = 1.0 - v0_img
            uv_by_name[n] = (u0, v0, u1, v1)

            ui_icons[n] = tex[n]

        rgba_bytes = pygame.image.tobytes(atlas, "RGBA", True)
        return AtlasData(size=size, rgba_bytes=rgba_bytes, uv_by_name=uv_by_name, ui_icons=ui_icons)

    def uv_by_block_face(self, uv_by_name: Dict[str, Tuple[float, float, float, float]]):
        grass_top = uv_by_name["grass_top"]
        grass_side = uv_by_name["grass_side"]
        dirt = uv_by_name["dirt"]
        stone = uv_by_name["stone"]
        sand = uv_by_name["sand"]
        log_top = uv_by_name["wood_log_top"]
        log_side = uv_by_name["wood_log_side"]
        leaves = uv_by_name["leaves"]
        water = uv_by_name["water"]
        bedrock = uv_by_name["bedrock"]
        snow = uv_by_name["snow"]
        glass = uv_by_name["glass"]
        
        coal_ore_uv = uv_by_name["coal_ore"]
        iron_ore_uv = uv_by_name["iron_ore"]
        gold_ore_uv = uv_by_name["gold_ore"]
        diamond_ore_uv = uv_by_name["diamond_ore"]
        redstone_ore_uv = uv_by_name["redstone_ore"]
        copper_ore_uv = uv_by_name["copper_ore"]
        lava_uv = uv_by_name["lava"]
        tall_grass_uv = uv_by_name["tall_grass"]
        flower_red_uv = uv_by_name["flower_red"]
        flower_yellow_uv = uv_by_name["flower_yellow"]
        granite_uv = uv_by_name["granite"]
        andesite_uv = uv_by_name["andesite"]
        diorite_uv = uv_by_name["diorite"]
        clay_uv = uv_by_name["clay"]
        mushroom_red_uv = uv_by_name["mushroom_red"]
        mushroom_brown_uv = uv_by_name["mushroom_brown"]
        sugar_cane_uv = uv_by_name["sugar_cane"]

        planks = uv_by_name["planks"]
        cobble = uv_by_name["cobblestone"]
        gravel = uv_by_name["gravel"]

        m = {}

        for face in (FACE_PX, FACE_NX, FACE_PZ, FACE_NZ):
            m[(BLOCK_GRASS, face)] = grass_side
        m[(BLOCK_GRASS, FACE_PY)] = grass_top
        m[(BLOCK_GRASS, FACE_NY)] = dirt

        for face in (FACE_PX, FACE_NX, FACE_PY, FACE_NY, FACE_PZ, FACE_NZ):
            m[(BLOCK_DIRT, face)] = dirt

        for face in (FACE_PX, FACE_NX, FACE_PY, FACE_NY, FACE_PZ, FACE_NZ):
            m[(BLOCK_STONE, face)] = stone

        for face in (FACE_PX, FACE_NX, FACE_PY, FACE_NY, FACE_PZ, FACE_NZ):
            m[(BLOCK_SAND, face)] = sand

        for face in (FACE_PX, FACE_NX, FACE_PZ, FACE_NZ):
            m[(BLOCK_LOG, face)] = log_side
        m[(BLOCK_LOG, FACE_PY)] = log_top
        m[(BLOCK_LOG, FACE_NY)] = log_top

        for face in (FACE_PX, FACE_NX, FACE_PY, FACE_NY, FACE_PZ, FACE_NZ):
            m[(BLOCK_LEAVES, face)] = leaves

        for face in (FACE_PX, FACE_NX, FACE_PY, FACE_NY, FACE_PZ, FACE_NZ):
            m[(BLOCK_WATER, face)] = water

        for face in (FACE_PX, FACE_NX, FACE_PY, FACE_NY, FACE_PZ, FACE_NZ):
            m[(BLOCK_GLASS, face)] = glass

        for face in (FACE_PX, FACE_NX, FACE_PY, FACE_NY, FACE_PZ, FACE_NZ):
            m[(BLOCK_BEDROCK, face)] = bedrock

        for face in (FACE_PX, FACE_NX, FACE_PY, FACE_NY, FACE_PZ, FACE_NZ):
            m[(BLOCK_SNOW, face)] = snow

        for face in (FACE_PX, FACE_NX, FACE_PY, FACE_NY, FACE_PZ, FACE_NZ):
            m[(BLOCK_PLANKS, face)] = planks

        for face in (FACE_PX, FACE_NX, FACE_PY, FACE_NY, FACE_PZ, FACE_NZ):
            m[(BLOCK_STICK, face)] = planks

        crafting_front = uv_by_name.get("crafting_front", planks)
        crafting_top = uv_by_name.get("crafting_top", planks)
        for face in (FACE_PX, FACE_NX, FACE_PZ, FACE_NZ):
            m[(BLOCK_CRAFTING_TABLE, face)] = crafting_front
        m[(BLOCK_CRAFTING_TABLE, FACE_PY)] = crafting_top
        m[(BLOCK_CRAFTING_TABLE, FACE_NY)] = planks

        for face in (FACE_PX, FACE_NX, FACE_PY, FACE_NY, FACE_PZ, FACE_NZ):
            m[(BLOCK_COBBLESTONE, face)] = cobble

        for face in (FACE_PX, FACE_NX, FACE_PY, FACE_NY, FACE_PZ, FACE_NZ):
            m[(BLOCK_GRAVEL, face)] = gravel

        for face in (FACE_PX, FACE_NX, FACE_PY, FACE_NY, FACE_PZ, FACE_NZ):
            m[(BLOCK_LAVA, face)] = lava_uv

        for face in (FACE_PX, FACE_NX, FACE_PY, FACE_NY, FACE_PZ, FACE_NZ):
            m[(BLOCK_COAL_ORE, face)] = coal_ore_uv
            m[(BLOCK_IRON_ORE, face)] = iron_ore_uv
            m[(BLOCK_GOLD_ORE, face)] = gold_ore_uv
            m[(BLOCK_DIAMOND_ORE, face)] = diamond_ore_uv
            m[(BLOCK_REDSTONE_ORE, face)] = redstone_ore_uv
            m[(BLOCK_COPPER_ORE, face)] = copper_ore_uv

        for face in (FACE_PX, FACE_NX, FACE_PY, FACE_NY, FACE_PZ, FACE_NZ):
            m[(BLOCK_TALL_GRASS, face)] = tall_grass_uv
            m[(BLOCK_FLOWER_RED, face)] = flower_red_uv
            m[(BLOCK_FLOWER_YELLOW, face)] = flower_yellow_uv

        furnace_front = uv_by_name.get("furnace_front", cobble)
        furnace_top = uv_by_name.get("furnace_top", cobble)
        furnace_side = uv_by_name.get("furnace_side", cobble)
        # Default sides
        for face in (FACE_PX, FACE_NX, FACE_PZ, FACE_NZ):
            m[(BLOCK_FURNACE, face)] = furnace_side
        m[(BLOCK_FURNACE, FACE_PY)] = furnace_top
        m[(BLOCK_FURNACE, FACE_NY)] = furnace_top
        # Front face on +Z (faces south by default)
        m[(BLOCK_FURNACE, FACE_PZ)] = furnace_front

        chest_front = uv_by_name.get("chest_front", planks)
        chest_top = uv_by_name.get("chest_top", planks)
        chest_side = uv_by_name.get("chest_side", planks)
        for face in (FACE_PX, FACE_NX, FACE_PZ, FACE_NZ):
            m[(BLOCK_CHEST, face)] = chest_side
        m[(BLOCK_CHEST, FACE_PY)] = chest_top
        m[(BLOCK_CHEST, FACE_NY)] = chest_top
        m[(BLOCK_CHEST, FACE_PZ)] = chest_front

        for face in (FACE_PX, FACE_NX, FACE_PY, FACE_NY, FACE_PZ, FACE_NZ):
            m[(BLOCK_GRANITE, face)] = granite_uv
            m[(BLOCK_ANDESITE, face)] = andesite_uv
            m[(BLOCK_DIORITE, face)] = diorite_uv
            m[(BLOCK_CLAY, face)] = clay_uv
            m[(BLOCK_MUSHROOM_RED, face)] = mushroom_red_uv
            m[(BLOCK_MUSHROOM_BROWN, face)] = mushroom_brown_uv
            m[(BLOCK_SUGAR_CANE, face)] = sugar_cane_uv

        # Phase 10: new blocks
        coal_block_uv = uv_by_name.get("coal_block", stone)
        iron_block_uv = uv_by_name.get("iron_block", stone)
        gold_block_uv = uv_by_name.get("gold_block", stone)
        diamond_block_uv = uv_by_name.get("diamond_block", stone)
        redstone_block_uv = uv_by_name.get("redstone_block", stone)
        copper_block_uv = uv_by_name.get("copper_block", stone)
        sandstone_uv = uv_by_name.get("sandstone", sand)
        stone_bricks_uv = uv_by_name.get("stone_bricks", stone)
        bricks_uv = uv_by_name.get("bricks", stone)
        bookshelf_side_uv = uv_by_name.get("bookshelf_side", planks)
        tnt_side_uv = uv_by_name.get("tnt_side", stone)
        tnt_top_uv = uv_by_name.get("tnt_top", stone)

        for face in (FACE_PX, FACE_NX, FACE_PY, FACE_NY, FACE_PZ, FACE_NZ):
            m[(BLOCK_COAL_BLOCK, face)] = coal_block_uv
            m[(BLOCK_IRON_BLOCK, face)] = iron_block_uv
            m[(BLOCK_GOLD_BLOCK, face)] = gold_block_uv
            m[(BLOCK_DIAMOND_BLOCK, face)] = diamond_block_uv
            m[(BLOCK_REDSTONE_BLOCK, face)] = redstone_block_uv
            m[(BLOCK_COPPER_BLOCK, face)] = copper_block_uv
            m[(BLOCK_SANDSTONE, face)] = sandstone_uv
            m[(BLOCK_STONE_BRICKS, face)] = stone_bricks_uv
            m[(BLOCK_BRICKS, face)] = bricks_uv

        # Bookshelf: planks top/bottom, book pattern sides
        for face in (FACE_PX, FACE_NX, FACE_PZ, FACE_NZ):
            m[(BLOCK_BOOKSHELF, face)] = bookshelf_side_uv
        m[(BLOCK_BOOKSHELF, FACE_PY)] = planks
        m[(BLOCK_BOOKSHELF, FACE_NY)] = planks

        # TNT: sand bottom, tnt_top top, tnt_side sides
        for face in (FACE_PX, FACE_NX, FACE_PZ, FACE_NZ):
            m[(BLOCK_TNT, face)] = tnt_side_uv
        m[(BLOCK_TNT, FACE_PY)] = tnt_top_uv
        m[(BLOCK_TNT, FACE_NY)] = sand

        # Deepslate variants
        deepslate_uv = uv_by_name.get("deepslate", stone)
        deepslate_coal_uv = uv_by_name.get("deepslate_coal_ore", coal_ore_uv)
        deepslate_iron_uv = uv_by_name.get("deepslate_iron_ore", iron_ore_uv)
        deepslate_gold_uv = uv_by_name.get("deepslate_gold_ore", gold_ore_uv)
        deepslate_redstone_uv = uv_by_name.get("deepslate_redstone_ore", redstone_ore_uv)
        deepslate_diamond_uv = uv_by_name.get("deepslate_diamond_ore", diamond_ore_uv)
        deepslate_copper_uv = uv_by_name.get("deepslate_copper_ore", copper_ore_uv)
        for face in (FACE_PX, FACE_NX, FACE_PY, FACE_NY, FACE_PZ, FACE_NZ):
            m[(BLOCK_DEEPSLATE, face)] = deepslate_uv
            m[(BLOCK_DEEPSLATE_COAL, face)] = deepslate_coal_uv
            m[(BLOCK_DEEPSLATE_IRON, face)] = deepslate_iron_uv
            m[(BLOCK_DEEPSLATE_GOLD, face)] = deepslate_gold_uv
            m[(BLOCK_DEEPSLATE_REDSTONE, face)] = deepslate_redstone_uv
            m[(BLOCK_DEEPSLATE_DIAMOND, face)] = deepslate_diamond_uv
            m[(BLOCK_DEEPSLATE_COPPER, face)] = deepslate_copper_uv

        # Wool: plain wool texture all faces
        from .chunk import BLOCK_WOOL, BLOCK_BED
        wool_uv = uv_by_name.get("wool", planks)
        for face in (FACE_PX, FACE_NX, FACE_PY, FACE_NY, FACE_PZ, FACE_NZ):
            m[(BLOCK_WOOL, face)] = wool_uv

        # Bed: reuse wool tex on top/sides, planks on bottom (simple placeholder).
        for face in (FACE_PX, FACE_NX, FACE_PZ, FACE_NZ):
            m[(BLOCK_BED, face)] = wool_uv
        m[(BLOCK_BED, FACE_PY)] = wool_uv
        m[(BLOCK_BED, FACE_NY)] = planks

        return m