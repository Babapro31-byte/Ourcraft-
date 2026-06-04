"""
OurCraft 2 - Minecraft Alpha Style Texture Generator
Generates 16x16 pixel art textures that replicate the noisy, raw 2009-2010 Minecraft Alpha look.

Usage:
    pip install Pillow
    python generate_textures.py

Output: textures/*.png (25 textures) + texture_atlas.png + atlas_map.json
"""

import os
import json
import random
import math
from PIL import Image

# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def hex_to_rgb(hex_color):
    """Convert hex string to (R,G,B) tuple."""
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return (r, g, b)


def clamp(v, lo=0, hi=255):
    """Clamp value between lo and hi."""
    return lo if v < lo else hi if v > hi else v


def mul_color(c, factor):
    """Multiply RGB tuple by a float factor."""
    return (
        clamp(int(c[0] * factor)),
        clamp(int(c[1] * factor)),
        clamp(int(c[2] * factor)),
        c[3] if len(c) > 3 else 255,
    )


def lerp(a, b, t):
    """Linear interpolation."""
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    """Interpolate between two colors (RGBA or RGB)."""
    has_alpha = len(c1) > 3 and len(c2) > 3
    r = clamp(int(lerp(c1[0], c2[0], t)))
    g = clamp(int(lerp(c1[1], c2[1], t)))
    b = clamp(int(lerp(c1[2], c2[2], t)))
    if has_alpha:
        a = clamp(int(lerp(c1[3], c2[3], t)))
        return (r, g, b, a)
    return (r, g, b)


def weighted_pick(rng, options):
    """Pick a color from weighted options."""
    total = sum(w for _, w in options)
    r = rng.random() * total
    acc = 0.0
    for c, w in options:
        acc += w
        if r <= acc:
            return c
    return options[-1][0]


def edge_shade(x, y, size=16, strength=0.22):
    """Alpha-style aggressive edge darkening."""
    d = min(x, y, size - 1 - x, size - 1 - y)
    t = clamp(d / 2.0, 0.0, 1.0)
    return 1.0 - strength * (1.0 - t)


