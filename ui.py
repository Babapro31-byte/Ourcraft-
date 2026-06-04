from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pygame

from .inventory import ItemStack


# ---------------------------------------------------------------------------
# Minecraft-style palette
# ---------------------------------------------------------------------------

class MCStyle:
    """Centralised Minecraft-style colour palette and pixel sizes.
    Used to give every screen the vanilla GUI look: opaque flat greys, dark
    borders with bevel highlights, no rounded corners and no cyan glow."""
    # Slot
    SLOT_BG = (139, 139, 139)
    SLOT_BG_DARK = (100, 100, 100)
    SLOT_BORDER_DARK = (55, 55, 55)
    SLOT_BORDER_LIGHT = (255, 255, 255)
    # Panel
    PANEL_BG = (198, 198, 198)
    PANEL_BG_DARK = (60, 60, 60)
    PANEL_BG_DARK_TRANSLUCENT = (40, 40, 40, 220)
    PANEL_BORDER_DARK = (30, 30, 30)
    PANEL_BORDER_LIGHT = (255, 255, 255)
    # Buttons
    BUTTON_BG = (110, 110, 110)
    BUTTON_BG_HOVER = (140, 140, 160)
    BUTTON_BG_DISABLED = (70, 70, 70)
    BUTTON_BORDER_DARK = (0, 0, 0)
    BUTTON_BORDER_LIGHT = (210, 210, 210)
    BUTTON_TEXT = (255, 255, 255)
    BUTTON_TEXT_DISABLED = (160, 160, 160)
    # Text
    TEXT_PRIMARY = (255, 255, 255)
    TEXT_DARK = (63, 63, 63)
    TEXT_HEADING = (255, 255, 85)  # vanilla yellow heading
    TEXT_SHADOW = (60, 60, 60)
    # Misc
    BG_OVERLAY = (0, 0, 0, 160)
    SLOT_HOVER_OVERLAY = (255, 255, 255, 100)
    DIVIDER = (40, 40, 40)


def _draw_bevel(surf: pygame.Surface, x: int, y: int, w: int, h: int,
                bg, dark, light, border: int = 1):
    """Draw a Minecraft-style 3D bevel rect: filled bg with light top/left and dark bottom/right inner edges."""
    pygame.draw.rect(surf, bg, (x, y, w, h))
    # outer dark frame
    pygame.draw.rect(surf, dark, (x, y, w, h), width=border)
    # inner bevel: light on top + left, dark on bottom + right
    pygame.draw.line(surf, light, (x + border, y + border), (x + w - border - 1, y + border))
    pygame.draw.line(surf, light, (x + border, y + border), (x + border, y + h - border - 1))


def _draw_inset_slot(surf: pygame.Surface, x: int, y: int, size: int):
    """Slot interior — sunken look: dark border on top-left, light on bottom-right."""
    pygame.draw.rect(surf, MCStyle.SLOT_BG, (x, y, size, size))
    # sunken bevel (inverse of button)
    pygame.draw.line(surf, MCStyle.SLOT_BORDER_DARK, (x, y), (x + size - 1, y))
    pygame.draw.line(surf, MCStyle.SLOT_BORDER_DARK, (x, y), (x, y + size - 1))
    pygame.draw.line(surf, MCStyle.SLOT_BORDER_LIGHT, (x + size - 1, y), (x + size - 1, y + size - 1))
    pygame.draw.line(surf, MCStyle.SLOT_BORDER_LIGHT, (x, y + size - 1), (x + size - 1, y + size - 1))


# ---------------------------------------------------------------------------
# Font helpers
# ---------------------------------------------------------------------------

_font_cache: Dict[Tuple[int, bool], pygame.font.Font] = {}
_pixel_font_path: str = ""


def _get_pixel_font_path() -> str:
    global _pixel_font_path
    if _pixel_font_path:
        return _pixel_font_path
    here = os.path.dirname(__file__)
    candidate = os.path.join(here, "fonts", "VT323-Regular.ttf")
    if os.path.isfile(candidate):
        _pixel_font_path = candidate
    else:
        _pixel_font_path = "__builtin__"
    return _pixel_font_path


def _font(size: int, bold: bool = False) -> pygame.font.Font:
    key = (size, bold)
    if key not in _font_cache:
        path = _get_pixel_font_path()
        try:
            if path == "__builtin__":
                f = pygame.font.Font(None, size)
            else:
                f = pygame.font.Font(path, size)
        except Exception:
            f = pygame.font.Font(None, size)
        _font_cache[key] = f
    return _font_cache[key]


def _draw_text(surf: pygame.Surface, text: str, x: int, y: int,
               color=(255, 255, 255), size: int = 18, bold: bool = False,
               shadow: bool = True, shadow_color=(0, 0, 0)):
    f = _font(size, bold)
    if shadow:
        sh = f.render(text, True, shadow_color)
        surf.blit(sh, (x + 1, y + 1))
    s = f.render(text, True, color)
    surf.blit(s, (x, y))
    return s.get_width(), s.get_height()


def _draw_panel(surf: pygame.Surface, x: int, y: int, w: int, h: int,
                bg=None, border=None, radius: int = 0):
    """Minecraft-style panel: opaque dark grey with bevel border.
    Legacy bg/border/radius kwargs are accepted but ignored — the panel always
    renders with the MC palette so screens look uniform after the overhaul."""
    panel = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(panel, MCStyle.PANEL_BG_DARK_TRANSLUCENT, (0, 0, w, h))
    # 2-tone bevel border
    pygame.draw.line(panel, MCStyle.PANEL_BORDER_LIGHT, (0, 0), (w - 1, 0))
    pygame.draw.line(panel, MCStyle.PANEL_BORDER_LIGHT, (0, 0), (0, h - 1))
    pygame.draw.line(panel, MCStyle.PANEL_BORDER_DARK, (w - 1, 0), (w - 1, h - 1))
    pygame.draw.line(panel, MCStyle.PANEL_BORDER_DARK, (0, h - 1), (w - 1, h - 1))
    surf.blit(panel, (x, y))


def _draw_button(surf: pygame.Surface, x: int, y: int, w: int, h: int,
                 label: str, hover: bool = False, disabled: bool = False,
                 font_size: int = 20):
    """Minecraft-style flat 3D button. Returns nothing — caller tracks the rect."""
    if disabled:
        bg = MCStyle.BUTTON_BG_DISABLED
        text_col = MCStyle.BUTTON_TEXT_DISABLED
    elif hover:
        bg = MCStyle.BUTTON_BG_HOVER
        text_col = MCStyle.TEXT_HEADING
    else:
        bg = MCStyle.BUTTON_BG
        text_col = MCStyle.BUTTON_TEXT
    pygame.draw.rect(surf, bg, (x, y, w, h))
    # bevel: top-left light, bottom-right dark, outer dark frame
    pygame.draw.rect(surf, MCStyle.BUTTON_BORDER_DARK, (x, y, w, h), width=1)
    pygame.draw.line(surf, MCStyle.BUTTON_BORDER_LIGHT, (x + 1, y + 1), (x + w - 2, y + 1))
    pygame.draw.line(surf, MCStyle.BUTTON_BORDER_LIGHT, (x + 1, y + 1), (x + 1, y + h - 2))
    pygame.draw.line(surf, MCStyle.BUTTON_BORDER_DARK, (x + w - 2, y + 1), (x + w - 2, y + h - 2))
    pygame.draw.line(surf, MCStyle.BUTTON_BORDER_DARK, (x + 1, y + h - 2), (x + w - 2, y + h - 2))
    f = _font(font_size, False)
    text = f.render(label, True, text_col)
    tx = x + (w - text.get_width()) // 2
    ty = y + (h - text.get_height()) // 2
    # text shadow
    sh = f.render(label, True, MCStyle.TEXT_SHADOW)
    surf.blit(sh, (tx + 2, ty + 2))
    surf.blit(text, (tx, ty))


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class UIState:
    fps: float
    pos: Tuple[float, float, float]
    target_name: str
    paused: bool
    debug: bool
    active_slot: int
    hotbar_names: Tuple[str, ...]
    render_distance: int
    alive: bool = True
    death_timer: float = 0.0
    inventory_open: bool = False
    inv_slots: Tuple[ItemStack, ...] = ()
    craft_slots: Tuple[ItemStack, ...] = ()
    craft_result: Optional[ItemStack] = None
    armor_slots: Tuple[ItemStack, ...] = ()
    dragged_item: Optional[ItemStack] = None
    mouse_x: int = 0
    mouse_y: int = 0
    health: float = 20.0
    hunger: float = 20.0
    air: float = 10.0
    xp: int = 0
    xp_level: int = 0
    xp_progress: float = 0.0
    crafting_table_open: bool = False
    craft_slots_3x3: Tuple[ItemStack, ...] = ()
    craft_result_3x3: Optional[ItemStack] = None
    furnace_open: bool = False
    furnace_input: Optional[ItemStack] = None
    furnace_fuel: Optional[ItemStack] = None
    furnace_output: Optional[ItemStack] = None
    furnace_progress: float = 0.0
    furnace_fuel_left: float = 0.0
    furnace_fuel_max: float = 1.0
    chest_open: bool = False
    chest_slots: Tuple[ItemStack, ...] = ()
    # F3 debug
    cx: int = 0
    cz: int = 0
    biome_name: str = ""
    facing: str = ""
    memory_mb: int = 0
    # Title screen
    game_state: str = "playing"
    title_seed_input: str = ""
    title_entering_seed: bool = False
    new_world_mode: str = "survival"  # "survival" | "creative"
    # World select
    world_list: Tuple[Tuple[int, float, Optional[Tuple[float, float, float]]], ...] = ()
    world_select_scroll: int = 0
    world_select_hover: int = -1
    # Combat
    damage_flash_timer: float = 0.0
    # Minimap (raw RGBA bytes for 64x64 surface, plus player facing in radians)
    minimap_rgba: Optional[bytes] = None
    minimap_yaw: float = 0.0
    # 8A: Settings (shown in pause panel)
    fov: float = 75.0
    sensitivity: float = 0.0023
    # 8C: Creative mode indicator
    game_mode: str = "survival"
    # Pause menu: which setting is currently selected (for up/down adjust)
    pause_selected: int = 0  # 0=render, 1=fov, 2=sensitivity
    # Keybinds menu
    keybinds_open: bool = False
    keybinds: Optional[Dict[str, int]] = None
    rebinding_action: Optional[str] = None
    keybinds_scroll: int = 0
    # Options menu (from title screen)
    options_tab: str = "video"  # "video" | "controls" | "sound"
    # Sound volumes (0.0 - 1.0)
    master_volume: float = 1.0
    music_volume: float = 0.8
    sfx_volume: float = 1.0
    # Stats overlay
    stats_open: bool = False
    stats: Optional[Dict[str, float]] = None
    # In-game command bar
    command_active: bool = False
    command_text: str = ""
    command_error: str = ""
    # Creative inventory
    creative_inv_open: bool = False
    creative_inv_scroll: int = 0


# ---------------------------------------------------------------------------
# Main UI class
# ---------------------------------------------------------------------------

