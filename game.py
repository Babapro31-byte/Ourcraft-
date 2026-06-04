from __future__ import annotations

import os
import random
import shutil
import sys
from dataclasses import dataclass
from typing import Optional, Tuple

import moderngl
import pygame

from .audio import AudioManager
from .chunk import (
    BLOCK_AIR, BLOCK_BED, BLOCK_CHEST, BLOCK_CRAFTING_TABLE, BLOCK_FURNACE,
    BLOCK_WOOL, is_solid
)
from .config import DEFAULT_KEYBINDS, load_config, save_config
from .inventory import ItemStack
from .entity import Mob
from .items import (
    FOODS, get_definition, is_spawn_egg, SPAWN_EGG_TO_MOB,
    ITEM_BOWL, ITEM_BUCKET, ITEM_FLINT_AND_STEEL, ITEM_LAVA_BUCKET,
    ITEM_MUSHROOM_STEW, ITEM_SHEARS, ITEM_WATER_BUCKET,
)
from .minimap import Minimap
from .player import InputState, Player, block_name
from .recipes import (
    CRAFT_RECIPES, CRAFT_RECIPES_3x3, FUEL_VALUES, SHAPELESS_RECIPES_2x2,
    SHAPELESS_RECIPES_3x3, SMELT_RECIPES, match_recipe,
)
from .renderer import Renderer
from .save_manager import SaveManager
from .texture_manager import TextureManager
from .ui import UI, UIState
from .world import World


