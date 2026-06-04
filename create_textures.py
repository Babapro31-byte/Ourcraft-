"""Generate placeholder 16x16 PNG textures for new block types added in Section 2."""
from __future__ import annotations

import os
import struct
import zlib


def _png(pixels: list[tuple[int, int, int, int]]) -> bytes:
    """Build a minimal 16x16 RGBA PNG from a flat list of (R,G,B,A) tuples."""
    w, h = 16, 16
    raw = b""
    for row in range(h):
        raw += b"\x00"  # filter type None
        for col in range(w):
            r, g, b, a = pixels[row * w + col]
            raw += bytes([r, g, b, a])
    compressed = zlib.compress(raw)

    def chunk(tag: bytes, data: bytes) -> bytes:
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
    idat = chunk(b"IDAT", compressed)
    iend = chunk(b"IEND", b"")
    return sig + ihdr + idat + iend


def solid(r: int, g: int, b: int, a: int = 255) -> list[tuple[int, int, int, int]]:
    return [(r, g, b, a)] * 256


def stone_ore(dot_r: int, dot_g: int, dot_b: int) -> list[tuple[int, int, int, int]]:
    """Stone-gray background with scattered colored dots."""
    base = (120, 120, 120, 255)
    dot = (dot_r, dot_g, dot_b, 255)
    # Fixed dot positions (visually balanced for 16x16)
    dots = {2, 5, 9, 13, 19, 23, 30, 37, 43, 50, 57, 60, 67, 74, 80, 88,
            95, 100, 107, 114, 120, 127, 133, 140, 147, 153, 160, 167, 173,
            180, 187, 193, 200, 207, 213, 220, 227, 233, 240, 247, 252}
    return [dot if i in dots else base for i in range(256)]


def tall_grass_tex() -> list[tuple[int, int, int, int]]:
    """Grass blades on transparent background."""
    px = [(0, 0, 0, 0)] * 256
    green_shades = [(34, 139, 34, 255), (0, 128, 0, 255), (50, 160, 50, 255)]
    cols = [2, 5, 7, 10, 13]
    for col in cols:
        g = green_shades[col % 3]
        for row in range(5, 16):
            px[row * 16 + col] = g
        for row in range(2, 7):
            lean = col + (row % 2)
            if 0 <= lean < 16:
                px[row * 16 + lean] = g
    return px


def flower_tex(petal_r: int, petal_g: int, petal_b: int) -> list[tuple[int, int, int, int]]:
    """Simple cross-shaped flower on transparent background."""
    px = [(0, 0, 0, 0)] * 256
    stem = (34, 139, 34, 255)
    petal = (petal_r, petal_g, petal_b, 255)
    center = (255, 255, 0, 255)
    # Stem
    for row in range(8, 16):
        px[row * 16 + 8] = stem
    # Petals (cross pattern around center)
    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]:
        r, c = 6 + dr, 8 + dc
        if 0 <= r < 16 and 0 <= c < 16:
            px[r * 16 + c] = petal
    px[6 * 16 + 8] = center
    return px


def granite_tex() -> list[tuple[int, int, int, int]]:
    """Granite — pinkish-brown base with darker speckles."""
    base = (170, 110, 90, 255)
    dark = (130, 80, 60, 255)
    light = (190, 130, 110, 255)
    px = []
    for row in range(16):
        for col in range(16):
            v = (row * 7 + col * 11 + (row * col) % 5) % 17
            if v < 4:
                px.append(dark)
            elif v < 8:
                px.append(light)
            else:
                px.append(base)
    return px


def andesite_tex() -> list[tuple[int, int, int, int]]:
    """Andesite — neutral medium gray with subtle speckles."""
    base = (110, 110, 115, 255)
    dark = (80, 80, 85, 255)
    light = (135, 135, 140, 255)
    px = []
    for row in range(16):
        for col in range(16):
            v = (row * 13 + col * 7) % 19
            if v < 3:
                px.append(dark)
            elif v < 7:
                px.append(light)
            else:
                px.append(base)
    return px


def diorite_tex() -> list[tuple[int, int, int, int]]:
    """Diorite — light grayish-white with darker speckles."""
    base = (200, 200, 210, 255)
    dark = (140, 140, 150, 255)
    spot = (225, 225, 230, 255)
    px = []
    for row in range(16):
        for col in range(16):
            v = (row * 5 + col * 11 + (row + col) % 3) % 13
            if v < 3:
                px.append(dark)
            elif v < 6:
                px.append(spot)
            else:
                px.append(base)
    return px


def clay_tex() -> list[tuple[int, int, int, int]]:
    """Clay — smooth blue-gray."""
    base = (150, 155, 175, 255)
    light = (165, 170, 190, 255)
    dark = (135, 140, 160, 255)
    px = []
    for row in range(16):
        for col in range(16):
            v = (row + col * 2) % 4
            if v == 0:
                px.append(light)
            elif v == 2:
                px.append(dark)
            else:
                px.append(base)
    return px


def mushroom_red_tex() -> list[tuple[int, int, int, int]]:
    """Red mushroom — cap with white dots, stem below, transparent bg."""
    px = [(0, 0, 0, 0)] * 256
    cap = (180, 30, 30, 255)
    cap_dark = (130, 20, 20, 255)
    dot = (240, 240, 240, 255)
    stem = (220, 200, 170, 255)
    # Cap rows 4-8, cols 4-11
    for row in range(4, 9):
        for col in range(4, 12):
            px[row * 16 + col] = cap_dark if (row == 4 or col in (4, 11)) else cap
    # White spots
    for r, c in [(5, 6), (5, 10), (7, 5), (7, 8), (7, 11)]:
        if 0 <= r < 16 and 0 <= c < 16:
            px[r * 16 + c] = dot
    # Stem rows 9-13, cols 7-9
    for row in range(9, 14):
        for col in range(7, 10):
            px[row * 16 + col] = stem
    return px


def mushroom_brown_tex() -> list[tuple[int, int, int, int]]:
    """Brown mushroom — rounded cap on stem, transparent bg."""
    px = [(0, 0, 0, 0)] * 256
    cap = (130, 90, 60, 255)
    cap_dark = (95, 65, 40, 255)
    stem = (220, 200, 170, 255)
    for row in range(4, 9):
        for col in range(3, 13):
            d = (row - 6) ** 2 + (col - 8) ** 2
            if d <= 16:
                px[row * 16 + col] = cap_dark if d > 10 else cap
    for row in range(9, 14):
        for col in range(7, 10):
            px[row * 16 + col] = stem
    return px


def sugar_cane_tex() -> list[tuple[int, int, int, int]]:
    """Sugar cane — vertical green stalks on transparent bg."""
    px = [(0, 0, 0, 0)] * 256
    green = (110, 195, 100, 255)
    green_dark = (75, 150, 70, 255)
    green_light = (145, 215, 130, 255)
    for col in (5, 8, 11):
        for row in range(16):
            v = (row + col) % 5
            if v == 0:
                px[row * 16 + col] = green_light
            elif v == 2:
                px[row * 16 + col] = green_dark
            else:
                px[row * 16 + col] = green
    return px