class UI:
    def __init__(self, size: Tuple[int, int], icons: Dict[str, pygame.Surface]):
        self.w, self.h = int(size[0]), int(size[1])
        self.icons = icons
        self.surface = pygame.Surface((self.w, self.h), flags=pygame.SRCALPHA, depth=32)
        self._kb_rects: list = []
        # Resolve pixel font path early
        _get_pixel_font_path()

    def resize(self, size: Tuple[int, int]):
        self.w, self.h = int(size[0]), int(size[1])
        self.surface = pygame.Surface((self.w, self.h), flags=pygame.SRCALPHA, depth=32)

    def render(self, state: UIState) -> bytes:
        self.surface.fill((0, 0, 0, 0))
        if state.game_state == "title":
            self._draw_title_screen(state)
        elif state.game_state == "world_select":
            self._draw_world_select(state)
        elif state.game_state == "options":
            self._draw_options_screen(state)
        elif not state.alive:
            self._draw_death_screen(state)
        elif state.crafting_table_open:
            self._draw_crafting_table_screen(state)
            if state.dragged_item and not state.dragged_item.is_empty():
                self._draw_dragged_item(state)
        elif state.furnace_open:
            self._draw_furnace_screen(state)
            if state.dragged_item and not state.dragged_item.is_empty():
                self._draw_dragged_item(state)
        elif state.chest_open:
            self._draw_chest_screen(state)
            if state.dragged_item and not state.dragged_item.is_empty():
                self._draw_dragged_item(state)
        elif state.inventory_open:
            self._draw_inventory_screen(state)
            if state.dragged_item and not state.dragged_item.is_empty():
                self._draw_dragged_item(state)
        elif state.paused:
            self._draw_hotbar(state)
            self._draw_hud(state)
            self._draw_vitals(state)
            if state.keybinds_open:
                self._draw_keybinds_menu(state)
            elif state.stats_open:
                self._draw_pause(state)
                self._draw_stats_screen(state)
            else:
                self._draw_pause(state)
        elif state.creative_inv_open:
            self._draw_creative_inventory(state)
        else:
            self._draw_crosshair()
            self._draw_hotbar(state)
            self._draw_hud(state)
            self._draw_vitals(state)
            self._draw_minimap(state)
            if state.damage_flash_timer > 0.0:
                self._draw_damage_flash(state.damage_flash_timer)
        # Command bar overlays everything (including inventories) when active
        if state.command_active:
            self._draw_command_bar(state)
        elif state.command_error:
            self._draw_command_error(state)
        return pygame.image.tobytes(self.surface, "RGBA", False)

    # ------------------------------------------------------------------
    # Minimap
    # ------------------------------------------------------------------

    def _draw_minimap(self, state: UIState):
        if not state.minimap_rgba:
            return
        size = 64
        margin = 14
        x0 = self.w - size - margin
        y0 = margin

        # Outer frame
        _draw_panel(self.surface, x0 - 6, y0 - 6, size + 12, size + 12,
                    bg=(10, 14, 28, 220), border=(80, 110, 180, 220), radius=8)

        # Map pixels
        try:
            map_surf = pygame.image.frombuffer(state.minimap_rgba, (size, size), "RGBA")
            self.surface.blit(map_surf, (x0, y0))
        except (ValueError, pygame.error):
            pass

        # Player facing arrow at center: forward_world = (sin(yaw), -cos(yaw)) in XZ.
        import math
        cx_p = x0 + size // 2
        cy_p = y0 + size // 2
        yaw = float(state.minimap_yaw)
        fx = math.sin(yaw)
        fz = -math.cos(yaw)
        # Perpendicular for the arrow base
        nx, nz = -fz, fx
        tip = (cx_p + int(fx * 7), cy_p + int(fz * 7))
        left = (cx_p + int(-fx * 3 + nx * 3), cy_p + int(-fz * 3 + nz * 3))
        right = (cx_p + int(-fx * 3 - nx * 3), cy_p + int(-fz * 3 - nz * 3))
        pygame.draw.polygon(self.surface, (255, 240, 100), [tip, left, right])
        pygame.draw.polygon(self.surface, (60, 30, 0), [tip, left, right], width=1)

        # Cardinal indicator
        _draw_text(self.surface, "N", x0 + size // 2 - 4, y0 - 14,
                   color=(200, 220, 255), size=11, bold=True, shadow=True)

    # ------------------------------------------------------------------
    # Title screen
    # ------------------------------------------------------------------

    def _draw_title_screen(self, state: UIState):
        # Dirt-stack inspired flat dark background (Minecraft main menu style)
        self.surface.fill((26, 26, 26))
        # Subtle tile pattern using dirt brown stripes
        for sy in range(0, self.h, 32):
            shade = 36 if (sy // 32) % 2 == 0 else 30
            pygame.draw.rect(self.surface, (shade, shade, shade), (0, sy, self.w, 32))

        cx = self.w // 2

        # ── Game title ─────────────────────────────────────────────────
        title = "OurCraft 2"
        title_f = _font(72, bold=True)
        title_s = title_f.render(title, True, MCStyle.TEXT_HEADING)
        title_sh = title_f.render(title, True, (60, 60, 30))
        tx = cx - title_s.get_width() // 2
        ty = self.h // 4
        self.surface.blit(title_sh, (tx + 3, ty + 3))
        self.surface.blit(title_s, (tx, ty))

        # Subtitle
        sub = "Alpha"
        sub_f = _font(22)
        sub_s = sub_f.render(sub, True, MCStyle.TEXT_PRIMARY)
        self.surface.blit(sub_s, (cx - sub_s.get_width() // 2, ty + title_s.get_height() + 6))

        btn_w, btn_h, gap = 320, 44, 10
        sp_y = self.h // 2
        op_y = sp_y + btn_h + gap
        qt_y = op_y + btn_h + gap

        if state.title_entering_seed:
            # ── Seed input + mode selection panel ─────────────────────
            panel_w, panel_h = 420, 220
            px = cx - panel_w // 2
            py = self.h // 2 - panel_h // 2
            _draw_panel(self.surface, px, py, panel_w, panel_h,
                        bg=(8, 12, 28, 240), border=(80, 120, 220, 200), radius=14)

            _draw_text(self.surface, "Enter World Seed:",
                       cx - 82, py + 18, color=(180, 200, 240), size=20, bold=True)

            field_x, field_y = px + 20, py + 52
            field_w, field_h = panel_w - 40, 38
            pygame.draw.rect(self.surface, (20, 28, 55, 240),
                             (field_x, field_y, field_w, field_h), border_radius=6)
            pygame.draw.rect(self.surface, (100, 140, 230, 220),
                             (field_x, field_y, field_w, field_h), width=2, border_radius=6)
            display_text = state.title_seed_input + "|"
            _draw_text(self.surface, display_text,
                       field_x + 10, field_y + 8, color=(230, 240, 255), size=18, shadow=False)

            # ── Mode selection buttons ─────────────────────────────────
            _draw_text(self.surface, "Game Mode:",
                       cx - 56, py + 104, color=(160, 180, 230), size=16, shadow=False)

            modes = [("survival", "⛏ Survival", (200, 160, 80)), ("creative", "✦ Creative", (80, 180, 200))]
            mbtn_w, mbtn_h = 170, 34
            total_mw = mbtn_w * 2 + 12
            mbtn_x0 = cx - total_mw // 2
            for i, (m_key, m_label, m_color) in enumerate(modes):
                mx0 = mbtn_x0 + i * (mbtn_w + 12)
                my0 = py + 128
                is_selected = (state.new_world_mode == m_key)
                border_c = (*m_color, 255) if is_selected else (*m_color, 100)
                bg_c = (*m_color, 80) if is_selected else (15, 20, 40, 200)
                _draw_panel(self.surface, mx0, my0, mbtn_w, mbtn_h,
                            bg=bg_c, border=border_c, radius=8)
                lc = (240, 240, 255) if is_selected else (140, 160, 200)
                _draw_text(self.surface, m_label, mx0 + mbtn_w // 2 - 40, my0 + 8,
                           color=lc, size=15, bold=is_selected, shadow=False)

            _draw_text(self.surface, "ENTER to start  ·  ESC to cancel",
                       cx - 120, py + 186, color=(100, 120, 170), size=13, shadow=False)
        else:
            # ── Buttons (Minecraft-style) ──────────────────────────────
            mx, my = state.mouse_x, state.mouse_y
            bx = cx - btn_w // 2
            sp_hover = (bx <= mx <= bx + btn_w) and (sp_y <= my <= sp_y + btn_h)
            op_hover = (bx <= mx <= bx + btn_w) and (op_y <= my <= op_y + btn_h)
            qt_hover = (bx <= mx <= bx + btn_w) and (qt_y <= my <= qt_y + btn_h)
            _draw_button(self.surface, bx, sp_y, btn_w, btn_h, "Singleplayer", hover=sp_hover)
            _draw_button(self.surface, bx, op_y, btn_w, btn_h, "Options...", hover=op_hover)
            _draw_button(self.surface, bx, qt_y, btn_w, btn_h, "Quit Game", hover=qt_hover)

        # Version footer
        _draw_text(self.surface, "v0.1  |  OurCraft 2",
                   8, self.h - 22, color=MCStyle.TEXT_PRIMARY, size=14, shadow=True)

    # ------------------------------------------------------------------
    # World select screen
    # ------------------------------------------------------------------

    def world_select_layout(self) -> dict:
        """Return geometry for the world-select screen so game.py can hit-test clicks."""
        list_w = 520
        row_h = 56
        max_visible = 6
        cx = self.w // 2
        list_x = cx - list_w // 2
        list_y = self.h // 4 + 50
        new_btn_y = list_y + max_visible * row_h + 14
        back_btn_y = new_btn_y + 56
        return {
            "list_x": list_x,
            "list_y": list_y,
            "list_w": list_w,
            "row_h": row_h,
            "max_visible": max_visible,
            "new_btn_y": new_btn_y,
            "new_btn_h": 48,
            "back_btn_y": back_btn_y,
            "back_btn_h": 36,
            "btn_w": list_w,
            "delete_w": 36,
        }

    def _draw_world_select(self, state: UIState):
        # Flat dark background (Minecraft option-screen look)
        self.surface.fill((26, 26, 26))
        for sy in range(0, self.h, 32):
            shade = 36 if (sy // 32) % 2 == 0 else 30
            pygame.draw.rect(self.surface, (shade, shade, shade), (0, sy, self.w, 32))

        cx = self.w // 2
        L = self.world_select_layout()

        # Heading
        _draw_text(self.surface, "Select World", cx - 110, self.h // 4 - 10,
                   color=MCStyle.TEXT_HEADING, size=38, bold=True, shadow=True)

        worlds = state.world_list
        if not worlds:
            _draw_text(self.surface, "No worlds yet — create a new one below",
                       cx - 180, L["list_y"] + 20,
                       color=(150, 170, 210), size=16, shadow=False)
        else:
            import time
            now = time.time()
            scroll = max(0, min(state.world_select_scroll, max(0, len(worlds) - L["max_visible"])))
            visible = worlds[scroll:scroll + L["max_visible"]]
            for i, (seed, mtime, ppos) in enumerate(visible):
                row_y = L["list_y"] + i * L["row_h"]
                actual_idx = scroll + i
                hover = (state.world_select_hover == actual_idx)
                # Row uses button-like bevel: hover → lighter grey
                _draw_button(self.surface, L["list_x"], row_y, L["list_w"], L["row_h"] - 6,
                             "", hover=hover, font_size=1)

                # Seed
                _draw_text(self.surface, f"Seed: {seed}", L["list_x"] + 14, row_y + 8,
                           color=MCStyle.TEXT_PRIMARY, size=17, bold=True, shadow=True)

                # Time ago
                dt_s = max(0.0, now - mtime)
                if dt_s < 60:
                    age = f"{int(dt_s)}s ago"
                elif dt_s < 3600:
                    age = f"{int(dt_s / 60)}m ago"
                elif dt_s < 86400:
                    age = f"{int(dt_s / 3600)}h ago"
                else:
                    age = f"{int(dt_s / 86400)}d ago"

                pos_txt = ""
                if ppos:
                    pos_txt = f"  ·  pos ({ppos[0]:+.0f}, {ppos[1]:+.0f}, {ppos[2]:+.0f})"
                _draw_text(self.surface, f"Last played: {age}{pos_txt}",
                           L["list_x"] + 14, row_y + 30,
                           color=(200, 200, 200), size=13, shadow=True)

                # Delete button (small X on the right)
                dx = L["list_x"] + L["list_w"] - L["delete_w"] - 8
                dy = row_y + (L["row_h"] - 6 - 28) // 2
                _draw_button(self.surface, dx, dy, L["delete_w"], 28, "X",
                             hover=False, font_size=16)

            # Scroll hint
            if len(worlds) > L["max_visible"]:
                _draw_text(self.surface,
                           f"{scroll + 1}-{min(len(worlds), scroll + L['max_visible'])} of {len(worlds)}  ·  scroll",
                           cx - 80, L["list_y"] - 24,
                           color=MCStyle.TEXT_PRIMARY, size=12, shadow=True)

        mx, my = state.mouse_x, state.mouse_y

        # New World button
        new_hover = (L["list_x"] <= mx <= L["list_x"] + L["btn_w"]
                     and L["new_btn_y"] <= my <= L["new_btn_y"] + L["new_btn_h"])
        _draw_button(self.surface, L["list_x"], L["new_btn_y"], L["btn_w"],
                     L["new_btn_h"], "Create New World", hover=new_hover, font_size=20)

        # Back button
        back_hover = (L["list_x"] <= mx <= L["list_x"] + L["btn_w"]
                      and L["back_btn_y"] <= my <= L["back_btn_y"] + L["back_btn_h"])
        _draw_button(self.surface, L["list_x"], L["back_btn_y"], L["btn_w"],
                     L["back_btn_h"], "Cancel", hover=back_hover, font_size=18)

    # ------------------------------------------------------------------
    # Damage flash
    # ------------------------------------------------------------------

    def _draw_damage_flash(self, timer: float):
        alpha = int(min(1.0, timer / 0.3) * 120)
        overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        overlay.fill((180, 0, 0, alpha))
        self.surface.blit(overlay, (0, 0))

    # ------------------------------------------------------------------
    # Command bar ("/" key)
    # ------------------------------------------------------------------

    def _draw_command_bar(self, state: UIState) -> None:
        bar_h = 32
        bar_y = self.h - bar_h - 4
        bar_x = 4
        bar_w = self.w - 8
        pygame.draw.rect(self.surface, (0, 0, 0, 180), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        pygame.draw.rect(self.surface, (200, 200, 200, 160), (bar_x, bar_y, bar_w, bar_h), width=1, border_radius=4)
        display = "/" + state.command_text + "|"
        _draw_text(self.surface, display, bar_x + 8, bar_y + 7, color=(255, 255, 255), size=16, shadow=False)

    def _draw_command_error(self, state: UIState) -> None:
        if not state.command_error:
            return
        msg = state.command_error
        bar_h = 28
        bar_y = self.h - bar_h - 4
        bar_x = 4
        bar_w = self.w - 8
        pygame.draw.rect(self.surface, (80, 0, 0, 200), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        _draw_text(self.surface, msg, bar_x + 8, bar_y + 6, color=(255, 100, 100), size=15, shadow=False)

    # ------------------------------------------------------------------
    # Creative inventory
    # ------------------------------------------------------------------

    def _draw_creative_inventory(self, state: UIState) -> None:
        from .chunk import (
            BLOCK_GRASS, BLOCK_DIRT, BLOCK_STONE, BLOCK_SAND,
            BLOCK_LOG, BLOCK_LEAVES, BLOCK_WATER, BLOCK_BEDROCK, BLOCK_SNOW,
            BLOCK_GLASS, BLOCK_PLANKS, BLOCK_CRAFTING_TABLE, BLOCK_COBBLESTONE,
            BLOCK_GRAVEL, BLOCK_LAVA, BLOCK_COAL_ORE, BLOCK_IRON_ORE,
            BLOCK_GOLD_ORE, BLOCK_DIAMOND_ORE, BLOCK_REDSTONE_ORE,
            BLOCK_TALL_GRASS, BLOCK_FLOWER_RED, BLOCK_FLOWER_YELLOW,
            BLOCK_FURNACE, BLOCK_CHEST, BLOCK_GRANITE, BLOCK_ANDESITE,
            BLOCK_DIORITE, BLOCK_CLAY, BLOCK_MUSHROOM_RED, BLOCK_MUSHROOM_BROWN,
            BLOCK_SUGAR_CANE, BLOCK_COAL_BLOCK, BLOCK_IRON_BLOCK,
            BLOCK_GOLD_BLOCK, BLOCK_DIAMOND_BLOCK, BLOCK_REDSTONE_BLOCK,
            BLOCK_SANDSTONE, BLOCK_STONE_BRICKS, BLOCK_BRICKS, BLOCK_BOOKSHELF,
            BLOCK_TNT, BLOCK_WOOL, BLOCK_BED, BLOCK_DEEPSLATE,
            BLOCK_DEEPSLATE_COAL, BLOCK_DEEPSLATE_IRON,
            BLOCK_DEEPSLATE_GOLD, BLOCK_DEEPSLATE_DIAMOND,
            BLOCK_DEEPSLATE_REDSTONE, BLOCK_COPPER_ORE,
            BLOCK_DEEPSLATE_COPPER, BLOCK_COPPER_BLOCK,
        )
        from .items import (
            ITEM_WOODEN_SWORD, ITEM_STONE_SWORD, ITEM_IRON_SWORD,
            ITEM_DIAMOND_SWORD, ITEM_WOODEN_PICKAXE, ITEM_STONE_PICKAXE,
            ITEM_IRON_PICKAXE, ITEM_DIAMOND_PICKAXE, ITEM_WOODEN_AXE,
            ITEM_STONE_AXE, ITEM_IRON_AXE, ITEM_DIAMOND_AXE,
            ITEM_WOODEN_SHOVEL, ITEM_STONE_SHOVEL, ITEM_IRON_SHOVEL,
            ITEM_DIAMOND_SHOVEL, ITEM_WOODEN_HOE, ITEM_STONE_HOE,
            ITEM_IRON_HOE, ITEM_DIAMOND_HOE,
            ITEM_LEATHER_HELMET, ITEM_LEATHER_CHESTPLATE,
            ITEM_LEATHER_LEGGINGS, ITEM_LEATHER_BOOTS,
            ITEM_IRON_HELMET, ITEM_IRON_CHESTPLATE,
            ITEM_IRON_LEGGINGS, ITEM_IRON_BOOTS,
            ITEM_DIAMOND_HELMET, ITEM_DIAMOND_CHESTPLATE,
            ITEM_DIAMOND_LEGGINGS, ITEM_DIAMOND_BOOTS,
            ITEM_GOLD_HELMET, ITEM_GOLD_CHESTPLATE,
            ITEM_GOLD_LEGGINGS, ITEM_GOLD_BOOTS,
            ITEM_APPLE, ITEM_RAW_BEEF, ITEM_COOKED_BEEF,
            ITEM_CHICKEN, ITEM_PORKCHOP, ITEM_MUSHROOM_STEW, ITEM_GOLDEN_APPLE,
            ITEM_COAL, ITEM_RAW_IRON, ITEM_RAW_GOLD, ITEM_DIAMOND,
            ITEM_REDSTONE, ITEM_RAW_COPPER, ITEM_IRON_INGOT, ITEM_GOLD_INGOT,
            ITEM_BUCKET, ITEM_WATER_BUCKET, ITEM_LAVA_BUCKET,
            ITEM_SHEARS, ITEM_FLINT_AND_STEEL,
            ITEM_CLAY_BALL, ITEM_SUGAR, ITEM_BONE_MEAL,
            ITEM_PAPER, ITEM_BOOK, ITEM_STRING, ITEM_LEATHER,
            ITEM_FEATHER, ITEM_BONE, ITEM_GUNPOWDER, ITEM_BOWL,
            ITEM_ROTTEN_FLESH, ITEM_WOOL,
            ITEM_SPAWN_EGG_COW, ITEM_SPAWN_EGG_PIG, ITEM_SPAWN_EGG_CHICKEN,
            ITEM_SPAWN_EGG_SHEEP, ITEM_SPAWN_EGG_ZOMBIE, ITEM_SPAWN_EGG_SKELETON,
            ITEM_SPAWN_EGG_SPIDER, ITEM_SPAWN_EGG_CREEPER, ITEM_SPAWN_EGG_VILLAGER,
        )

        ALL_ITEMS = [
            # Terrain blocks
            BLOCK_GRASS, BLOCK_DIRT, BLOCK_STONE, BLOCK_COBBLESTONE, BLOCK_SAND,
            BLOCK_GRAVEL, BLOCK_BEDROCK, BLOCK_SNOW, BLOCK_GLASS,
            BLOCK_GRANITE, BLOCK_ANDESITE, BLOCK_DIORITE, BLOCK_CLAY,
            BLOCK_SANDSTONE, BLOCK_STONE_BRICKS, BLOCK_BRICKS, BLOCK_BOOKSHELF,
            # Wood
            BLOCK_LOG, BLOCK_PLANKS, BLOCK_LEAVES,
            # Functional
            BLOCK_CRAFTING_TABLE, BLOCK_FURNACE, BLOCK_CHEST,
            BLOCK_TNT, BLOCK_BED,
            # Decorative
            BLOCK_WOOL, BLOCK_TALL_GRASS, BLOCK_FLOWER_RED, BLOCK_FLOWER_YELLOW,
            BLOCK_MUSHROOM_RED, BLOCK_MUSHROOM_BROWN, BLOCK_SUGAR_CANE,
            # Liquid
            BLOCK_WATER, BLOCK_LAVA,
            # Ores
            BLOCK_COAL_ORE, BLOCK_IRON_ORE, BLOCK_GOLD_ORE,
            BLOCK_DIAMOND_ORE, BLOCK_REDSTONE_ORE, BLOCK_COPPER_ORE,
            BLOCK_DEEPSLATE, BLOCK_DEEPSLATE_COAL, BLOCK_DEEPSLATE_IRON,
            BLOCK_DEEPSLATE_GOLD, BLOCK_DEEPSLATE_DIAMOND,
            BLOCK_DEEPSLATE_REDSTONE, BLOCK_DEEPSLATE_COPPER,
            # Storage blocks
            BLOCK_COAL_BLOCK, BLOCK_IRON_BLOCK, BLOCK_GOLD_BLOCK,
            BLOCK_DIAMOND_BLOCK, BLOCK_REDSTONE_BLOCK, BLOCK_COPPER_BLOCK,
            # Materials
            ITEM_COAL, ITEM_RAW_IRON, ITEM_RAW_GOLD, ITEM_DIAMOND,
            ITEM_REDSTONE, ITEM_RAW_COPPER, ITEM_IRON_INGOT, ITEM_GOLD_INGOT,
            ITEM_CLAY_BALL, ITEM_SUGAR, ITEM_BONE_MEAL,
            ITEM_PAPER, ITEM_BOOK, ITEM_STRING, ITEM_LEATHER,
            ITEM_FEATHER, ITEM_BONE, ITEM_GUNPOWDER, ITEM_BOWL, ITEM_ROTTEN_FLESH,
            ITEM_WOOL,
            # Tools
            ITEM_WOODEN_SWORD, ITEM_STONE_SWORD, ITEM_IRON_SWORD, ITEM_DIAMOND_SWORD,
            ITEM_WOODEN_PICKAXE, ITEM_STONE_PICKAXE, ITEM_IRON_PICKAXE, ITEM_DIAMOND_PICKAXE,
            ITEM_WOODEN_AXE, ITEM_STONE_AXE, ITEM_IRON_AXE, ITEM_DIAMOND_AXE,
            ITEM_WOODEN_SHOVEL, ITEM_STONE_SHOVEL, ITEM_IRON_SHOVEL, ITEM_DIAMOND_SHOVEL,
            ITEM_WOODEN_HOE, ITEM_STONE_HOE, ITEM_IRON_HOE, ITEM_DIAMOND_HOE,
            ITEM_SHEARS, ITEM_FLINT_AND_STEEL,
            ITEM_BUCKET, ITEM_WATER_BUCKET, ITEM_LAVA_BUCKET,
            # Armor
            ITEM_LEATHER_HELMET, ITEM_LEATHER_CHESTPLATE, ITEM_LEATHER_LEGGINGS, ITEM_LEATHER_BOOTS,
            ITEM_IRON_HELMET, ITEM_IRON_CHESTPLATE, ITEM_IRON_LEGGINGS, ITEM_IRON_BOOTS,
            ITEM_GOLD_HELMET, ITEM_GOLD_CHESTPLATE, ITEM_GOLD_LEGGINGS, ITEM_GOLD_BOOTS,
            ITEM_DIAMOND_HELMET, ITEM_DIAMOND_CHESTPLATE, ITEM_DIAMOND_LEGGINGS, ITEM_DIAMOND_BOOTS,
            # Food
            ITEM_APPLE, ITEM_GOLDEN_APPLE,
            ITEM_RAW_BEEF, ITEM_COOKED_BEEF, ITEM_CHICKEN, ITEM_PORKCHOP,
            ITEM_MUSHROOM_STEW,
            # Spawn eggs (creative-only: right-click to spawn the mob)
            ITEM_SPAWN_EGG_COW, ITEM_SPAWN_EGG_PIG, ITEM_SPAWN_EGG_CHICKEN,
            ITEM_SPAWN_EGG_SHEEP, ITEM_SPAWN_EGG_ZOMBIE, ITEM_SPAWN_EGG_SKELETON,
            ITEM_SPAWN_EGG_SPIDER, ITEM_SPAWN_EGG_CREEPER, ITEM_SPAWN_EGG_VILLAGER,
        ]

        cols = 9
        cell = 40
        padding = 6
        panel_w = cols * (cell + padding) + padding
        panel_h = self.h - 100
        px = (self.w - panel_w) // 2
        py = 50

        # Background panel
        _draw_panel(self.surface, px, py, panel_w, panel_h,
                    bg=(20, 20, 20, 220), border=(140, 140, 140, 200), radius=8)

        # Title
        _draw_text(self.surface, "Creative Inventory", px + panel_w // 2 - 70, py + 8,
                   color=(240, 240, 240), size=18, bold=True, shadow=True)

        # Scrollable item grid
        rows_visible = (panel_h - 50) // (cell + padding)
        max_rows = (len(ALL_ITEMS) + cols - 1) // cols
        scroll = min(state.creative_inv_scroll, max(0, max_rows - rows_visible))

        grid_y0 = py + 36
        self._creative_item_rects = []
        for row in range(rows_visible):
            actual_row = row + scroll
            for col in range(cols):
                idx = actual_row * cols + col
                if idx >= len(ALL_ITEMS):
                    break
                item_id = ALL_ITEMS[idx]
                cx2 = px + padding + col * (cell + padding)
                cy2 = grid_y0 + row * (cell + padding)
                # Cell background
                pygame.draw.rect(self.surface, (50, 50, 50, 200), (cx2, cy2, cell, cell), border_radius=4)
                pygame.draw.rect(self.surface, (100, 100, 100, 180), (cx2, cy2, cell, cell), width=1, border_radius=4)
                # Item icon
                tex_name = self._hotbar_tex_name_for_id(item_id)
                icon = self.icons.get(tex_name) if tex_name else None
                if icon is not None:
                    icon_s = pygame.transform.scale(icon, (cell - 6, cell - 6))
                    self.surface.blit(icon_s, (cx2 + 3, cy2 + 3))
                self._creative_item_rects.append((cx2, cy2, cell, cell, item_id))

        # Hotbar at bottom of panel
        self._draw_hotbar(state)

        # Scroll hint
        if max_rows > rows_visible:
            _draw_text(self.surface, f"Scroll: {scroll+1}/{max_rows}", px + panel_w - 100, py + panel_h - 22,
                       color=(160, 160, 160), size=12, shadow=False)

    def _hotbar_tex_name_for_id(self, item_id: int) -> str:
        """Return icon key for a block/item ID using the shared block_name mapping."""
        return block_name(item_id)

    def _draw_death_screen(self, state: UIState):
        # Red overlay
        overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        overlay.fill((120, 0, 0, 150))
        self.surface.blit(overlay, (0, 0))

        # Death message
        msg = "YOU DIED!"
        f_size = 72
        w_msg, h_msg = _draw_text(self.surface, msg, 0, 0, color=(255, 50, 50), size=f_size, bold=True, shadow=True)
        # Actually draw centered
        _draw_text(self.surface, msg, (self.w - w_msg) // 2, (self.h - h_msg) // 2 - 40, color=(255, 50, 50), size=f_size, bold=True, shadow=True)

        # Respawn message
        respawn_in = max(0.0, 2.0 - state.death_timer)
        msg2 = f"Respawning in {respawn_in:.1f}s..."
        w_msg2, h_msg2 = _draw_text(self.surface, msg2, 0, 0, color=(255, 255, 255), size=24, bold=False, shadow=True)
        _draw_text(self.surface, msg2, (self.w - w_msg2) // 2, (self.h + h_msg) // 2 + 10, color=(255, 255, 255), size=24, bold=False, shadow=True)

    # ------------------------------------------------------------------
    # Crosshair
    # ------------------------------------------------------------------

    def _draw_crosshair(self):
        cx = self.w // 2
        cy = self.h // 2
        arm = 11
        gap = 4
        thick = 2
        white = (255, 255, 255, 220)
        black = (0, 0, 0, 140)

        for ox, oy in ((1, 0), (0, 1), (-1, 0), (0, -1)):
            # horizontal arms shadow
            pygame.draw.rect(self.surface, black,
                             (cx + gap + ox, cy - thick // 2 + oy, arm, thick))
            pygame.draw.rect(self.surface, black,
                             (cx - gap - arm + ox, cy - thick // 2 + oy, arm, thick))
            # vertical arms shadow
            pygame.draw.rect(self.surface, black,
                             (cx - thick // 2 + ox, cy + gap + oy, thick, arm))
            pygame.draw.rect(self.surface, black,
                             (cx - thick // 2 + ox, cy - gap - arm + oy, thick, arm))

        pygame.draw.rect(self.surface, white, (cx + gap, cy - thick // 2, arm, thick))
        pygame.draw.rect(self.surface, white, (cx - gap - arm, cy - thick // 2, arm, thick))
        pygame.draw.rect(self.surface, white, (cx - thick // 2, cy + gap, thick, arm))
        pygame.draw.rect(self.surface, white, (cx - thick // 2, cy - gap - arm, thick, arm))

    # ------------------------------------------------------------------
    # Hotbar
    # ------------------------------------------------------------------

    def _draw_hotbar(self, state: UIState):
        slot_count = 9
        slot_size = 46
        pad = 2
        margin = 6
        bar_w = slot_count * slot_size + (slot_count - 1) * pad + margin * 2
        bar_h = slot_size + margin * 2
        x0 = (self.w - bar_w) // 2
        y0 = self.h - bar_h - 10

        # Hotbar background — flat dark grey with light bevel (vanilla style)
        pygame.draw.rect(self.surface, (40, 40, 40), (x0, y0, bar_w, bar_h))
        pygame.draw.rect(self.surface, MCStyle.PANEL_BORDER_DARK, (x0, y0, bar_w, bar_h), width=1)
        pygame.draw.line(self.surface, MCStyle.PANEL_BORDER_LIGHT,
                         (x0 + 1, y0 + 1), (x0 + bar_w - 2, y0 + 1))
        pygame.draw.line(self.surface, MCStyle.PANEL_BORDER_LIGHT,
                         (x0 + 1, y0 + 1), (x0 + 1, y0 + bar_h - 2))

        mx, my = state.mouse_x, state.mouse_y

        for i in range(slot_count):
            sx = x0 + margin + i * (slot_size + pad)
            sy = y0 + margin

            # Sunken slot
            _draw_inset_slot(self.surface, sx, sy, slot_size)

            if i == state.active_slot:
                # 2px white outline around active slot
                pygame.draw.rect(self.surface, MCStyle.SLOT_BORDER_LIGHT,
                                 (sx - 2, sy - 2, slot_size + 4, slot_size + 4), width=2)

            # Item icon
            name = state.hotbar_names[i] if i < len(state.hotbar_names) else ""
            icon = self.icons.get(name)
            if icon is not None:
                icon_size = 32
                scaled = pygame.transform.scale(icon, (icon_size, icon_size))
                self.surface.blit(scaled, (sx + (slot_size - icon_size) // 2,
                                           sy + (slot_size - icon_size) // 2))

            # Item count (bottom-right) for stacks > 1
            if i < len(state.inv_slots):
                stack = state.inv_slots[i]
                if stack is not None and not stack.is_empty() and stack.count > 1:
                    _draw_text(self.surface, str(stack.count),
                               sx + slot_size - 16, sy + slot_size - 18,
                               color=MCStyle.TEXT_PRIMARY, size=14, bold=True, shadow=True)
                if stack is not None and not stack.is_empty():
                    self._draw_durability_bar(sx, sy, slot_size, stack)

            # Tooltip on hover
            is_hover = (sx <= mx < sx + slot_size and sy <= my < sy + slot_size)
            if is_hover and i < len(state.inv_slots):
                stack = state.inv_slots[i]
                if stack is not None and not stack.is_empty():
                    self._draw_tooltip(sx, sy, slot_size, stack)

    # ------------------------------------------------------------------
    # HUD
    # ------------------------------------------------------------------

    def _draw_hud(self, state: UIState):
        x, y, z = state.pos

        fps = state.fps
        if fps >= 60:
            fps_col = (80, 255, 120)
        elif fps >= 30:
            fps_col = (255, 210, 60)
        else:
            fps_col = (255, 70, 70)

        lines: List[Tuple[str, Tuple[int, int, int]]] = [
            (f"FPS  {int(fps):>4}", fps_col),
            (f"X {x:+.1f}  Y {y:+.1f}  Z {z:+.1f}", (170, 190, 255)),
            (f"▸ {state.target_name}", (190, 190, 210)),
        ]
        if state.debug:
            lines.extend([
                (f"RD    {state.render_distance} chunks", (120, 255, 160)),
                (f"Chunk  ({state.cx}, {state.cz})", (140, 200, 255)),
                (f"Biome  {state.biome_name}", (180, 255, 180)),
                (f"Facing  {state.facing}", (255, 220, 140)),
                (f"Mem    {state.memory_mb} MB", (200, 180, 255)),
            ])

        line_h = 22
        pad_x = 10
        pad_y = 8
        panel_w = 280
        panel_h = len(lines) * line_h + pad_y * 2

        _draw_panel(self.surface, 8, 8, panel_w, panel_h,
                    bg=(0, 0, 0, 150), border=(50, 60, 100, 120), radius=8)

        for i, (txt, col) in enumerate(lines):
            _draw_text(self.surface, txt,
                       8 + pad_x, 8 + pad_y + i * line_h,
                       color=col, size=14, shadow=True)

    # ------------------------------------------------------------------
    # Vitals (health & hunger bars)
    # ------------------------------------------------------------------

    def _draw_vitals(self, state: UIState):
        bar_w = 180
        bar_h = 12
        gap = 6
        hotbar_top = self.h - 10 - 46
        y_hb = hotbar_top - bar_h - gap

        # --- XP bar (green, full hotbar width) above health/hunger ---
        xp_bar_w = bar_w * 2 + gap
        xp_y = y_hb - bar_h - gap - 2
        xp_x = self.w // 2 - xp_bar_w // 2
        _draw_panel(self.surface, xp_x - 2, xp_y - 2, xp_bar_w + 4, bar_h + 4,
                    bg=(10, 30, 10, 180), border=(40, 120, 40, 120), radius=4)
        fill_xp = int(xp_bar_w * max(0.0, min(1.0, state.xp_progress)))
        if fill_xp > 0:
            pygame.draw.rect(self.surface, (80, 220, 80), (xp_x, xp_y, fill_xp, bar_h))
        _draw_text(self.surface, f"Lv {state.xp_level}", xp_x - 40, xp_y + 1,
                   color=(120, 255, 120), size=10, shadow=False)

        # Health bar (red) — left side
        x = self.w // 2 - bar_w - gap // 2
        _draw_panel(self.surface, x - 2, y_hb - 2, bar_w + 4, bar_h + 4,
                    bg=(40, 20, 20, 200), border=(80, 40, 40, 150), radius=4)
        fill = int(bar_w * max(0.0, min(1.0, state.health / 20.0)))
        if fill > 0:
            pygame.draw.rect(self.surface, (200, 40, 40), (x, y_hb, fill, bar_h))
        _draw_text(self.surface, f"❤ {int(state.health)}/20", x + 4, y_hb + 1,
                   color=(255, 150, 150), size=10, shadow=False)

        # Hunger bar (orange) — right side
        x2 = self.w // 2 + gap // 2
        _draw_panel(self.surface, x2 - 2, y_hb - 2, bar_w + 4, bar_h + 4,
                    bg=(60, 40, 20, 200), border=(150, 100, 40, 150), radius=4)
        fill2 = int(bar_w * max(0.0, min(1.0, state.hunger / 20.0)))
        if fill2 > 0:
            pygame.draw.rect(self.surface, (200, 130, 40), (x2, y_hb, fill2, bar_h))
        _draw_text(self.surface, f"🍖 {int(state.hunger)}/20", x2 + 4, y_hb + 1,
                   color=(255, 200, 100), size=10, shadow=False)

        # Air bar (blue) — only visible while underwater / refilling
        if state.air < 10.0:
            air_y = xp_y - bar_h - gap
            air_x = self.w // 2 - bar_w // 2
            _draw_panel(self.surface, air_x - 2, air_y - 2, bar_w + 4, bar_h + 4,
                        bg=(10, 20, 40, 200), border=(40, 80, 150, 150), radius=4)
            fill_air = int(bar_w * max(0.0, min(1.0, state.air / 10.0)))
            if fill_air > 0:
                pygame.draw.rect(self.surface, (60, 140, 230), (air_x, air_y, fill_air, bar_h))
            _draw_text(self.surface, f"O2 {state.air:.1f}/10", air_x + 4, air_y + 1,
                       color=(180, 220, 255), size=10, shadow=False)

    # ------------------------------------------------------------------
    # Options screen (from title)
    # ------------------------------------------------------------------

    def _draw_options_screen(self, state: UIState):
        # Background
        self.surface.fill((26, 26, 26))
        for sy in range(0, self.h, 32):
            shade = 36 if (sy // 32) % 2 == 0 else 30
            pygame.draw.rect(self.surface, (shade, shade, shade), (0, sy, self.w, 32))

        cx = self.w // 2
        _draw_text(self.surface, "Options", cx - 60, 60,
                   color=MCStyle.TEXT_HEADING, size=42, bold=True, shadow=True)

        # Tab buttons
        tabs = [("video", "Video Settings"), ("controls", "Controls"), ("sound", "Sound")]
        tab_w = 200
        tab_h = 36
        tab_gap = 8
        total_w = len(tabs) * tab_w + (len(tabs) - 1) * tab_gap
        tab_x0 = cx - total_w // 2
        tab_y = 130
        mx, my = state.mouse_x, state.mouse_y
        self._options_tab_rects = []
        for i, (key, label) in enumerate(tabs):
            tx = tab_x0 + i * (tab_w + tab_gap)
            hover = (tx <= mx <= tx + tab_w) and (tab_y <= my <= tab_y + tab_h)
            active = (state.options_tab == key)
            _draw_button(self.surface, tx, tab_y, tab_w, tab_h, label,
                         hover=hover or active, font_size=16)
            if active:
                pygame.draw.line(self.surface, MCStyle.TEXT_HEADING,
                                 (tx + 4, tab_y + tab_h - 1),
                                 (tx + tab_w - 4, tab_y + tab_h - 1), 2)
            self._options_tab_rects.append((tx, tab_y, tab_w, tab_h, key))

        # Tab body panel
        body_x = cx - 300
        body_y = tab_y + tab_h + 12
        body_w = 600
        body_h = self.h - body_y - 80
        _draw_panel(self.surface, body_x, body_y, body_w, body_h)

        self._options_action_rects = []
        if state.options_tab == "video":
            self._draw_options_video(state, body_x + 24, body_y + 24, body_w - 48)
        elif state.options_tab == "controls":
            _draw_text(self.surface, "Press the Controls button below to rebind keys.",
                       body_x + 24, body_y + 24, color=MCStyle.TEXT_PRIMARY, size=16, shadow=True)
            kb_btn_y = body_y + 70
            kb_hover = (body_x + 24 <= mx <= body_x + 24 + 300) and (kb_btn_y <= my <= kb_btn_y + 36)
            _draw_button(self.surface, body_x + 24, kb_btn_y, 300, 36, "Open Controls...",
                         hover=kb_hover, font_size=18)
            self._options_action_rects.append(("open_keybinds", body_x + 24, kb_btn_y, 300, 36))
        elif state.options_tab == "sound":
            self._draw_options_sound(state, body_x + 24, body_y + 24, body_w - 48)

        # Back button
        back_w = 200
        back_h = 40
        back_x = cx - back_w // 2
        back_y = self.h - 60
        back_hover = (back_x <= mx <= back_x + back_w) and (back_y <= my <= back_y + back_h)
        _draw_button(self.surface, back_x, back_y, back_w, back_h, "Done", hover=back_hover, font_size=18)
        self._options_action_rects.append(("back", back_x, back_y, back_w, back_h))

    def _draw_options_video(self, state: UIState, x: int, y: int, w: int):
        # Render distance + FOV + sensitivity sliders (reuse pause-style display)
        rows = [
            ("Render Distance", f"{state.render_distance} chunks",
             (state.render_distance - 4) / max(1, 12 - 4), "render"),
            ("Field of View", f"{int(state.fov)}",
             (state.fov - 60.0) / 60.0, "fov"),
            ("Mouse Sensitivity", f"{state.sensitivity:.4f}",
             (state.sensitivity - 0.0008) / 0.0042, "sens"),
        ]
        for i, (label, value_s, frac, key) in enumerate(rows):
            ry = y + i * 70
            _draw_text(self.surface, label, x, ry,
                       color=MCStyle.TEXT_PRIMARY, size=17, bold=True, shadow=True)
            _draw_text(self.surface, value_s, x + w - 100, ry,
                       color=MCStyle.TEXT_HEADING, size=17, bold=True, shadow=True)
            # Slider bar
            bar_x = x
            bar_y = ry + 28
            bar_w = w
            bar_h = 12
            pygame.draw.rect(self.surface, MCStyle.SLOT_BG_DARK, (bar_x, bar_y, bar_w, bar_h))
            pygame.draw.rect(self.surface, MCStyle.SLOT_BORDER_DARK,
                             (bar_x, bar_y, bar_w, bar_h), width=1)
            frac = max(0.0, min(1.0, frac))
            knob_w = 14
            knob_x = bar_x + int((bar_w - knob_w) * frac)
            _draw_button(self.surface, knob_x, bar_y - 2, knob_w, bar_h + 4, "",
                         hover=False, font_size=1)
            self._options_action_rects.append((f"slider:{key}", bar_x, bar_y - 4, bar_w, bar_h + 8))

    def _draw_options_sound(self, state: UIState, x: int, y: int, w: int):
        rows = [
            ("Master Volume", state.master_volume, "master"),
            ("Music",         state.music_volume,  "music"),
            ("Sound Effects", state.sfx_volume,    "sfx"),
        ]
        for i, (label, frac, key) in enumerate(rows):
            ry = y + i * 70
            pct = int(frac * 100)
            _draw_text(self.surface, label, x, ry,
                       color=MCStyle.TEXT_PRIMARY, size=17, bold=True, shadow=True)
            _draw_text(self.surface, f"{pct}%", x + w - 80, ry,
                       color=MCStyle.TEXT_HEADING, size=17, bold=True, shadow=True)
            bar_x = x
            bar_y = ry + 28
            bar_w = w
            bar_h = 12
            pygame.draw.rect(self.surface, MCStyle.SLOT_BG_DARK, (bar_x, bar_y, bar_w, bar_h))
            pygame.draw.rect(self.surface, MCStyle.SLOT_BORDER_DARK,
                             (bar_x, bar_y, bar_w, bar_h), width=1)
            frac = max(0.0, min(1.0, frac))
            knob_w = 14
            knob_x = bar_x + int((bar_w - knob_w) * frac)
            _draw_button(self.surface, knob_x, bar_y - 2, knob_w, bar_h + 4, "",
                         hover=False, font_size=1)
            self._options_action_rects.append((f"slider:vol_{key}", bar_x, bar_y - 4, bar_w, bar_h + 8))

    # ------------------------------------------------------------------
    # Stats / Achievements screen
    # ------------------------------------------------------------------

    def _draw_stats_screen(self, state: UIState):
        # Dim background (overlay)
        overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        overlay.fill(MCStyle.BG_OVERLAY)
        self.surface.blit(overlay, (0, 0))

        panel_w = 520
        panel_h = 420
        px = (self.w - panel_w) // 2
        py = (self.h - panel_h) // 2
        _draw_panel(self.surface, px, py, panel_w, panel_h)

        cx = px + panel_w // 2
        _draw_text(self.surface, "Statistics", cx - 70, py + 20,
                   color=MCStyle.TEXT_HEADING, size=32, bold=True, shadow=True)
        pygame.draw.line(self.surface, MCStyle.DIVIDER,
                         (px + 30, py + 70), (px + panel_w - 30, py + 70), 1)

        stats = state.stats or {}
        rows = [
            ("Blocks Broken",   str(stats.get("blocks_broken", 0))),
            ("Blocks Placed",   str(stats.get("blocks_placed", 0))),
            ("Mobs Killed",     str(stats.get("mobs_killed", 0))),
            ("Items Crafted",   str(stats.get("items_crafted", 0))),
            ("Distance Walked", f"{float(stats.get('distance_walked', 0.0)):.1f} m"),
        ]
        row_y = py + 90
        for label, value in rows:
            _draw_text(self.surface, label, px + 40, row_y,
                       color=MCStyle.TEXT_PRIMARY, size=18, bold=True, shadow=True)
            _draw_text(self.surface, value, px + panel_w - 40 - len(value) * 11, row_y,
                       color=MCStyle.TEXT_HEADING, size=18, bold=True, shadow=True)
            row_y += 36

        # Close button
        mx, my = state.mouse_x, state.mouse_y
        bw, bh = 160, 36
        bx = cx - bw // 2
        by = py + panel_h - bh - 20
        hover = (bx <= mx <= bx + bw) and (by <= my <= by + bh)
        _draw_button(self.surface, bx, by, bw, bh, "Close", hover=hover, font_size=18)
        self._stats_close_rect = (bx, by, bw, bh)

    # ------------------------------------------------------------------
    # Pause menu
    # ------------------------------------------------------------------

    def _draw_pause(self, state: UIState):
        # Dark overlay with subtle vignette feel
        overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        overlay.fill((5, 8, 18, 170))
        self.surface.blit(overlay, (0, 0))

        panel_w = 460
        panel_h = 600
        px = (self.w - panel_w) // 2
        py = (self.h - panel_h) // 2

        # Panel
        _draw_panel(self.surface, px, py, panel_w, panel_h,
                    bg=(8, 10, 22, 240), border=(70, 100, 200, 200), radius=18)

        cx = px + panel_w // 2

        # ── Title ──────────────────────────────────────────────
        title_f = _font(40, bold=True)
        title_s = title_f.render("Game Menu", True, MCStyle.TEXT_HEADING)
        title_sh = title_f.render("Game Menu", True, (60, 60, 20))
        tx = cx - title_s.get_width() // 2
        self.surface.blit(title_sh, (tx + 2, py + 24 + 2))
        self.surface.blit(title_s, (tx, py + 24))

        # Divider
        div_y = py + 84
        pygame.draw.line(self.surface, MCStyle.DIVIDER,
                         (px + 30, div_y), (px + panel_w - 30, div_y), 1)

        # ── Settings sliders ───────────────────────────────────
        sliders = [
            ("Render Distance", f"{state.render_distance}",
             (state.render_distance - 4) / max(1, 12 - 4)),
            ("FOV", f"{int(state.fov)}",
             (state.fov - 60.0) / max(0.01, 120.0 - 60.0)),
            ("Sensitivity", f"{state.sensitivity:.4f}",
             (state.sensitivity - 0.0008) / max(1e-6, 0.005 - 0.0008)),
        ]

        slider_top = py + 100
        slider_gap = 64
        for idx, (label, value_s, frac) in enumerate(sliders):
            sy = slider_top + idx * slider_gap
            sel = (idx == state.pause_selected)
            arrow = "> " if sel else "  "
            label_color = MCStyle.TEXT_HEADING if sel else MCStyle.TEXT_PRIMARY
            val_color = MCStyle.TEXT_HEADING if sel else MCStyle.TEXT_PRIMARY
            _draw_text(self.surface, arrow + label, cx - 145, sy,
                       color=label_color, size=18, bold=sel, shadow=True)
            _draw_text(self.surface, value_s, cx + 80, sy,
                       color=val_color, size=18, bold=True, shadow=True)
            # Slider track — flat MC-style
            bar_w = 340
            bar_h = 10
            bar_x = cx - bar_w // 2
            bar_y = sy + 28
            pygame.draw.rect(self.surface, MCStyle.SLOT_BG_DARK,
                             (bar_x, bar_y, bar_w, bar_h))
            pygame.draw.rect(self.surface, MCStyle.SLOT_BORDER_DARK,
                             (bar_x, bar_y, bar_w, bar_h), width=1)
            frac = max(0.0, min(1.0, frac))
            filled = int(bar_w * frac)
            # Knob
            hx = bar_x + filled
            knob_w, knob_h = 12, bar_h + 4
            knob_y = bar_y - 2
            _draw_button(self.surface, hx - knob_w // 2, knob_y, knob_w, knob_h, "",
                         hover=sel, font_size=1)

        _draw_text(self.surface, "Tab: select  Left/Right: adjust",
                   cx - 145, slider_top + 3 * slider_gap - 6,
                   color=MCStyle.TEXT_PRIMARY, size=13, shadow=True)

        # ── Game mode badge ────────────────────────────────────
        gm_y = slider_top + 3 * slider_gap + 14
        gm_label = ("CREATIVE MODE" if state.game_mode == "creative" else "SURVIVAL MODE")
        _draw_text(self.surface, gm_label, cx - 70, gm_y + 4,
                   color=MCStyle.TEXT_HEADING, size=17, bold=True, shadow=True)
        _draw_text(self.surface, "Press F4 to toggle", cx - 56, gm_y + 28,
                   color=MCStyle.TEXT_PRIMARY, size=12, shadow=True)

        # ── Buttons (Minecraft-style) ──────────────────────────
        mx, my = state.mouse_x, state.mouse_y
        buttons = [
            ("Back to Game",         "ESC"),
            ("Stats & Achievements", "L"),
            ("Controls...",          "K"),
            ("Toggle Debug (F3)",    "F3"),
            ("Save and Quit",        "Q"),
        ]
        btn_w = 380
        btn_h = 38
        btn_gap = 6
        btn_start_y = gm_y + 50
        self._pause_button_rects = []
        for i, (label, key) in enumerate(buttons):
            bx = cx - btn_w // 2
            by = btn_start_y + i * (btn_h + btn_gap)
            hover = (bx <= mx <= bx + btn_w) and (by <= my <= by + btn_h)
            _draw_button(self.surface, bx, by, btn_w, btn_h,
                         f"{label}  [{key}]", hover=hover, font_size=18)
            self._pause_button_rects.append((bx, by, btn_w, btn_h, label))

        # ── Footer tip ─────────────────────────────────────────
        _draw_text(self.surface, "OurCraft 2",
                   cx - 42, py + panel_h - 28,
                   color=MCStyle.TEXT_PRIMARY, size=14, shadow=True)

    # ------------------------------------------------------------------
    # Keybinds menu
    # ------------------------------------------------------------------

    # Human-readable labels for each bindable action
    _ACTION_LABELS = [
        ("move_forward",  "Move Forward"),
        ("move_back",     "Move Backward"),
        ("move_left",     "Strafe Left"),
        ("move_right",    "Strafe Right"),
        ("jump",          "Jump"),
        ("sneak",         "Sneak / Crouch"),
        ("sprint",        "Sprint"),
        ("inventory",     "Open Inventory"),
        ("drop",          "Save & Quit (paused)"),
        ("debug",         "Toggle Debug (F3)"),
        ("toggle_mode",   "Toggle Creative/Survival"),
        ("hotbar_1",      "Hotbar Slot 1"),
        ("hotbar_2",      "Hotbar Slot 2"),
        ("hotbar_3",      "Hotbar Slot 3"),
        ("hotbar_4",      "Hotbar Slot 4"),
        ("hotbar_5",      "Hotbar Slot 5"),
        ("hotbar_6",      "Hotbar Slot 6"),
        ("hotbar_7",      "Hotbar Slot 7"),
        ("hotbar_8",      "Hotbar Slot 8"),
        ("hotbar_9",      "Hotbar Slot 9"),
    ]

    def _draw_keybinds_menu(self, state: UIState) -> None:
        overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        overlay.fill((5, 8, 18, 180))
        self.surface.blit(overlay, (0, 0))

        panel_w = 520
        panel_h = min(680, self.h - 40)
        px = (self.w - panel_w) // 2
        py = (self.h - panel_h) // 2
        _draw_panel(self.surface, px, py, panel_w, panel_h,
                    bg=(8, 10, 22, 245), border=(140, 100, 255, 200), radius=18)

        cx = px + panel_w // 2

        # Title
        title_f = _font(36, bold=True)
        ts = title_f.render("CONTROLS", True, (210, 180, 255))
        self.surface.blit(ts, (cx - ts.get_width() // 2, py + 14))
        pygame.draw.line(self.surface, (80, 55, 150),
                         (px + 30, py + 58), (px + panel_w - 30, py + 58), 1)

        keybinds = state.keybinds or {}
        row_h = 30
        visible_rows = (panel_h - 100) // row_h
        max_scroll = max(0, len(self._ACTION_LABELS) - visible_rows)
        scroll = max(0, min(state.keybinds_scroll, max_scroll))
        state.keybinds_scroll = scroll

        # Store row rects for click detection (cleared each frame)
        self._kb_rects = []

        for vi, gi in enumerate(range(scroll, min(scroll + visible_rows, len(self._ACTION_LABELS)))):
            action, label = self._ACTION_LABELS[gi]
            ry = py + 68 + vi * row_h
            is_waiting = (state.rebinding_action == action)
            is_conflict = sum(1 for a, _ in self._ACTION_LABELS if keybinds.get(a) == keybinds.get(action) and a != action) > 0

            # Row highlight
            if is_waiting:
                pygame.draw.rect(self.surface, (60, 30, 90, 180),
                                 (px + 10, ry, panel_w - 20, row_h - 2), border_radius=4)
            elif vi % 2 == 0:
                pygame.draw.rect(self.surface, (15, 17, 35, 120),
                                 (px + 10, ry, panel_w - 20, row_h - 2), border_radius=4)

            self._kb_rects.append((px + 10, ry, panel_w - 20, row_h - 2, action))

            # Action label
            lc = (220, 220, 255) if not is_waiting else (255, 200, 100)
            _draw_text(self.surface, label, px + 20, ry + 6, color=lc, size=16, shadow=False)

            # Key name
            key_int = keybinds.get(action, 0)
            if is_waiting:
                key_str = "Press a key..."
                kc = (255, 180, 60)
            else:
                key_str = pygame.key.name(key_int).upper() if key_int else "UNBOUND"
                kc = (255, 100, 100) if is_conflict else (140, 220, 140)
            _draw_text(self.surface, key_str, px + panel_w - 160, ry + 6, color=kc, size=16, shadow=False)

        # Scroll hint
        if max_scroll > 0:
            pct = scroll / max_scroll
            bar_x = px + panel_w - 14
            bar_y = py + 68
            bar_h = panel_h - 100
            thumb_h = max(20, int(bar_h * visible_rows / len(self._ACTION_LABELS)))
            thumb_y = bar_y + int((bar_h - thumb_h) * pct)
            pygame.draw.rect(self.surface, (50, 40, 80), (bar_x, bar_y, 6, bar_h), border_radius=3)
            pygame.draw.rect(self.surface, (140, 100, 255), (bar_x, thumb_y, 6, thumb_h), border_radius=3)

        # Footer
        footer = "Click a row to rebind  |  ESC to go back  |  Scroll to see more"
        _draw_text(self.surface, footer, cx - 195, py + panel_h - 26,
                   color=(90, 75, 130), size=13, shadow=False)

    # ------------------------------------------------------------------
    # Inventory screen
    # ------------------------------------------------------------------

    def _draw_inventory_screen(self, state: UIState):
        # Dark background overlay
        overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        overlay.fill((8, 10, 20, 200))
        self.surface.blit(overlay, (0, 0))

        slot_size = 46
        pad = 4
        margin = 10

        # Main inventory: 3 rows x 9 cols
        inv_rows = 3
        inv_cols = 9
        inv_w = inv_cols * slot_size + (inv_cols - 1) * pad + margin * 2
        inv_h = inv_rows * slot_size + (inv_rows - 1) * pad + margin * 2

        # Crafting grid: 2x2
        craft_w = 2 * slot_size + pad + margin * 2
        craft_h = 2 * slot_size + pad + margin * 2

        # Result slot
        result_size = slot_size + 16
        result_w = result_size + margin * 2
        result_h = result_size + margin * 2

        # Hotbar
        hotbar_w = 9 * slot_size + 8 * pad + margin * 2
        hotbar_h = slot_size + margin * 2

        # Total panel width
        panel_w = max(inv_w + craft_w + result_w + pad * 4, hotbar_w + margin * 2) + margin * 2
        panel_h = margin + craft_h + pad * 2 + inv_h + pad * 2 + hotbar_h + margin * 2 + 40  # +40 for title
        px = (self.w - panel_w) // 2
        py = (self.h - panel_h) // 2

        _draw_panel(self.surface, px, py, panel_w, panel_h,
                    bg=(12, 14, 28, 245), border=(70, 90, 160, 200), radius=14)

        # Title
        _draw_text(self.surface, "INVENTORY", px + 16, py + 12,
                   color=(200, 210, 240), size=22, bold=True, shadow=False)

        # ── Crafting grid ──────────────────────────────────────
        cg_x = px + panel_w - craft_w - result_w - pad * 3 - margin
        cg_y = py + 50

        _draw_text(self.surface, "Crafting", cg_x, cg_y - 22,
                   color=(140, 160, 210), size=13, shadow=False)

        mx, my = state.mouse_x, state.mouse_y

        for r in range(2):
            for c in range(2):
                sx = cg_x + margin + c * (slot_size + pad)
                sy = cg_y + margin + r * (slot_size + pad)
                idx = r * 2 + c
                stack = state.craft_slots[idx] if idx < len(state.craft_slots) else None
                is_hover = (sx <= mx < sx + slot_size and sy <= my < sy + slot_size)
                self._draw_item_slot(sx, sy, slot_size, stack, slot_id=f"c{idx}", hover=is_hover)

        # ── Crafting result ────────────────────────────────────
        res_x = cg_x + craft_w + pad * 2
        res_y = cg_y + (craft_h - result_h) // 2
        _draw_text(self.surface, "Result", res_x, res_y - 22,
                   color=(140, 160, 210), size=13, shadow=False)
        rx = res_x + margin
        ry = res_y + margin
        is_hover_result = (rx <= mx < rx + result_size and ry <= my < ry + result_size)
        self._draw_item_slot(rx, ry, result_size,
                             state.craft_result, slot_id="result", highlight=True, hover=is_hover_result)

        # ── Armor slots (helmet / chestplate / leggings / boots) ──
        armor_x = px + margin
        armor_y = py + 58
        _draw_text(self.surface, "Armor", armor_x, armor_y - 20,
                   color=(140, 160, 210), size=13, shadow=False)
        for i in range(4):
            sx = armor_x + i * (slot_size + pad)
            sy = armor_y
            stack = state.armor_slots[i] if i < len(state.armor_slots) else None
            is_hover = (sx <= mx < sx + slot_size and sy <= my < sy + slot_size)
            self._draw_item_slot(sx, sy, slot_size, stack, slot_id=f"a{i}", hover=is_hover)

        # ── Main inventory (3x9) ───────────────────────────────
        inv_x = px + margin
        inv_y = cg_y + craft_h + pad * 3

        _draw_text(self.surface, "Items", inv_x, inv_y - 22,
                   color=(140, 160, 210), size=13, shadow=False)

        for r in range(inv_rows):
            for c in range(inv_cols):
                sx = inv_x + margin + c * (slot_size + pad)
                sy = inv_y + margin + r * (slot_size + pad)
                idx = r * inv_cols + c + 9  # Offset past hotbar
                stack = state.inv_slots[idx] if idx < len(state.inv_slots) else None
                is_hover = (sx <= mx < sx + slot_size and sy <= my < sy + slot_size)
                self._draw_item_slot(sx, sy, slot_size, stack, slot_id=f"m{idx}", hover=is_hover)

        # ── Hotbar ─────────────────────────────────────────────
        hb_x = px + (panel_w - hotbar_w) // 2
        hb_y = inv_y + inv_h + pad * 2

        _draw_text(self.surface, "Hotbar", hb_x, hb_y - 22,
                   color=(140, 160, 210), size=13, shadow=False)

        for i in range(9):
            sx = hb_x + margin + i * (slot_size + pad)
            sy = hb_y + margin
            stack = state.inv_slots[i] if i < len(state.inv_slots) else None
            is_active = (i == state.active_slot)
            is_hover = (sx <= mx < sx + slot_size and sy <= my < sy + slot_size)
            self._draw_item_slot(sx, sy, slot_size, stack, slot_id=f"h{i}",
                                 highlight=is_active, hover=is_hover)

    def _draw_item_slot(self, x: int, y: int, size: int,
                        stack: Optional[ItemStack],
                        slot_id: str = "",
                        highlight: bool = False,
                        hover: bool = False):
        rect = pygame.Rect(x, y, size, size)

        # Minecraft-style sunken slot interior
        _draw_inset_slot(self.surface, x, y, size)

        if highlight:
            # 2px white outline around active slot (vanilla hotbar selector)
            pygame.draw.rect(self.surface, MCStyle.SLOT_BORDER_LIGHT,
                             (x - 2, y - 2, size + 4, size + 4), width=2)

        if hover:
            overlay = pygame.Surface((size, size), pygame.SRCALPHA)
            overlay.fill(MCStyle.SLOT_HOVER_OVERLAY)
            self.surface.blit(overlay, (x, y))

        if stack is None or stack.is_empty():
            if hover:
                self._draw_tooltip(x, y, size, None)
            return

        icon_name = block_name(stack.block_id)
        icon = self.icons.get(icon_name)
        if icon is not None:
            icon_size = max(24, size - 14)
            scaled = pygame.transform.scale(icon, (icon_size, icon_size))
            self.surface.blit(scaled, (x + (size - icon_size) // 2,
                                       y + (size - icon_size) // 2))

        if stack.count > 1:
            count_text = str(stack.count)
            _draw_text(self.surface, count_text,
                       x + size - 6, y + size - 16,
                       color=(255, 255, 255), size=13, bold=True, shadow=True)

        # Durability bar (only for tools that have taken damage)
        self._draw_durability_bar(x, y, size, stack)

        if hover:
            self._draw_tooltip(x, y, size, stack)

    def _draw_durability_bar(self, x: int, y: int, size: int, stack: ItemStack):
        """Draw a colored bar at the bottom of the slot if the stack is a damaged tool.
        stack.durability holds REMAINING durability (set to max on craft, decremented
        on use). Bar fills left-to-right with green when full, shrinks from the right
        as the tool wears, turning yellow then red (Minecraft style)."""
        from .items import get_definition, is_item_id
        if not is_item_id(stack.block_id):
            return
        item_def = get_definition(stack.block_id)
        if item_def.max_durability <= 0:
            return
        # Only draw when tool has been used at least once.
        if stack.durability >= item_def.max_durability:
            return
        if stack.durability <= 0:
            return
        frac = stack.durability / item_def.max_durability
        bar_w = size - 8
        bar_h = 3
        bx = x + 4
        by = y + size - 7
        pygame.draw.rect(self.surface, (0, 0, 0, 220), (bx, by, bar_w, bar_h))
        if frac > 0.5:
            col = (60, 220, 60)
        elif frac > 0.25:
            col = (230, 210, 60)
        else:
            col = (230, 60, 60)
        fill = int(bar_w * frac)
        if fill > 0:
            pygame.draw.rect(self.surface, col, (bx, by, fill, bar_h))

    def _draw_tooltip(self, x: int, y: int, size: int, stack: Optional[ItemStack]):
        """Draw a tooltip above the slot showing the block's display name."""
        if stack is None or stack.is_empty():
            return
        display_name = block_display_name(stack.block_id)
        if not display_name:
            return

        f = _font(14, bold=True)
        text_s = f.render(display_name, True, (255, 255, 255))
        text_sh = f.render(display_name, True, (0, 0, 0))
        tw = text_s.get_width()
        th = text_s.get_height()

        pad_x = 8
        pad_y = 4
        tip_w = tw + pad_x * 2
        tip_h = th + pad_y * 2

        # Position tooltip above the slot
        tip_x = x + size // 2 - tip_w // 2
        tip_y = y - tip_h - 6

        # Clamp to screen edges
        if tip_x < 4:
            tip_x = 4
        if tip_x + tip_w > self.w - 4:
            tip_x = self.w - tip_w - 4
        if tip_y < 4:
            tip_y = y + size + 6  # Show below if no room above

        # Background
        _draw_panel(self.surface, tip_x, tip_y, tip_w, tip_h,
                    bg=(20, 22, 40, 235), border=(100, 130, 200, 200), radius=5)
        # Text with shadow
        self.surface.blit(text_sh, (tip_x + pad_x + 1, tip_y + pad_y + 1))
        self.surface.blit(text_s, (tip_x + pad_x, tip_y + pad_y))

    # ------------------------------------------------------------------
    # Crafting Table screen (3x3)
    # ------------------------------------------------------------------

    def _draw_crafting_table_screen(self, state: UIState):
        overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        overlay.fill((8, 10, 20, 200))
        self.surface.blit(overlay, (0, 0))

        slot_size = 46
        pad = 4
        margin = 10

        craft_cols = 3
        craft_rows = 3
        craft_w = craft_cols * slot_size + (craft_cols - 1) * pad + margin * 2
        craft_h = craft_rows * slot_size + (craft_rows - 1) * pad + margin * 2

        result_size = slot_size + 16
        result_w = result_size + margin * 2
        result_h = result_size + margin * 2

        inv_rows = 3
        inv_cols = 9
        inv_w = inv_cols * slot_size + (inv_cols - 1) * pad + margin * 2
        inv_h = inv_rows * slot_size + (inv_rows - 1) * pad + margin * 2

        hotbar_w = 9 * slot_size + 8 * pad + margin * 2
        hotbar_h = slot_size + margin * 2

        panel_w = max(craft_w + result_w + pad * 4, inv_w + margin * 2, hotbar_w + margin * 2) + margin * 2
        panel_h = margin + craft_h + pad * 2 + inv_h + pad * 2 + hotbar_h + margin * 2 + 40
        px = (self.w - panel_w) // 2
        py = (self.h - panel_h) // 2

        _draw_panel(self.surface, px, py, panel_w, panel_h,
                    bg=(12, 14, 28, 245), border=(70, 90, 160, 200), radius=14)

        _draw_text(self.surface, "CRAFTING TABLE", px + 16, py + 12,
                   color=(200, 210, 240), size=22, bold=True, shadow=False)

        mx, my = state.mouse_x, state.mouse_y

        # 3x3 crafting grid
        cg_x = px + margin
        cg_y = py + 50
        _draw_text(self.surface, "Crafting (3x3)", cg_x, cg_y - 22,
                   color=(140, 160, 210), size=13, shadow=False)

        for r in range(3):
            for c in range(3):
                sx = cg_x + margin + c * (slot_size + pad)
                sy = cg_y + margin + r * (slot_size + pad)
                idx = r * 3 + c
                stack = state.craft_slots_3x3[idx] if idx < len(state.craft_slots_3x3) else None
                is_hover = (sx <= mx < sx + slot_size and sy <= my < sy + slot_size)
                self._draw_item_slot(sx, sy, slot_size, stack, slot_id=f"t{idx}", hover=is_hover)

        # Result slot
        res_x = cg_x + craft_w + pad * 2
        res_y = cg_y + (craft_h - result_h) // 2
        _draw_text(self.surface, "Result", res_x, res_y - 22,
                   color=(140, 160, 210), size=13, shadow=False)
        rx = res_x + margin
        ry = res_y + margin
        is_hover_result = (rx <= mx < rx + result_size and ry <= my < ry + result_size)
        self._draw_item_slot(rx, ry, result_size,
                             state.craft_result_3x3, slot_id="tr", highlight=True, hover=is_hover_result)

        # Main inventory (3x9)
        inv_x = px + margin
        inv_y = cg_y + craft_h + pad * 3
        _draw_text(self.surface, "Items", inv_x, inv_y - 22,
                   color=(140, 160, 210), size=13, shadow=False)

        for r in range(inv_rows):
            for c in range(inv_cols):
                sx = inv_x + margin + c * (slot_size + pad)
                sy = inv_y + margin + r * (slot_size + pad)
                idx = r * inv_cols + c + 9
                stack = state.inv_slots[idx] if idx < len(state.inv_slots) else None
                is_hover = (sx <= mx < sx + slot_size and sy <= my < sy + slot_size)
                self._draw_item_slot(sx, sy, slot_size, stack, slot_id=f"m{idx}", hover=is_hover)

        # Hotbar
        hb_x = px + (panel_w - hotbar_w) // 2
        hb_y = inv_y + inv_h + pad * 2
        _draw_text(self.surface, "Hotbar", hb_x, hb_y - 22,
                   color=(140, 160, 210), size=13, shadow=False)

        for i in range(9):
            sx = hb_x + margin + i * (slot_size + pad)
            sy = hb_y + margin
            stack = state.inv_slots[i] if i < len(state.inv_slots) else None
            is_active = (i == state.active_slot)
            is_hover = (sx <= mx < sx + slot_size and sy <= my < sy + slot_size)
            self._draw_item_slot(sx, sy, slot_size, stack, slot_id=f"h{i}",
                                 highlight=is_active, hover=is_hover)

    # ------------------------------------------------------------------
    # Furnace screen
    # ------------------------------------------------------------------

    def _draw_furnace_screen(self, state: UIState):
        overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        overlay.fill((8, 10, 20, 200))
        self.surface.blit(overlay, (0, 0))

        SLOT = 46
        PAD = 4
        M = 10

        inv_rows, inv_cols = 3, 9
        inv_w = inv_cols * SLOT + (inv_cols - 1) * PAD + M * 2
        inv_h = inv_rows * SLOT + (inv_rows - 1) * PAD + M * 2
        hbar_w = 9 * SLOT + 8 * PAD + M * 2
        hbar_h = SLOT + M * 2

        furn_h = SLOT + 20 + SLOT + M * 2
        panel_w = max(inv_w, hbar_w) + M * 4
        panel_h = 40 + M + furn_h + PAD * 3 + inv_h + PAD * 2 + hbar_h + M * 2

        px = (self.w - panel_w) // 2
        py = (self.h - panel_h) // 2

        _draw_panel(self.surface, px, py, panel_w, panel_h,
                    bg=(12, 14, 28, 245), border=(70, 90, 160, 200), radius=14)
        _draw_text(self.surface, "FIRIN", px + 16, py + 12,
                   color=(200, 210, 240), size=22, bold=True, shadow=False)

        mx, my = state.mouse_x, state.mouse_y
        fg_x = px + M * 3
        fg_y = py + 50

        fi_x = fg_x + M
        fi_y = fg_y + M
        ff_x = fg_x + M
        ff_y = fg_y + M + SLOT + 20
        fo_x = fg_x + M + SLOT + 70
        fo_y = fg_y + M + (SLOT + 20 + SLOT) // 2 - SLOT // 2

        _draw_text(self.surface, "Ham Madde", fi_x, fi_y - 18,
                   color=(140, 160, 210), size=13, shadow=False)
        _draw_text(self.surface, "Yakit", ff_x, ff_y - 18,
                   color=(140, 160, 210), size=13, shadow=False)
        _draw_text(self.surface, "Urun", fo_x, fo_y - 18,
                   color=(140, 160, 210), size=13, shadow=False)

        self._draw_item_slot(fi_x, fi_y, SLOT, state.furnace_input, slot_id="fi",
                             hover=(fi_x <= mx < fi_x + SLOT and fi_y <= my < fi_y + SLOT))
        self._draw_item_slot(ff_x, ff_y, SLOT, state.furnace_fuel, slot_id="ff",
                             hover=(ff_x <= mx < ff_x + SLOT and ff_y <= my < ff_y + SLOT))
        self._draw_item_slot(fo_x, fo_y, SLOT + 16, state.furnace_output, slot_id="fo",
                             highlight=True,
                             hover=(fo_x <= mx < fo_x + SLOT + 16 and fo_y <= my < fo_y + SLOT + 16))

        # Progress arrow
        arrow_x = fg_x + M + SLOT + 10
        arrow_y = fg_y + M + (SLOT + 20) // 2 - 8
        fuel_frac = (state.furnace_fuel_left / max(state.furnace_fuel_max, 0.001))
        prog_frac = state.furnace_progress
        pygame.draw.rect(self.surface, (50, 55, 80, 220), (arrow_x, arrow_y, 50, 16), border_radius=3)
        pygame.draw.rect(self.surface, (80, 120, 220, 220), (arrow_x, arrow_y, int(50 * prog_frac), 16), border_radius=3)
        # Fuel flame indicator (small bar below)
        pygame.draw.rect(self.surface, (50, 55, 80, 220), (ff_x, ff_y - 8, SLOT, 6), border_radius=2)
        pygame.draw.rect(self.surface, (220, 140, 40, 220), (ff_x, ff_y - 8, int(SLOT * fuel_frac), 6), border_radius=2)

        # Player inventory
        inv_x = px + M
        inv_y = fg_y + furn_h + PAD * 3
        _draw_text(self.surface, "Esyalar", inv_x, inv_y - 22,
                   color=(140, 160, 210), size=13, shadow=False)
        for r in range(inv_rows):
            for c in range(inv_cols):
                sx = inv_x + M + c * (SLOT + PAD)
                sy = inv_y + M + r * (SLOT + PAD)
                idx = r * inv_cols + c + 9
                stack = state.inv_slots[idx] if idx < len(state.inv_slots) else None
                self._draw_item_slot(sx, sy, SLOT, stack, slot_id=f"m{idx}",
                                     hover=(sx <= mx < sx + SLOT and sy <= my < sy + SLOT))

        hb_x = px + (panel_w - hbar_w) // 2
        hb_y = inv_y + inv_h + PAD * 2
        _draw_text(self.surface, "Hotbar", hb_x, hb_y - 22,
                   color=(140, 160, 210), size=13, shadow=False)
        for i in range(9):
            sx = hb_x + M + i * (SLOT + PAD)
            sy = hb_y + M
            stack = state.inv_slots[i] if i < len(state.inv_slots) else None
            self._draw_item_slot(sx, sy, SLOT, stack, slot_id=f"h{i}",
                                 highlight=(i == state.active_slot),
                                 hover=(sx <= mx < sx + SLOT and sy <= my < sy + SLOT))

    # ------------------------------------------------------------------
    # Chest screen
    # ------------------------------------------------------------------

    def _draw_chest_screen(self, state: UIState):
        overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        overlay.fill((8, 10, 20, 200))
        self.surface.blit(overlay, (0, 0))

        SLOT = 46
        PAD = 4
        M = 10

        chest_rows, chest_cols = 3, 9
        inv_rows, inv_cols = 3, 9
        inv_w = inv_cols * SLOT + (inv_cols - 1) * PAD + M * 2
        inv_h = inv_rows * SLOT + (inv_rows - 1) * PAD + M * 2
        hbar_w = 9 * SLOT + 8 * PAD + M * 2
        hbar_h = SLOT + M * 2
        chest_w = chest_cols * SLOT + (chest_cols - 1) * PAD + M * 2
        chest_h = chest_rows * SLOT + (chest_rows - 1) * PAD + M * 2

        panel_w = max(chest_w, inv_w, hbar_w) + M * 4
        panel_h = 40 + M + chest_h + PAD * 3 + inv_h + PAD * 2 + hbar_h + M * 2

        px = (self.w - panel_w) // 2
        py = (self.h - panel_h) // 2

        _draw_panel(self.surface, px, py, panel_w, panel_h,
                    bg=(12, 14, 28, 245), border=(70, 90, 160, 200), radius=14)
        _draw_text(self.surface, "SANDIK", px + 16, py + 12,
                   color=(200, 210, 240), size=22, bold=True, shadow=False)

        mx, my = state.mouse_x, state.mouse_y
        cg_x = px + M
        cg_y = py + 50
        _draw_text(self.surface, "Sandik Icerigi", cg_x, cg_y - 22,
                   color=(140, 160, 210), size=13, shadow=False)

        for r in range(chest_rows):
            for c in range(chest_cols):
                sx = cg_x + M + c * (SLOT + PAD)
                sy = cg_y + M + r * (SLOT + PAD)
                idx = r * chest_cols + c
                stack = state.chest_slots[idx] if idx < len(state.chest_slots) else None
                self._draw_item_slot(sx, sy, SLOT, stack, slot_id=f"ch{idx}",
                                     hover=(sx <= mx < sx + SLOT and sy <= my < sy + SLOT))

        inv_x = px + M
        inv_y = cg_y + chest_h + PAD * 3
        _draw_text(self.surface, "Esyalar", inv_x, inv_y - 22,
                   color=(140, 160, 210), size=13, shadow=False)
        for r in range(inv_rows):
            for c in range(inv_cols):
                sx = inv_x + M + c * (SLOT + PAD)
                sy = inv_y + M + r * (SLOT + PAD)
                idx = r * inv_cols + c + 9
                stack = state.inv_slots[idx] if idx < len(state.inv_slots) else None
                self._draw_item_slot(sx, sy, SLOT, stack, slot_id=f"m{idx}",
                                     hover=(sx <= mx < sx + SLOT and sy <= my < sy + SLOT))

        hb_x = px + (panel_w - hbar_w) // 2
        hb_y = inv_y + inv_h + PAD * 2
        _draw_text(self.surface, "Hotbar", hb_x, hb_y - 22,
                   color=(140, 160, 210), size=13, shadow=False)
        for i in range(9):
            sx = hb_x + M + i * (SLOT + PAD)
            sy = hb_y + M
            stack = state.inv_slots[i] if i < len(state.inv_slots) else None
            self._draw_item_slot(sx, sy, SLOT, stack, slot_id=f"h{i}",
                                 highlight=(i == state.active_slot),
                                 hover=(sx <= mx < sx + SLOT and sy <= my < sy + SLOT))

    def _draw_dragged_item(self, state: UIState):
        item = state.dragged_item
        if item is None or item.is_empty():
            return
        size = 40
        x = state.mouse_x - size // 2
        y = state.mouse_y - size // 2
        rect = pygame.Rect(x, y, size, size)
        pygame.draw.rect(self.surface, (20, 24, 40, 200), rect, border_radius=5)
        pygame.draw.rect(self.surface, (100, 130, 220, 200), rect, width=2, border_radius=5)

        icon_name = block_name(item.block_id)
        icon = self.icons.get(icon_name)
        if icon is not None:
            icon_size = 28
            scaled = pygame.transform.scale(icon, (icon_size, icon_size))
            self.surface.blit(scaled, (x + (size - icon_size) // 2,
                                       y + (size - icon_size) // 2))
        if item.count > 1:
            _draw_text(self.surface, str(item.count),
                       x + size - 5, y + size - 15,
                       color=(255, 255, 255), size=12, bold=True, shadow=True)


def block_name(block_id: int) -> str:
    from .chunk import (
        BLOCK_AIR, BLOCK_ANDESITE, BLOCK_BOOKSHELF, BLOCK_BRICKS,
        BLOCK_CHEST, BLOCK_CLAY, BLOCK_COAL_BLOCK,
        BLOCK_COBBLESTONE, BLOCK_COPPER_BLOCK, BLOCK_COPPER_ORE,
        BLOCK_CRAFTING_TABLE, BLOCK_DEEPSLATE_COPPER,
        BLOCK_DIAMOND_BLOCK, BLOCK_DIORITE, BLOCK_DIRT,
        BLOCK_FURNACE, BLOCK_GLASS, BLOCK_GOLD_BLOCK,
        BLOCK_GRANITE, BLOCK_GRASS, BLOCK_GRAVEL,
        BLOCK_IRON_BLOCK, BLOCK_LEAVES, BLOCK_LOG,
        BLOCK_MUSHROOM_BROWN, BLOCK_MUSHROOM_RED, BLOCK_PLANKS,
        BLOCK_REDSTONE_BLOCK, BLOCK_SAND, BLOCK_SANDSTONE,
        BLOCK_SNOW, BLOCK_STICK, BLOCK_STONE,
        BLOCK_STONE_BRICKS, BLOCK_SUGAR_CANE,
        BLOCK_TNT, BLOCK_WATER,
    )
    from .items import ITEMS, is_item_id
    if is_item_id(block_id):
        defn = ITEMS.get(block_id)
        if defn and defn.texture_name:
            return defn.texture_name
        return "dirt"
    return {
        BLOCK_AIR: "air",
        BLOCK_GRASS: "grass_top",
        BLOCK_DIRT: "dirt",
        BLOCK_STONE: "stone",
        BLOCK_SAND: "sand",
        BLOCK_LOG: "wood_log_side",
        BLOCK_LEAVES: "leaves",
        BLOCK_WATER: "water",
        BLOCK_GLASS: "glass",
        BLOCK_SNOW: "snow",
        BLOCK_PLANKS: "planks",
        BLOCK_STICK: "stick",
        BLOCK_CRAFTING_TABLE: "crafting_top",
        BLOCK_COBBLESTONE: "cobblestone",
        BLOCK_GRAVEL: "gravel",
        BLOCK_FURNACE: "furnace_front",
        BLOCK_CHEST: "chest_front",
        BLOCK_GRANITE: "granite",
        BLOCK_ANDESITE: "andesite",
        BLOCK_DIORITE: "diorite",
        BLOCK_CLAY: "clay",
        BLOCK_MUSHROOM_RED: "mushroom_red",
        BLOCK_MUSHROOM_BROWN: "mushroom_brown",
        BLOCK_SUGAR_CANE: "sugar_cane",
        BLOCK_COAL_BLOCK: "coal_block",
        BLOCK_IRON_BLOCK: "iron_block",
        BLOCK_GOLD_BLOCK: "gold_block",
        BLOCK_DIAMOND_BLOCK: "diamond_block",
        BLOCK_REDSTONE_BLOCK: "redstone_block",
        BLOCK_COPPER_BLOCK: "copper_block",
        BLOCK_COPPER_ORE: "copper_ore",
        BLOCK_DEEPSLATE_COPPER: "deepslate_copper_ore",
        BLOCK_SANDSTONE: "sandstone",
        BLOCK_STONE_BRICKS: "stone_bricks",
        BLOCK_BRICKS: "bricks",
        BLOCK_BOOKSHELF: "bookshelf_side",
        BLOCK_TNT: "tnt_side",
    }.get(block_id, "dirt")


def block_display_name(block_id: int) -> str:
    """Return the Turkish display name for a block."""
    from .chunk import (
        BLOCK_AIR, BLOCK_ANDESITE, BLOCK_BEDROCK, BLOCK_BOOKSHELF,
        BLOCK_BRICKS, BLOCK_CHEST, BLOCK_CLAY, BLOCK_COAL_BLOCK,
        BLOCK_COBBLESTONE, BLOCK_COPPER_BLOCK, BLOCK_COPPER_ORE,
        BLOCK_CRAFTING_TABLE, BLOCK_DEEPSLATE_COPPER,
        BLOCK_DIAMOND_BLOCK, BLOCK_DIORITE, BLOCK_DIRT,
        BLOCK_FURNACE, BLOCK_GLASS, BLOCK_GOLD_BLOCK,
        BLOCK_GRANITE, BLOCK_GRASS, BLOCK_GRAVEL,
        BLOCK_IRON_BLOCK, BLOCK_LEAVES, BLOCK_LOG,
        BLOCK_MUSHROOM_BROWN, BLOCK_MUSHROOM_RED, BLOCK_PLANKS,
        BLOCK_REDSTONE_BLOCK, BLOCK_SAND, BLOCK_SANDSTONE,
        BLOCK_SNOW, BLOCK_STICK, BLOCK_STONE,
        BLOCK_STONE_BRICKS, BLOCK_SUGAR_CANE,
        BLOCK_TNT, BLOCK_WATER,
    )
    from .items import ITEMS
    item_def = ITEMS.get(block_id)
    if item_def:
        return item_def.name.replace("_", " ").title()
    return {
        BLOCK_AIR: "",
        BLOCK_GRASS: "Cimen",
        BLOCK_DIRT: "Toprak",
        BLOCK_STONE: "Tas",
        BLOCK_SAND: "Kum",
        BLOCK_LOG: "Odun",
        BLOCK_LEAVES: "Yaprak",
        BLOCK_WATER: "Su",
        BLOCK_BEDROCK: "Ana Kaya",
        BLOCK_SNOW: "Kar",
        BLOCK_GLASS: "Cam",
        BLOCK_PLANKS: "Tahta",
        BLOCK_STICK: "Cubuk",
        BLOCK_CRAFTING_TABLE: "Calisma Masasi",
        BLOCK_COBBLESTONE: "Kirik Tas",
        BLOCK_GRAVEL: "Cakil",
        BLOCK_FURNACE: "Firin",
        BLOCK_CHEST: "Sandik",
        BLOCK_GRANITE: "Granit",
        BLOCK_ANDESITE: "Andezit",
        BLOCK_DIORITE: "Diorit",
        BLOCK_CLAY: "Kil",
        BLOCK_MUSHROOM_RED: "Kirmizi Mantar",
        BLOCK_MUSHROOM_BROWN: "Kahve Mantar",
        BLOCK_SUGAR_CANE: "Seker Kamisi",
        BLOCK_COAL_BLOCK: "Komur Bloku",
        BLOCK_IRON_BLOCK: "Demir Bloku",
        BLOCK_GOLD_BLOCK: "Altin Bloku",
        BLOCK_DIAMOND_BLOCK: "Elmas Bloku",
        BLOCK_REDSTONE_BLOCK: "Redstone Bloku",
        BLOCK_COPPER_BLOCK: "Bakir Bloku",
        BLOCK_COPPER_ORE: "Bakir Cevheri",
        BLOCK_DEEPSLATE_COPPER: "Derin Bakir Cevheri",
        BLOCK_SANDSTONE: "Kumtasi",
        BLOCK_STONE_BRICKS: "Tas Tugla",
        BLOCK_BRICKS: "Tugla",
        BLOCK_BOOKSHELF: "Kitaplik",
        BLOCK_TNT: "TNT",
    }.get(block_id, f"Blok {block_id}")