@dataclass(slots=True)
class Settings:
    render_distance: int = 6


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("OurCraft 2")

        # Request MSAA 4× for smoother edges (before set_mode)
        try:
            pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1)
            pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, 4)
        except Exception:
            pass

        self.size = (1280, 720)
        flags = pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE
        pygame.display.set_mode(self.size, flags)

        # Initialize audio AFTER display but before other subsystems
        try:
            self.audio = AudioManager()
        except Exception as e:
            print(f"Warning: Audio system initialization failed: {e}")
            self.audio = None

        self.ctx = moderngl.create_context()
        self.ctx.enable(moderngl.DEPTH_TEST)
        try:
            self.ctx.enable(moderngl.MULTISAMPLE)
        except Exception:
            pass

        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.base_dir = os.path.join(self.project_root, "ourcraft2")

        # Load config
        self.cfg = load_config()

        self._ensure_textures()
        tm = TextureManager(self.base_dir)
        names = [
            "grass_top",
            "grass_side",
            "dirt",
            "stone",
            "sand",
            "wood_log_top",
            "wood_log_side",
            "leaves",
            "water",
            "bedrock",
            "snow",
            "glass",
            "cobblestone",
            "planks",
            "gravel",
            "lava",
            "coal_ore",
            "iron_ore",
            "gold_ore",
            "diamond_ore",
            "redstone_ore",
            "tall_grass",
            "flower_red",
            "flower_yellow",
            # Phase variety: stone variants + decoratives
            "granite",
            "andesite",
            "diorite",
            "clay",
            "mushroom_red",
            "mushroom_brown",
            "sugar_cane",
            # 7A per-face block textures
            "furnace_front",
            "furnace_top",
            "furnace_side",
            "chest_front",
            "chest_top",
            "chest_side",
            "crafting_front",
            "crafting_top",
            # 7B item textures (used in inventory UI via ui_icons)
            "stick",
            "coal",
            "iron_ingot",
            "gold_ingot",
            "diamond",
            "raw_beef",
            "cooked_beef",
            "apple",
            "chicken",
            "porkchop",
            "wool",
            "bone",
            "string",
            "rotten_flesh",
            "gunpowder",
            "leather",
            "feather",
            "raw_iron",
            "raw_gold",
            "redstone",
            "wooden_pickaxe",
            "stone_pickaxe",
            "iron_pickaxe",
            "diamond_pickaxe",
            "wooden_axe",
            "stone_axe",
            "iron_axe",
            "diamond_axe",
            "wooden_shovel",
            "stone_shovel",
            "iron_shovel",
            "diamond_shovel",
            "wooden_sword",
            "stone_sword",
            "iron_sword",
            "diamond_sword",
            "wooden_hoe",
            "stone_hoe",
            "iron_hoe",
            "diamond_hoe",
            # Phase 10: new blocks
            "coal_block",
            "iron_block",
            "gold_block",
            "diamond_block",
            "redstone_block",
            "sandstone",
            "stone_bricks",
            "bricks",
            "bookshelf_side",
            "tnt_side",
            "tnt_top",
            # Phase 10: new items
            "clay_ball",
            "brick",
            "paper",
            "book",
            "bowl",
            "mushroom_stew",
            "golden_apple",
            "sugar",
            "bone_meal",
            "shears",
            "flint_and_steel",
            "bucket",
            "water_bucket",
            "lava_bucket",
            # Deepslate layer (Minecraft 1.18+)
            "deepslate",
            "deepslate_coal_ore",
            "deepslate_iron_ore",
            "deepslate_gold_ore",
            "deepslate_redstone_ore",
            "deepslate_diamond_ore",
            "deepslate_copper_ore",
            # Copper (Minecraft-accurate: ore / deepslate / block + raw + ingot)
            "copper_ore",
            "copper_block",
            "raw_copper",
            "copper_ingot",
            # Mob billboard sprites (kept for backward-compat)
            "mob_cow", "mob_pig", "mob_sheep", "mob_chicken",
            "mob_zombie", "mob_skeleton", "mob_spider", "mob_creeper", "mob_villager",
            # 3D mob part textures
            "mob_cow_head", "mob_cow_body", "mob_cow_leg",
            "mob_pig_head", "mob_pig_body", "mob_pig_leg",
            "mob_sheep_head", "mob_sheep_wool", "mob_sheep_leg",
            "mob_chicken_head", "mob_chicken_body", "mob_chicken_leg", "mob_chicken_wing",
            "mob_zombie_head", "mob_zombie_body", "mob_zombie_arm", "mob_zombie_leg",
            "mob_skeleton_head", "mob_skeleton_body", "mob_skeleton_arm", "mob_skeleton_leg",
            "mob_spider_head", "mob_spider_body", "mob_spider_leg",
            "mob_creeper_head", "mob_creeper_body", "mob_creeper_leg",
            "mob_villager_head", "mob_villager_body", "mob_villager_arm", "mob_villager_leg",
            # Per-face head fronts
            "mob_cow_head_front", "mob_pig_head_front", "mob_sheep_head_front",
            "mob_chicken_head_front", "mob_zombie_head_front", "mob_skeleton_head_front",
            "mob_spider_head_front", "mob_creeper_head_front", "mob_villager_head_front",
            # Armor icons (4 pieces × leather/iron/gold/diamond)
            "leather_helmet", "leather_chestplate", "leather_leggings", "leather_boots",
            "iron_helmet", "iron_chestplate", "iron_leggings", "iron_boots",
            "gold_helmet", "gold_chestplate", "gold_leggings", "gold_boots",
            "diamond_helmet", "diamond_chestplate", "diamond_leggings", "diamond_boots",
            # Spawn eggs (creative)
            "spawn_egg_cow", "spawn_egg_pig", "spawn_egg_chicken", "spawn_egg_sheep",
            "spawn_egg_zombie", "spawn_egg_skeleton", "spawn_egg_spider",
            "spawn_egg_creeper", "spawn_egg_villager",
        ]
        atlas = tm.build_atlas(names)
        uv_by_block_face = tm.uv_by_block_face(atlas.uv_by_name)

        self.renderer = Renderer(self.ctx, self.base_dir, atlas, uv_by_block_face, fov=self.cfg.get("fov", 75.0))
        self.renderer.resize(*self.size)
        # Save uv table for particle system to use after world is created
        self._uv_by_block_face = uv_by_block_face

        self.ui = UI(self.size, atlas.ui_icons)
        self.settings = Settings(render_distance=int(self.cfg.get("render_distance", 6)))
        self.paused = False
        self.inventory_open = False
        self.crafting_table_open = False
        self.crafting_table_pos = None
        self.furnace_open = False
        self.open_furnace_pos = None
        self.furnace_states = {}   # (x,y,z) → {input, fuel, output, progress, fuel_left, fuel_max}
        self.chest_open = False
        self.open_chest_pos = None
        self.chest_inventories = {}  # (x,y,z) → [ItemStack] * 27
        self.debug = False
        # Keybinds menu state (persisted across frames)
        self._keybinds_open = False
        self._rebinding_action = None
        self._keybinds_scroll = 0

        # Inventory UI interaction state
        self.dragged_item: Optional[ItemStack] = None
        self.mouse_x = 0
        self.mouse_y = 0

        # Cooldown for block placement
        self._place_cooldown: float = 0.0

        # Game state machine
        self.game_state: str = "title"
        self._title_seed_input: str = ""
        self._title_entering_seed: bool = False
        self._new_world_mode: str = "survival"

        # In-game command bar ("/" key)
        self._cmd_active: bool = False
        self._cmd_text: str = ""
        self._cmd_error: str = ""
        self._cmd_error_timer: float = 0.0

        # Creative inventory (E in creative mode)
        self._creative_inv_open: bool = False
        self._creative_inv_scroll: int = 0
        self.world: Optional[World] = None
        self.player: Optional[Player] = None

        # World select state
        self._world_list: list = []
        self._world_select_scroll: int = 0
        self._world_select_hover: int = -1

        # 8A: Pause settings state — index of selected slider (0=render, 1=fov, 2=sens)
        self._pause_selected: int = 0
        # Options / pause tabbed UI: "video" | "controls" | "sound"
        self._options_tab: str = "video"
        self._pause_tab: str = "video"
        # Stats screen overlay (toggled from pause menu)
        self._stats_open: bool = False
        # Player stats — bumped on relevant gameplay events; persisted via SaveManager.
        self.stats = {
            "blocks_broken": 0,
            "blocks_placed": 0,
            "mobs_killed": 0,
            "items_crafted": 0,
            "distance_walked": 0.0,
        }

        # Minimap (top-down small world view)
        self.minimap = Minimap()

        self.clock = pygame.time.Clock()
        self._mouse_locked = False
        self._lock_mouse(False)  # unlocked on title screen

    # ------------------------------------------------------------------
    # Game state transitions
    # ------------------------------------------------------------------

    def _start_game(self, seed: int) -> None:
        """Create world + player for the given seed and switch to playing."""
        self.world = World(seed)
        # Wire particle UV table for block break debris
        self.world._uv_by_block_face = self._uv_by_block_face
        self.player = Player(sensitivity=self.cfg.get("sensitivity", 0.0023))
        self.paused = False
        self.inventory_open = False
        self.crafting_table_open = False
        self.furnace_open = False
        self.open_furnace_pos = None
        self.furnace_states = {}
        self.chest_open = False
        self.open_chest_pos = None
        self.chest_inventories = {}
        self.dragged_item = None
        self._place_cooldown = 0.0

        # Attach save manager
        sm = SaveManager(seed)
        self.world.save_manager = sm
        sm.load_meta(self.world)
        self.world.entities = sm.load_entities()
        self.chest_inventories = sm.load_chests()
        self.furnace_states = sm.load_furnaces()
        self.world.bed_positions = sm.load_beds()

        # Pre-generate spawn-area chunks (5x5 around origin)
        for dz in range(-2, 3):
            for dx in range(-2, 3):
                try:
                    self.world.get_chunk(dx, dz, generate=True)
                except Exception as e:
                    print(f"Warning: chunk ({dx},{dz}) generation failed: {e}")

        # Reset per-world stats (carried into player.stats below for save/load).
        self.stats = {
            "blocks_broken": 0,
            "blocks_placed": 0,
            "mobs_killed": 0,
            "items_crafted": 0,
            "distance_walked": 0.0,
        }
        # Load player save or find a safe spawn
        if not sm.load_player(self.player):
            # New player: establish a persistent world_spawn if missing, then place player there.
            if self.world.world_spawn is None:
                self.world.world_spawn = self._find_safe_spawn()
                sm.save_meta(self.world)
            sx, sy, sz = self.world.world_spawn
            self.player.pos[:] = (sx, sy, sz)
            # Apply selected game mode for new worlds
            self.player.game_mode = self._new_world_mode
            if self._new_world_mode == "creative":
                self.player.flying = True
            print(f"Spawned at world_spawn ({sx:.1f}, {sy:.1f}, {sz:.1f}), mode={self._new_world_mode}")
        else:
            # Existing player: ensure world_spawn exists (for worlds saved before this feature).
            if self.world.world_spawn is None:
                self.world.world_spawn = self._find_safe_spawn()
                sm.save_meta(self.world)
            # If the save had stats, restore them.
            loaded = getattr(self.player, "_loaded_stats", None)
            if isinstance(loaded, dict):
                for k, v in loaded.items():
                    if k in self.stats:
                        self.stats[k] = v
            print(f"Loaded save at ({self.player.pos[0]:.1f}, {self.player.pos[1]:.1f}, {self.player.pos[2]:.1f})")
        # Mirror stats onto the player so save_player can persist them.
        self.player.stats = self.stats

        self.world.update_streaming(tuple(self.player.pos.tolist()), self.settings.render_distance)
        self._lock_mouse(True)
        self.game_state = "playing"

    def _save_all(self) -> None:
        """Save player, meta, and all modified chunks."""
        if self.game_state != "playing" or self.world is None or self.player is None:
            return
        sm = self.world.save_manager
        if sm is None:
            return
        self.world.chest_inventories = self.chest_inventories
        self.world.furnace_states = self.furnace_states
        sm.save_all_modified(self.world, self.player)
        print("Game saved.")

    def _drain_pending_chest_loot(self) -> None:
        """Populate chest inventories for any chests placed during world gen."""
        if self.world is None:
            return
        pending = getattr(self.world, "pending_chest_loot", None)
        if not pending:
            return
        done = []
        for pos, items in pending.items():
            wx, wy, wz = pos
            cx, cz = self.world.chunk_coords(wx, wz)
            chunk = self.world.chunks.get((cx, cz))
            if chunk is None:
                continue
            done.append(pos)
            if pos in self.chest_inventories:
                continue
            slots = [ItemStack() for _ in range(27)]
            for i, stack in enumerate(items):
                if i >= 27:
                    break
                slots[i] = stack
            self.chest_inventories[pos] = slots
        for p in done:
            pending.pop(p, None)

    def _return_to_title(self) -> None:
        """Tear down world/player and return to the title screen."""
        if self.world is not None:
            self.world.shutdown_workers()
        self.world = None
        self.player = None
        self.paused = False
        self.inventory_open = False
        self.crafting_table_open = False
        self.furnace_open = False
        self.open_furnace_pos = None
        self.furnace_states = {}
        self.chest_open = False
        self.open_chest_pos = None
        self.chest_inventories = {}
        self.dragged_item = None
        self._title_seed_input = ""
        self._title_entering_seed = False
        self._lock_mouse(False)
        self.game_state = "title"

    def _handle_title_click(self, mx: int, my: int) -> None:
        cx = self.size[0] // 2
        btn_w, btn_h, gap = 320, 44, 10
        sp_y = self.size[1] // 2
        op_y = sp_y + btn_h + gap
        qt_y = op_y + btn_h + gap

        if self._title_entering_seed:
            # Mode selection buttons inside the seed panel
            panel_w, panel_h = 420, 220
            py = self.size[1] // 2 - panel_h // 2
            mbtn_w, mbtn_h = 170, 34
            total_mw = mbtn_w * 2 + 12
            mbtn_x0 = cx - total_mw // 2
            my0 = py + 128
            for i, m_key in enumerate(("survival", "creative")):
                mx0 = mbtn_x0 + i * (mbtn_w + 12)
                if mx0 <= mx <= mx0 + mbtn_w and my0 <= my <= my0 + mbtn_h:
                    self._new_world_mode = m_key
            return

        if cx - btn_w // 2 <= mx <= cx + btn_w // 2:
            if sp_y <= my <= sp_y + btn_h:
                self._enter_world_select()
            elif op_y <= my <= op_y + btn_h:
                self.game_state = "options"
                self._options_tab = "video"
            elif qt_y <= my <= qt_y + btn_h:
                pygame.quit()
                sys.exit()

    def _handle_options_click(self, mx: int, my: int) -> None:
        # Tabs
        for (tx, ty, tw, th, key) in getattr(self.ui, "_options_tab_rects", []):
            if tx <= mx <= tx + tw and ty <= my <= ty + th:
                self._options_tab = key
                return
        # Action / slider rects
        for entry in getattr(self.ui, "_options_action_rects", []):
            action, rx, ry, rw, rh = entry
            if not (rx <= mx <= rx + rw and ry <= my <= ry + rh):
                continue
            if action == "back":
                save_config(self.cfg)
                self.game_state = "title"
                return
            if action == "open_keybinds":
                # Reuse the keybinds UI; we are not in-game, so re-enter title afterwards.
                self._keybinds_open = True
                return
            if action.startswith("slider:"):
                self._options_apply_slider(action[7:], mx, rx, rw)
                return

    def _handle_options_drag(self, mx: int, my: int) -> None:
        for entry in getattr(self.ui, "_options_action_rects", []):
            action, rx, ry, rw, rh = entry
            if action.startswith("slider:") and rx <= mx <= rx + rw and ry <= my <= ry + rh:
                self._options_apply_slider(action[7:], mx, rx, rw)
                return

    def _options_apply_slider(self, key: str, mx: int, rx: int, rw: int) -> None:
        frac = max(0.0, min(1.0, (mx - rx) / max(1, rw)))
        if key == "render":
            self.settings.render_distance = int(round(4 + frac * (12 - 4)))
            self.cfg["render_distance"] = self.settings.render_distance
        elif key == "fov":
            self.cfg["fov"] = 60.0 + frac * 60.0
        elif key == "sens":
            self.cfg["sensitivity"] = 0.0008 + frac * 0.0042
            if self.player is not None:
                self.player.sensitivity = float(self.cfg["sensitivity"])
        elif key == "vol_master":
            self.cfg["master_volume"] = frac
            try:
                import pygame as _pg
                _pg.mixer.music.set_volume(frac * float(self.cfg.get("music_volume", 0.8)))
            except Exception:
                pass
        elif key == "vol_music":
            self.cfg["music_volume"] = frac
            try:
                import pygame as _pg
                _pg.mixer.music.set_volume(frac * float(self.cfg.get("master_volume", 1.0)))
            except Exception:
                pass
        elif key == "vol_sfx":
            self.cfg["sfx_volume"] = frac

    def _enter_world_select(self) -> None:
        self._world_list = SaveManager.list_worlds()
        self._world_select_scroll = 0
        self._world_select_hover = -1
        self.game_state = "world_select"

    def _pause_adjust(self, direction: int) -> None:
        """Adjust the currently selected pause-menu setting up/down.
        direction: +1 or -1. Mutates self.settings/self.cfg and self.player.sensitivity."""
        sel = self._pause_selected
        if sel == 0:
            self.settings.render_distance = max(4, min(12, self.settings.render_distance + direction))
            self.cfg["render_distance"] = self.settings.render_distance
        elif sel == 1:
            new_fov = float(self.cfg.get("fov", 75.0)) + direction * 2.0
            new_fov = max(60.0, min(120.0, new_fov))
            self.cfg["fov"] = new_fov
        elif sel == 2:
            cur = float(self.cfg.get("sensitivity", 0.0023))
            new_sens = max(0.0008, min(0.005, cur + direction * 0.0002))
            self.cfg["sensitivity"] = new_sens
            if self.player is not None:
                self.player.sensitivity = new_sens

    def _handle_world_select_click(self, mx: int, my: int) -> None:
        L = self.ui.world_select_layout()
        # New World button
        if L["list_x"] <= mx <= L["list_x"] + L["btn_w"]:
            if L["new_btn_y"] <= my <= L["new_btn_y"] + L["new_btn_h"]:
                self._start_game(random.randrange(1_000_000_000))
                return
            if L["back_btn_y"] <= my <= L["back_btn_y"] + L["back_btn_h"]:
                self.game_state = "title"
                return

        # World row clicks
        if not (L["list_x"] <= mx <= L["list_x"] + L["list_w"]):
            return
        for i, entry in enumerate(self._world_list[self._world_select_scroll:
                                                   self._world_select_scroll + L["max_visible"]]):
            row_y = L["list_y"] + i * L["row_h"]
            if not (row_y <= my <= row_y + L["row_h"] - 6):
                continue
            seed = entry[0]
            # Delete X button hit-test
            dx = L["list_x"] + L["list_w"] - L["delete_w"] - 8
            dy = row_y + (L["row_h"] - 6 - 28) // 2
            if dx <= mx <= dx + L["delete_w"] and dy <= my <= dy + 28:
                if SaveManager.delete_world(seed):
                    self._world_list = SaveManager.list_worlds()
                    max_scroll = max(0, len(self._world_list) - L["max_visible"])
                    self._world_select_scroll = min(self._world_select_scroll, max_scroll)
                return
            # Otherwise load the world
            self._start_game(seed)
            return

    def _update_world_select_hover(self, mx: int, my: int) -> None:
        L = self.ui.world_select_layout()
        self._world_select_hover = -1
        if not (L["list_x"] <= mx <= L["list_x"] + L["list_w"]):
            return
        for i in range(L["max_visible"]):
            row_y = L["list_y"] + i * L["row_h"]
            if row_y <= my <= row_y + L["row_h"] - 6:
                idx = self._world_select_scroll + i
                if 0 <= idx < len(self._world_list):
                    self._world_select_hover = idx
                return

    # ------------------------------------------------------------------
    # Spawn / helpers
    # ------------------------------------------------------------------

    def _is_night(self) -> bool:
        """time_of_day: 0=midnight, 0.5=noon, 1=midnight again. Night when sun is below horizon."""
        t = float(getattr(self.world, "time_of_day", 0.5)) % 1.0
        return t < 0.25 or t > 0.75

    def _try_sleep_in_bed(self, bed_pos: Tuple[int, int, int]) -> bool:
        """Right-click on a bed: set spawn, skip night to morning, restore HP/hunger."""
        if self.world.get_block(bed_pos[0], bed_pos[1], bed_pos[2]) != BLOCK_BED:
            return False
        entry = self.world.bed_positions.get(tuple(bed_pos))
        if entry is None:
            return False
        if not self._is_night():
            print("You can only sleep at night")
            return True
        # Set personal spawn point to foot of the bed
        foot = entry["foot"]
        self.player.spawn_point = (float(foot[0]), float(foot[1]), float(foot[2]))
        # Skip to morning (just after sunrise: time = 0.30 ≈ sunrise+a bit)
        self.world.time_of_day = 0.30
        # Restore HP and hunger
        self.player.health = 20.0
        self.player.hunger = 20.0
        # Persist immediately
        if self.world.save_manager is not None:
            try:
                self.world.save_manager.save_meta(self.world)
                self.world.save_manager.save_player(self.player)
            except Exception as e:
                print(f"Warning: bed save failed: {e}")
        print("Good morning! Spawn point set.")
        return True

    def _find_safe_spawn(self) -> Tuple[float, float, float]:
        """Search outward from (0,0) in a chunk-radius spiral for a safe above-water spawn."""
        from .chunk import is_solid
        sea_level = self.world.sea_level

        for radius in range(65):
            if radius == 0:
                ring = [(0, 0)]
            else:
                r = radius
                ring = []
                for i in range(-r, r + 1):
                    ring.append((i, -r))
                    ring.append((i, r))
                for j in range(-r + 1, r):
                    ring.append((-r, j))
                    ring.append((r, j))

            for cx, cz in ring:
                wx = cx * 16 + 8
                wz = cz * 16 + 8
                # Force-generate the candidate chunk so get_block sees real terrain
                # (previously, distant unloaded chunks returned AIR and the player fell through).
                try:
                    self.world.get_chunk(cx, cz, generate=True)
                except Exception:
                    continue
                h = self.world.terrain_height(wx, wz)
                if h < sea_level + 1:
                    continue
                # Need 3 clear air blocks above the surface
                clear = True
                for dy in range(1, 4):
                    if is_solid(self.world.get_block(wx, h + dy, wz)):
                        clear = False
                        break
                if clear:
                    return (float(wx) + 0.5, float(h + 1), float(wz) + 0.5)

        # Fallback: just go above sea level at origin
        h = self.world.terrain_height(0, 0)
        return (0.5, float(max(h + 1, sea_level + 5)), 0.5)

    def _ensure_textures(self):
        dst = os.path.join(self.base_dir, "textures")
        os.makedirs(dst, exist_ok=True)

        need = [
            "grass_top.png",
            "grass_side.png",
            "dirt.png",
            "stone.png",
            "sand.png",
            "wood_log_top.png",
            "wood_log_side.png",
            "leaves.png",
            "water.png",
            "bedrock.png",
            "snow.png",
            "glass.png",
            "cobblestone.png",
            "planks.png",
            "gravel.png",
            "lava.png",
            "coal_ore.png",
            "iron_ore.png",
            "gold_ore.png",
            "diamond_ore.png",
            "redstone_ore.png",
            "tall_grass.png",
            "flower_red.png",
            "flower_yellow.png",
            # 7A per-face block textures
            "furnace_front.png",
            "furnace_top.png",
            "furnace_side.png",
            "chest_front.png",
            "chest_top.png",
            "chest_side.png",
            "crafting_front.png",
            "crafting_top.png",
            # 7B item textures
            "stick.png",
            "coal.png",
            "iron_ingot.png",
            "gold_ingot.png",
            "diamond.png",
            "raw_beef.png",
            "cooked_beef.png",
            "apple.png",
            "chicken.png",
            "porkchop.png",
            "wool.png",
            "bone.png",
            "string.png",
            "rotten_flesh.png",
            "gunpowder.png",
            "raw_iron.png",
            "raw_gold.png",
            "redstone.png",
            "wooden_pickaxe.png",
            "stone_pickaxe.png",
            "iron_pickaxe.png",
            "diamond_pickaxe.png",
            "wooden_axe.png",
            "stone_axe.png",
            "iron_axe.png",
            "diamond_axe.png",
            "wooden_shovel.png",
            "stone_shovel.png",
            "iron_shovel.png",
            "diamond_shovel.png",
            "wooden_sword.png",
            "stone_sword.png",
            "iron_sword.png",
            "diamond_sword.png",
            "wooden_hoe.png",
            "stone_hoe.png",
            "iron_hoe.png",
            "diamond_hoe.png",
            # Phase 10: new blocks
            "coal_block.png",
            "iron_block.png",
            "gold_block.png",
            "diamond_block.png",
            "redstone_block.png",
            "sandstone.png",
            "stone_bricks.png",
            "bricks.png",
            "bookshelf_side.png",
            "tnt_side.png",
            "tnt_top.png",
            # Phase 10: new items
            "clay_ball.png",
            "brick.png",
            "paper.png",
            "book.png",
            "bowl.png",
            "mushroom_stew.png",
            "golden_apple.png",
            "sugar.png",
            "bone_meal.png",
            "shears.png",
            "flint_and_steel.png",
            "bucket.png",
            "water_bucket.png",
            "lava_bucket.png",
            # Spawn eggs (creative)
            "spawn_egg_cow.png",
            "spawn_egg_pig.png",
            "spawn_egg_chicken.png",
            "spawn_egg_sheep.png",
            "spawn_egg_zombie.png",
            "spawn_egg_skeleton.png",
            "spawn_egg_spider.png",
            "spawn_egg_creeper.png",
            "spawn_egg_villager.png",
        ]

        src = os.path.join(self.project_root, "textures")
        if not os.path.isdir(src):
            missing = [n for n in need if not os.path.isfile(os.path.join(dst, n))]
            if missing:
                try:
                    from .create_textures import main as _gen_textures
                    _gen_textures()
                    still_missing = [n for n in missing if not os.path.isfile(os.path.join(dst, n))]
                    if still_missing:
                        raise FileNotFoundError(os.path.join(dst, still_missing[0]))
                except Exception:
                    raise FileNotFoundError(os.path.join(dst, missing[0]))
            return

        # Always copy fresh textures from root textures/ (overwrite stale/corrupted ones)
        for n in need:
            sp = os.path.join(src, n)
            dp = os.path.join(dst, n)
            if os.path.isfile(sp):
                shutil.copyfile(sp, dp)

        missing2 = [n for n in need if not os.path.isfile(os.path.join(dst, n))]
        if missing2:
            try:
                from .create_textures import main as _gen_textures
                _gen_textures()
                still_missing = [n for n in missing2 if not os.path.isfile(os.path.join(dst, n))]
                if still_missing:
                    raise FileNotFoundError(os.path.join(dst, still_missing[0]))
            except Exception:
                raise FileNotFoundError(os.path.join(dst, missing2[0]))

    def _key(self, action: str) -> int:
        """Return the pygame key constant for the given action."""
        return self.cfg.get("keybinds", {}).get(action, DEFAULT_KEYBINDS.get(action, 0))

    def _toggle_game_mode(self) -> None:
        if self.player is None:
            return
        if self.player.game_mode == "survival":
            self.player.game_mode = "creative"
            self.player.flying = True
        else:
            self.player.game_mode = "survival"
            self.player.flying = False

    def _execute_command(self, text: str) -> None:
        """Parse and run a slash command typed in the command bar."""
        if self.player is None:
            return
        cmd = text.strip().lower()
        if cmd == "creative":
            self.player.game_mode = "creative"
            self.player.flying = True
        elif cmd == "survival":
            self.player.game_mode = "survival"
            self.player.flying = False
        else:
            self._cmd_error = f"Bilinmeyen komut: /{text.strip()}"
            self._cmd_error_timer = 3.0

    def _handle_creative_inv_click(self, mx: int, my: int) -> None:
        """Give player the clicked item from the creative inventory (infinite stock)."""
        if self.player is None:
            return
        rects = getattr(self.ui, "_creative_item_rects", [])
        for (cx_, cy_, cw, ch, item_id) in rects:
            if cx_ <= mx <= cx_ + cw and cy_ <= my <= cy_ + ch:
                from .items import get_definition, is_item_id
                if is_item_id(item_id):
                    defn = get_definition(item_id)
                    count = 1 if defn.max_stack == 1 else defn.max_stack
                else:
                    count = 64
                self.player.inventory.add_item(item_id, count)
                break

    def _lock_mouse(self, locked: bool):
        self._mouse_locked = bool(locked)
        pygame.event.set_grab(self._mouse_locked)
        pygame.mouse.set_visible(not self._mouse_locked)
        pygame.mouse.get_rel()

    # ------------------------------------------------------------------
    # Crafting helpers
    # ------------------------------------------------------------------

    def _tick_furnaces(self, dt: float) -> None:
        for fs in self.furnace_states.values():
            inp = fs['input']
            if inp.is_empty():
                fs['progress'] = 0.0
                continue
            recipe = SMELT_RECIPES.get(inp.block_id)
            if recipe is None:
                fs['progress'] = 0.0
                continue
            result_id, result_count, smelt_time = recipe
            if fs['fuel_left'] <= 0.0:
                fuel = fs['fuel']
                if not fuel.is_empty():
                    fval = FUEL_VALUES.get(fuel.block_id, 0.0)
                    if fval > 0.0:
                        fuel.count -= 1
                        if fuel.count <= 0:
                            fs['fuel'] = ItemStack()
                        fs['fuel_left'] = fval
                        fs['fuel_max'] = fval
                else:
                    fs['progress'] = 0.0
                    continue
            fs['fuel_left'] = max(0.0, fs['fuel_left'] - dt)
            progress_rate = 1.0 / smelt_time
            fs['progress'] = min(1.0, fs['progress'] + dt * progress_rate)
            if fs['progress'] >= 1.0:
                out = fs['output']
                if out.is_empty():
                    fs['output'] = ItemStack(result_id, result_count)
                elif out.block_id == result_id and out.count + result_count <= 64:
                    out.count += result_count
                else:
                    continue
                fs['progress'] = 0.0
                inp.count -= 1
                if inp.count <= 0:
                    fs['input'] = ItemStack()

    def _update_crafting(self):
        """Recalculate crafting result based on current grid contents."""
        inv = self.player.inventory
        if self.crafting_table_open:
            pattern = tuple(
                tuple(inv.craft_grid_3x3[r * 3 + c].block_id for c in range(3))
                for r in range(3)
            )
            recipe = match_recipe(pattern, CRAFT_RECIPES_3x3 + CRAFT_RECIPES, SHAPELESS_RECIPES_3x3)
            if recipe:
                dur = get_definition(recipe.result_id).max_durability
                inv.craft_result_3x3 = ItemStack(recipe.result_id, recipe.result_count, dur)
            else:
                inv.craft_result_3x3 = ItemStack()
        else:
            pattern = inv.get_craft_pattern()
            recipe = match_recipe(pattern, CRAFT_RECIPES, SHAPELESS_RECIPES_2x2)
            if recipe:
                dur = get_definition(recipe.result_id).max_durability
                inv.craft_result = ItemStack(recipe.result_id, recipe.result_count, dur)
            else:
                inv.craft_result = ItemStack()

    def _return_crafting_grid_items(self, grid_3x3: bool = False) -> None:
        """Return crafting grid items to the main inventory when UI closes.
        Items that don't fit stay in the grid (no drop entity system yet)."""
        if self.player is None:
            return
        inv = self.player.inventory
        grid = inv.craft_grid_3x3 if grid_3x3 else inv.craft_grid
        for stack in grid:
            if stack.is_empty():
                continue
            remaining = inv.add_item(stack.block_id, stack.count)
            stack.count = remaining
            if remaining <= 0:
                stack.block_id = BLOCK_AIR
                stack.count = 0
        if grid_3x3:
            inv.craft_result_3x3 = ItemStack()
        else:
            inv.craft_result = ItemStack()

    def _consume_crafting_grid(self):
        """Remove one item from each non-empty crafting slot when taking result."""
        inv = self.player.inventory
        if self.crafting_table_open:
            for i in range(len(inv.craft_grid_3x3)):
                s = inv.craft_grid_3x3[i]
                if not s.is_empty():
                    s.count -= 1
                    if s.count <= 0:
                        s.block_id = BLOCK_AIR
                        s.count = 0
        else:
            for i in range(len(inv.craft_grid)):
                s = inv.craft_grid[i]
                if not s.is_empty():
                    s.count -= 1
                    if s.count <= 0:
                        s.block_id = BLOCK_AIR
                        s.count = 0
        self._update_crafting()

    # ------------------------------------------------------------------
    # Inventory slot helpers
    # ------------------------------------------------------------------

    def _slot_at_point(self, mx: int, my: int) -> Optional[str]:
        """Determine which inventory slot is under the mouse. Returns slot id like 'h0', 'm9', 'c0', 'result'."""
        slot_size = 46
        pad = 4
        margin = 10

        if self.furnace_open:
            return self._furnace_slot_at_point(mx, my, slot_size, pad, margin)
        if self.chest_open:
            return self._chest_slot_at_point(mx, my, slot_size, pad, margin)

        inv_rows = 3
        inv_cols = 9
        inv_w = inv_cols * slot_size + (inv_cols - 1) * pad + margin * 2
        inv_h = inv_rows * slot_size + (inv_rows - 1) * pad + margin * 2

        hotbar_w = 9 * slot_size + 8 * pad + margin * 2
        hotbar_h = slot_size + margin * 2

        # Crafting table uses 3x3 grid, normal inventory uses 2x2 grid
        if self.crafting_table_open:
            craft_w = 3 * slot_size + 2 * pad + margin * 2
            craft_h = 3 * slot_size + 2 * pad + margin * 2
            result_size = slot_size + 16
            result_w = result_size + margin * 2
            result_h = result_size + margin * 2
            panel_w = max(craft_w + result_w + pad * 4, inv_w + margin * 2, hotbar_w + margin * 2) + margin * 2
            panel_h = margin + craft_h + pad * 2 + inv_h + pad * 2 + hotbar_h + margin * 2 + 40
            px = (self.size[0] - panel_w) // 2
            py = (self.size[1] - panel_h) // 2
            cg_x = px + margin
            cg_y = py + 50
        else:
            # Normal inventory layout
            craft_w = 2 * slot_size + pad + margin * 2
            craft_h = 2 * slot_size + pad + margin * 2
            result_size = slot_size + 16
            result_w = result_size + margin * 2
            result_h = result_size + margin * 2
            panel_w = max(inv_w + craft_w + result_w + pad * 4, hotbar_w + margin * 2) + margin * 2
            panel_h = margin + craft_h + pad * 2 + inv_h + pad * 2 + hotbar_h + margin * 2 + 40
            px = (self.size[0] - panel_w) // 2
            py = (self.size[1] - panel_h) // 2
            cg_x = px + panel_w - craft_w - result_w - pad * 3 - margin
            cg_y = py + 50

        # Armor slots — only in the normal inventory screen (left of crafting grid)
        if not self.crafting_table_open:
            armor_x = px + margin
            armor_y = py + 58
            for i in range(4):
                sx = armor_x + i * (slot_size + pad)
                sy = armor_y
                if sx <= mx < sx + slot_size and sy <= my < sy + slot_size:
                    return f"a{i}"

        # Crafting grid (2x2 or 3x3 depending on crafting_table_open)
        craft_size = 3 if self.crafting_table_open else 2
        for r in range(craft_size):
            for c in range(craft_size):
                sx = cg_x + margin + c * (slot_size + pad)
                sy = cg_y + margin + r * (slot_size + pad)
                if sx <= mx < sx + slot_size and sy <= my < sy + slot_size:
                    prefix = "t" if self.crafting_table_open else "c"
                    return f"{prefix}{r * craft_size + c}"

        # Result slot
        res_x = cg_x + craft_w + pad * 2
        res_y = cg_y + (craft_h - result_h) // 2
        rx = res_x + margin
        ry = res_y + margin
        if rx <= mx < rx + result_size and ry <= my < ry + result_size:
            return "tr" if self.crafting_table_open else "result"

        # Main inventory (3x9)
        if self.crafting_table_open:
            inv_x = px + margin
        else:
            inv_x = px + margin
        inv_y = cg_y + craft_h + pad * 3
        for r in range(inv_rows):
            for c in range(inv_cols):
                sx = inv_x + margin + c * (slot_size + pad)
                sy = inv_y + margin + r * (slot_size + pad)
                if sx <= mx < sx + slot_size and sy <= my < sy + slot_size:
                    return f"m{r * inv_cols + c + 9}"

        # Hotbar
        hb_x = px + (panel_w - hotbar_w) // 2
        hb_y = inv_y + inv_h + pad * 2
        for i in range(9):
            sx = hb_x + margin + i * (slot_size + pad)
            sy = hb_y + margin
            if sx <= mx < sx + slot_size and sy <= my < sy + slot_size:
                return f"h{i}"

        return None

    def _furnace_slot_at_point(self, mx: int, my: int, SLOT: int, PAD: int, M: int) -> Optional[str]:
        inv_cols = 9
        inv_w = inv_cols * SLOT + (inv_cols - 1) * PAD + M * 2
        hbar_w = 9 * SLOT + 8 * PAD + M * 2
        inv_h = 3 * SLOT + 2 * PAD + M * 2
        furn_h = SLOT + 20 + SLOT + M * 2
        panel_w = max(inv_w, hbar_w) + M * 4
        panel_h = 40 + M + furn_h + PAD * 3 + inv_h + PAD * 2 + SLOT + M * 2 + M * 2
        px = (self.size[0] - panel_w) // 2
        py = (self.size[1] - panel_h) // 2
        fg_x = px + M * 3
        fg_y = py + 50
        fi_x = fg_x + M;  fi_y = fg_y + M
        ff_x = fg_x + M;  ff_y = fg_y + M + SLOT + 20
        fo_x = fg_x + M + SLOT + 70;  fo_y = fg_y + M + (SLOT + 20 + SLOT) // 2 - SLOT // 2
        if fi_x <= mx < fi_x + SLOT and fi_y <= my < fi_y + SLOT:
            return "fi"
        if ff_x <= mx < ff_x + SLOT and ff_y <= my < ff_y + SLOT:
            return "ff"
        if fo_x <= mx < fo_x + SLOT + 16 and fo_y <= my < fo_y + SLOT + 16:
            return "fo"
        inv_x = px + M;  inv_y = fg_y + furn_h + PAD * 3
        for r in range(3):
            for c in range(inv_cols):
                sx = inv_x + M + c * (SLOT + PAD)
                sy = inv_y + M + r * (SLOT + PAD)
                if sx <= mx < sx + SLOT and sy <= my < sy + SLOT:
                    return f"m{r * inv_cols + c + 9}"
        hb_x = px + (panel_w - hbar_w) // 2;  hb_y = inv_y + inv_h + PAD * 2
        for i in range(9):
            sx = hb_x + M + i * (SLOT + PAD);  sy = hb_y + M
            if sx <= mx < sx + SLOT and sy <= my < sy + SLOT:
                return f"h{i}"
        return None

    def _chest_slot_at_point(self, mx: int, my: int, SLOT: int, PAD: int, M: int) -> Optional[str]:
        inv_cols = 9
        inv_w = inv_cols * SLOT + (inv_cols - 1) * PAD + M * 2
        hbar_w = 9 * SLOT + 8 * PAD + M * 2
        inv_h = 3 * SLOT + 2 * PAD + M * 2
        chest_h = 3 * SLOT + 2 * PAD + M * 2
        panel_w = max(inv_w, hbar_w) + M * 4
        panel_h = 40 + M + chest_h + PAD * 3 + inv_h + PAD * 2 + SLOT + M * 2 + M * 2
        px = (self.size[0] - panel_w) // 2
        py = (self.size[1] - panel_h) // 2
        cg_x = px + M;  cg_y = py + 50
        for r in range(3):
            for c in range(inv_cols):
                sx = cg_x + M + c * (SLOT + PAD)
                sy = cg_y + M + r * (SLOT + PAD)
                if sx <= mx < sx + SLOT and sy <= my < sy + SLOT:
                    return f"ch{r * inv_cols + c}"
        inv_x = px + M;  inv_y = cg_y + chest_h + PAD * 3
        for r in range(3):
            for c in range(inv_cols):
                sx = inv_x + M + c * (SLOT + PAD)
                sy = inv_y + M + r * (SLOT + PAD)
                if sx <= mx < sx + SLOT and sy <= my < sy + SLOT:
                    return f"m{r * inv_cols + c + 9}"
        hb_x = px + (panel_w - hbar_w) // 2;  hb_y = inv_y + inv_h + PAD * 2
        for i in range(9):
            sx = hb_x + M + i * (SLOT + PAD);  sy = hb_y + M
            if sx <= mx < sx + SLOT and sy <= my < sy + SLOT:
                return f"h{i}"
        return None

    def _get_furnace_state(self, pos=None):
        key = pos or self.open_furnace_pos
        if key not in self.furnace_states:
            self.furnace_states[key] = {
                'input': ItemStack(), 'fuel': ItemStack(), 'output': ItemStack(),
                'progress': 0.0, 'fuel_left': 0.0, 'fuel_max': 1.0,
            }
        return self.furnace_states[key]

    def _get_stack(self, slot_id: str) -> Optional[ItemStack]:
        inv = self.player.inventory
        if slot_id == "fi":
            return self._get_furnace_state()['input']
        elif slot_id == "ff":
            return self._get_furnace_state()['fuel']
        elif slot_id == "fo":
            return self._get_furnace_state()['output']
        elif slot_id == "tr":
            return inv.craft_result_3x3
        elif slot_id == "result":
            return inv.craft_result
        elif slot_id.startswith("a"):
            return inv.armor[int(slot_id[1:])]
        elif slot_id.startswith("ch"):
            idx = int(slot_id[2:])
            pos = self.open_chest_pos
            if pos not in self.chest_inventories:
                self.chest_inventories[pos] = [ItemStack() for _ in range(27)]
            return self.chest_inventories[pos][idx]
        elif slot_id.startswith("t"):
            idx = int(slot_id[1:])
            return inv.craft_grid_3x3[idx]
        elif slot_id.startswith("h"):
            idx = int(slot_id[1:])
            return inv.hotbar[idx]
        elif slot_id.startswith("m"):
            idx = int(slot_id[1:])
            if idx < inv.HOTBAR_SIZE:
                return inv.hotbar[idx]
            return inv.main[idx - inv.HOTBAR_SIZE]
        elif slot_id.startswith("c"):
            idx = int(slot_id[1:])
            return inv.craft_grid[idx]
        return None

    def _set_stack(self, slot_id: str, stack: ItemStack):
        inv = self.player.inventory
        if slot_id == "fi":
            self._get_furnace_state()['input'] = stack
        elif slot_id == "ff":
            self._get_furnace_state()['fuel'] = stack
        elif slot_id == "fo":
            self._get_furnace_state()['output'] = stack
        elif slot_id == "tr":
            inv.craft_result_3x3 = stack
        elif slot_id == "result":
            inv.craft_result = stack
        elif slot_id.startswith("a"):
            inv.armor[int(slot_id[1:])] = stack
        elif slot_id.startswith("ch"):
            idx = int(slot_id[2:])
            pos = self.open_chest_pos
            if pos not in self.chest_inventories:
                self.chest_inventories[pos] = [ItemStack() for _ in range(27)]
            self.chest_inventories[pos][idx] = stack
        elif slot_id.startswith("t"):
            idx = int(slot_id[1:])
            inv.craft_grid_3x3[idx] = stack
            self._update_crafting()
        elif slot_id.startswith("h"):
            idx = int(slot_id[1:])
            inv.hotbar[idx] = stack
        elif slot_id.startswith("m"):
            idx = int(slot_id[1:])
            if idx < inv.HOTBAR_SIZE:
                inv.hotbar[idx] = stack
            else:
                inv.main[idx - inv.HOTBAR_SIZE] = stack
        elif slot_id.startswith("c"):
            idx = int(slot_id[1:])
            inv.craft_grid[idx] = stack
            self._update_crafting()

    def _shift_move_stack(self, slot_id: str) -> None:
        stack = self._get_stack(slot_id)
        if stack is None or stack.is_empty():
            return
        inv = self.player.inventory
        if slot_id.startswith("h"):
            targets = inv.main
        elif slot_id.startswith("m"):
            targets = inv.hotbar
        else:
            return
        to_move = stack.count
        bid = stack.block_id
        dur = stack.durability
        for t in targets:
            if t.block_id == bid and not t.is_empty() and t.count < 64:
                space = 64 - t.count
                add = min(space, to_move)
                t.count += add
                to_move -= add
                if to_move <= 0:
                    break
        if to_move > 0:
            for t in targets:
                if t.is_empty():
                    t.block_id = bid
                    t.count = to_move
                    t.durability = dur
                    to_move = 0
                    break
        stack.count = to_move
        if stack.count <= 0:
            stack.block_id = BLOCK_AIR
            stack.count = 0
            stack.durability = 0

    def _collect_same_item(self, target_slot_id: str) -> None:
        """Minecraft-style double-click: pull all matching items into target slot
        (partial stacks first, then full stacks), up to max_stack."""
        target = self._get_stack(target_slot_id)
        if target is None or target.is_empty():
            return
        bid = int(target.block_id)
        max_stack = target.max_stack() if hasattr(target, "max_stack") else 64

        candidates: list[str] = []
        candidates += [f"h{i}" for i in range(9)]
        candidates += [f"m{i}" for i in range(27)]
        if self.crafting_table_open:
            candidates += [f"t{i}" for i in range(9)]
        else:
            candidates += [f"c{i}" for i in range(4)]
        if self.chest_open:
            candidates += [f"k{i}" for i in range(27)]

        partial: list[str] = []
        full: list[str] = []
        for sid in candidates:
            if sid == target_slot_id:
                continue
            s = self._get_stack(sid)
            if s is None or s.is_empty() or int(s.block_id) != bid:
                continue
            (partial if s.count < max_stack else full).append(sid)

        for sid in partial + full:
            if target.count >= max_stack:
                break
            s = self._get_stack(sid)
            if s is None or s.is_empty():
                continue
            take = min(int(s.count), max_stack - int(target.count))
            target.count += take
            s.count -= take
            if s.count <= 0:
                s.block_id = BLOCK_AIR
                s.count = 0
            self._set_stack(sid, s)
        self._set_stack(target_slot_id, target)

    def _handle_inventory_click(self, button: int, mx: int, my: int):
        """Handle mouse clicks in inventory UI."""
        slot_id = self._slot_at_point(mx, my)
        if slot_id is None:
            return

        inv = self.player.inventory
        slot_stack = self._get_stack(slot_id)
        if slot_stack is None:
            return

        # Armor slots reject any item that isn't the matching armor piece (when placing).
        if slot_id.startswith("a") and self.dragged_item is not None and not self.dragged_item.is_empty():
            from .items import get_definition
            if get_definition(self.dragged_item.block_id).armor_slot != int(slot_id[1:]):
                return

        # Right-click an armor piece in a normal slot with an empty cursor → auto-equip it.
        if (button == 3 and not slot_id.startswith("a")
                and (self.dragged_item is None or self.dragged_item.is_empty())
                and not slot_stack.is_empty()):
            from .items import get_definition
            asl = get_definition(slot_stack.block_id).armor_slot
            if asl is not None and asl >= 0 and inv.armor[asl].is_empty():
                inv.armor[asl] = slot_stack.copy()
                slot_stack.block_id = BLOCK_AIR
                slot_stack.count = 0
                slot_stack.durability = 0
                return

        # Double-click collect: gather all matching items into this slot (max stack)
        if button == 1:
            now = pygame.time.get_ticks()
            last_slot = getattr(self, "_last_inv_click_slot", None)
            last_time = getattr(self, "_last_inv_click_time", 0)
            same = (slot_id == last_slot)
            within = (now - last_time) < 300
            # Skip craft-result, furnace-output, and armor slots — not collect targets
            collectable = slot_id not in ("result", "tr", "fo") and not slot_id.startswith("a")
            no_drag = (self.dragged_item is None or self.dragged_item.is_empty())
            if same and within and collectable and no_drag and not slot_stack.is_empty():
                self._collect_same_item(slot_id)
                self._last_inv_click_time = 0
                self._last_inv_click_slot = None
                return
            self._last_inv_click_slot = slot_id
            self._last_inv_click_time = now

        if slot_id == "fo":
            # Take furnace output
            fs = self._get_furnace_state()
            out = fs['output']
            if not out.is_empty():
                if self.dragged_item is None or self.dragged_item.is_empty():
                    self.dragged_item = out.copy()
                    fs['output'] = ItemStack()
                elif self.dragged_item.can_merge_with(out):
                    space = 64 - self.dragged_item.count
                    add = min(space, out.count)
                    self.dragged_item.count += add
                    out.count -= add
                    if out.count <= 0:
                        fs['output'] = ItemStack()
            return

        if slot_id == "result" or slot_id == "tr":
            is_3x3 = slot_id == "tr"
            result_stack = inv.craft_result_3x3 if is_3x3 else inv.craft_result
            if result_stack.is_empty():
                return

            # Shift+Click: bulk craft into inventory until grid empty or inv full
            if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                while True:
                    current = inv.craft_result_3x3 if is_3x3 else inv.craft_result
                    if current.is_empty():
                        break
                    bid = current.block_id
                    cnt = current.count
                    remaining = inv.add_item(bid, cnt)
                    if remaining > 0:
                        # No room — undo partial add and stop
                        if remaining < cnt:
                            inv.remove_item(bid, cnt - remaining)
                        break
                    self._consume_crafting_grid()
                return

            # Normal click: take one result into dragged_item
            if self.dragged_item is None or self.dragged_item.is_empty():
                self.dragged_item = result_stack.copy()
                self._consume_crafting_grid()
            elif self.dragged_item.can_merge_with(result_stack):
                space = 64 - self.dragged_item.count
                add = min(space, result_stack.count)
                self.dragged_item.count += add
                if add >= result_stack.count:
                    self._consume_crafting_grid()
            return

        # Left click
        if button == 1:
            if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                self._shift_move_stack(slot_id)
                return
            if self.dragged_item is None or self.dragged_item.is_empty():
                # Pick up entire stack
                self.dragged_item = slot_stack.copy()
                slot_stack.block_id = BLOCK_AIR
                slot_stack.count = 0
            else:
                if slot_stack.is_empty():
                    # Place dragged item here
                    self._set_stack(slot_id, self.dragged_item.copy())
                    self.dragged_item.block_id = BLOCK_AIR
                    self.dragged_item.count = 0
                    self.dragged_item = None
                elif slot_stack.block_id == self.dragged_item.block_id:
                    # Merge stacks
                    space = 64 - slot_stack.count
                    add = min(space, self.dragged_item.count)
                    slot_stack.count += add
                    self.dragged_item.count -= add
                    if self.dragged_item.count <= 0:
                        self.dragged_item = None
                else:
                    # Swap
                    old = slot_stack.copy()
                    self._set_stack(slot_id, self.dragged_item.copy())
                    self.dragged_item = old

        # Right click (place one / split stack)
        elif button == 3:
            if self.dragged_item is None or self.dragged_item.is_empty():
                if not slot_stack.is_empty():
                    # Pick up half
                    half = slot_stack.count // 2
                    self.dragged_item = ItemStack(slot_stack.block_id, slot_stack.count - half)
                    slot_stack.count = half
                    if slot_stack.count <= 0:
                        slot_stack.block_id = BLOCK_AIR
            else:
                if slot_stack.is_empty():
                    # Place one
                    self._set_stack(slot_id, ItemStack(self.dragged_item.block_id, 1))
                    self.dragged_item.count -= 1
                    if self.dragged_item.count <= 0:
                        self.dragged_item = None
                elif slot_stack.block_id == self.dragged_item.block_id and slot_stack.count < 64:
                    # Add one
                    slot_stack.count += 1
                    self.dragged_item.count -= 1
                    if self.dragged_item.count <= 0:
                        self.dragged_item = None

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self):
        from .chunk import BLOCK_BED  # Ensure local scope binding
        FIXED_DT = 1.0 / 20.0          # 20 ticks/sec physics, Minecraft-style
        self._tick_accum = 0.0
        running = True
        while running:
            raw_dt = self.clock.tick(120) / 1000.0
            dt = min(raw_dt, 0.033)  # Cap dt at ~30 FPS-equivalent to prevent tunneling

            # ── Title screen ───────────────────────────────────────────────
            if self.game_state == "title":
                for e in pygame.event.get():
                    if e.type == pygame.QUIT:
                        running = False
                    elif e.type == pygame.VIDEORESIZE:
                        self.size = (int(e.w), int(e.h))
                        pygame.display.set_mode(self.size, pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE)
                        self.renderer.resize(*self.size)
                        self.ui.resize(self.size)
                    elif e.type == pygame.KEYDOWN:
                        if self._title_entering_seed:
                            if e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                                try:
                                    seed = int(self._title_seed_input) if self._title_seed_input else random.randrange(1_000_000_000)
                                except ValueError:
                                    seed = random.randrange(1_000_000_000)
                                self._start_game(seed)
                            elif e.key == pygame.K_BACKSPACE:
                                self._title_seed_input = self._title_seed_input[:-1]
                            elif e.key == pygame.K_ESCAPE:
                                self._title_entering_seed = False
                            elif e.unicode and e.unicode.isprintable() and len(self._title_seed_input) < 18:
                                self._title_seed_input += e.unicode
                        else:
                            if e.key == pygame.K_ESCAPE:
                                running = False
                    elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                        tmx, tmy = pygame.mouse.get_pos()
                        self._handle_title_click(tmx, tmy)
                if running and self.game_state == "title":
                    tmx, tmy = pygame.mouse.get_pos()
                    title_ui_state = UIState(
                        fps=self.clock.get_fps(), pos=(0.0, 0.0, 0.0),
                        target_name="", paused=False, debug=False,
                        active_slot=0, hotbar_names=(), render_distance=6,
                        game_state="title",
                        title_seed_input=self._title_seed_input,
                        title_entering_seed=self._title_entering_seed,
                        new_world_mode=self._new_world_mode,
                        mouse_x=tmx, mouse_y=tmy,
                    )
                    ui_rgba = self.ui.render(title_ui_state)
                    self.renderer.render_title(ui_rgba)
                    pygame.display.flip()
                continue
            # ──────────────────────────────────────────────────────────────

            # ── Options screen (from title) ────────────────────────────
            if self.game_state == "options":
                for e in pygame.event.get():
                    if e.type == pygame.QUIT:
                        running = False
                    elif e.type == pygame.VIDEORESIZE:
                        self.size = (int(e.w), int(e.h))
                        pygame.display.set_mode(self.size, pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE)
                        self.renderer.resize(*self.size)
                        self.ui.resize(self.size)
                    elif e.type == pygame.KEYDOWN:
                        if e.key == pygame.K_ESCAPE:
                            save_config(self.cfg)
                            self.game_state = "title"
                    elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                        omx, omy = pygame.mouse.get_pos()
                        self._handle_options_click(omx, omy)
                    elif e.type == pygame.MOUSEMOTION and pygame.mouse.get_pressed()[0]:
                        omx, omy = pygame.mouse.get_pos()
                        self._handle_options_drag(omx, omy)
                if running and self.game_state == "options":
                    omx, omy = pygame.mouse.get_pos()
                    op_ui_state = UIState(
                        fps=self.clock.get_fps(), pos=(0.0, 0.0, 0.0),
                        target_name="", paused=False, debug=False,
                        active_slot=0, hotbar_names=(),
                        render_distance=self.settings.render_distance,
                        game_state="options",
                        options_tab=self._options_tab,
                        fov=float(self.cfg.get("fov", 75.0)),
                        sensitivity=float(self.cfg.get("sensitivity", 0.0023)),
                        master_volume=float(self.cfg.get("master_volume", 1.0)),
                        music_volume=float(self.cfg.get("music_volume", 0.8)),
                        sfx_volume=float(self.cfg.get("sfx_volume", 1.0)),
                        mouse_x=omx, mouse_y=omy,
                    )
                    ui_rgba = self.ui.render(op_ui_state)
                    self.renderer.render_title(ui_rgba)
                    pygame.display.flip()
                continue
            # ──────────────────────────────────────────────────────────────

            # ── World select screen ────────────────────────────────────
            if self.game_state == "world_select":
                for e in pygame.event.get():
                    if e.type == pygame.QUIT:
                        running = False
                    elif e.type == pygame.VIDEORESIZE:
                        self.size = (int(e.w), int(e.h))
                        pygame.display.set_mode(self.size, pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE)
                        self.renderer.resize(*self.size)
                        self.ui.resize(self.size)
                    elif e.type == pygame.KEYDOWN:
                        if e.key == pygame.K_ESCAPE:
                            self.game_state = "title"
                    elif e.type == pygame.MOUSEWHEEL:
                        L = self.ui.world_select_layout()
                        max_scroll = max(0, len(self._world_list) - L["max_visible"])
                        self._world_select_scroll = max(0, min(max_scroll,
                                                                self._world_select_scroll - int(e.y)))
                    elif e.type == pygame.MOUSEMOTION:
                        self._update_world_select_hover(*e.pos)
                    elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                        self._handle_world_select_click(*pygame.mouse.get_pos())
                if running and self.game_state == "world_select":
                    wmx, wmy = pygame.mouse.get_pos()
                    ws_ui_state = UIState(
                        fps=self.clock.get_fps(), pos=(0.0, 0.0, 0.0),
                        target_name="", paused=False, debug=False,
                        active_slot=0, hotbar_names=(), render_distance=6,
                        game_state="world_select",
                        world_list=tuple(self._world_list),
                        world_select_scroll=self._world_select_scroll,
                        world_select_hover=self._world_select_hover,
                        mouse_x=wmx, mouse_y=wmy,
                    )
                    ui_rgba = self.ui.render(ws_ui_state)
                    self.renderer.render_title(ui_rgba)
                    pygame.display.flip()
                continue
            # ──────────────────────────────────────────────────────────────

            mouse_dx = 0.0
            mouse_dy = 0.0
            place_pressed = False
            pick_pressed = False
            scroll_delta = 0
            break_held = False
            hotbar_index = None
            inv_toggle = False

            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self._save_all()
                    running = False
                elif e.type == pygame.VIDEORESIZE:
                    self.size = (int(e.w), int(e.h))
                    pygame.display.set_mode(self.size, pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE)
                    self.renderer.resize(*self.size)
                    self.ui.resize(self.size)
                elif e.type == pygame.KEYDOWN:
                    # Command bar input (opened with "/")
                    if self._cmd_active:
                        if e.key == pygame.K_ESCAPE:
                            self._cmd_active = False
                            self._cmd_text = ""
                        elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            self._execute_command(self._cmd_text)
                            self._cmd_active = False
                            self._cmd_text = ""
                        elif e.key == pygame.K_BACKSPACE:
                            self._cmd_text = self._cmd_text[:-1]
                        elif e.unicode and e.unicode.isprintable() and len(self._cmd_text) < 64:
                            self._cmd_text += e.unicode
                        continue
                    # Open command bar with "/" (K_SLASH or typed "/" character)
                    if (not self.paused and not self.inventory_open and not self.crafting_table_open
                        and not self.furnace_open and not self.chest_open and not self._creative_inv_open):
                        if e.key == pygame.K_SLASH or e.unicode == "/":
                            self._cmd_active = True
                            self._cmd_text = ""
                            self._cmd_error = ""
                            continue
                    # Keybind rebinding mode — capture next key
                    if self._rebinding_action:
                        if e.key != pygame.K_ESCAPE:
                            self.cfg["keybinds"][self._rebinding_action] = e.key
                            save_config(self.cfg)
                        self._rebinding_action = None
                        continue
                    if e.key == pygame.K_ESCAPE:
                        if self._creative_inv_open:
                            self._creative_inv_open = False
                            self._lock_mouse(True)
                        elif self._stats_open:
                            self._stats_open = False
                        elif self._keybinds_open:
                            self._keybinds_open = False
                        elif self.crafting_table_open:
                            self.crafting_table_open = False
                            self._lock_mouse(True)
                            if self.dragged_item and not self.dragged_item.is_empty():
                                self.player.inventory.add_item(self.dragged_item.block_id, self.dragged_item.count)
                                self.dragged_item = None
                            self._return_crafting_grid_items(grid_3x3=True)
                        elif self.furnace_open:
                            self.furnace_open = False
                            self._lock_mouse(True)
                            if self.dragged_item and not self.dragged_item.is_empty():
                                self.player.inventory.add_item(self.dragged_item.block_id, self.dragged_item.count)
                                self.dragged_item = None
                        elif self.chest_open:
                            self.chest_open = False
                            self._lock_mouse(True)
                            if self.dragged_item and not self.dragged_item.is_empty():
                                self.player.inventory.add_item(self.dragged_item.block_id, self.dragged_item.count)
                                self.dragged_item = None
                        elif self.inventory_open:
                            self.inventory_open = False
                            self._lock_mouse(True)
                            if self.dragged_item and not self.dragged_item.is_empty():
                                self.player.inventory.add_item(self.dragged_item.block_id, self.dragged_item.count)
                                self.dragged_item = None
                            self._return_crafting_grid_items(grid_3x3=False)
                        else:
                            self.paused = not self.paused
                            self._lock_mouse(not self.paused)
                    elif e.key == self._key("inventory"):
                        if not self.paused:
                            if self.furnace_open or self.chest_open:
                                self.furnace_open = False
                                self.chest_open = False
                                self._lock_mouse(True)
                                if self.dragged_item and not self.dragged_item.is_empty():
                                    self.player.inventory.add_item(self.dragged_item.block_id, self.dragged_item.count)
                                    self.dragged_item = None
                            elif self.player.game_mode == "creative":
                                self._creative_inv_open = not self._creative_inv_open
                                self._lock_mouse(not self._creative_inv_open)
                            else:
                                was_open = self.inventory_open
                                self.inventory_open = not self.inventory_open
                                self._lock_mouse(not self.inventory_open)
                                if self.inventory_open:
                                    self._update_crafting()
                                elif was_open:
                                    if self.dragged_item and not self.dragged_item.is_empty():
                                        self.player.inventory.add_item(self.dragged_item.block_id, self.dragged_item.count)
                                        self.dragged_item = None
                                    self._return_crafting_grid_items(grid_3x3=False)
                    elif e.key == self._key("debug"):
                        self.debug = not self.debug
                    elif any(e.key == self._key(f"hotbar_{i}") for i in range(1, 10)):
                        for i in range(1, 10):
                            if e.key == self._key(f"hotbar_{i}"):
                                hotbar_index = i - 1
                                break
                    elif self.paused and e.key == pygame.K_TAB:
                        self._pause_selected = (self._pause_selected + 1) % 3
                    elif self.paused and e.key in (pygame.K_LEFT, pygame.K_DOWN):
                        self._pause_adjust(-1)
                    elif self.paused and e.key in (pygame.K_RIGHT, pygame.K_UP):
                        self._pause_adjust(+1)
                    elif e.key == self._key("toggle_mode"):
                        self._toggle_game_mode()
                    elif self.paused and e.key == pygame.K_k:
                        self._keybinds_open = not self._keybinds_open
                    elif e.key == self._key("drop"):
                        if self.paused:
                            self._save_all()
                            self._return_to_title()
                            continue
                        elif (not self.inventory_open
                              and not self.crafting_table_open
                              and not self.chest_open
                              and not self.furnace_open
                              and not self._keybinds_open):
                            ctrl_held = bool(pygame.key.get_mods() & pygame.KMOD_CTRL)
                            self.player.drop_active(self.world, count=64 if ctrl_held else 1)
                elif e.type == pygame.MOUSEWHEEL:
                    if self._keybinds_open:
                        self._keybinds_scroll = max(0, self._keybinds_scroll - int(e.y))
                    elif self._creative_inv_open:
                        self._creative_inv_scroll = max(0, self._creative_inv_scroll - int(e.y))
                    else:
                        scroll_delta = int(e.y)
                elif e.type == pygame.MOUSEBUTTONDOWN:
                    if self._keybinds_open and e.button == 1:
                        mx, my = pygame.mouse.get_pos()
                        rects = self.ui._kb_rects
                        for (rx, ry, rw, rh, action) in rects:
                            if rx <= mx <= rx + rw and ry <= my <= ry + rh:
                                self._rebinding_action = action
                                break
                    elif self.paused and self._stats_open and e.button == 1:
                        mx, my = pygame.mouse.get_pos()
                        cr = getattr(self.ui, "_stats_close_rect", None)
                        if cr:
                            cx_, cy_, cw_, ch_ = cr
                            if cx_ <= mx <= cx_ + cw_ and cy_ <= my <= cy_ + ch_:
                                self._stats_open = False
                    elif self.paused and not self._keybinds_open and e.button == 1:
                        mx, my = pygame.mouse.get_pos()
                        for (rx, ry, rw, rh, label) in getattr(self.ui, "_pause_button_rects", []):
                            if rx <= mx <= rx + rw and ry <= my <= ry + rh:
                                if label == "Back to Game":
                                    self.paused = False
                                    self._lock_mouse(True)
                                elif label == "Stats & Achievements":
                                    self._stats_open = True
                                elif label == "Controls...":
                                    self._keybinds_open = True
                                elif label == "Toggle Debug (F3)":
                                    self.debug = not self.debug
                                elif label == "Save and Quit":
                                    self._save_all()
                                    self._return_to_title()
                                break
                    elif self._creative_inv_open and e.button == 1:
                        mx, my = pygame.mouse.get_pos()
                        self._handle_creative_inv_click(mx, my)
                    elif self.crafting_table_open or self.inventory_open or self.furnace_open or self.chest_open:
                        mx, my = pygame.mouse.get_pos()
                        self._handle_inventory_click(e.button, mx, my)
                    else:
                        if e.button == 3:
                            # Try eating food first
                            active = self.player.inventory.active_stack()
                            food = FOODS.get(active.block_id) if active and not active.is_empty() else None
                            handled = False
                            if food and self.player.hunger < 20.0:
                                consumed_id = active.block_id
                                self.player.hunger = min(20.0, self.player.hunger + food[0])
                                active.count -= 1
                                if active.count <= 0:
                                    active.block_id = BLOCK_AIR
                                    active.count = 0
                                # Mushroom stew leaves an empty bowl
                                if consumed_id == ITEM_MUSHROOM_STEW:
                                    self.player.inventory.add_item(ITEM_BOWL, 1)
                                handled = True
                            # Try utility item actions (flint&steel, bucket) on hit target
                            if not handled and active and not active.is_empty() and self.player.target and self.player.target.hit:
                                aid = active.block_id
                                tpos = self.player.target.block_pos
                                ppos = self.player.target.place_pos
                                hit_bid = self.player.target.block_id
                                if aid == ITEM_FLINT_AND_STEEL:
                                    self.world.set_block(ppos[0], ppos[1], ppos[2], BLOCK_LAVA)
                                    fs_defn = get_definition(ITEM_FLINT_AND_STEEL)
                                    if fs_defn.max_durability > 0:
                                        active.durability -= 1
                                        if active.durability <= 0:
                                            active.count -= 1
                                            active.durability = fs_defn.max_durability
                                            if active.count <= 0:
                                                active.block_id = BLOCK_AIR
                                                active.count = 0
                                                active.durability = 0
                                    handled = True
                                elif aid == ITEM_BUCKET:
                                    if hit_bid == BLOCK_WATER:
                                        self.world.remove_water(tpos[0], tpos[1], tpos[2])
                                        self.world.set_block(tpos[0], tpos[1], tpos[2], BLOCK_AIR)
                                        active.block_id = ITEM_WATER_BUCKET
                                        active.count = 1
                                        handled = True
                                    elif hit_bid == BLOCK_LAVA:
                                        self.world.set_block(tpos[0], tpos[1], tpos[2], BLOCK_AIR)
                                        active.block_id = ITEM_LAVA_BUCKET
                                        active.count = 1
                                        handled = True
                                elif aid == ITEM_WATER_BUCKET:
                                    self.world.place_water_source(ppos[0], ppos[1], ppos[2])
                                    active.block_id = ITEM_BUCKET
                                    active.count = 1
                                    handled = True
                                elif aid == ITEM_LAVA_BUCKET:
                                    self.world.set_block(ppos[0], ppos[1], ppos[2], BLOCK_LAVA)
                                    active.block_id = ITEM_BUCKET
                                    active.count = 1
                                    handled = True
                                elif is_spawn_egg(aid):
                                    # Spawn the mob standing on the clicked surface (place_pos).
                                    mob_type = SPAWN_EGG_TO_MOB[aid]
                                    self.world.entities.append(
                                        Mob((ppos[0] + 0.5, float(ppos[1]), ppos[2] + 0.5), mob_type))
                                    # Minecraft: eggs are consumed in survival, infinite in creative.
                                    if self.player.game_mode != "creative":
                                        active.count -= 1
                                        if active.count <= 0:
                                            active.block_id = BLOCK_AIR
                                            active.count = 0
                                    self._place_cooldown = 0.25
                                    handled = True
                            if not handled:
                                # Right-click: check for interactive blocks before placing
                                if self.player.target and self.player.target.hit:
                                    bid = self.player.target.block_id
                                    tpos = self.player.target.block_pos
                                    if bid == BLOCK_CRAFTING_TABLE:
                                        self.crafting_table_open = True
                                        self._lock_mouse(False)
                                        self._update_crafting()
                                    elif bid == BLOCK_FURNACE:
                                        self.furnace_open = True
                                        self.open_furnace_pos = tpos
                                        self._lock_mouse(False)
                                    elif bid == BLOCK_CHEST:
                                        self.chest_open = True
                                        self.open_chest_pos = tpos
                                        if tpos not in self.chest_inventories:
                                            self.chest_inventories[tpos] = [ItemStack() for _ in range(27)]
                                        self._lock_mouse(False)
                                    elif bid == BLOCK_BED:
                                        if self._try_sleep_in_bed(tpos):
                                            pass
                                        else:
                                            if self._place_cooldown <= 0.0:
                                                place_pressed = True
                                    else:
                                        if self._place_cooldown <= 0.0:
                                            place_pressed = True
                                else:
                                    if self._place_cooldown <= 0.0:
                                        place_pressed = True
                        elif e.button == 2:
                            pick_pressed = True

            if self.game_state != "playing":
                continue

            if not self.paused and not self.inventory_open and not self.furnace_open and not self.chest_open and self._mouse_locked:
                mdx, mdy = pygame.mouse.get_rel()
                mouse_dx = float(mdx)
                mouse_dy = float(mdy)
                break_held = pygame.mouse.get_pressed(3)[0]
                if pygame.mouse.get_pressed(3)[2] and self._place_cooldown <= 0.0:
                    place_pressed = True

            keys = pygame.key.get_pressed()
            move_x = float(keys[self._key("move_right")]) - float(keys[self._key("move_left")])
            move_z = float(keys[self._key("move_forward")]) - float(keys[self._key("move_back")])
            jump = bool(keys[self._key("jump")])
            crouch = bool(keys[self._key("sneak")] or keys[pygame.K_RSHIFT])
            sprint = bool(keys[self._key("sprint")] or keys[pygame.K_RCTRL])
            attack_pressed = bool(pygame.mouse.get_pressed(3)[0]) and self._mouse_locked and not self.paused and not self.inventory_open and not self.furnace_open and not self.chest_open

            inp = InputState(
                move_x=move_x,
                move_z=move_z,
                jump=jump,
                crouch=crouch,
                sprint=sprint,
                mouse_dx=mouse_dx,
                mouse_dy=mouse_dy,
                break_held=break_held,
                place_pressed=place_pressed,
                pick_pressed=pick_pressed,
                hotbar_index=hotbar_index,
                scroll_delta=scroll_delta,
                attack_pressed=attack_pressed,
            )

            if not self.paused and not self.inventory_open:
                self._place_cooldown = max(0.0, self._place_cooldown - dt)
                if self._cmd_error_timer > 0.0:
                    self._cmd_error_timer = max(0.0, self._cmd_error_timer - dt)
                self.world.update_streaming(tuple(self.player.pos.tolist()), self.settings.render_distance)
                self._drain_pending_chest_loot()
                self.world.time_of_day = (self.world.time_of_day + dt / 1800.0) % 1.0

                # Per-FRAME: camera look, raycast target, edge actions (place/break/attack).
                self.player.update_look(dt, self.world, inp)

                # Fixed 20 TPS physics simulation, independent of frame rate. Up to
                # 5 catch-up ticks per frame (spiral-of-death guard).
                self._tick_accum += min(raw_dt, 0.25)
                _n_ticks = 0
                while self._tick_accum >= FIXED_DT and _n_ticks < 5:
                    self._tick_accum -= FIXED_DT
                    _n_ticks += 1
                    self.player.tick(self.world, inp)
                    for ent in tuple(self.world.entities):
                        ent.tick(self.world, self.player)
                # Interpolate positions for smooth rendering between ticks.
                _alpha = self._tick_accum / FIXED_DT
                self.player.update_render_interp(_alpha)
                for ent in self.world.entities:
                    ent.render_pos = ent.prev_pos + (ent.pos - ent.prev_pos) * _alpha

                # Particle physics update
                if getattr(self.world, 'particles', None) is not None:
                    self.world.particles.update(dt, self.world)
                # Ongoing mob spawning + despawn
                if getattr(self.world, 'spawn_manager', None) is not None:
                    self.world.spawn_manager.update(dt, self.world, self.player)
                # Water flow simulation
                self.world.tick_water(dt)
                if inp.place_pressed:
                    self._place_cooldown = 0.25
                self._tick_furnaces(dt)
                self.minimap.update(self.world, tuple(self.player.pos.tolist()), dt)

                # 8B: Sprint FOV zoom — smoothly lerp toward sprint target
                _base_fov = float(self.cfg.get("fov", 75.0))
                _is_sprinting = bool(sprint) and (move_x != 0.0 or move_z != 0.0) and self.player.on_ground
                _target_fov = _base_fov + (5.0 if _is_sprinting else 0.0)
                self.renderer.fov += (_target_fov - self.renderer.fov) * min(1.0, dt * 8.0)

                if not self.player.alive and self.player.death_timer > 2.0:
                    target = None
                    sp = getattr(self.player, "spawn_point", None)
                    if sp is not None:
                        try:
                            from .chunk import BLOCK_BED
                            bx, by, bz = int(sp[0]), int(sp[1]), int(sp[2])
                            if self.world.get_block(bx, by, bz) == BLOCK_BED:
                                target = (float(sp[0]) + 0.5, float(sp[1]) + 1.0, float(sp[2]) + 0.5)
                            else:
                                self.player.spawn_point = None
                        except Exception:
                            self.player.spawn_point = None
                    if target is None and self.world.world_spawn is not None:
                        target = self.world.world_spawn
                    if target is None:
                        target = self._find_safe_spawn()
                    self.player.respawn(tuple(target))

                # Entities are simulated in the fixed-tick loop above; here we just
                # cull any that died (attack hits, lava, despawn).
                if hasattr(self.world, 'entities'):
                    dead = [ent for ent in self.world.entities if not ent.alive]
                    for ent in dead:
                        self.world.entities.remove(ent)

            cam = self.player.camera(use_render=True)
            pos = (float(self.player.pos[0]), float(self.player.pos[1]), float(self.player.pos[2]))
            tgt = self.player.target
            tgt_name = block_name(tgt.block_id) if tgt and tgt.hit else "air"

            hotbar_names = []
            for bid in self.player.hotbar:
                hotbar_names.append(self._hotbar_texture_name(bid))

            # Get mouse position for UI
            mx, my = pygame.mouse.get_pos()
            inv = self.player.inventory
            all_slots = tuple(inv.hotbar) + tuple(inv.main)
            craft_slots = tuple(inv.craft_grid)

            # F3 debug info
            pcx, pcz = self.world.chunk_coords(int(self.player.pos[0]), int(self.player.pos[2]))
            biome_id = 0
            biome_names = {0: "Overworld"}
            face_names = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
            face_idx = int((self.player.yaw % (2 * 3.14159)) / (3.14159 / 4) + 0.5) % 8
            memory_mb = 0
            try:
                import psutil
                memory_mb = psutil.Process().memory_info().rss // 1048576
            except Exception:
                pass

            _fstate = self._get_furnace_state() if self.furnace_open else None
            ui_state = UIState(
                fps=self.clock.get_fps(),
                pos=pos,
                target_name=tgt_name,
                paused=self.paused,
                debug=self.debug,
                active_slot=self.player.active_slot,
                hotbar_names=tuple(hotbar_names),
                render_distance=self.settings.render_distance,
                alive=self.player.alive,
                death_timer=self.player.death_timer,
                inventory_open=self.inventory_open,
                inv_slots=all_slots,
                craft_slots=craft_slots,
                craft_result=inv.craft_result if not inv.craft_result.is_empty() else None,
                armor_slots=tuple(inv.armor),
                dragged_item=self.dragged_item,
                mouse_x=mx,
                mouse_y=my,
                health=self.player.health,
                hunger=self.player.hunger,
                air=getattr(self.player, 'air', 10.0),
                xp=getattr(self.player, 'xp', 0),
                xp_level=getattr(self.player, 'xp_level', 0),
                xp_progress=getattr(self.player, 'xp_progress', 0.0),
                crafting_table_open=self.crafting_table_open,
                craft_slots_3x3=tuple(inv.craft_grid_3x3) if self.crafting_table_open else (),
                craft_result_3x3=inv.craft_result_3x3 if self.crafting_table_open and not inv.craft_result_3x3.is_empty() else None,
                furnace_open=self.furnace_open,
                furnace_input=_fstate['input'] if _fstate is not None else None,
                furnace_fuel=_fstate['fuel'] if _fstate is not None else None,
                furnace_output=_fstate['output'] if _fstate is not None else None,
                furnace_progress=_fstate['progress'] if _fstate is not None else 0.0,
                furnace_fuel_left=_fstate['fuel_left'] if _fstate is not None else 0.0,
                furnace_fuel_max=max(_fstate['fuel_max'], 0.001) if _fstate is not None else 1.0,
                chest_open=self.chest_open,
                chest_slots=tuple(self.chest_inventories.get(self.open_chest_pos, [])) if self.chest_open else (),
                cx=pcx,
                cz=pcz,
                biome_name=biome_names.get(biome_id, "Unknown"),
                facing=face_names[face_idx] if face_names else "N",
                memory_mb=memory_mb,
                game_state="playing",
                damage_flash_timer=getattr(self.player, 'damage_flash_timer', 0.0),
                minimap_rgba=self.minimap.to_bytes(),
                minimap_yaw=float(self.player.yaw),
                fov=float(self.cfg.get("fov", 75.0)),
                sensitivity=float(self.cfg.get("sensitivity", 0.0023)),
                game_mode=getattr(self.player, "game_mode", "survival"),
                pause_selected=self._pause_selected,
                keybinds_open=self._keybinds_open,
                keybinds=self.cfg.get("keybinds", {}),
                rebinding_action=self._rebinding_action,
                keybinds_scroll=self._keybinds_scroll,
                stats_open=self._stats_open,
                stats=dict(self.stats),
                command_active=self._cmd_active,
                command_text=self._cmd_text,
                command_error=self._cmd_error if self._cmd_error_timer > 0.0 else "",
                creative_inv_open=self._creative_inv_open,
                creative_inv_scroll=self._creative_inv_scroll,
            )
            ui_rgba = self.ui.render(ui_state)

            self.renderer.render(self.world, cam, self.settings.render_distance, ui_rgba, self.player.target, self.player.break_progress)
            pygame.display.flip()

        # Persist all settings the user may have changed during the session
        self.cfg["render_distance"] = int(self.settings.render_distance)
        save_config(self.cfg)
        pygame.quit()

    def _hotbar_texture_name(self, block_id: int) -> str:
        from .chunk import (
            BLOCK_AIR, BLOCK_CHEST, BLOCK_COAL_ORE, BLOCK_COBBLESTONE,
            BLOCK_CRAFTING_TABLE, BLOCK_DIAMOND_ORE, BLOCK_DIRT,
            BLOCK_ANDESITE, BLOCK_CLAY, BLOCK_DIORITE,
            BLOCK_FLOWER_RED, BLOCK_FLOWER_YELLOW, BLOCK_FURNACE,
            BLOCK_GLASS, BLOCK_GOLD_ORE, BLOCK_GRANITE, BLOCK_GRASS, BLOCK_GRAVEL,
            BLOCK_IRON_ORE, BLOCK_LAVA, BLOCK_LEAVES, BLOCK_LOG,
            BLOCK_MUSHROOM_BROWN, BLOCK_MUSHROOM_RED,
            BLOCK_PLANKS, BLOCK_REDSTONE_ORE, BLOCK_SAND,
            BLOCK_SNOW, BLOCK_STICK, BLOCK_STONE, BLOCK_SUGAR_CANE,
            BLOCK_TALL_GRASS, BLOCK_WATER,
        )
        from .items import is_item_id, ITEMS
        if block_id == BLOCK_AIR:
            return ""
        if is_item_id(int(block_id)):
            defn = ITEMS.get(int(block_id))
            return defn.texture_name if (defn and defn.texture_name) else ""
        return {
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
            BLOCK_CRAFTING_TABLE: "crafting_front",
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
            BLOCK_FURNACE: "furnace_front",
            BLOCK_CHEST: "chest_front",
            BLOCK_GRANITE: "granite",
            BLOCK_ANDESITE: "andesite",
            BLOCK_DIORITE: "diorite",
            BLOCK_CLAY: "clay",
            BLOCK_MUSHROOM_RED: "mushroom_red",
            BLOCK_MUSHROOM_BROWN: "mushroom_brown",
            BLOCK_SUGAR_CANE: "sugar_cane",
        }.get(int(block_id), "")