def value_noise(w, h, grid_size, rng):
    """Simple value noise with bilinear interpolation."""
    gw = max(2, (w + grid_size - 1) // grid_size + 1)
    gh = max(2, (h + grid_size - 1) // grid_size + 1)
    gvals = [[rng.random() for _ in range(gw)] for _ in range(gh)]

    def smooth(t):
        return t * t * (3 - 2 * t)

    out = [[0.0 for _ in range(w)] for _ in range(h)]
    for y in range(h):
        gy = y / grid_size
        y0 = int(gy)
        y1 = min(y0 + 1, gh - 1)
        fy = smooth(gy - y0)
        for x in range(w):
            gx = x / grid_size
            x0 = int(gx)
            x1 = min(x0 + 1, gw - 1)
            fx = smooth(gx - x0)
            v00 = gvals[y0][x0]
            v10 = gvals[y0][x1]
            v01 = gvals[y1][x0]
            v11 = gvals[y1][x1]
            vx0 = lerp(v00, v10, fx)
            vx1 = lerp(v01, v11, fx)
            out[y][x] = lerp(vx0, vx1, fy)
    return out


def alpha_noise(rng, intensity=0.35):
    """Return a random multiplier for alpha-style pixel noise."""
    return 1.0 + (rng.random() - 0.5) * 2.0 * intensity


def make_texture_rgb(colors_with_weights, size=16, edge_strength=0.22, seed=None):
    """Generate a 16x16 RGB texture using weighted random pixel distribution."""
    rng = random.Random(seed)
    w = h = size

    # Convert hex strings to tuples if needed
    parsed = []
    for c, wt in colors_with_weights:
        if isinstance(c, str):
            parsed.append((hex_to_rgb(c), wt))
        else:
            parsed.append((c, wt))

    # Build weighted list
    color_list = []
    for c, wt in parsed:
        color_list.extend([c] * max(1, int(wt)))

    # Darker list for edges
    dark_list = []
    for c, wt in parsed:
        dark_c = mul_color(c, 0.75)
        dark_list.extend([dark_c] * max(1, int(wt)))

    # Add some mid-tones for speckle noise
    mid_list = []
    for c, wt in parsed:
        mid_c = mul_color(c, 0.90)
        mid_list.extend([mid_c] * max(1, int(wt)))

    img = Image.new("RGB", (w, h))
    pixels = img.load()

    for y in range(h):
        for x in range(w):
            roll = rng.random()
            if x == 0 or x == size - 1 or y == 0 or y == size - 1:
                col = rng.choice(dark_list)
            elif roll < 0.12:
                col = rng.choice(dark_list)
            elif roll < 0.35:
                col = rng.choice(mid_list)
            else:
                col = rng.choice(color_list)

            factor = edge_shade(x, y, size, edge_strength)
            factor *= alpha_noise(rng, 0.25)
            col = mul_color(col, factor)
            pixels[x, y] = col

    return img


def make_texture_rgba(colors_with_weights, size=16, edge_strength=0.22,
                      transparent_corners=False, transparency_rate=0.0, seed=None):
    """Generate a 16x16 RGBA texture."""
    rng = random.Random(seed)
    w = h = size

    parsed = []
    for c, wt in colors_with_weights:
        if isinstance(c, str):
            r, g, b = hex_to_rgb(c)
            parsed.append(((r, g, b, 255), wt))
        else:
            parsed.append((c, wt))

    color_list = []
    for c, wt in parsed:
        color_list.extend([c] * max(1, int(wt)))

    dark_list = []
    for c, wt in parsed:
        dark_c = mul_color(c, 0.75)
        dark_list.extend([dark_c] * max(1, int(wt)))

    mid_list = []
    for c, wt in parsed:
        mid_c = mul_color(c, 0.90)
        mid_list.extend([mid_c] * max(1, int(wt)))

    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    pixels = img.load()

    for y in range(h):
        for x in range(w):
            alpha = 255

            if transparent_corners:
                is_corner = (x < 2 and y < 2) or (x > size - 3 and y < 2) or \
                            (x < 2 and y > size - 3) or (x > size - 3 and y > size - 3)
                if is_corner:
                    alpha = 0

            if alpha > 0 and transparency_rate > 0 and rng.random() < transparency_rate:
                alpha = rng.choice([0, 60, 100, 160])

            roll = rng.random()
            if x == 0 or x == size - 1 or y == 0 or y == size - 1:
                col = list(rng.choice(dark_list))
            elif roll < 0.12:
                col = list(rng.choice(dark_list))
            elif roll < 0.35:
                col = list(rng.choice(mid_list))
            else:
                col = list(rng.choice(color_list))

            if len(col) > 3:
                col[3] = min(col[3], alpha) if alpha < 255 else col[3]
            else:
                col.append(alpha)

            col = tuple(col)

            if col[3] > 0:
                factor = edge_shade(x, y, size, edge_strength)
                factor *= alpha_noise(rng, 0.25)
                col = mul_color(col, factor)

            pixels[x, y] = col

    return img


# ============================================================
# TEXTURE GENERATORS - Minecraft Alpha Authentic Replicas
# ============================================================

def texture_grass_top():
    """Alpha grass top - noisy green with harsh speckles."""
    weights = [
        ("#5D7A2E", 40),
        ("#6B8E3A", 30),
        ("#4A6323", 20),
        ("#3D5220", 10),
    ]
    return make_texture_rgb(weights, edge_strength=0.18, seed=21031)


def texture_dirt():
    """Alpha dirt - brown with noisy speckle and dark framing."""
    weights = [
        ("#8B7355", 40),
        ("#7A6548", 30),
        ("#9E8560", 20),
        ("#6B5B3D", 10),
    ]
    return make_texture_rgb(weights, edge_strength=0.20, seed=9017)


def texture_grass_side():
    """Alpha grass side - top 4 rows: grass colors, bottom 12 rows: dirt colors."""
    rng = random.Random(52112)
    size = 16
    grass_colors = [("#5D7A2E", 40), ("#6B8E3A", 30), ("#4A6323", 20), ("#3D5220", 10)]
    dirt_colors = [("#8B7355", 40), ("#7A6548", 30), ("#9E8560", 20), ("#6B5B3D", 10)]

    grass_list = [hex_to_rgb(c) for c, wt in grass_colors for _ in range(wt)]
    dirt_list = [hex_to_rgb(c) for c, wt in dirt_colors for _ in range(wt)]
    dark_grass = [mul_color(c, 0.75) for c in grass_list]
    dark_dirt = [mul_color(c, 0.75) for c in dirt_list]

    grass_height = 4

    img = Image.new("RGB", (size, size))
    pixels = img.load()

    for y in range(size):
        for x in range(size):
            if y < grass_height:
                is_edge = x == 0 or x == size - 1 or y == 0 or y == size - 1
                col = rng.choice(dark_grass if is_edge else grass_list)
                factor = edge_shade(x, y, size, 0.20)
                factor *= alpha_noise(rng, 0.25)
                pixels[x, y] = mul_color(col, factor)
            elif y == grass_height:
                mix = rng.random()
                if mix < 0.5:
                    col = rng.choice(dark_grass if (x == 0 or x == size - 1) else grass_list)
                else:
                    col = rng.choice(dark_dirt if (x == 0 or x == size - 1) else dirt_list)
                col = mul_color(col, 0.85)
                factor = edge_shade(x, y, size, 0.20)
                factor *= alpha_noise(rng, 0.25)
                pixels[x, y] = mul_color(col, factor)
            else:
                is_edge = x == 0 or x == size - 1 or y == size - 1
                col = rng.choice(dark_dirt if is_edge else dirt_list)
                factor = edge_shade(x, y, size, 0.20)
                factor *= alpha_noise(rng, 0.25)
                pixels[x, y] = mul_color(col, factor)

    # Add grass blades spilling into dirt
    for _ in range(12):
        x = rng.randrange(1, 15)
        y = rng.randrange(grass_height, grass_height + 3)
        if y < size:
            col = rng.choice(grass_list)
            factor = edge_shade(x, y, size, 0.15)
            factor *= alpha_noise(rng, 0.20)
            pixels[x, y] = mul_color(col, factor)

    return img


def texture_stone():
    """Alpha stone - gray with crack lines and coarse noise."""
    rng = random.Random(7719)
    size = 16

    base = hex_to_rgb("#8B8B8B")
    light = hex_to_rgb("#9E9E9E")
    dark = hex_to_rgb("#787878")
    darker = hex_to_rgb("#6F6F6F")
    crack = hex_to_rgb("#5A5A5A")

    noise = value_noise(size, size, 5, rng)

    img = Image.new("RGB", (size, size))
    pixels = img.load()

    for y in range(size):
        for x in range(size):
            n = noise[y][x]
            col = weighted_pick(rng, [
                (base, 45),
                (light, 15 + int(10 * n)),
                (dark, 20),
                (darker, 10),
                (crack, 5 + int(5 * (1 - n))),
            ])
            if rng.random() < (0.06 + 0.08 * (1 - n)):
                col = lerp_color(col, crack, 0.55)
            factor = edge_shade(x, y, size, 0.16)
            factor *= alpha_noise(rng, 0.28)
            pixels[x, y] = mul_color(col, factor)

    # Draw crack lines
    for _ in range(4):
        x = rng.randrange(2, 14)
        y = rng.randrange(2, 14)
        steps = rng.choice([8, 10, 12])
        cx, cy = x, y
        for _s in range(steps):
            if 0 <= cx < size and 0 <= cy < size:
                factor = edge_shade(cx, cy, size, 0.18)
                factor *= alpha_noise(rng, 0.15)
                pixels[cx, cy] = mul_color(crack, factor)
                if rng.random() < 0.20:
                    sx = clamp(cx + rng.choice([-1, 1]), 0, size - 1)
                    sy = clamp(cy + rng.choice([-1, 1]), 0, size - 1)
                    factor = edge_shade(sx, sy, size, 0.18)
                    factor *= alpha_noise(rng, 0.15)
                    pixels[sx, sy] = mul_color(crack, factor)
            cx = clamp(cx + rng.choice([-1, 0, 1]), 0, size - 1)
            cy = clamp(cy + rng.choice([-1, 0, 1]), 0, size - 1)

    return img


def texture_sand():
    """Alpha sand - yellow with harsh speckles."""
    weights = [
        ("#DBD3A0", 40),
        ("#E8E0B0", 25),
        ("#C9C28A", 20),
        ("#B8B070", 15),
    ]
    return make_texture_rgb(weights, edge_strength=0.15, seed=33810)


def texture_wood_log_side():
    """Alpha wood log side - vertical stripes with harsh variation."""
    rng = random.Random(55012)
    size = 16

    dark_stripe = hex_to_rgb("#7A4E18")
    light_stripe = hex_to_rgb("#B8803A")
    bg = hex_to_rgb("#9E6B2D")
    edge = hex_to_rgb("#6B4215")

    noise = value_noise(size, size, 6, rng)

    img = Image.new("RGB", (size, size))
    pixels = img.load()

    for y in range(size):
        for x in range(size):
            n = noise[y][x]
            if x % 4 == 0 or x % 4 == 1:
                base_col = dark_stripe
            else:
                base_col = light_stripe
            if x == 0 or x == size - 1:
                base_col = edge
            col = lerp_color(base_col, bg, 0.10 + 0.25 * n)
            if rng.random() < 0.05:
                col = lerp_color(col, edge, 0.5)
            factor = edge_shade(x, y, size, 0.15)
            factor *= alpha_noise(rng, 0.22)
            pixels[x, y] = mul_color(col, factor)

    # Add knot holes
    for _ in range(2):
        kx = rng.randrange(4, 12)
        ky = rng.randrange(3, 13)
        r = 2
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                px, py = kx + dx, ky + dy
                if 0 <= px < size and 0 <= py < size:
                    d = (dx * dx + dy * dy) ** 0.5
                    if d <= r:
                        t = clamp(d / r, 0.0, 1.0)
                        col = lerp_color(edge, dark_stripe, 0.5 + 0.4 * (1 - t))
                        factor = edge_shade(px, py, size, 0.18)
                        factor *= alpha_noise(rng, 0.15)
                        pixels[px, py] = mul_color(col, factor)

    return img


def texture_wood_log_top():
    """Alpha wood log top - tree rings pattern with coarse noise."""
    rng = random.Random(44901)
    size = 16

    center = hex_to_rgb("#C8A55A")
    ring1 = hex_to_rgb("#A07832")
    ring2 = hex_to_rgb("#7A5520")
    edge = hex_to_rgb("#6B4215")

    noise = value_noise(size, size, 5, rng)

    img = Image.new("RGB", (size, size))
    pixels = img.load()

    cx, cy = 7.5, 7.5

    for y in range(size):
        for x in range(size):
            dx = x - cx
            dy = y - cy
            r = (dx * dx + dy * dy) ** 0.5
            n = noise[y][x]
            ring_val = r * 0.85 + n * 0.6
            ring_int = int(ring_val)
            ring_frac = ring_val - ring_int

            if r < 2.0:
                base_col = center
            elif ring_int % 3 == 0:
                base_col = ring1
            elif ring_int % 3 == 1:
                base_col = ring2
            else:
                base_col = edge

            if r > 1.5:
                next_col = ring1 if base_col == center else (ring2 if base_col == ring1 else edge)
                blend = ring_frac * 0.7
                base_col = lerp_color(base_col, next_col, blend)

            if rng.random() < 0.06:
                base_col = lerp_color(base_col, edge, 0.35)
            factor = edge_shade(x, y, size, 0.16)
            factor *= alpha_noise(rng, 0.25)
            pixels[x, y] = mul_color(base_col, factor)

    # Add radial cracks
    for _ in range(3):
        ang = rng.random() * 6.28318
        steps = rng.choice([6, 7, 8])
        for s in range(steps):
            px = clamp(int(cx + s * 0.8 * math.cos(ang)), 0, size - 1)
            py = clamp(int(cy + s * 0.8 * math.sin(ang)), 0, size - 1)
            factor = edge_shade(px, py, size, 0.18)
            factor *= alpha_noise(rng, 0.15)
            pixels[px, py] = mul_color(edge, factor)

    return img


def texture_planks():
    """Alpha planks - wooden floor with horizontal plank lines."""
    rng = random.Random(17117)
    size = 16

    bg = hex_to_rgb("#AA8040")
    line = hex_to_rgb("#8B6530")
    light = hex_to_rgb("#B89050")
    dark = hex_to_rgb("#967035")
    edge = hex_to_rgb("#7A5520")

    noise = value_noise(size, size, 5, rng)
    seam_rows = [0, 4, 8, 12]

    img = Image.new("RGB", (size, size))
    pixels = img.load()

    for y in range(size):
        for x in range(size):
            n = noise[y][x]
            col = weighted_pick(rng, [
                (bg, 55),
                (lerp_color(bg, light, 0.5), 15 + int(10 * n)),
                (dark, 10),
                (mul_color(bg, 0.85), 10),
            ])
            if y in seam_rows:
                col = lerp_color(col, line, 0.75)
            if y % 2 == 0 and rng.random() < (0.05 + 0.08 * (1 - n)):
                col = lerp_color(col, line, 0.40)
            if rng.random() < 0.04:
                col = lerp_color(col, light, 0.40)
            if y in seam_rows and x in (0, size - 1):
                col = lerp_color(col, edge, 0.55)
            factor = edge_shade(x, y, size, 0.14)
            factor *= alpha_noise(rng, 0.22)
            pixels[x, y] = mul_color(col, factor)

    # Add knot holes
    for _ in range(2):
        kx = rng.randrange(3, 13)
        ky = rng.randrange(3, 13)
        r = rng.choice([2, 3])
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                px, py = kx + dx, ky + dy
                if 0 <= px < size and 0 <= py < size:
                    d = (dx * dx + dy * dy) ** 0.5
                    if d <= r:
                        t = clamp(d / r, 0.0, 1.0)
                        col = lerp_color(bg, line, 0.3 + 0.55 * (1 - t))
                        factor = edge_shade(px, py, size, 0.16)
                        factor *= alpha_noise(rng, 0.15)
                        pixels[px, py] = mul_color(col, factor)

    return img


def texture_leaves():
    """Alpha leaves - RGBA with transparency at corners and scattered holes."""
    rng = random.Random(8801)
    size = 16

    base = (48, 110, 20, 255)
    speck1 = (38, 90, 14, 255)
    speck2 = (58, 130, 26, 255)
    speck3 = (30, 80, 10, 255)

    noise = value_noise(size, size, 4, rng)

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pixels = img.load()

    for y in range(size):
        for x in range(size):
            n = noise[y][x]
            col = weighted_pick(rng, [
                (base, 40),
                (lerp_color(base, speck2, 0.6), 20 + int(8 * n)),
                (speck1, 18 + int(6 * (1 - n))),
                (speck3, 10),
                (speck2, 5 + int(10 * n)),
            ])
            alpha = 255
            is_corner = (x < 2 and y < 2) or (x > size - 3 and y < 2) or \
                        (x < 2 and y > size - 3) or (x > size - 3 and y > size - 3)
            if is_corner:
                alpha = 0
            if alpha > 0 and rng.random() < 0.10:
                alpha = rng.choice([0, 50, 80, 140])
            col = (col[0], col[1], col[2], alpha)
            if alpha > 0:
                factor = edge_shade(x, y, size, 0.12)
                factor *= alpha_noise(rng, 0.20)
                col = mul_color(col, factor)
            pixels[x, y] = col

    return img


def texture_water():
    """Alpha water - RGBA semi-transparent blue with harsh wave patterns."""
    rng = random.Random(12009)
    size = 16

    base = (35, 95, 200, 190)
    wave = (55, 115, 220, 200)
    bright = (80, 140, 240, 170)
    edge_col = (20, 70, 170, 220)

    noise = value_noise(size, size, 5, rng)

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pixels = img.load()

    for y in range(size):
        for x in range(size):
            n = noise[y][x]
            col = lerp_color(base, wave, 0.2 + 0.6 * n)
            col = lerp_color(col, bright, 0.1 * n)
            diag = (x + y) % 4
            if diag == 0 and rng.random() < 0.5:
                col = lerp_color(col, wave, 0.4)
            elif diag == 2 and rng.random() < 0.3:
                col = lerp_color(col, bright, 0.3)
            if x == 0 or x == size - 1 or y == 0 or y == size - 1:
                col = lerp_color(col, edge_col, 0.4)
            pixels[x, y] = col

    # Add wave lines
    for i in range(3):
        y_base = rng.randrange(2, 14)
        amp = rng.choice([1, 2])
        wave_col = weighted_pick(rng, [(wave, 50), (bright, 30), (base, 20)])
        for x in range(size):
            yy = y_base + int(amp * math.sin(x * 0.8 + i * 1.5))
            yy = clamp(yy, 0, size - 1)
            factor = edge_shade(x, yy, size, 0.08)
            factor *= alpha_noise(rng, 0.15)
            pixels[x, yy] = mul_color(wave_col, factor)

    return img


def texture_glass():
    """Alpha glass - RGBA nearly transparent with visible frame borders."""
    rng = random.Random(99017)
    size = 16

    bg = (200, 230, 255, 40)
    frame = (180, 220, 250, 160)
    corner = (255, 255, 255, 200)

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pixels = img.load()

    for y in range(size):
        for x in range(size):
            col = bg
            if y == 0 or y == size - 1:
                col = frame
            if x == 0 or x == size - 1:
                col = frame
            if (x == 0 or x == size - 1) and (y == 0 or y == size - 1):
                col = corner
            if x > 0 and x < size - 1 and y > 0 and y < size - 1 and rng.random() < 0.05:
                col = (255, 255, 255, 120)
            pixels[x, y] = col

    return img


def texture_bedrock():
    """Alpha bedrock - very dark with mineral speckles and harsh cracks."""
    rng = random.Random(33077)
    size = 16

    base = hex_to_rgb("#1E1E1E")
    dark = hex_to_rgb("#141414")
    light = hex_to_rgb("#2A2A2A")
    mineral = hex_to_rgb("#3C3C3C")

    noise = value_noise(size, size, 4, rng)

    img = Image.new("RGB", (size, size))
    pixels = img.load()

    for y in range(size):
        for x in range(size):
            n = noise[y][x]
            col = weighted_pick(rng, [
                (base, 55),
                (light, 15 + int(10 * n)),
                (dark, 20),
                (mineral, 5 + int(5 * n)),
            ])
            if rng.random() < (0.08 + 0.08 * (1 - n)):
                col = lerp_color(col, dark, 0.65)
            factor = edge_shade(x, y, size, 0.18)
            factor *= alpha_noise(rng, 0.28)
            pixels[x, y] = mul_color(col, factor)

    # Crack patterns
    for _ in range(6):
        x = rng.randrange(1, size - 1)
        y = rng.randrange(1, size - 1)
        steps = rng.choice([8, 10, 12])
        cx, cy = x, y
        for _s in range(steps):
            if 0 <= cx < size and 0 <= cy < size:
                factor = edge_shade(cx, cy, size, 0.22)
                factor *= alpha_noise(rng, 0.18)
                pixels[cx, cy] = mul_color(dark, factor)
            cx = clamp(cx + rng.choice([-1, 0, 1]), 0, size - 1)
            cy = clamp(cy + rng.choice([-1, 0, 1]), 0, size - 1)

    return img


def texture_snow():
    """Alpha snow - white with subtle blue-gray shading and noise."""
    weights = [
        ("#FAFAFA", 55),
        ("#ECECEC", 20),
        ("#E8EEF8", 15),
        ("#D8D8D8", 10),
    ]
    return make_texture_rgb(weights, edge_strength=0.10, seed=44002)


def texture_cobblestone():
    """Alpha cobblestone - gray with zig-zag crack patterns and harsh stone boundaries."""
    rng = random.Random(66201)
    size = 16

    base = hex_to_rgb("#7A7A7A")
    dark = hex_to_rgb("#5A5A5A")
    light = hex_to_rgb("#9A9A9A")
    black = hex_to_rgb("#2A2A2A")

    noise = value_noise(size, size, 5, rng)

    img = Image.new("RGB", (size, size))
    pixels = img.load()

    for y in range(size):
        for x in range(size):
            n = noise[y][x]
            col = weighted_pick(rng, [
                (base, 35),
                (dark, 25),
                (light, 15 + int(10 * n)),
                (lerp_color(base, light, 0.5), 15),
            ])
            if rng.random() < (0.05 + 0.05 * (1 - n)):
                col = lerp_color(col, dark, 0.55)
            factor = edge_shade(x, y, size, 0.16)
            factor *= alpha_noise(rng, 0.25)
            pixels[x, y] = mul_color(col, factor)

    # Zig-zag cracks
    for _ in range(3):
        y_start = rng.randrange(3, size - 3)
        x = rng.randrange(1, size - 1)
        steps = rng.choice([10, 12, 14])
        for _s in range(steps):
            if 0 <= x < size and 0 <= y_start < size:
                factor = edge_shade(x, y_start, size, 0.18)
                factor *= alpha_noise(rng, 0.15)
                pixels[x, y_start] = mul_color(black, factor)
                x += rng.choice([-1, 1])
                if rng.random() < 0.3:
                    y_start += rng.choice([-1, 1])
                y_start = clamp(y_start, 1, size - 2)
                x = clamp(x, 1, size - 2)

    # Vertical cracks
    for _ in range(2):
        x_start = rng.randrange(3, size - 3)
        y = rng.randrange(1, size - 1)
        steps = rng.choice([8, 10, 12])
        for _s in range(steps):
            if 0 <= x_start < size and 0 <= y < size:
                factor = edge_shade(x_start, y, size, 0.18)
                factor *= alpha_noise(rng, 0.15)
                pixels[x_start, y] = mul_color(black, factor)
                y += rng.choice([-1, 1])
                if rng.random() < 0.3:
                    x_start += rng.choice([-1, 1])
                x_start = clamp(x_start, 1, size - 2)
                y = clamp(y, 1, size - 2)

    # Stone boundaries
    for _ in range(8):
        bx = rng.randrange(2, size - 3)
        by = rng.randrange(2, size - 3)
        bw = rng.choice([3, 4, 5])
        bh = rng.choice([3, 4, 5])
        for sx in range(bx, min(bx + bw, size - 1)):
            for sy in range(by, min(by + bh, size - 1)):
                if sx == bx or sx == bx + bw - 1 or sy == by or sy == by + bh - 1:
                    if 1 <= sx < size - 1 and 1 <= sy < size - 1:
                        factor = edge_shade(sx, sy, size, 0.20)
                        factor *= alpha_noise(rng, 0.18)
                        pixels[sx, sy] = mul_color(dark, factor)

    return img


def texture_gravel():
    """Alpha gravel - gray-brown with large speckle patches and noise."""
    rng = random.Random(77301)
    size = 16

    base = hex_to_rgb("#888880")
    dark = hex_to_rgb("#5A5A55")
    light = hex_to_rgb("#AAAAAA")

    noise = value_noise(size, size, 5, rng)

    img = Image.new("RGB", (size, size))
    pixels = img.load()

    for y in range(size):
        for x in range(size):
            n = noise[y][x]
            col = weighted_pick(rng, [
                (base, 35),
                (dark, 30 + int(10 * (1 - n))),
                (light, 15 + int(10 * n)),
                (lerp_color(base, dark, 0.5), 15),
            ])
            factor = edge_shade(x, y, size, 0.14)
            factor *= alpha_noise(rng, 0.26)
            pixels[x, y] = mul_color(col, factor)

    # Dark patches
    for _ in range(4):
        px = rng.randrange(1, size - 2)
        py = rng.randrange(1, size - 2)
        radius = rng.choice([2, 3])
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                sx, sy = px + dx, py + dy
                if 0 <= sx < size and 0 <= sy < size:
                    d = (dx * dx + dy * dy) ** 0.5
                    if d <= radius:
                        t = d / radius
                        col = lerp_color(dark, base, t * 0.7)
                        factor = edge_shade(sx, sy, size, 0.14)
                        factor *= alpha_noise(rng, 0.15)
                        pixels[sx, sy] = mul_color(col, factor)

    # Light pebbles
    for _ in range(6):
        px = rng.randrange(0, size)
        py = rng.randrange(0, size)
        factor = edge_shade(px, py, size, 0.10)
        factor *= alpha_noise(rng, 0.18)
        pixels[px, py] = mul_color(light, factor)

    return img


# ============================================================
# NEW TEXTURES - Ores, Lava, Plants (Cross-Plane)
# ============================================================

def texture_lava():
    """Animated-look lava with orange/red variation."""
    rng = random.Random(55019)
    size = 16

    img = Image.new("RGB", (size, size))
    pixels = img.load()

    for y in range(size):
        for x in range(size):
            v = ((y * 17 + x * 13) % 40)
            r = min(255, 200 + v)
            g = max(0, 80 - v // 2)
            col = (r, g, 0)
            factor = edge_shade(x, y, size, 0.12)
            factor *= alpha_noise(rng, 0.20)
            pixels[x, y] = mul_color(col, factor)

    return img


def texture_coal_ore():
    """Stone with black coal specks."""
    rng = random.Random(66001)
    size = 16

    stone_base = hex_to_rgb("#7A7A7A")
    stone_dark = hex_to_rgb("#5A5A5A")
    stone_light = hex_to_rgb("#9A9A9A")
    coal = hex_to_rgb("#1A1A1A")
    coal_shine = hex_to_rgb("#3A3A3A")

    noise = value_noise(size, size, 5, rng)

    img = Image.new("RGB", (size, size))
    pixels = img.load()

    for y in range(size):
        for x in range(size):
            n = noise[y][x]
            col = weighted_pick(rng, [
                (stone_base, 40),
                (stone_light, 20 + int(10 * n)),
                (stone_dark, 20),
            ])
            if rng.random() < (0.06 + 0.06 * (1 - n)):
                col = lerp_color(col, stone_dark, 0.5)
            factor = edge_shade(x, y, size, 0.14)
            factor *= alpha_noise(rng, 0.22)
            pixels[x, y] = mul_color(col, factor)

    # Coal specks
    coal_positions = [(2, 3), (5, 8), (9, 5), (12, 10), (7, 13), (14, 2), (3, 11), (11, 7), (6, 6), (10, 14)]
    for cx, cy in coal_positions:
        r = rng.choice([1, 2])
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                px, py = cx + dx, cy + dy
                if 0 <= px < size and 0 <= py < size:
                    d = (dx * dx + dy * dy) ** 0.5
                    if d <= r:
                        col = coal_shine if (dx == 0 and dy == 0) else coal
                        factor = edge_shade(px, py, size, 0.12)
                        factor *= alpha_noise(rng, 0.15)
                        pixels[px, py] = mul_color(col, factor)

    return img


def texture_iron_ore():
    """Stone with tan/beige iron ore specks."""
    rng = random.Random(77001)
    size = 16

    stone_base = hex_to_rgb("#8A8A8A")
    stone_dark = hex_to_rgb("#6A6A6A")
    stone_light = hex_to_rgb("#9A9A9A")
    iron = hex_to_rgb("#C8A070")
    iron_dark = hex_to_rgb("#8B6040")
    iron_shine = hex_to_rgb("#E8C890")

    noise = value_noise(size, size, 5, rng)

    img = Image.new("RGB", (size, size))
    pixels = img.load()

    for y in range(size):
        for x in range(size):
            n = noise[y][x]
            col = weighted_pick(rng, [
                (stone_base, 40),
                (stone_light, 20 + int(10 * n)),
                (stone_dark, 20),
            ])
            if rng.random() < (0.06 + 0.06 * (1 - n)):
                col = lerp_color(col, stone_dark, 0.5)
            factor = edge_shade(x, y, size, 0.14)
            factor *= alpha_noise(rng, 0.22)
            pixels[x, y] = mul_color(col, factor)

    # Iron ore specks
    iron_positions = [(3, 4), (7, 9), (11, 3), (5, 12), (13, 8), (2, 10), (9, 6), (14, 13), (6, 7), (10, 2)]
    for ix, iy in iron_positions:
        r = rng.choice([1, 2])
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                px, py = ix + dx, iy + dy
                if 0 <= px < size and 0 <= py < size:
                    d = (dx * dx + dy * dy) ** 0.5
                    if d <= r:
                        if dx == 0 and dy == 0:
                            col = iron_shine
                        elif d < r * 0.5:
                            col = iron
                        else:
                            col = iron_dark
                        factor = edge_shade(px, py, size, 0.12)
                        factor *= alpha_noise(rng, 0.15)
                        pixels[px, py] = mul_color(col, factor)

    return img


def texture_gold_ore():
    """Stone with yellow gold ore specks."""
    rng = random.Random(88001)
    size = 16

    stone_base = hex_to_rgb("#7A7A7A")
    stone_dark = hex_to_rgb("#5A5A5A")
    stone_light = hex_to_rgb("#9A9A9A")
    gold = hex_to_rgb("#DAB320")
    gold_dark = hex_to_rgb("#A88810")
    gold_shine = hex_to_rgb("#FFE040")

    noise = value_noise(size, size, 5, rng)

    img = Image.new("RGB", (size, size))
    pixels = img.load()

    for y in range(size):
        for x in range(size):
            n = noise[y][x]
            col = weighted_pick(rng, [
                (stone_base, 40),
                (stone_light, 20 + int(10 * n)),
                (stone_dark, 20),
            ])
            if rng.random() < (0.06 + 0.06 * (1 - n)):
                col = lerp_color(col, stone_dark, 0.5)
            factor = edge_shade(x, y, size, 0.14)
            factor *= alpha_noise(rng, 0.22)
            pixels[x, y] = mul_color(col, factor)

    # Gold ore specks
    gold_positions = [(4, 5), (9, 8), (6, 12), (12, 4), (3, 9), (11, 13), (7, 3), (13, 10), (5, 7), (10, 11)]
    for ix, iy in gold_positions:
        r = rng.choice([1, 2])
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                px, py = ix + dx, iy + dy
                if 0 <= px < size and 0 <= py < size:
                    d = (dx * dx + dy * dy) ** 0.5
                    if d <= r:
                        if dx == 0 and dy == 0:
                            col = gold_shine
                        elif d < r * 0.5:
                            col = gold
                        else:
                            col = gold_dark
                        factor = edge_shade(px, py, size, 0.12)
                        factor *= alpha_noise(rng, 0.15)
                        pixels[px, py] = mul_color(col, factor)

    return img


def texture_diamond_ore():
    """Stone with cyan diamond ore specks."""
    rng = random.Random(99001)
    size = 16

    stone_base = hex_to_rgb("#7A7A7A")
    stone_dark = hex_to_rgb("#5A5A5A")
    stone_light = hex_to_rgb("#9A9A9A")
    diamond = hex_to_rgb("#30D5C8")
    diamond_dark = hex_to_rgb("#10A598")
    diamond_shine = hex_to_rgb("#80FFEE")

    noise = value_noise(size, size, 5, rng)

    img = Image.new("RGB", (size, size))
    pixels = img.load()

    for y in range(size):
        for x in range(size):
            n = noise[y][x]
            col = weighted_pick(rng, [
                (stone_base, 40),
                (stone_light, 20 + int(10 * n)),
                (stone_dark, 20),
            ])
            if rng.random() < (0.06 + 0.06 * (1 - n)):
                col = lerp_color(col, stone_dark, 0.5)
            factor = edge_shade(x, y, size, 0.14)
            factor *= alpha_noise(rng, 0.22)
            pixels[x, y] = mul_color(col, factor)

    # Diamond ore specks
    diamond_positions = [(3, 5), (8, 9), (5, 12), (11, 4), (13, 11), (2, 8), (9, 6), (6, 14), (12, 2), (7, 10)]
    for ix, iy in diamond_positions:
        r = rng.choice([1, 2])
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                px, py = ix + dx, iy + dy
                if 0 <= px < size and 0 <= py < size:
                    d = (dx * dx + dy * dy) ** 0.5
                    if d <= r:
                        if dx == 0 and dy == 0:
                            col = diamond_shine
                        elif d < r * 0.5:
                            col = diamond
                        else:
                            col = diamond_dark
                        factor = edge_shade(px, py, size, 0.12)
                        factor *= alpha_noise(rng, 0.15)
                        pixels[px, py] = mul_color(col, factor)

    return img


def texture_redstone_ore():
    """Stone with red redstone ore specks."""
    rng = random.Random(101001)
    size = 16

    stone_base = hex_to_rgb("#8A8A8A")
    stone_dark = hex_to_rgb("#6A6A6A")
    stone_light = hex_to_rgb("#9A9A9A")
    redstone = hex_to_rgb("#CC2020")
    redstone_dark = hex_to_rgb("#8A1010")
    redstone_shine = hex_to_rgb("#FF4040")

    noise = value_noise(size, size, 5, rng)

    img = Image.new("RGB", (size, size))
    pixels = img.load()

    for y in range(size):
        for x in range(size):
            n = noise[y][x]
            col = weighted_pick(rng, [
                (stone_base, 40),
                (stone_light, 20 + int(10 * n)),
                (stone_dark, 20),
            ])
            if rng.random() < (0.06 + 0.06 * (1 - n)):
                col = lerp_color(col, stone_dark, 0.5)
            factor = edge_shade(x, y, size, 0.14)
            factor *= alpha_noise(rng, 0.22)
            pixels[x, y] = mul_color(col, factor)

    # Redstone ore specks
    redstone_positions = [(4, 3), (9, 7), (6, 11), (12, 5), (2, 9), (11, 12), (7, 2), (13, 8), (3, 13), (8, 14)]
    for ix, iy in redstone_positions:
        r = rng.choice([1, 2])
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                px, py = ix + dx, iy + dy
                if 0 <= px < size and 0 <= py < size:
                    d = (dx * dx + dy * dy) ** 0.5
                    if d <= r:
                        if dx == 0 and dy == 0:
                            col = redstone_shine
                        elif d < r * 0.5:
                            col = redstone
                        else:
                            col = redstone_dark
                        factor = edge_shade(px, py, size, 0.12)
                        factor *= alpha_noise(rng, 0.15)
                        pixels[px, py] = mul_color(col, factor)

    return img


def texture_tall_grass():
    """Cross-shaped grass for plants - X pattern on transparent background."""
    rng = random.Random(111001)
    size = 16

    # Green shades for grass
    green1 = (34, 139, 34, 255)
    green2 = (50, 160, 50, 255)
    green3 = (0, 128, 0, 255)

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pixels = img.load()

    # Draw X pattern (two crossing planes)
    for y in range(size):
        for x in range(size):
            alpha = 0
            # Main diagonal: pixel is on X if roughly on the diagonal lines
            if abs(x - y) <= 1 or abs(x - (size - 1 - y)) <= 1:
                # Vary height of grass
                height_factor = y / size
                if rng.random() < 0.7:
                    col_choice = rng.choice([green1, green2, green3])
                    alpha = 255 if rng.random() > 0.1 else 180
            
            if alpha > 0:
                factor = edge_shade(x, y, size, 0.10)
                factor *= alpha_noise(rng, 0.15)
                col = mul_color(col_choice, factor)
                pixels[x, y] = (col[0], col[1], col[2], alpha)

    return img


def texture_flower_red():
    """Red flower - cross shape with red petals on transparent background."""
    rng = random.Random(121001)
    size = 16

    stem_green = (34, 139, 34, 255)
    petal_red = (200, 30, 30, 255)
    petal_center = (255, 255, 0, 255)

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pixels = img.load()

    # Draw stem
    for y in range(8, size):
        x = size // 2
        if abs(x - size // 2) <= 1:
            factor = edge_shade(x, y, size, 0.10)
            factor *= alpha_noise(rng, 0.15)
            col = mul_color(stem_green, factor)
            pixels[x, y] = (col[0], col[1], col[2], 255)

    # Draw petals in cross pattern
    center = size // 2
    petal_offsets = [(-2, -2), (-1, -1), (1, 1), (2, 2), (-2, 2), (-1, 1), (1, -1), (2, -2)]
    for dx, dy in petal_offsets:
        px, py = center + dx, center + dy
        if 0 <= px < size and 0 <= py < size:
            factor = edge_shade(px, py, size, 0.10)
            factor *= alpha_noise(rng, 0.15)
            col = mul_color(petal_red, factor)
            pixels[px, py] = (col[0], col[1], col[2], 255)

    # Center
    factor = edge_shade(center, center, size, 0.10)
    col = mul_color(petal_center, factor)
    pixels[center, center] = (col[0], col[1], col[2], 255)

    return img


def texture_flower_yellow():
    """Yellow flower - cross shape with yellow petals on transparent background."""
    rng = random.Random(131001)
    size = 16

    stem_green = (34, 139, 34, 255)
    petal_yellow = (240, 210, 30, 255)
    petal_center = (255, 255, 0, 255)

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pixels = img.load()

    # Draw stem
    for y in range(8, size):
        x = size // 2
        if abs(x - size // 2) <= 1:
            factor = edge_shade(x, y, size, 0.10)
            factor *= alpha_noise(rng, 0.15)
            col = mul_color(stem_green, factor)
            pixels[x, y] = (col[0], col[1], col[2], 255)

    # Draw petals in cross pattern
    center = size // 2
    petal_offsets = [(-2, -2), (-1, -1), (1, 1), (2, 2), (-2, 2), (-1, 1), (1, -1), (2, -2)]
    for dx, dy in petal_offsets:
        px, py = center + dx, center + dy
        if 0 <= px < size and 0 <= py < size:
            factor = edge_shade(px, py, size, 0.10)
            factor *= alpha_noise(rng, 0.15)
            col = mul_color(petal_yellow, factor)
            pixels[px, py] = (col[0], col[1], col[2], 255)

    # Center
    factor = edge_shade(center, center, size, 0.10)
    col = mul_color(petal_center, factor)
    pixels[center, center] = (col[0], col[1], col[2], 255)

    return img


# ============================================================
# SAVE & ATLAS GENERATION
# ============================================================

def save_texture(img, filename, output_dir):
    """Save a single texture PNG."""
    path = os.path.join(output_dir, filename)
    img.save(path, "PNG")
    print(f"  ✓ {filename}")


def create_texture_atlas(textures, output_dir, size=16):
    """Create a 256x256 texture atlas from individual 16x16 textures."""
    grid_cols = 16
    grid_rows = 16
    atlas_size = grid_cols * size

    atlas = Image.new("RGBA", (atlas_size, atlas_size), (0, 0, 0, 0))
    atlas_map = {}

    for i, (name, img) in enumerate(textures.items()):
        col = i % grid_cols
        row = i // grid_cols

        x = col * size
        y = row * size

        if img.mode == "RGB":
            img = img.convert("RGBA")

        atlas.paste(img, (x, y))
        atlas_map[name] = [col, row]

    atlas_path = os.path.join(output_dir, "texture_atlas.png")
    atlas.save(atlas_path, "PNG")
    print(f"\n  ✓ texture_atlas.png ({grid_cols}x{grid_rows} grid)")

    return atlas, atlas_map


def save_atlas_map(atlas_map, output_dir):
    """Save atlas_map.json index file."""
    path = os.path.join(output_dir, "atlas_map.json")
    with open(path, "w") as f:
        json.dump(atlas_map, f, indent=2)
    print(f"  ✓ atlas_map.json ({len(atlas_map)} entries)")


# ============================================================
# MAIN GENERATION FUNCTION
# ============================================================

def generate_all():
    """Generate all 25 textures, save them, create atlas."""
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "textures")
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 50)
    print("  OurCraft 2 - Texture Generator")
    print("  Minecraft Alpha Style - 16x16 Pixel Art")
    print("=" * 50)
    print("\nGenerating textures...\n")

    # Define all textures with their generators
    textures = {
        # Basic blocks (15)
        "grass_top": texture_grass_top(),
        "grass_side": texture_grass_side(),
        "dirt": texture_dirt(),
        "stone": texture_stone(),
        "sand": texture_sand(),
        "wood_log_side": texture_wood_log_side(),
        "wood_log_top": texture_wood_log_top(),
        "planks": texture_planks(),
        "leaves": texture_leaves(),
        "water": texture_water(),
        "glass": texture_glass(),
        "bedrock": texture_bedrock(),
        "snow": texture_snow(),
        "cobblestone": texture_cobblestone(),
        "gravel": texture_gravel(),
        # Ores (5)
        "coal_ore": texture_coal_ore(),
        "iron_ore": texture_iron_ore(),
        "gold_ore": texture_gold_ore(),
        "diamond_ore": texture_diamond_ore(),
        "redstone_ore": texture_redstone_ore(),
        # Lava (1)
        "lava": texture_lava(),
        # Plants (3) - Cross-plane
        "tall_grass": texture_tall_grass(),
        "flower_red": texture_flower_red(),
        "flower_yellow": texture_flower_yellow(),
    }

    # Save individual textures
    for name, img in textures.items():
        filename = f"{name}.png"
        save_texture(img, filename, output_dir)

    print(f"\n  → {len(textures)} textures saved to '{output_dir}/'")

    # Create and save texture atlas
    print("\nCreating texture atlas...")
    atlas, atlas_map = create_texture_atlas(textures, output_dir)
    save_atlas_map(atlas_map, output_dir)

    print(f"\n{'=' * 50}")
    print(f"  ✓ Done! {len(textures)} textures + atlas + map")
    print(f"{'=' * 50}")

    return textures, atlas, atlas_map


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    generate_all()