def lava_tex() -> list[tuple[int, int, int, int]]:
    """Animated-look lava with orange/red variation."""
    px = []
    for row in range(16):
        for col in range(16):
            v = ((row * 17 + col * 13) % 40)
            r = min(255, 200 + v)
            g = max(0, 80 - v // 2)
            px.append((r, g, 0, 255))
    return px


# ---------------------------------------------------------------------------
# Block textures: per-face for furnace / chest / crafting table (Phase 7A)
# ---------------------------------------------------------------------------

def _stone_base(seed: int) -> list[tuple[int, int, int, int]]:
    """Cobblestone-ish gray with subtle variation."""
    px = []
    for row in range(16):
        for col in range(16):
            v = ((row * 31 + col * 17 + seed * 13) % 36) - 18
            shade = max(85, min(170, 125 + v))
            px.append((shade, shade, shade, 255))
    return px


def _wood_base(plank_dir: str = "h") -> list[tuple[int, int, int, int]]:
    """Plank-like wood texture with grain lines."""
    px = []
    base = (155, 110, 65)
    dark = (105, 70, 35)
    light = (180, 135, 85)
    for row in range(16):
        for col in range(16):
            if plank_dir == "h":
                # horizontal planks: dark line every 4 rows
                if row in (0, 4, 8, 12, 15):
                    c = dark
                elif (row + col) % 5 == 0:
                    c = light
                else:
                    c = base
            else:
                if col in (0, 4, 8, 12, 15):
                    c = dark
                elif (row + col) % 5 == 0:
                    c = light
                else:
                    c = base
            px.append((c[0], c[1], c[2], 255))
    return px


def furnace_front_tex() -> list[tuple[int, int, int, int]]:
    """Stone face + dark furnace mouth in lower-center."""
    px = _stone_base(7)
    # Black mouth: rows 7-12, cols 4-11
    for row in range(7, 13):
        for col in range(4, 12):
            if row in (7, 12) or col in (4, 11):
                px[row * 16 + col] = (35, 25, 20, 255)
            else:
                # Inner glow: orange ember
                ember = (180, 80, 25, 255) if (row + col) % 3 == 0 else (30, 20, 15, 255)
                px[row * 16 + col] = ember
    return px


def furnace_top_tex() -> list[tuple[int, int, int, int]]:
    """Plain coarse stone for top/bottom of the furnace."""
    px = _stone_base(11)
    # A subtle inset square to suggest "top opening"
    for row in range(3, 13):
        for col in range(3, 13):
            if row in (3, 12) or col in (3, 12):
                r, g, b, _ = px[row * 16 + col]
                px[row * 16 + col] = (max(60, r - 30), max(60, g - 30), max(60, b - 30), 255)
    return px


def furnace_side_tex() -> list[tuple[int, int, int, int]]:
    """Plain stone for the four sides."""
    return _stone_base(19)


def chest_front_tex() -> list[tuple[int, int, int, int]]:
    """Wooden chest front with metal lock."""
    px = _wood_base("h")
    # Lock: small dark square in middle
    for row in range(6, 10):
        for col in range(7, 10):
            if 6 <= row <= 9 and 7 <= col <= 9:
                if row in (6, 9) or col in (7, 9):
                    px[row * 16 + col] = (50, 40, 25, 255)
                else:
                    px[row * 16 + col] = (215, 175, 50, 255)  # gold latch
    # Hinges: dark vertical bars at top
    for col in (1, 14):
        for row in range(0, 4):
            px[row * 16 + col] = (60, 45, 30, 255)
    return px


def chest_side_tex() -> list[tuple[int, int, int, int]]:
    """Plain wood side."""
    return _wood_base("h")


def chest_top_tex() -> list[tuple[int, int, int, int]]:
    """Wood with a dark center seam for the lid."""
    px = _wood_base("h")
    # Seam line in middle row
    for col in range(16):
        px[7 * 16 + col] = (75, 55, 30, 255)
        px[8 * 16 + col] = (75, 55, 30, 255)
    return px


def crafting_front_tex() -> list[tuple[int, int, int, int]]:
    """Wood with a 3x3 grid overlay."""
    px = _wood_base("h")
    # 3x3 grid: dark lines at cols 5,10 and rows 5,10
    grid_color = (70, 50, 30, 255)
    for r in range(16):
        for c in (4, 5, 10, 11):
            px[r * 16 + c] = grid_color
    for c in range(16):
        for r in (4, 5, 10, 11):
            px[r * 16 + c] = grid_color
    # Border
    for i in range(16):
        px[0 * 16 + i] = (60, 40, 25, 255)
        px[15 * 16 + i] = (60, 40, 25, 255)
        px[i * 16 + 0] = (60, 40, 25, 255)
        px[i * 16 + 15] = (60, 40, 25, 255)
    return px


def crafting_top_tex() -> list[tuple[int, int, int, int]]:
    """Wood top with a heavier 3x3 grid pattern."""
    px = _wood_base("h")
    grid_color = (40, 25, 15, 255)
    for r in range(16):
        for c in (5, 10):
            px[r * 16 + c] = grid_color
    for c in range(16):
        for r in (5, 10):
            px[r * 16 + c] = grid_color
    return px


# ---------------------------------------------------------------------------
# Item textures (Phase 7B)
# ---------------------------------------------------------------------------

def _make_tool(handle_color: tuple, head_color: tuple, shape: str) -> list[tuple[int, int, int, int]]:
    """Generic tool sprite: diagonal handle bottom-left → top-right, head at top-right.

    shape: 'pickaxe' | 'axe' | 'shovel' | 'sword' | 'hoe'
    """
    transparent = (0, 0, 0, 0)
    px = [transparent] * 256

    # Handle: diagonal line from (13,2) to (2,13) — top-right to bottom-left
    handle = handle_color + (255,) if len(handle_color) == 3 else handle_color
    handle_dark = (max(0, handle[0] - 30), max(0, handle[1] - 30), max(0, handle[2] - 30), 255)
    for i in range(12):
        c = 2 + i      # column
        r = 13 - i     # row
        if 0 <= r < 16 and 0 <= c < 16:
            px[r * 16 + c] = handle
            if c + 1 < 16:
                px[r * 16 + c + 1] = handle_dark

    head = head_color + (255,) if len(head_color) == 3 else head_color
    head_dark = (max(0, head[0] - 35), max(0, head[1] - 35), max(0, head[2] - 35), 255)

    if shape == "pickaxe":
        # Horizontal head bar at row 2, cols 5-13
        for c in range(5, 14):
            px[2 * 16 + c] = head
            px[3 * 16 + c] = head_dark
        # Vertical head ends
        for r in range(1, 4):
            px[r * 16 + 5] = head
            px[r * 16 + 13] = head
    elif shape == "axe":
        # Blade triangle: rows 2-7, cols 9-14
        for r in range(2, 8):
            for c in range(9, 14):
                if c - 9 + r - 2 <= 5 and c >= 9:
                    px[r * 16 + c] = head
                    if c == 13:
                        px[r * 16 + c] = head_dark
    elif shape == "shovel":
        # Spade: trapezoid at top-right rows 1-6, cols 9-13
        for r in range(1, 7):
            for c in range(9, 14):
                if (c - 11) ** 2 + (r - 3) ** 2 <= 10:
                    px[r * 16 + c] = head
        px[1 * 16 + 11] = head_dark
    elif shape == "sword":
        # Diagonal blade: along same diagonal as handle, but only top half
        for i in range(6, 13):
            c = 2 + i
            r = 13 - i
            if 0 <= r < 16 and 0 <= c < 16:
                px[r * 16 + c] = head
                if c + 1 < 16:
                    px[r * 16 + c + 1] = head_dark
                if r - 1 >= 0:
                    px[(r - 1) * 16 + c] = head
        # Crossguard around row 8, col 7
        for d in range(-1, 2):
            r, c = 8 + d, 7 - d
            if 0 <= r < 16 and 0 <= c < 16:
                px[r * 16 + c] = handle_dark
    elif shape == "hoe":
        # L-shape head: horizontal bar rows 2, cols 9-13 + vertical rows 2-5 col 13
        for c in range(9, 14):
            px[2 * 16 + c] = head
            px[3 * 16 + c] = head_dark
        for r in range(2, 6):
            px[r * 16 + 13] = head

    return px


def wooden_pickaxe_tex(): return _make_tool((140, 95, 50), (165, 130, 80), "pickaxe")
def stone_pickaxe_tex():  return _make_tool((140, 95, 50), (130, 130, 130), "pickaxe")
def iron_pickaxe_tex():   return _make_tool((140, 95, 50), (220, 220, 225), "pickaxe")
def diamond_pickaxe_tex(): return _make_tool((140, 95, 50), (90, 220, 230), "pickaxe")

def wooden_axe_tex(): return _make_tool((140, 95, 50), (165, 130, 80), "axe")
def stone_axe_tex():  return _make_tool((140, 95, 50), (130, 130, 130), "axe")
def iron_axe_tex():   return _make_tool((140, 95, 50), (220, 220, 225), "axe")
def diamond_axe_tex(): return _make_tool((140, 95, 50), (90, 220, 230), "axe")

def wooden_shovel_tex(): return _make_tool((140, 95, 50), (165, 130, 80), "shovel")
def stone_shovel_tex():  return _make_tool((140, 95, 50), (130, 130, 130), "shovel")
def iron_shovel_tex():   return _make_tool((140, 95, 50), (220, 220, 225), "shovel")
def diamond_shovel_tex(): return _make_tool((140, 95, 50), (90, 220, 230), "shovel")

def wooden_sword_tex(): return _make_tool((140, 95, 50), (165, 130, 80), "sword")
def stone_sword_tex():  return _make_tool((140, 95, 50), (130, 130, 130), "sword")
def iron_sword_tex():   return _make_tool((140, 95, 50), (220, 220, 225), "sword")
def diamond_sword_tex(): return _make_tool((140, 95, 50), (90, 220, 230), "sword")

def wooden_hoe_tex(): return _make_tool((140, 95, 50), (165, 130, 80), "hoe")
def stone_hoe_tex():  return _make_tool((140, 95, 50), (130, 130, 130), "hoe")
def iron_hoe_tex():   return _make_tool((140, 95, 50), (220, 220, 225), "hoe")
def diamond_hoe_tex(): return _make_tool((140, 95, 50), (90, 220, 230), "hoe")


def stick_tex() -> list[tuple[int, int, int, int]]:
    """Brown diagonal stick."""
    transparent = (0, 0, 0, 0)
    px = [transparent] * 256
    handle = (140, 95, 50, 255)
    dark = (95, 60, 25, 255)
    for i in range(13):
        c = 1 + i
        r = 14 - i
        if 0 <= r < 16 and 0 <= c < 16:
            px[r * 16 + c] = handle
            if c + 1 < 16:
                px[r * 16 + c + 1] = dark
    return px


def coal_tex() -> list[tuple[int, int, int, int]]:
    """Lumpy black nugget."""
    transparent = (0, 0, 0, 0)
    px = [transparent] * 256
    for r in range(3, 14):
        for c in range(3, 14):
            d = (r - 8) ** 2 + (c - 8) ** 2
            if d <= 25:
                shade = 25 + ((r * 7 + c * 11) % 18)
                px[r * 16 + c] = (shade, shade, shade, 255)
            elif d <= 30:
                px[r * 16 + c] = (12, 12, 12, 255)
    return px


def _ingot(color_base: tuple) -> list[tuple[int, int, int, int]]:
    """Generic ingot bar shape."""
    transparent = (0, 0, 0, 0)
    px = [transparent] * 256
    light = (min(255, color_base[0] + 40), min(255, color_base[1] + 40), min(255, color_base[2] + 40), 255)
    dark = (max(0, color_base[0] - 50), max(0, color_base[1] - 50), max(0, color_base[2] - 50), 255)
    base = (color_base[0], color_base[1], color_base[2], 255)
    # Rounded rectangle rows 5-10, cols 2-13
    for r in range(5, 11):
        for c in range(2, 14):
            if r == 5 or r == 10:
                px[r * 16 + c] = dark
            elif c == 2 or c == 13:
                px[r * 16 + c] = dark
            elif r == 6:
                px[r * 16 + c] = light
            else:
                px[r * 16 + c] = base
    return px


def iron_ingot_tex(): return _ingot((200, 200, 210))
def gold_ingot_tex(): return _ingot((225, 200, 70))
def copper_ingot_tex(): return _ingot((205, 125, 80))


def diamond_tex() -> list[tuple[int, int, int, int]]:
    """Cyan diamond rhombus."""
    transparent = (0, 0, 0, 0)
    px = [transparent] * 256
    base = (95, 215, 230, 255)
    light = (180, 240, 250, 255)
    dark = (50, 150, 175, 255)
    cx, cy = 8, 8
    for r in range(16):
        for c in range(16):
            d = abs(r - cy) + abs(c - cx)
            if d == 5:
                px[r * 16 + c] = dark
            elif d == 4:
                px[r * 16 + c] = base
            elif d < 4:
                px[r * 16 + c] = light if (r < cy and c < cx) else base
    return px


def raw_beef_tex() -> list[tuple[int, int, int, int]]:
    """Raw red meat slice."""
    transparent = (0, 0, 0, 0)
    px = [transparent] * 256
    red = (185, 50, 55, 255)
    pink = (220, 100, 95, 255)
    fat = (235, 215, 195, 255)
    for r in range(3, 14):
        for c in range(3, 14):
            d = (r - 8) ** 2 + (c - 8) ** 2
            if d <= 28:
                if (r + c) % 7 == 0:
                    px[r * 16 + c] = fat
                elif (r * 3 + c * 5) % 11 < 4:
                    px[r * 16 + c] = pink
                else:
                    px[r * 16 + c] = red
    return px


def cooked_beef_tex() -> list[tuple[int, int, int, int]]:
    """Browned cooked meat slice."""
    transparent = (0, 0, 0, 0)
    px = [transparent] * 256
    brown = (115, 70, 35, 255)
    crust = (75, 45, 20, 255)
    lite = (160, 110, 70, 255)
    for r in range(3, 14):
        for c in range(3, 14):
            d = (r - 8) ** 2 + (c - 8) ** 2
            if d <= 28:
                if d > 22:
                    px[r * 16 + c] = crust
                elif (r * 3 + c * 5) % 11 < 4:
                    px[r * 16 + c] = lite
                else:
                    px[r * 16 + c] = brown
    return px


def apple_tex() -> list[tuple[int, int, int, int]]:
    """Red apple with green stem."""
    transparent = (0, 0, 0, 0)
    px = [transparent] * 256
    red = (200, 30, 30, 255)
    dark = (140, 20, 20, 255)
    light = (240, 80, 60, 255)
    stem = (90, 60, 30, 255)
    leaf = (30, 140, 30, 255)
    for r in range(4, 14):
        for c in range(4, 13):
            d = (r - 9) ** 2 + (c - 8) ** 2
            if d <= 22:
                if d > 18:
                    px[r * 16 + c] = dark
                elif (r * 3 + c * 5) % 7 < 2:
                    px[r * 16 + c] = light
                else:
                    px[r * 16 + c] = red
    # Stem and leaf
    px[3 * 16 + 8] = stem
    px[2 * 16 + 8] = stem
    px[2 * 16 + 9] = leaf
    px[3 * 16 + 10] = leaf
    return px


def chicken_tex() -> list[tuple[int, int, int, int]]:
    """Pinkish raw chicken meat slab."""
    transparent = (0, 0, 0, 0)
    px = [transparent] * 256
    pink = (240, 190, 180, 255)
    dark = (200, 140, 130, 255)
    for r in range(3, 14):
        for c in range(3, 14):
            d = (r - 8) ** 2 + (c - 8) ** 2
            if d <= 28:
                if (r * 5 + c * 7) % 9 < 2:
                    px[r * 16 + c] = dark
                else:
                    px[r * 16 + c] = pink
    return px


def porkchop_tex() -> list[tuple[int, int, int, int]]:
    """Pink raw porkchop."""
    transparent = (0, 0, 0, 0)
    px = [transparent] * 256
    pink = (230, 150, 140, 255)
    dark = (180, 100, 90, 255)
    fat = (245, 220, 210, 255)
    for r in range(3, 14):
        for c in range(3, 14):
            d = (r - 8) ** 2 + (c - 8) ** 2
            if d <= 28:
                v = (r * 3 + c * 7) % 11
                if v < 2:
                    px[r * 16 + c] = fat
                elif v < 5:
                    px[r * 16 + c] = dark
                else:
                    px[r * 16 + c] = pink
    return px


def wool_tex() -> list[tuple[int, int, int, int]]:
    """White wool fluff."""
    base = (235, 235, 235, 255)
    dark = (200, 200, 200, 255)
    light = (250, 250, 250, 255)
    px = []
    for r in range(16):
        for c in range(16):
            v = (r * 7 + c * 13 + (r * c) % 5) % 13
            if v < 3:
                px.append(dark)
            elif v < 7:
                px.append(light)
            else:
                px.append(base)
    return px


def bone_tex() -> list[tuple[int, int, int, int]]:
    """Bone — off-white vertical bar with rounded knobs."""
    transparent = (0, 0, 0, 0)
    px = [transparent] * 256
    bone = (240, 235, 215, 255)
    shadow = (200, 195, 175, 255)
    # Vertical shaft
    for r in range(4, 12):
        for c in range(7, 10):
            px[r * 16 + c] = bone
        px[r * 16 + 7] = shadow if r % 2 == 0 else bone
    # Top knob
    for c in range(6, 11):
        px[3 * 16 + c] = bone
        px[2 * 16 + c] = bone if c in (7, 8, 9) else (0, 0, 0, 0)
    # Bottom knob
    for c in range(6, 11):
        px[12 * 16 + c] = bone
        px[13 * 16 + c] = bone if c in (7, 8, 9) else (0, 0, 0, 0)
    return px


def string_tex() -> list[tuple[int, int, int, int]]:
    """Coiled string — light gray squiggle."""
    transparent = (0, 0, 0, 0)
    px = [transparent] * 256
    s = (220, 220, 210, 255)
    d = (170, 170, 160, 255)
    # Wavy diagonal
    for i in range(2, 14):
        c = 2 + (i + (i // 3)) % 12
        px[i * 16 + c] = s
        if c + 1 < 16:
            px[i * 16 + c + 1] = d
    return px


def rotten_flesh_tex() -> list[tuple[int, int, int, int]]:
    """Greenish-brown rotten meat."""
    transparent = (0, 0, 0, 0)
    px = [transparent] * 256
    base = (130, 110, 70, 255)
    rot = (90, 110, 60, 255)
    dark = (70, 60, 40, 255)
    for r in range(3, 14):
        for c in range(3, 14):
            d = (r - 8) ** 2 + (c - 8) ** 2
            if d <= 28:
                v = (r * 5 + c * 3) % 11
                if v < 3:
                    px[r * 16 + c] = rot
                elif v < 5:
                    px[r * 16 + c] = dark
                else:
                    px[r * 16 + c] = base
    return px


def gunpowder_tex() -> list[tuple[int, int, int, int]]:
    """Dark gray gunpowder dust."""
    transparent = (0, 0, 0, 0)
    px = [transparent] * 256
    dust = (60, 60, 60, 255)
    light = (100, 100, 100, 255)
    for r in range(4, 13):
        for c in range(4, 13):
            v = (r * 11 + c * 7) % 13
            if v < 4:
                px[r * 16 + c] = light
            elif v < 10:
                px[r * 16 + c] = dust
    return px


def leather_tex() -> list[tuple[int, int, int, int]]:
    """Leather scrap — brown grainy patch."""
    transparent = (0, 0, 0, 0)
    px = [transparent] * 256
    base = (120, 80, 50, 255)
    dark = (90, 55, 30, 255)
    light = (150, 105, 70, 255)
    for r in range(3, 14):
        for c in range(3, 14):
            v = (r * 13 + c * 7 + (r * c) % 5) % 11
            if v < 3:
                px[r * 16 + c] = dark
            elif v < 6:
                px[r * 16 + c] = light
            else:
                px[r * 16 + c] = base
    return px


def feather_tex() -> list[tuple[int, int, int, int]]:
    """Feather — white V-shaped quill on transparent background."""
    transparent = (0, 0, 0, 0)
    px = [transparent] * 256
    white = (240, 240, 240, 255)
    shade = (200, 200, 205, 255)
    quill = (220, 200, 160, 255)
    # Central quill — diagonal
    for i in range(2, 14):
        px[i * 16 + (15 - i)] = quill
    # Barbs fanning to one side
    for i in range(3, 13):
        for j in range(1, i - 1):
            c = (15 - i) - j
            if 0 <= c < 16:
                px[i * 16 + c] = white if (i + j) % 3 != 0 else shade
    return px


def raw_iron_tex() -> list[tuple[int, int, int, int]]:
    """Raw iron lump — pinkish-brown stone-like nugget."""
    transparent = (0, 0, 0, 0)
    px = [transparent] * 256
    base = (190, 150, 130, 255)
    dark = (140, 100, 80, 255)
    light = (220, 180, 160, 255)
    for r in range(3, 14):
        for c in range(3, 14):
            d = (r - 8) ** 2 + (c - 8) ** 2
            if d <= 24:
                v = (r * 5 + c * 7) % 11
                if v < 3:
                    px[r * 16 + c] = dark
                elif v < 6:
                    px[r * 16 + c] = light
                else:
                    px[r * 16 + c] = base
    return px


def raw_gold_tex() -> list[tuple[int, int, int, int]]:
    """Raw gold lump — yellowish nugget."""
    transparent = (0, 0, 0, 0)
    px = [transparent] * 256
    base = (220, 180, 60, 255)
    dark = (160, 120, 30, 255)
    light = (250, 220, 100, 255)
    for r in range(3, 14):
        for c in range(3, 14):
            d = (r - 8) ** 2 + (c - 8) ** 2
            if d <= 24:
                v = (r * 5 + c * 7) % 11
                if v < 3:
                    px[r * 16 + c] = dark
                elif v < 6:
                    px[r * 16 + c] = light
                else:
                    px[r * 16 + c] = base
    return px


def raw_copper_tex() -> list[tuple[int, int, int, int]]:
    """Raw copper lump — orange-brown nugget with greenish oxidation flecks."""
    transparent = (0, 0, 0, 0)
    px = [transparent] * 256
    base = (200, 115, 65, 255)
    dark = (150, 80, 45, 255)
    light = (230, 150, 95, 255)
    oxide = (110, 170, 130, 255)  # patina speck
    for r in range(3, 14):
        for c in range(3, 14):
            d = (r - 8) ** 2 + (c - 8) ** 2
            if d <= 24:
                v = (r * 5 + c * 7) % 12
                if v < 2:
                    px[r * 16 + c] = dark
                elif v < 4:
                    px[r * 16 + c] = light
                elif v == 4:
                    px[r * 16 + c] = oxide
                else:
                    px[r * 16 + c] = base
    return px


def redstone_tex() -> list[tuple[int, int, int, int]]:
    """Redstone dust — red sparkly powder."""
    transparent = (0, 0, 0, 0)
    px = [transparent] * 256
    base = (200, 30, 30, 255)
    bright = (255, 80, 80, 255)
    dark = (140, 10, 10, 255)
    for r in range(4, 13):
        for c in range(4, 13):
            v = (r * 11 + c * 7) % 13
            if v < 3:
                px[r * 16 + c] = bright
            elif v < 5:
                px[r * 16 + c] = dark
            elif v < 11:
                px[r * 16 + c] = base
    return px


# ---------------------------------------------------------------------------
# New block textures (Phase 10: extended crafting)
# ---------------------------------------------------------------------------

def _storage_block(color_base: tuple) -> list[tuple[int, int, int, int]]:
    """Generic mineral storage block: rounded squares grid pattern."""
    r0, g0, b0 = color_base
    base = (r0, g0, b0, 255)
    light = (min(255, r0 + 50), min(255, g0 + 50), min(255, b0 + 50), 255)
    dark = (max(0, r0 - 50), max(0, g0 - 50), max(0, b0 - 50), 255)
    px = []
    for r in range(16):
        for c in range(16):
            # 2x2 grid of "nuggets" with edges
            block_r = r // 8
            block_c = c // 8
            ir = r - block_r * 8
            ic = c - block_c * 8
            if ir == 0 or ic == 0 or ir == 7 or ic == 7:
                px.append(dark)
            elif ir == 1 and ic == 1:
                px.append(light)
            elif (ir * 3 + ic * 5) % 7 < 2:
                px.append(light)
            else:
                px.append(base)
    return px


def coal_block_tex(): return _storage_block((35, 35, 35))
def iron_block_tex(): return _storage_block((220, 220, 230))
def gold_block_tex(): return _storage_block((230, 200, 60))
def diamond_block_tex(): return _storage_block((95, 215, 230))
def redstone_block_tex(): return _storage_block((175, 30, 30))
def copper_block_tex(): return _storage_block((200, 110, 60))


def sandstone_tex() -> list[tuple[int, int, int, int]]:
    """Compressed sand: horizontal bands."""
    base = (215, 195, 145, 255)
    light = (235, 215, 165, 255)
    dark = (175, 155, 110, 255)
    px = []
    for r in range(16):
        for c in range(16):
            if r in (0, 5, 10, 15):
                px.append(dark)
            elif r in (1, 6, 11):
                px.append(light)
            elif (r * 3 + c * 7) % 11 < 2:
                px.append(light)
            else:
                px.append(base)
    return px


def stone_bricks_tex() -> list[tuple[int, int, int, int]]:
    """Gray brick wall pattern."""
    base = (130, 130, 135, 255)
    light = (160, 160, 165, 255)
    mortar = (75, 75, 80, 255)
    px = []
    for r in range(16):
        for c in range(16):
            # Bricks 8w x 4h, alternating courses
            course = r // 4
            offset = 4 if course % 2 == 1 else 0
            brick_col_edge = (c + offset) % 8 == 0
            if r % 4 == 0 or brick_col_edge:
                px.append(mortar)
            elif (r * 5 + c * 3) % 13 < 2:
                px.append(light)
            else:
                px.append(base)
    return px


def bricks_tex() -> list[tuple[int, int, int, int]]:
    """Red clay brick wall pattern."""
    base = (170, 80, 60, 255)
    light = (200, 110, 85, 255)
    mortar = (210, 200, 180, 255)
    px = []
    for r in range(16):
        for c in range(16):
            course = r // 4
            offset = 4 if course % 2 == 1 else 0
            brick_col_edge = (c + offset) % 8 == 0
            if r % 4 == 0 or brick_col_edge:
                px.append(mortar)
            elif (r * 5 + c * 3) % 13 < 2:
                px.append(light)
            else:
                px.append(base)
    return px


def bookshelf_side_tex() -> list[tuple[int, int, int, int]]:
    """Two rows of book spines on plank background."""
    px = _wood_base("h")
    # Books arranged in two horizontal rows (rows 2-6, rows 9-13)
    book_colors = [
        (130, 30, 30, 255),
        (50, 80, 150, 255),
        (60, 130, 60, 255),
        (180, 140, 40, 255),
        (110, 60, 130, 255),
        (200, 90, 30, 255),
    ]
    for band_top in (2, 9):
        for c in range(16):
            book_idx = c // 3
            if book_idx >= len(book_colors):
                book_idx = book_idx % len(book_colors)
            color = book_colors[book_idx]
            for r in range(band_top, band_top + 5):
                if c % 3 == 0:
                    px[r * 16 + c] = (30, 25, 20, 255)
                else:
                    px[r * 16 + c] = color
    return px


def tnt_side_tex() -> list[tuple[int, int, int, int]]:
    """Red TNT with letters."""
    base = (200, 30, 30, 255)
    dark = (140, 20, 20, 255)
    white = (240, 240, 240, 255)
    px = []
    for r in range(16):
        for c in range(16):
            if r in (0, 15) or c in (0, 15):
                px.append(dark)
            else:
                px.append(base)
    # Faux "TNT" text band in middle (rows 6-9)
    for c in range(2, 14):
        px[7 * 16 + c] = white
        px[8 * 16 + c] = white
    # Mortar-ish darker stripes
    for r in (4, 11):
        for c in range(1, 15):
            if (c % 2) == 0:
                px[r * 16 + c] = dark
    return px


def tnt_top_tex() -> list[tuple[int, int, int, int]]:
    """White fuse on red top."""
    base = (200, 30, 30, 255)
    dark = (140, 20, 20, 255)
    fuse = (240, 220, 90, 255)
    fuse_dark = (160, 110, 30, 255)
    px = []
    for r in range(16):
        for c in range(16):
            if r in (0, 15) or c in (0, 15):
                px.append(dark)
            else:
                px.append(base)
    # Fuse circle in center
    for r in range(6, 11):
        for c in range(6, 11):
            d = (r - 8) ** 2 + (c - 8) ** 2
            if d <= 4:
                px[r * 16 + c] = fuse
            elif d <= 8:
                px[r * 16 + c] = fuse_dark
    return px


# ---------------------------------------------------------------------------
# New item textures (Phase 10: extended crafting)
# ---------------------------------------------------------------------------

def clay_ball_tex() -> list[tuple[int, int, int, int]]:
    """Lump of clay."""
    transparent = (0, 0, 0, 0)
    px = [transparent] * 256
    base = (150, 155, 175, 255)
    light = (175, 180, 200, 255)
    dark = (115, 120, 140, 255)
    for r in range(4, 13):
        for c in range(4, 13):
            d = (r - 8) ** 2 + (c - 8) ** 2
            if d <= 22:
                v = (r * 5 + c * 3) % 11
                if v < 2:
                    px[r * 16 + c] = light
                elif v < 4:
                    px[r * 16 + c] = dark
                else:
                    px[r * 16 + c] = base
    return px


def brick_item_tex() -> list[tuple[int, int, int, int]]:
    """Single fired brick item."""
    transparent = (0, 0, 0, 0)
    px = [transparent] * 256
    base = (170, 80, 60, 255)
    light = (200, 110, 85, 255)
    dark = (110, 50, 35, 255)
    for r in range(5, 12):
        for c in range(3, 14):
            if r == 5 or r == 11 or c == 3 or c == 13:
                px[r * 16 + c] = dark
            elif r == 6:
                px[r * 16 + c] = light
            else:
                px[r * 16 + c] = base
    return px


def paper_tex() -> list[tuple[int, int, int, int]]:
    """Sheet of paper."""
    transparent = (0, 0, 0, 0)
    px = [transparent] * 256
    base = (240, 240, 230, 255)
    shadow = (200, 200, 190, 255)
    line = (170, 170, 180, 255)
    for r in range(3, 14):
        for c in range(3, 13):
            if r == 3 or r == 13 or c == 3 or c == 12:
                px[r * 16 + c] = shadow
            else:
                px[r * 16 + c] = base
    # Faint text lines
    for r in (6, 8, 10):
        for c in range(5, 11):
            px[r * 16 + c] = line
    return px


def book_tex() -> list[tuple[int, int, int, int]]:
    """Brown book with band."""
    transparent = (0, 0, 0, 0)
    px = [transparent] * 256
    cover = (130, 65, 30, 255)
    dark = (80, 40, 20, 255)
    page = (240, 230, 200, 255)
    band = (200, 180, 40, 255)
    for r in range(3, 14):
        for c in range(3, 13):
            if c == 3 or c == 12 or r == 3 or r == 13:
                px[r * 16 + c] = dark
            else:
                px[r * 16 + c] = cover
    # Pages strip (right side)
    for r in range(4, 13):
        px[r * 16 + 11] = page
    # Decorative band
    for c in range(3, 13):
        px[8 * 16 + c] = band
    return px


def bowl_tex() -> list[tuple[int, int, int, int]]:
    """Wooden bowl viewed from front."""
    transparent = (0, 0, 0, 0)
    px = [transparent] * 256
    wood = (155, 110, 65, 255)
    dark = (105, 70, 35, 255)
    interior = (75, 50, 25, 255)
    # Outer ellipse rows 8-13
    for r in range(8, 14):
        for c in range(2, 14):
            d = ((r - 10.5) * 2) ** 2 / 4 + (c - 8) ** 2
            if d <= 36:
                if r == 8 or d > 30:
                    px[r * 16 + c] = dark
                elif r == 9:
                    px[r * 16 + c] = interior
                else:
                    px[r * 16 + c] = wood
    return px


def mushroom_stew_tex() -> list[tuple[int, int, int, int]]:
    """Bowl with brown stew."""
    px = bowl_tex()
    stew = (140, 80, 40, 255)
    stew_chunk = (180, 110, 60, 255)
    # Fill bowl interior with stew
    for r in range(8, 11):
        for c in range(3, 13):
            d = ((r - 10.5) * 2) ** 2 / 4 + (c - 8) ** 2
            if d <= 25:
                if (r * 3 + c * 5) % 7 < 2:
                    px[r * 16 + c] = stew_chunk
                else:
                    px[r * 16 + c] = stew
    return px


def golden_apple_tex() -> list[tuple[int, int, int, int]]:
    """Gold-colored apple."""
    transparent = (0, 0, 0, 0)
    px = [transparent] * 256
    gold = (230, 195, 60, 255)
    dark = (160, 130, 30, 255)
    light = (255, 230, 130, 255)
    stem = (90, 60, 30, 255)
    leaf = (30, 140, 30, 255)
    for r in range(4, 14):
        for c in range(4, 13):
            d = (r - 9) ** 2 + (c - 8) ** 2
            if d <= 22:
                if d > 18:
                    px[r * 16 + c] = dark
                elif (r * 3 + c * 5) % 7 < 2:
                    px[r * 16 + c] = light
                else:
                    px[r * 16 + c] = gold
    px[3 * 16 + 8] = stem
    px[2 * 16 + 8] = stem
    px[2 * 16 + 9] = leaf
    return px


def sugar_tex() -> list[tuple[int, int, int, int]]:
    """White sugar grains."""
    transparent = (0, 0, 0, 0)
    px = [transparent] * 256
    white = (250, 250, 250, 255)
    light = (220, 220, 220, 255)
    for r in range(4, 13):
        for c in range(4, 13):
            v = (r * 7 + c * 11) % 13
            if v < 4:
                px[r * 16 + c] = light
            elif v < 11:
                px[r * 16 + c] = white
    return px


def bone_meal_tex() -> list[tuple[int, int, int, int]]:
    """Off-white bone dust."""
    transparent = (0, 0, 0, 0)
    px = [transparent] * 256
    base = (240, 235, 215, 255)
    light = (255, 250, 230, 255)
    for r in range(4, 13):
        for c in range(4, 13):
            v = (r * 11 + c * 7) % 13
            if v < 4:
                px[r * 16 + c] = light
            elif v < 11:
                px[r * 16 + c] = base
    return px


def shears_tex() -> list[tuple[int, int, int, int]]:
    """Two crossed iron blades with handles."""
    transparent = (0, 0, 0, 0)
    px = [transparent] * 256
    blade = (220, 220, 225, 255)
    blade_dark = (160, 160, 165, 255)
    handle = (110, 70, 30, 255)
    # Blade 1: diagonal top-left to center
    for i in range(8):
        r = 2 + i
        c = 2 + i
        if 0 <= r < 16 and 0 <= c < 16:
            px[r * 16 + c] = blade
            if c + 1 < 16:
                px[r * 16 + c + 1] = blade_dark
    # Blade 2: diagonal top-right to center
    for i in range(8):
        r = 2 + i
        c = 13 - i
        if 0 <= r < 16 and 0 <= c < 16:
            px[r * 16 + c] = blade
            if c - 1 >= 0:
                px[r * 16 + c - 1] = blade_dark
    # Handles below
    for r in range(10, 14):
        px[r * 16 + 5] = handle
        px[r * 16 + 6] = handle
        px[r * 16 + 9] = handle
        px[r * 16 + 10] = handle
    return px


def flint_and_steel_tex() -> list[tuple[int, int, int, int]]:
    """Steel bar with flint chunk."""
    transparent = (0, 0, 0, 0)
    px = [transparent] * 256
    steel = (200, 200, 205, 255)
    steel_dark = (130, 130, 135, 255)
    flint = (60, 60, 70, 255)
    flint_light = (100, 100, 110, 255)
    # Steel bar (diagonal)
    for i in range(10):
        r = 2 + i
        c = 2 + i
        if 0 <= r < 16 and 0 <= c < 16:
            px[r * 16 + c] = steel
            if c + 1 < 16:
                px[r * 16 + c + 1] = steel_dark
    # Flint chunk at bottom-right
    for r in range(10, 14):
        for c in range(10, 14):
            d = (r - 12) ** 2 + (c - 12) ** 2
            if d <= 4:
                px[r * 16 + c] = flint
            elif d <= 8:
                px[r * 16 + c] = flint_light
    return px


def bucket_tex() -> list[tuple[int, int, int, int]]:
    """Iron bucket shape."""
    transparent = (0, 0, 0, 0)
    px = [transparent] * 256
    iron = (200, 200, 210, 255)
    dark = (140, 140, 150, 255)
    light = (230, 230, 240, 255)
    # Trapezoid bucket: rows 4-13
    for r in range(4, 14):
        # Wider at top, narrower at bottom
        margin = max(0, (r - 4) // 3)
        for c in range(3 + margin, 13 - margin):
            if r == 4 or r == 13:
                px[r * 16 + c] = dark
            elif c == 3 + margin or c == 12 - margin:
                px[r * 16 + c] = dark
            elif r == 5:
                px[r * 16 + c] = light
            else:
                px[r * 16 + c] = iron
    # Handle arc (top)
    for c in range(4, 13):
        px[2 * 16 + c] = dark if c in (4, 12) else iron
        if c in (5, 11):
            px[3 * 16 + c] = dark
    return px


def water_bucket_tex() -> list[tuple[int, int, int, int]]:
    """Bucket with water inside."""
    px = bucket_tex()
    water = (60, 130, 220, 255)
    water_light = (110, 170, 240, 255)
    # Fill interior with water rows 6-12
    for r in range(6, 13):
        margin = max(0, (r - 4) // 3)
        for c in range(4 + margin, 12 - margin):
            if (r + c) % 4 == 0:
                px[r * 16 + c] = water_light
            else:
                px[r * 16 + c] = water
    return px


def lava_bucket_tex() -> list[tuple[int, int, int, int]]:
    """Bucket with lava inside."""
    px = bucket_tex()
    for r in range(6, 13):
        margin = max(0, (r - 4) // 3)
        for c in range(4 + margin, 12 - margin):
            v = ((r * 17 + c * 13) % 40)
            rcol = min(255, 200 + v)
            gcol = max(0, 80 - v // 2)
            px[r * 16 + c] = (rcol, gcol, 0, 255)
    return px


def deepslate_tex() -> list[tuple[int, int, int, int]]:
    """Deepslate — dark gray stone with subtle vertical streaks."""
    base = (54, 54, 60, 255)
    light = (72, 72, 80, 255)
    dark = (38, 38, 44, 255)
    px = []
    for row in range(16):
        for col in range(16):
            v = (row * 7 + col * 3 + (row + col * 2) % 5) % 13
            if v < 3:
                px.append(dark)
            elif v < 6:
                px.append(light)
            else:
                px.append(base)
    return px


def deepslate_ore(dot_r: int, dot_g: int, dot_b: int) -> list[tuple[int, int, int, int]]:
    """Deepslate background with scattered colored ore dots."""
    base_tex = deepslate_tex()
    dot = (dot_r, dot_g, dot_b, 255)
    dots = {2, 5, 9, 13, 19, 23, 30, 37, 43, 50, 57, 60, 67, 74, 80, 88,
            95, 100, 107, 114, 120, 127, 133, 140, 147, 153, 160, 167, 173,
            180, 187, 193, 200, 207, 213, 220, 227, 233, 240, 247, 252}
    return [dot if i in dots else base_tex[i] for i in range(256)]


# ---------------------------------------------------------------------------
# Mob sprite textures (front-view billboards) — 16x16 RGBA, transparent bg
# ---------------------------------------------------------------------------

def _blank() -> list[tuple[int, int, int, int]]:
    return [(0, 0, 0, 0)] * 256


def _rect(px, r0, r1, c0, c1, color):
    for r in range(max(0, r0), min(16, r1)):
        for c in range(max(0, c0), min(16, c1)):
            px[r * 16 + c] = color


def _dot(px, r, c, color):
    if 0 <= r < 16 and 0 <= c < 16:
        px[r * 16 + c] = color


def _svg_rect(px, x, y, w, h, color):
    """Apply an SVG-style rect (top-left x,y; width w, height h) to the 16x16 buffer.

    _rect takes (row0, row1, col0, col1); SVG y maps directly to row (both top-down).
    """
    _rect(px, y, y + h, x, x + w, color)


def _shade_mob_tile(px):
    """Add gentle volume to a flat 16x16 mob part tile (Faz 3.3).

    Row 0 is the top of the part (atlas v grows downward), so we light the top
    and shade the bottom, darken the outer 1px ring for cube definition, and add
    a faint deterministic dither to break up solid fills. Hue is preserved — only
    per-pixel brightness is nudged. Transparent texels (a==0) are left untouched.
    """
    out = list(px)
    for row in range(16):
        # Top brighter, bottom darker: +0.10 .. -0.10 over the 16 rows.
        vfac = 1.10 - (row / 15.0) * 0.20
        for col in range(16):
            i = row * 16 + col
            r, g, b, a = out[i]
            if a == 0:
                continue
            f = vfac
            if row == 0 or row == 15 or col == 0 or col == 15:
                f *= 0.90  # soft edge AO ring
            # Faint deterministic dither in roughly [-2.4, +2.4].
            dith = ((((i * 2654435761) >> 8) & 3) - 1.5) * 1.6
            nr = int(max(0, min(255, r * f + dith)))
            ng = int(max(0, min(255, g * f + dith)))
            nb = int(max(0, min(255, b * f + dith)))
            out[i] = (nr, ng, nb, a)
    return out


def mob_cow_tex() -> list[tuple[int, int, int, int]]:
    """Cow — brown body, lighter face, two black eyes, dark muzzle."""
    px = _blank()
    body = (140, 90, 55, 255)
    body_dark = (95, 60, 35, 255)
    face = (175, 130, 90, 255)
    muzzle = (230, 200, 175, 255)
    horn = (240, 230, 200, 255)
    eye = (15, 10, 10, 255)
    # Body block
    _rect(px, 3, 14, 3, 13, body)
    # Side shadows
    _rect(px, 3, 14, 3, 4, body_dark)
    _rect(px, 13, 14, 3, 13, body_dark)
    # Face panel
    _rect(px, 4, 10, 5, 11, face)
    # Muzzle
    _rect(px, 8, 10, 6, 10, muzzle)
    # Horns at top
    _dot(px, 2, 4, horn); _dot(px, 2, 11, horn)
    _dot(px, 3, 4, horn); _dot(px, 3, 11, horn)
    # Eyes
    _rect(px, 6, 7, 6, 7, eye)
    _rect(px, 6, 7, 9, 10, eye)
    # Brown spots on body
    _dot(px, 11, 5, body_dark); _dot(px, 11, 6, body_dark)
    _dot(px, 12, 5, body_dark)
    _dot(px, 10, 10, body_dark); _dot(px, 10, 11, body_dark)
    return px


def mob_pig_tex() -> list[tuple[int, int, int, int]]:
    """Pig — pink body, darker snout, two eyes, two nostrils."""
    px = _blank()
    body = (235, 160, 165, 255)
    body_dark = (190, 120, 130, 255)
    snout = (215, 135, 140, 255)
    nostril = (110, 60, 65, 255)
    eye = (15, 10, 10, 255)
    _rect(px, 3, 14, 3, 13, body)
    _rect(px, 13, 14, 3, 13, body_dark)
    _rect(px, 3, 14, 3, 4, body_dark)
    # Ears triangles top
    _dot(px, 2, 4, body); _dot(px, 2, 5, body)
    _dot(px, 2, 10, body); _dot(px, 2, 11, body)
    # Snout
    _rect(px, 8, 11, 6, 10, snout)
    _dot(px, 9, 7, nostril); _dot(px, 9, 9, nostril)
    # Eyes
    _rect(px, 5, 6, 5, 7, eye)
    _rect(px, 5, 6, 9, 11, eye)
    return px


def mob_sheep_tex() -> list[tuple[int, int, int, int]]:
    """Sheep — fluffy off-white body, gray face, eyes."""
    px = _blank()
    wool = (235, 230, 225, 255)
    wool_dark = (200, 195, 190, 255)
    face = (95, 80, 70, 255)
    face_light = (140, 120, 105, 255)
    eye = (10, 10, 10, 255)
    # Fluffy body — slightly irregular silhouette
    _rect(px, 4, 14, 3, 13, wool)
    _rect(px, 13, 14, 3, 13, wool_dark)
    # Fluff bumps on top
    _dot(px, 3, 4, wool); _dot(px, 3, 6, wool); _dot(px, 3, 8, wool)
    _dot(px, 3, 10, wool); _dot(px, 3, 12, wool)
    _dot(px, 2, 5, wool); _dot(px, 2, 9, wool); _dot(px, 2, 11, wool)
    # Face oval
    _rect(px, 5, 11, 5, 11, face)
    _rect(px, 5, 6, 5, 11, face_light)
    # Eyes
    _dot(px, 7, 6, eye); _dot(px, 7, 9, eye)
    # Muzzle dark
    _rect(px, 9, 11, 7, 9, (60, 50, 40, 255))
    return px


def mob_chicken_tex() -> list[tuple[int, int, int, int]]:
    """Chicken — white body, red comb, yellow beak, eye."""
    px = _blank()
    body = (245, 245, 240, 255)
    body_dark = (200, 200, 195, 255)
    comb = (220, 40, 40, 255)
    beak = (250, 200, 50, 255)
    eye = (15, 10, 10, 255)
    # Narrower body for chicken
    _rect(px, 5, 14, 5, 11, body)
    _rect(px, 13, 14, 5, 11, body_dark)
    _rect(px, 5, 14, 5, 6, body_dark)
    # Comb on top
    _dot(px, 3, 7, comb); _dot(px, 3, 8, comb); _dot(px, 3, 9, comb)
    _dot(px, 2, 8, comb)
    # Beak (triangle pointing down-front)
    _dot(px, 7, 7, beak); _dot(px, 7, 8, beak); _dot(px, 7, 9, beak)
    _dot(px, 8, 8, beak)
    # Eye
    _dot(px, 6, 7, eye); _dot(px, 6, 10, eye)
    # Feet
    _dot(px, 14, 6, beak); _dot(px, 14, 10, beak)
    _dot(px, 15, 6, beak); _dot(px, 15, 10, beak)
    return px


def mob_zombie_tex() -> list[tuple[int, int, int, int]]:
    """Zombie — green skin, purple-blue torn clothing, dark eye sockets."""
    px = _blank()
    skin    = (92, 162, 82, 255)
    dark    = (58, 112, 52, 255)
    purple  = (128, 62, 168, 255)
    blue    = (60, 82, 172, 255)
    socket  = (14, 10, 10, 255)
    mouth   = (32, 60, 26, 255)
    # Upper body (purple shirt)
    _rect(px, 2, 8, 4, 12, purple)
    # Lower body (blue pants)
    _rect(px, 8, 14, 4, 12, blue)
    # Side shadows
    _rect(px, 2, 14, 4, 5, (85, 40, 115, 255))
    _rect(px, 8, 14, 11, 12, (42, 58, 128, 255))
    # Face area (green skin)
    _rect(px, 3, 9, 5, 11, skin)
    _rect(px, 2, 3, 5, 11, dark)
    # Eye sockets
    _rect(px, 5, 7, 5, 7, socket)
    _rect(px, 5, 7, 9, 11, socket)
    # Mouth
    _rect(px, 8, 9, 6, 10, mouth)
    # Arm shading
    _dot(px, 10, 5, (42, 58, 128, 255)); _dot(px, 11, 5, (42, 58, 128, 255))
    _dot(px, 10, 10, (42, 58, 128, 255)); _dot(px, 11, 10, (42, 58, 128, 255))
    return px


def mob_skeleton_tex() -> list[tuple[int, int, int, int]]:
    """Skeleton — bone-white body, hollow black eye sockets."""
    px = _blank()
    bone = (225, 225, 215, 255)
    bone_dark = (170, 170, 160, 255)
    socket = (10, 10, 10, 255)
    rib = (190, 190, 180, 255)
    # Tall body
    _rect(px, 2, 14, 4, 12, bone)
    _rect(px, 13, 14, 4, 12, bone_dark)
    _rect(px, 2, 14, 4, 5, bone_dark)
    # Skull eye sockets (deep)
    _rect(px, 4, 7, 5, 7, socket)
    _rect(px, 4, 7, 9, 11, socket)
    # Jaw line
    _rect(px, 8, 9, 5, 11, bone_dark)
    _dot(px, 8, 6, socket); _dot(px, 8, 8, socket); _dot(px, 8, 10, socket)
    # Rib hint
    _rect(px, 10, 11, 5, 11, rib)
    _rect(px, 12, 13, 5, 11, rib)
    return px


def mob_spider_tex() -> list[tuple[int, int, int, int]]:
    """Spider — dark body, 8 red eyes (2 rows of 4), legs poking out sides."""
    px = _blank()
    body = (55, 40, 35, 255)
    body_dark = (25, 18, 15, 255)
    leg = (35, 25, 20, 255)
    eye = (220, 30, 30, 255)
    # Round-ish body
    _rect(px, 5, 13, 4, 12, body)
    _rect(px, 12, 13, 4, 12, body_dark)
    _rect(px, 5, 6, 4, 12, body_dark)
    # Eight eyes in 2x4 grid
    for c in (5, 7, 8, 10):
        _dot(px, 7, c, eye)
    for c in (5, 7, 8, 10):
        _dot(px, 9, c, eye)
    # Legs left/right (3 segments each)
    _dot(px, 6, 2, leg); _dot(px, 6, 1, leg)
    _dot(px, 9, 2, leg); _dot(px, 9, 1, leg)
    _dot(px, 11, 2, leg); _dot(px, 11, 1, leg)
    _dot(px, 6, 13, leg); _dot(px, 6, 14, leg)
    _dot(px, 9, 13, leg); _dot(px, 9, 14, leg)
    _dot(px, 11, 13, leg); _dot(px, 11, 14, leg)
    return px


def mob_creeper_tex() -> list[tuple[int, int, int, int]]:
    """Creeper — bright green, classic inverted-T face."""
    px = _blank()
    body = (90, 180, 75, 255)
    body_dark = (55, 130, 50, 255)
    body_light = (120, 200, 100, 255)
    face = (15, 25, 15, 255)
    # Tall body
    _rect(px, 2, 14, 4, 12, body)
    # Mottled shading typical of creeper
    _rect(px, 2, 14, 4, 5, body_dark)
    _rect(px, 13, 14, 4, 12, body_dark)
    _dot(px, 3, 7, body_light); _dot(px, 4, 10, body_light)
    _dot(px, 10, 6, body_light); _dot(px, 12, 9, body_light)
    # Eyes (square sockets)
    _rect(px, 5, 8, 5, 7, face)
    _rect(px, 5, 8, 9, 11, face)
    # Mouth (inverted T)
    _rect(px, 8, 12, 7, 9, face)
    _rect(px, 10, 12, 5, 7, face)
    _rect(px, 10, 12, 9, 11, face)
    return px


def mob_villager_tex() -> list[tuple[int, int, int, int]]:
    """Villager — brown robe body, large nose, plain face."""
    px = _blank()
    robe = (110, 75, 50, 255)
    robe_dark = (70, 50, 30, 255)
    skin = (200, 165, 130, 255)
    nose = (155, 110, 80, 255)
    eye = (15, 10, 10, 255)
    hair = (60, 40, 25, 255)
    # Tall robe body
    _rect(px, 2, 14, 4, 12, robe)
    _rect(px, 13, 14, 4, 12, robe_dark)
    _rect(px, 2, 14, 4, 5, robe_dark)
    # Head/face area
    _rect(px, 3, 9, 5, 11, skin)
    # Hair on top
    _rect(px, 3, 4, 5, 11, hair)
    # Big prominent nose (signature villager feature)
    _rect(px, 6, 9, 7, 9, nose)
    # Eyes flanking nose
    _dot(px, 6, 6, eye); _dot(px, 6, 10, eye)
    # Arms folded — vertical bar across belly
    _rect(px, 10, 11, 5, 11, robe_dark)
    return px


# ---------------------------------------------------------------------------
# 3D mob part textures — 16×16 RGBA sprites for each box model part.
# These are scaled to 64×64 by TextureManager at atlas build time.
# Each covers all 6 faces (same texture wrapped around all faces of each cube).
# ---------------------------------------------------------------------------

def mob_cow_head() -> list[tuple[int, int, int, int]]:
    # Synthesized to match the new dark-brown cow body (no head SVG was provided).
    px = _blank()
    field = (75, 54, 33, 255); muzzle = (245, 245, 220, 255); eye = (43, 27, 16, 255)
    _svg_rect(px, 0, 0, 16, 16, field)   # full-cover bg (shader discards transparent texels)
    _svg_rect(px, 2, 3, 12, 10, field)
    _svg_rect(px, 9, 5, 5, 6, muzzle)
    _svg_rect(px, 4, 6, 2, 2, eye)
    _svg_rect(px, 10, 6, 2, 2, eye)
    return px


def mob_cow_body() -> list[tuple[int, int, int, int]]:
    px = _blank()
    _svg_rect(px, 0, 0, 16, 16, (75, 54, 33, 255))
    _svg_rect(px, 0, 2, 16, 10, (75, 54, 33, 255))
    _svg_rect(px, 4, 12, 8, 2, (245, 245, 220, 255))
    _svg_rect(px, 2, 4, 3, 3, (255, 255, 255, 255))
    _svg_rect(px, 11, 6, 4, 4, (255, 255, 255, 255))
    return px


def mob_cow_leg() -> list[tuple[int, int, int, int]]:
    px = _blank()
    _svg_rect(px, 0, 0, 16, 16, (75, 54, 33, 255))
    _svg_rect(px, 6, 2, 4, 10, (75, 54, 33, 255))
    _svg_rect(px, 6, 12, 4, 2, (43, 27, 16, 255))
    return px


def mob_pig_head() -> list[tuple[int, int, int, int]]:
    px = _blank()
    _svg_rect(px, 0, 0, 16, 16, (255, 192, 203, 255))
    _svg_rect(px, 2, 3, 12, 10, (255, 192, 203, 255))
    _svg_rect(px, 5, 8, 6, 4, (255, 182, 193, 255))
    # nostrils: black @ 0.3 over #FFB6C1
    _svg_rect(px, 6, 10, 1, 1, (178, 127, 135, 255))
    _svg_rect(px, 9, 10, 1, 1, (178, 127, 135, 255))
    _svg_rect(px, 4, 6, 2, 2, (0, 0, 0, 255))
    _svg_rect(px, 10, 6, 2, 2, (0, 0, 0, 255))
    return px


def mob_pig_body() -> list[tuple[int, int, int, int]]:
    px = _blank()
    _svg_rect(px, 0, 0, 16, 16, (255, 192, 203, 255))
    _svg_rect(px, 1, 4, 14, 8, (255, 192, 203, 255))
    _svg_rect(px, 1, 4, 14, 2, (255, 182, 193, 255))
    return px


def mob_pig_leg() -> list[tuple[int, int, int, int]]:
    px = _blank()
    _svg_rect(px, 0, 0, 16, 16, (255, 192, 203, 255))
    _svg_rect(px, 6, 6, 4, 8, (255, 192, 203, 255))
    _svg_rect(px, 6, 14, 4, 2, (218, 112, 214, 255))
    return px


def mob_sheep_head() -> list[tuple[int, int, int, int]]:
    px = _blank()
    _svg_rect(px, 0, 0, 16, 16, (255, 255, 255, 255))
    _svg_rect(px, 3, 3, 10, 10, (255, 255, 255, 255))
    _svg_rect(px, 5, 6, 6, 6, (211, 211, 211, 255))
    _svg_rect(px, 6, 8, 1, 1, (0, 0, 0, 255))
    _svg_rect(px, 9, 8, 1, 1, (0, 0, 0, 255))
    return px


def mob_sheep_wool() -> list[tuple[int, int, int, int]]:
    px = _blank()
    _svg_rect(px, 0, 0, 16, 16, (248, 248, 255, 255))
    _svg_rect(px, 1, 2, 14, 12, (248, 248, 255, 255))
    _svg_rect(px, 3, 4, 2, 2, (240, 240, 240, 255))
    _svg_rect(px, 10, 9, 3, 2, (240, 240, 240, 255))
    return px


def mob_sheep_leg() -> list[tuple[int, int, int, int]]:
    px = _blank()
    _svg_rect(px, 0, 0, 16, 16, (255, 255, 255, 255))
    _svg_rect(px, 6, 4, 4, 8, (255, 255, 255, 255))
    _svg_rect(px, 6, 12, 4, 4, (211, 211, 211, 255))
    return px


def mob_chicken_head() -> list[tuple[int, int, int, int]]:
    px = _blank()
    _svg_rect(px, 0, 0, 16, 16, (255, 255, 255, 255))
    _svg_rect(px, 4, 4, 8, 8, (255, 255, 255, 255))
    _svg_rect(px, 5, 8, 6, 3, (255, 255, 0, 255))
    _svg_rect(px, 6, 11, 4, 2, (255, 0, 0, 255))
    _svg_rect(px, 6, 6, 1, 1, (0, 0, 0, 255))
    _svg_rect(px, 9, 6, 1, 1, (0, 0, 0, 255))
    return px


def mob_chicken_body() -> list[tuple[int, int, int, int]]:
    px = _blank()
    _svg_rect(px, 0, 0, 16, 16, (255, 255, 255, 255))
    _svg_rect(px, 3, 5, 10, 8, (255, 255, 255, 255))
    return px


def mob_chicken_leg() -> list[tuple[int, int, int, int]]:
    px = _blank()
    _svg_rect(px, 0, 0, 16, 16, (255, 255, 0, 255))
    _svg_rect(px, 7, 6, 2, 8, (255, 255, 0, 255))
    _svg_rect(px, 6, 14, 4, 2, (255, 255, 0, 255))
    return px


def mob_chicken_wing() -> list[tuple[int, int, int, int]]:
    px = _blank()
    _svg_rect(px, 0, 0, 16, 16, (255, 255, 255, 255))
    _svg_rect(px, 4, 6, 8, 4, (255, 255, 255, 255))
    return px


def mob_zombie_head() -> list[tuple[int, int, int, int]]:
    px = _blank()
    _svg_rect(px, 0, 0, 16, 16, (46, 139, 87, 255))
    _svg_rect(px, 2, 2, 12, 12, (46, 139, 87, 255))
    _svg_rect(px, 4, 6, 2, 2, (0, 0, 0, 255))
    _svg_rect(px, 10, 6, 2, 2, (0, 0, 0, 255))
    _svg_rect(px, 2, 12, 12, 2, (0, 0, 255, 255))
    return px


def mob_zombie_body() -> list[tuple[int, int, int, int]]:
    px = _blank()
    _svg_rect(px, 0, 0, 16, 16, (0, 0, 255, 255))
    _svg_rect(px, 3, 2, 10, 12, (0, 0, 255, 255))
    _svg_rect(px, 1, 4, 2, 8, (46, 139, 87, 255))
    _svg_rect(px, 13, 4, 2, 8, (46, 139, 87, 255))
    return px


def mob_zombie_arm() -> list[tuple[int, int, int, int]]:
    px = _blank()
    _svg_rect(px, 0, 0, 16, 16, (46, 139, 87, 255))
    _svg_rect(px, 6, 2, 4, 2, (0, 0, 255, 255))
    _svg_rect(px, 6, 4, 4, 10, (46, 139, 87, 255))
    return px


def mob_zombie_leg() -> list[tuple[int, int, int, int]]:
    px = _blank()
    _svg_rect(px, 0, 0, 16, 16, (0, 0, 139, 255))
    _svg_rect(px, 6, 2, 4, 10, (0, 0, 139, 255))
    _svg_rect(px, 6, 12, 4, 4, (46, 139, 87, 255))
    return px


def mob_skeleton_head() -> list[tuple[int, int, int, int]]:
    px = _blank()
    _svg_rect(px, 0, 0, 16, 16, (255, 255, 255, 255))
    _svg_rect(px, 3, 3, 10, 10, (255, 255, 255, 255))
    _svg_rect(px, 5, 6, 2, 2, (0, 0, 0, 255))
    _svg_rect(px, 9, 6, 2, 2, (0, 0, 0, 255))
    # mouth: black @ 0.2 over #FFFFFF
    _svg_rect(px, 7, 9, 2, 1, (204, 204, 204, 255))
    return px


def mob_skeleton_body() -> list[tuple[int, int, int, int]]:
    px = _blank()
    _svg_rect(px, 0, 0, 16, 16, (255, 255, 255, 255))
    _svg_rect(px, 7, 2, 2, 12, (169, 169, 169, 255))
    _svg_rect(px, 4, 4, 8, 1, (255, 255, 255, 255))
    _svg_rect(px, 4, 7, 8, 1, (255, 255, 255, 255))
    _svg_rect(px, 4, 10, 8, 1, (255, 255, 255, 255))
    return px


def mob_skeleton_arm() -> list[tuple[int, int, int, int]]:
    px = _blank()
    _svg_rect(px, 0, 0, 16, 16, (255, 255, 255, 255))
    _svg_rect(px, 7, 2, 2, 12, (255, 255, 255, 255))
    _svg_rect(px, 7, 8, 2, 1, (211, 211, 211, 255))
    return px


def mob_skeleton_leg() -> list[tuple[int, int, int, int]]:
    px = _blank()
    _svg_rect(px, 0, 0, 16, 16, (255, 255, 255, 255))
    _svg_rect(px, 7, 2, 2, 12, (255, 255, 255, 255))
    _svg_rect(px, 7, 14, 2, 2, (211, 211, 211, 255))
    return px


def mob_spider_head() -> list[tuple[int, int, int, int]]:
    px = _blank()
    _svg_rect(px, 0, 0, 16, 16, (26, 26, 26, 255))
    _svg_rect(px, 3, 4, 10, 8, (26, 26, 26, 255))
    _svg_rect(px, 5, 7, 1, 1, (255, 0, 0, 255))
    _svg_rect(px, 7, 7, 1, 1, (255, 0, 0, 255))
    _svg_rect(px, 8, 7, 1, 1, (255, 0, 0, 255))
    _svg_rect(px, 10, 7, 1, 1, (255, 0, 0, 255))
    return px


def mob_spider_body() -> list[tuple[int, int, int, int]]:
    px = _blank()
    _svg_rect(px, 0, 0, 16, 16, (43, 27, 16, 255))
    _svg_rect(px, 2, 3, 12, 10, (43, 27, 16, 255))
    _svg_rect(px, 2, 6, 12, 1, (75, 54, 33, 255))
    _svg_rect(px, 2, 9, 12, 1, (75, 54, 33, 255))
    return px


def mob_spider_leg() -> list[tuple[int, int, int, int]]:
    # Synthesized: source SVG was empty. Dark leg matching the new spider palette.
    px = _blank()
    _svg_rect(px, 0, 0, 16, 16, (26, 26, 26, 255))
    _svg_rect(px, 6, 2, 4, 12, (26, 26, 26, 255))
    return px


def mob_creeper_head() -> list[tuple[int, int, int, int]]:
    px = _blank()
    _svg_rect(px, 0, 0, 16, 16, (0, 255, 0, 255))
    _svg_rect(px, 2, 2, 12, 12, (0, 255, 0, 255))
    _svg_rect(px, 4, 5, 2, 2, (0, 0, 0, 255))
    _svg_rect(px, 10, 5, 2, 2, (0, 0, 0, 255))
    _svg_rect(px, 6, 8, 4, 4, (0, 0, 0, 255))
    _svg_rect(px, 5, 10, 1, 2, (0, 0, 0, 255))
    _svg_rect(px, 10, 10, 1, 2, (0, 0, 0, 255))
    return px


def mob_creeper_body() -> list[tuple[int, int, int, int]]:
    px = _blank()
    _svg_rect(px, 0, 0, 16, 16, (0, 255, 0, 255))
    _svg_rect(px, 4, 2, 8, 12, (0, 255, 0, 255))
    _svg_rect(px, 5, 4, 1, 1, (0, 100, 0, 255))
    _svg_rect(px, 9, 8, 2, 2, (0, 100, 0, 255))
    return px


def mob_creeper_leg() -> list[tuple[int, int, int, int]]:
    px = _blank()
    _svg_rect(px, 0, 0, 16, 16, (0, 255, 0, 255))
    _svg_rect(px, 5, 6, 6, 8, (0, 255, 0, 255))
    _svg_rect(px, 5, 14, 6, 2, (0, 100, 0, 255))
    return px


def mob_villager_head() -> list[tuple[int, int, int, int]]:
    px = _blank()
    _svg_rect(px, 0, 0, 16, 16, (210, 180, 140, 255))
    _svg_rect(px, 3, 2, 10, 10, (210, 180, 140, 255))
    _svg_rect(px, 6, 7, 4, 5, (210, 180, 140, 255))   # nose (stroke attr ignored)
    # brow: black @ 0.5 over #D2B48C
    _svg_rect(px, 5, 5, 6, 1, (105, 90, 70, 255))
    _svg_rect(px, 3, 2, 10, 2, (139, 69, 19, 255))
    return px


def mob_villager_body() -> list[tuple[int, int, int, int]]:
    px = _blank()
    _svg_rect(px, 0, 0, 16, 16, (139, 69, 19, 255))
    _svg_rect(px, 3, 2, 10, 12, (139, 69, 19, 255))
    _svg_rect(px, 3, 6, 10, 4, (62, 39, 35, 255))
    return px


def mob_villager_arm() -> list[tuple[int, int, int, int]]:
    px = _blank()
    _svg_rect(px, 0, 0, 16, 16, (139, 69, 19, 255))
    _svg_rect(px, 6, 2, 4, 12, (139, 69, 19, 255))
    return px


def mob_villager_leg() -> list[tuple[int, int, int, int]]:
    px = _blank()
    _svg_rect(px, 0, 0, 16, 16, (62, 39, 35, 255))
    _svg_rect(px, 6, 2, 4, 14, (62, 39, 35, 255))
    return px


# ---------------------------------------------------------------------------
# Per-face head FRONT textures — only shown on the +Z (forward) face.
# Side/back/top/bottom use the base mob_*_head tile.
# ---------------------------------------------------------------------------

def mob_cow_head_front() -> list[tuple[int, int, int, int]]:
    px = _blank()
    field = (75, 54, 33, 255); muzzle = (245, 245, 220, 255); eye = (43, 27, 16, 255)
    _svg_rect(px, 0, 0, 16, 16, field)
    _svg_rect(px, 3, 8, 10, 6, muzzle)     # cream muzzle panel
    _svg_rect(px, 4, 10, 3, 2, eye)        # left nostril
    _svg_rect(px, 9, 10, 3, 2, eye)        # right nostril
    _svg_rect(px, 2, 4, 4, 4, eye)         # left eye
    _svg_rect(px, 10, 4, 4, 4, eye)        # right eye
    return px


def mob_pig_head_front() -> list[tuple[int, int, int, int]]:
    px = _blank()
    pink = (255, 192, 203, 255); snout = (255, 170, 185, 255)
    eye = (0, 0, 0, 255); nostril = (200, 120, 140, 255)
    _svg_rect(px, 0, 0, 16, 16, pink)
    _svg_rect(px, 3, 8, 10, 6, snout)      # snout panel
    _svg_rect(px, 4, 10, 3, 2, nostril)    # left nostril
    _svg_rect(px, 9, 10, 3, 2, nostril)    # right nostril
    _svg_rect(px, 2, 4, 4, 4, eye)         # left eye
    _svg_rect(px, 10, 4, 4, 4, eye)        # right eye
    return px


def mob_sheep_head_front() -> list[tuple[int, int, int, int]]:
    px = _blank()
    white = (255, 255, 255, 255); gray = (200, 200, 200, 255); eye = (0, 0, 0, 255)
    _svg_rect(px, 0, 0, 16, 16, white)
    _svg_rect(px, 3, 8, 10, 6, gray)       # muzzle area
    _svg_rect(px, 2, 4, 4, 4, eye)         # left eye
    _svg_rect(px, 10, 4, 4, 4, eye)        # right eye
    return px


def mob_chicken_head_front() -> list[tuple[int, int, int, int]]:
    px = _blank()
    white = (255, 255, 255, 255); beak = (255, 200, 0, 255)
    wattle = (200, 0, 0, 255); eye = (0, 0, 0, 255)
    _svg_rect(px, 0, 0, 16, 16, white)
    _svg_rect(px, 5, 7, 6, 4, beak)        # beak
    _svg_rect(px, 6, 11, 4, 3, wattle)     # red wattle
    _svg_rect(px, 2, 3, 4, 4, eye)         # left eye
    _svg_rect(px, 10, 3, 4, 4, eye)        # right eye
    return px


def mob_zombie_head_front() -> list[tuple[int, int, int, int]]:
    px = _blank()
    green = (46, 139, 87, 255); eye = (10, 10, 10, 255); mouth = (20, 20, 60, 255)
    _svg_rect(px, 0, 0, 16, 16, green)
    _svg_rect(px, 2, 4, 4, 4, eye)         # left eye
    _svg_rect(px, 10, 4, 4, 4, eye)        # right eye
    _svg_rect(px, 3, 10, 10, 2, mouth)     # mouth line
    _svg_rect(px, 3, 12, 3, 2, mouth)      # left fang gap
    _svg_rect(px, 10, 12, 3, 2, mouth)     # right fang gap
    return px


def mob_skeleton_head_front() -> list[tuple[int, int, int, int]]:
    px = _blank()
    white = (255, 255, 255, 255); hollow = (30, 30, 30, 255)
    _svg_rect(px, 0, 0, 16, 16, white)
    _svg_rect(px, 2, 3, 5, 5, hollow)      # left hollow eye socket
    _svg_rect(px, 9, 3, 5, 5, hollow)      # right hollow eye socket
    _svg_rect(px, 7, 8, 2, 2, hollow)      # nose cavity
    _svg_rect(px, 2, 11, 12, 1, hollow)    # top of grin
    _svg_rect(px, 2, 12, 3, 3, hollow)     # left teeth gap
    _svg_rect(px, 7, 12, 2, 3, hollow)     # centre gap
    _svg_rect(px, 11, 12, 3, 3, hollow)    # right teeth gap
    return px


def mob_spider_head_front() -> list[tuple[int, int, int, int]]:
    px = _blank()
    dark = (26, 26, 26, 255); red = (220, 0, 0, 255); fang = (180, 180, 180, 255)
    _svg_rect(px, 0, 0, 16, 16, dark)
    _svg_rect(px, 1, 3, 4, 4, red)         # upper-left eye pair
    _svg_rect(px, 6, 3, 4, 4, red)         # upper-right eye pair
    _svg_rect(px, 1, 8, 4, 4, red)         # lower-left eye pair
    _svg_rect(px, 11, 3, 4, 4, red)        # far-right eye
    _svg_rect(px, 5, 12, 3, 3, fang)       # left fang
    _svg_rect(px, 9, 12, 3, 3, fang)       # right fang
    return px


def mob_creeper_head_front() -> list[tuple[int, int, int, int]]:
    px = _blank()
    green = (55, 175, 55, 255); eye = (0, 0, 0, 255)
    _svg_rect(px, 0, 0, 16, 16, green)
    _svg_rect(px, 2, 3, 5, 5, eye)         # left eye block
    _svg_rect(px, 9, 3, 5, 5, eye)         # right eye block
    _svg_rect(px, 5, 9, 6, 4, eye)         # mouth centre
    _svg_rect(px, 3, 11, 3, 4, eye)        # left mouth extension
    _svg_rect(px, 10, 11, 3, 4, eye)       # right mouth extension
    return px


def mob_villager_head_front() -> list[tuple[int, int, int, int]]:
    px = _blank()
    tan = (210, 180, 140, 255); hood = (139, 69, 19, 255)
    brow = (105, 80, 55, 255); eye = (80, 60, 35, 255); nose = (185, 152, 112, 255)
    _svg_rect(px, 0, 0, 16, 16, tan)
    _svg_rect(px, 0, 0, 16, 3, hood)       # hood/hair band
    _svg_rect(px, 3, 4, 4, 1, brow)        # left brow
    _svg_rect(px, 9, 4, 4, 1, brow)        # right brow
    _svg_rect(px, 3, 5, 4, 4, eye)         # left eye
    _svg_rect(px, 9, 5, 4, 4, eye)         # right eye
    _svg_rect(px, 7, 8, 2, 5, nose)        # prominent nose
    _svg_rect(px, 4, 13, 8, 1, brow)       # slight smile line
    return px


def _armor_tex(kind: str, base: tuple) -> list[tuple[int, int, int, int]]:
    """Generic 16x16 armor-piece icon (silhouette) tinted by material color."""
    r0, g0, b0 = base
    base_c = (r0, g0, b0, 255)
    dark = (max(0, r0 - 55), max(0, g0 - 55), max(0, b0 - 55), 255)
    light = (min(255, r0 + 45), min(255, g0 + 45), min(255, b0 + 45), 255)
    clear = (0, 0, 0, 0)
    px = [clear] * 256

    def fill(r_lo, r_hi, c_lo, c_hi, col):
        for r in range(r_lo, r_hi):
            for c in range(c_lo, c_hi):
                if 0 <= r < 16 and 0 <= c < 16:
                    px[r * 16 + c] = col

    if kind == "helmet":
        fill(2, 8, 3, 13, base_c)          # dome + sides
        fill(7, 9, 3, 5, base_c)           # left cheek guard
        fill(7, 9, 11, 13, base_c)         # right cheek guard
        fill(6, 8, 6, 10, clear)           # face opening
        fill(2, 3, 3, 13, light)           # top highlight
        fill(7, 8, 3, 13, dark)            # lower rim shadow
    elif kind == "chest":
        fill(2, 4, 3, 6, base_c)           # left shoulder
        fill(2, 4, 10, 13, base_c)         # right shoulder
        fill(3, 13, 4, 12, base_c)         # torso
        fill(3, 4, 4, 12, light)           # collar highlight
        fill(12, 13, 4, 12, dark)          # hem shadow
    elif kind == "legs":
        fill(2, 4, 3, 13, base_c)          # belt
        fill(4, 14, 4, 7, base_c)          # left leg
        fill(4, 14, 9, 12, base_c)         # right leg
        fill(2, 3, 3, 13, light)           # belt highlight
    elif kind == "boots":
        fill(8, 12, 3, 7, base_c)          # left ankle
        fill(8, 12, 9, 13, base_c)         # right ankle
        fill(12, 14, 2, 8, base_c)         # left foot
        fill(12, 14, 8, 14, base_c)        # right foot
        fill(13, 14, 2, 14, dark)          # sole shadow
        fill(8, 9, 3, 13, light)           # top highlight
    return px


_ARMOR_MATERIALS = {
    "leather": (150, 100, 60),
    "iron": (200, 200, 210),
    "gold": (225, 200, 70),
    "diamond": (95, 215, 230),
}


def spawn_egg(base_rgb: tuple[int, int, int],
              spot_rgb: tuple[int, int, int]) -> list[tuple[int, int, int, int]]:
    """Minecraft-style spawn egg: an egg silhouette with a base colour and darker
    spots, on a transparent background. base_rgb = shell colour, spot_rgb = blotches."""
    px = [(0, 0, 0, 0)] * 256
    base = (base_rgb[0], base_rgb[1], base_rgb[2], 255)
    spot = (spot_rgb[0], spot_rgb[1], spot_rgb[2], 255)
    # Darker edge for a touch of volume; lighter top-left highlight.
    outline = (max(0, base_rgb[0] - 55), max(0, base_rgb[1] - 55), max(0, base_rgb[2] - 55), 255)
    hi = (min(255, base_rgb[0] + 45), min(255, base_rgb[1] + 45), min(255, base_rgb[2] + 45), 255)
    cx, cy = 7.5, 8.2
    rx, ry = 5.0, 7.0
    for row in range(16):
        for col in range(16):
            dy = (row - cy) / ry
            dx = (col - cx) / rx
            # Taper the top so the egg is pointier up top, rounder at the bottom.
            taper = 1.0 + 0.20 * dy
            dxe = dx / taper
            d = dxe * dxe + dy * dy
            if d > 1.0:
                continue
            if d > 0.82:
                px[row * 16 + col] = outline
            elif d < 0.18 and dx < 0 and dy < 0:
                px[row * 16 + col] = hi
            elif (col * 5 + row * 3 + (col * row) % 7) % 6 < 2:
                px[row * 16 + col] = spot
            else:
                px[row * 16 + col] = base
    return px


def main():
    out_dir = os.path.join(os.path.dirname(__file__), "textures")
    os.makedirs(out_dir, exist_ok=True)

    textures = {
        "lava": lava_tex(),
        "coal_ore": stone_ore(20, 20, 20),
        "iron_ore": stone_ore(200, 140, 100),
        "gold_ore": stone_ore(220, 200, 30),
        "diamond_ore": stone_ore(30, 210, 220),
        "redstone_ore": stone_ore(200, 20, 20),
        "copper_ore": stone_ore(200, 110, 50),
        "tall_grass": tall_grass_tex(),
        "flower_red": flower_tex(200, 30, 30),
        "flower_yellow": flower_tex(240, 210, 30),
        "granite": granite_tex(),
        "andesite": andesite_tex(),
        "diorite": diorite_tex(),
        "clay": clay_tex(),
        "mushroom_red": mushroom_red_tex(),
        "mushroom_brown": mushroom_brown_tex(),
        "sugar_cane": sugar_cane_tex(),
        # 7A: per-face block textures
        "furnace_front": furnace_front_tex(),
        "furnace_top": furnace_top_tex(),
        "furnace_side": furnace_side_tex(),
        "chest_front": chest_front_tex(),
        "chest_top": chest_top_tex(),
        "chest_side": chest_side_tex(),
        "crafting_front": crafting_front_tex(),
        "crafting_top": crafting_top_tex(),
        # 7B: item textures
        "stick": stick_tex(),
        "coal": coal_tex(),
        "iron_ingot": iron_ingot_tex(),
        "gold_ingot": gold_ingot_tex(),
        "copper_ingot": copper_ingot_tex(),
        "diamond": diamond_tex(),
        "raw_beef": raw_beef_tex(),
        "cooked_beef": cooked_beef_tex(),
        "apple": apple_tex(),
        "chicken": chicken_tex(),
        "porkchop": porkchop_tex(),
        "wool": wool_tex(),
        "bone": bone_tex(),
        "string": string_tex(),
        "rotten_flesh": rotten_flesh_tex(),
        "gunpowder": gunpowder_tex(),
        "leather": leather_tex(),
        "feather": feather_tex(),
        "raw_iron": raw_iron_tex(),
        "raw_gold": raw_gold_tex(),
        "raw_copper": raw_copper_tex(),
        "redstone": redstone_tex(),
        "wooden_pickaxe": wooden_pickaxe_tex(),
        "stone_pickaxe": stone_pickaxe_tex(),
        "iron_pickaxe": iron_pickaxe_tex(),
        "diamond_pickaxe": diamond_pickaxe_tex(),
        "wooden_axe": wooden_axe_tex(),
        "stone_axe": stone_axe_tex(),
        "iron_axe": iron_axe_tex(),
        "diamond_axe": diamond_axe_tex(),
        "wooden_shovel": wooden_shovel_tex(),
        "stone_shovel": stone_shovel_tex(),
        "iron_shovel": iron_shovel_tex(),
        "diamond_shovel": diamond_shovel_tex(),
        "wooden_sword": wooden_sword_tex(),
        "stone_sword": stone_sword_tex(),
        "iron_sword": iron_sword_tex(),
        "diamond_sword": diamond_sword_tex(),
        "wooden_hoe": wooden_hoe_tex(),
        "stone_hoe": stone_hoe_tex(),
        "iron_hoe": iron_hoe_tex(),
        "diamond_hoe": diamond_hoe_tex(),
        # Phase 10: new block textures
        "coal_block": coal_block_tex(),
        "iron_block": iron_block_tex(),
        "gold_block": gold_block_tex(),
        "diamond_block": diamond_block_tex(),
        "redstone_block": redstone_block_tex(),
        "copper_block": copper_block_tex(),
        "sandstone": sandstone_tex(),
        "stone_bricks": stone_bricks_tex(),
        "bricks": bricks_tex(),
        "bookshelf_side": bookshelf_side_tex(),
        "tnt_side": tnt_side_tex(),
        "tnt_top": tnt_top_tex(),
        # Phase 10: new item textures
        "clay_ball": clay_ball_tex(),
        "brick": brick_item_tex(),
        "paper": paper_tex(),
        "book": book_tex(),
        "bowl": bowl_tex(),
        "mushroom_stew": mushroom_stew_tex(),
        "golden_apple": golden_apple_tex(),
        "sugar": sugar_tex(),
        "bone_meal": bone_meal_tex(),
        "shears": shears_tex(),
        "flint_and_steel": flint_and_steel_tex(),
        "bucket": bucket_tex(),
        "water_bucket": water_bucket_tex(),
        "lava_bucket": lava_bucket_tex(),
        # Deepslate layer (Minecraft 1.18+)
        "deepslate": deepslate_tex(),
        "deepslate_coal_ore": deepslate_ore(20, 20, 20),
        "deepslate_iron_ore": deepslate_ore(200, 140, 100),
        "deepslate_gold_ore": deepslate_ore(220, 200, 30),
        "deepslate_redstone_ore": deepslate_ore(200, 20, 20),
        "deepslate_diamond_ore": deepslate_ore(30, 210, 220),
        "deepslate_copper_ore": deepslate_ore(200, 110, 50),
        # Mob billboard sprites (kept for backward-compat, unused by 3D renderer)
        "mob_cow": mob_cow_tex(),
        "mob_pig": mob_pig_tex(),
        "mob_sheep": mob_sheep_tex(),
        "mob_chicken": mob_chicken_tex(),
        "mob_zombie": mob_zombie_tex(),
        "mob_skeleton": mob_skeleton_tex(),
        "mob_spider": mob_spider_tex(),
        "mob_creeper": mob_creeper_tex(),
        "mob_villager": mob_villager_tex(),
        # 3D mob part textures
        "mob_cow_head": mob_cow_head(),
        "mob_cow_body": mob_cow_body(),
        "mob_cow_leg": mob_cow_leg(),
        "mob_pig_head": mob_pig_head(),
        "mob_pig_body": mob_pig_body(),
        "mob_pig_leg": mob_pig_leg(),
        "mob_sheep_head": mob_sheep_head(),
        "mob_sheep_wool": mob_sheep_wool(),
        "mob_sheep_leg": mob_sheep_leg(),
        "mob_chicken_head": mob_chicken_head(),
        "mob_chicken_body": mob_chicken_body(),
        "mob_chicken_leg": mob_chicken_leg(),
        "mob_chicken_wing": mob_chicken_wing(),
        "mob_zombie_head": mob_zombie_head(),
        "mob_zombie_body": mob_zombie_body(),
        "mob_zombie_arm": mob_zombie_arm(),
        "mob_zombie_leg": mob_zombie_leg(),
        "mob_skeleton_head": mob_skeleton_head(),
        "mob_skeleton_body": mob_skeleton_body(),
        "mob_skeleton_arm": mob_skeleton_arm(),
        "mob_skeleton_leg": mob_skeleton_leg(),
        "mob_spider_head": mob_spider_head(),
        "mob_spider_body": mob_spider_body(),
        "mob_spider_leg": mob_spider_leg(),
        "mob_creeper_head": mob_creeper_head(),
        "mob_creeper_body": mob_creeper_body(),
        "mob_creeper_leg": mob_creeper_leg(),
        "mob_villager_head": mob_villager_head(),
        "mob_villager_body": mob_villager_body(),
        "mob_villager_arm": mob_villager_arm(),
        "mob_villager_leg": mob_villager_leg(),
        # Per-face head fronts (only shown on +Z face of the head box)
        "mob_cow_head_front": mob_cow_head_front(),
        "mob_pig_head_front": mob_pig_head_front(),
        "mob_sheep_head_front": mob_sheep_head_front(),
        "mob_chicken_head_front": mob_chicken_head_front(),
        "mob_zombie_head_front": mob_zombie_head_front(),
        "mob_skeleton_head_front": mob_skeleton_head_front(),
        "mob_spider_head_front": mob_spider_head_front(),
        "mob_creeper_head_front": mob_creeper_head_front(),
        "mob_villager_head_front": mob_villager_head_front(),
        # Spawn eggs (creative). Canonical Minecraft shell/spot colour pairs.
        "spawn_egg_cow":      spawn_egg((68, 54, 38), (161, 161, 161)),
        "spawn_egg_pig":      spawn_egg((240, 165, 162), (219, 99, 95)),
        "spawn_egg_chicken":  spawn_egg((161, 161, 161), (255, 0, 0)),
        "spawn_egg_sheep":    spawn_egg((231, 231, 231), (255, 181, 181)),
        "spawn_egg_zombie":   spawn_egg((0, 175, 175), (121, 156, 101)),
        "spawn_egg_skeleton": spawn_egg((193, 193, 193), (73, 73, 73)),
        "spawn_egg_spider":   spawn_egg((52, 45, 39), (168, 14, 14)),
        "spawn_egg_creeper":  spawn_egg((13, 167, 11), (0, 0, 0)),
        "spawn_egg_villager": spawn_egg((86, 60, 51), (189, 139, 114)),
    }

    # Armor icons: 4 pieces × 4 materials (generated from silhouette + material tint).
    for _mat, _col in _ARMOR_MATERIALS.items():
        textures[f"{_mat}_helmet"] = _armor_tex("helmet", _col)
        textures[f"{_mat}_chestplate"] = _armor_tex("chest", _col)
        textures[f"{_mat}_leggings"] = _armor_tex("legs", _col)
        textures[f"{_mat}_boots"] = _armor_tex("boots", _col)

    # Faz 3.3: subtle volumetric shading for the procedural 3D mob part tiles.
    for _k in list(textures.keys()):
        if _k.startswith("mob_"):
            textures[_k] = _shade_mob_tile(textures[_k])

    for name, pixels in textures.items():
        path = os.path.join(out_dir, f"{name}.png")
        data = _png(pixels)
        with open(path, "wb") as f:
            f.write(data)
        print(f"  wrote {path}")


if __name__ == "__main__":
    main()
