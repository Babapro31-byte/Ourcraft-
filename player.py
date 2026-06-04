from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np

from .chunk import (
    BLOCK_AIR,
    BLOCK_BEDROCK,
    BLOCK_CLAY,
    BLOCK_COAL_ORE,
    BLOCK_COBBLESTONE,
    BLOCK_COPPER_ORE,
    BLOCK_CRAFTING_TABLE,
    BLOCK_DEEPSLATE_COAL,
    BLOCK_DEEPSLATE_COPPER,
    BLOCK_DEEPSLATE_DIAMOND,
    BLOCK_DEEPSLATE_GOLD,
    BLOCK_DEEPSLATE_IRON,
    BLOCK_DEEPSLATE_REDSTONE,
    BLOCK_DIAMOND_ORE,
    BLOCK_DIRT,
    BLOCK_FLOWER_RED,
    BLOCK_FLOWER_YELLOW,
    BLOCK_GLASS,
    BLOCK_GOLD_ORE,
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
    BLOCK_STICK,
    BLOCK_STONE,
    BLOCK_SUGAR_CANE,
    BLOCK_TALL_GRASS,
    BLOCK_WATER,
    is_solid,
)
from .inventory import Inventory
from .items import (
    ITEM_APPLE,
    ITEM_CLAY_BALL,
    ITEM_COAL,
    ITEM_DIAMOND,
    ITEM_RAW_COPPER,
    ITEM_RAW_GOLD,
    ITEM_RAW_IRON,
    ITEM_REDSTONE,
    ITEM_SHEARS,
    ToolTier,
    ToolType,
    effective_hardness,
    get_definition,
    is_item_id,
)
from .world import TargetBlock
from .entity import Mob


# Instant-break blocks (vegetation, etc.)
_INSTANT_BREAK = {
    BLOCK_WATER, BLOCK_LAVA, BLOCK_TALL_GRASS,
    BLOCK_FLOWER_RED, BLOCK_FLOWER_YELLOW, BLOCK_SNOW,
    BLOCK_MUSHROOM_RED, BLOCK_MUSHROOM_BROWN, BLOCK_SUGAR_CANE,
}

# Block → (drop_item_id, count) override. Default: block drops itself.
_BLOCK_DROP_ITEM = {
    BLOCK_STONE:        (BLOCK_COBBLESTONE, 1),
    BLOCK_COAL_ORE:     (ITEM_COAL, 1),
    BLOCK_IRON_ORE:     (ITEM_RAW_IRON, 1),
    BLOCK_GOLD_ORE:     (ITEM_RAW_GOLD, 1),
    BLOCK_DIAMOND_ORE:  (ITEM_DIAMOND, 1),
    BLOCK_REDSTONE_ORE: (ITEM_REDSTONE, 1),
    BLOCK_COPPER_ORE:   (ITEM_RAW_COPPER, 1),
    # Deepslate ore variants drop the same item as their stone counterparts.
    BLOCK_DEEPSLATE_COAL:     (ITEM_COAL, 1),
    BLOCK_DEEPSLATE_IRON:     (ITEM_RAW_IRON, 1),
    BLOCK_DEEPSLATE_GOLD:     (ITEM_RAW_GOLD, 1),
    BLOCK_DEEPSLATE_DIAMOND:  (ITEM_DIAMOND, 1),
    BLOCK_DEEPSLATE_REDSTONE: (ITEM_REDSTONE, 1),
    BLOCK_DEEPSLATE_COPPER:   (ITEM_RAW_COPPER, 1),
    BLOCK_CLAY:         (ITEM_CLAY_BALL, 4),
    BLOCK_LEAVES:       (BLOCK_AIR, 0),  # leaves drop nothing unless sheared
}


def _get_drops(block_id: int, tool_type: "ToolType" = None, tool_tier: "ToolTier" = None) -> Tuple[int, int]:
    """Return (item_id, count) for what a broken block drops.
    Honours pickaxe/tool gating from BLOCK_TOOL_INFO: a block that requires a
    minimum tier drops nothing when broken with the wrong tool or too low a tier."""
    from .items import BLOCK_TOOL_INFO, ToolType as _TT, ToolTier as _Tier
    if tool_type is None:
        tool_type = _TT.NONE
    if tool_tier is None:
        tool_tier = _Tier.NONE
    info = BLOCK_TOOL_INFO.get(block_id)
    if info is not None:
        best_tool, min_tier = info[1], info[2]
        # Only gate drops when a minimum tier is required (e.g. iron pickaxe for gold ore).
        # Preferred-tool-only blocks (dirt needs shovel, stone needs pickaxe) always drop.
        if min_tier != _Tier.NONE:
            if tool_type != best_tool or tool_tier < min_tier:
                return (BLOCK_AIR, 0)
    return _BLOCK_DROP_ITEM.get(block_id, (block_id, 1))

# Block hardness: time-to-break in seconds with bare hand (fallback).
# For blocks in items.BLOCK_TOOL_INFO, effective_hardness() is used instead.
_BLOCK_HARDNESS = {
    BLOCK_AIR: 0.0,
    BLOCK_WATER: 0.0,
    BLOCK_LAVA: 0.0,
    BLOCK_TALL_GRASS: 0.0,
    BLOCK_FLOWER_RED: 0.0,
    BLOCK_FLOWER_YELLOW: 0.0,
    BLOCK_LEAVES: 0.35,
    BLOCK_SNOW: 0.40,
    BLOCK_GLASS: 0.55,
    BLOCK_BEDROCK: float("inf"),
}


def block_name(block_id: int) -> str:
    from .chunk import (
        BLOCK_CHEST, BLOCK_COAL_ORE, BLOCK_COBBLESTONE, BLOCK_CRAFTING_TABLE,
        BLOCK_DIAMOND_ORE, BLOCK_FLOWER_RED, BLOCK_FLOWER_YELLOW,
        BLOCK_FURNACE, BLOCK_GOLD_ORE, BLOCK_GRAVEL, BLOCK_IRON_ORE, BLOCK_LAVA,
        BLOCK_REDSTONE_ORE, BLOCK_STICK, BLOCK_TALL_GRASS,
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


@dataclass(slots=True)
class InputState:
    move_x: float
    move_z: float
    jump: bool
    crouch: bool
    sprint: bool
    mouse_dx: float
    mouse_dy: float
    break_held: bool
    place_pressed: bool
    pick_pressed: bool
    hotbar_index: Optional[int]
    scroll_delta: int
    attack_pressed: bool = False


# ---------------------------------------------------------------------------
# Fixed-tick physics constants (Minecraft Java Edition, 20 ticks/sec).
# Velocities are stored in blocks/second; the fixed tick converts the
# per-tick Minecraft recurrences into this scale.  Reference values:
#   walk 4.317 b/s, sprint 5.612 b/s, sneak 1.295 b/s, jump apex ~1.25 blocks.
# ---------------------------------------------------------------------------
TICK = 1.0 / 20.0
WALK_SPEED = 4.317
SPRINT_SPEED = 5.612
SNEAK_SPEED = 1.30
SWIM_SPEED_MULT = 0.5
# Creative flight (kept snappy via approach()).
FLY_SPEED = 11.0
FLY_SPRINT_SPEED = 22.0
FLY_VERT_SPEED = 9.0
FLY_ACCEL = 60.0
# Horizontal friction: effective ground slip = block_slip * AIR_DRAG.
# Default block slipperiness is 0.6 (dirt/stone/grass); ice ~0.98, slime 0.8.
DEFAULT_SLIP = 0.6
AIR_DRAG = 0.91
AIR_CONTROL = 0.20          # fraction of ground accel available mid-air
SLIPPERINESS: dict = {}     # block_id -> raw slipperiness (ice/slime added later)
# Vertical: vy = (vy - GRAVITY_PER_TICK) * VERTICAL_DRAG each tick.
GRAVITY_PER_TICK = 1.6      # blocks/sec removed per tick -> terminal ~ -78.4
VERTICAL_DRAG = 0.98
TERMINAL_VELOCITY = -78.4
JUMP_VELOCITY = 8.4         # 0.42 b/tick * 20 -> apex ~1.25 blocks
SPRINT_JUMP_BOOST = 3.2     # forward momentum kick on a sprint-jump
# Water vertical handling.
WATER_JUMP_VELOCITY = 3.0
WATER_DRAG = 0.80
WATER_GRAV_MULT = 0.30
WATER_TERMINAL = 3.0


class Player:
    def __init__(self, sensitivity: float = 0.0023):
        self.pos = np.array([0.0, 80.0, 0.0], dtype="f4")
        self.vel = np.array([0.0, 0.0, 0.0], dtype="f4")
        # Fixed-tick render interpolation: prev_pos = pos at the start of the
        # last physics tick; render_pos = interpolated position for the camera.
        self.prev_pos = self.pos.copy()
        self.render_pos = self.pos.copy()
        self._hurt_cd = 0.0   # invulnerability timer (0.5s after an attack hit)
        self.yaw = 0.0
        self.pitch = -0.30
        self.on_ground = False
        self._crouching = False
        self.alive = True
        self.death_timer = 0.0

        self.reach = 5.0
        self.height_stand = 1.80
        self.height_crouch = 1.50
        self.radius = 0.30

        self.sensitivity = sensitivity

        # Bed-based personal spawn point (None = use world_spawn fallback).
        self.spawn_point: Optional[Tuple[float, float, float]] = None

        self.inventory = Inventory()
        self.active_slot = 0

        self.target: Optional[TargetBlock] = None
        self.break_pos: Optional[Tuple[int, int, int]] = None
        self.break_progress = 0.0

        self.health = 20.0
        self.hunger = 20.0
        self._hunger_drain_timer = 0.0
        self._last_fall_vel = 0.0
        self._air_y_peak: float = 0.0

        # Breathing / drowning
        self.air: float = 10.0          # 0..10, depletes underwater (~10s)
        self._drown_timer: float = 0.0  # damage cooldown once air==0

        self.xp: int = 0
        self.xp_level: int = 0
        self.xp_progress: float = 0.0
        self._attack_cooldown: float = 0.0
        self.damage_flash_timer: float = 0.0

        # 8C: Creative mode
        self.game_mode: str = "survival"  # "survival" | "creative"
        self.flying: bool = False
        self._last_space_press: float = 0.0   # for double-tap fly toggle
        self._space_was_down: bool = False
        self._elapsed: float = 0.0

    @property
    def hotbar(self):
        return [s.block_id for s in self.inventory.hotbar]

    def forward_right(self) -> Tuple[np.ndarray, np.ndarray]:
        cy = math.cos(self.yaw)
        sy = math.sin(self.yaw)
        cp = math.cos(self.pitch)
        sp = math.sin(self.pitch)
        forward = np.array([sy * cp, -sp, -cy * cp], dtype="f4")
        right = np.array([cy, 0.0, sy], dtype="f4")
        return forward, right

    def camera(self, use_render: bool = False):
        forward, _ = self.forward_right()
        base = self.render_pos if (use_render and self.render_pos is not None) else self.pos
        cam_pos = base + np.array([0.0, self.current_height() * 0.90, 0.0], dtype="f4")
        return {"pos": (float(cam_pos[0]), float(cam_pos[1]), float(cam_pos[2])),
                "forward": (float(forward[0]), float(forward[1]), float(forward[2]))}

    def update_render_interp(self, alpha: float) -> None:
        """Compute the interpolated camera position between the previous and
        current physics tick (alpha = leftover_accumulator / TICK, in [0,1))."""
        a = 0.0 if alpha < 0.0 else 1.0 if alpha > 1.0 else alpha
        self.render_pos = self.prev_pos + (self.pos - self.prev_pos) * a

    def _block_below(self, world) -> int:
        bx = int(math.floor(float(self.pos[0])))
        by = int(math.floor(float(self.pos[1]) - 0.05))
        bz = int(math.floor(float(self.pos[2])))
        return world.get_block(bx, by, bz)

    def current_height(self) -> float:
        return self.height_crouch if self._crouching else self.height_stand

    def aabb(self):
        h = self.current_height()
        mn = (self.pos[0] - self.radius, self.pos[1], self.pos[2] - self.radius)
        mx = (self.pos[0] + self.radius, self.pos[1] + h, self.pos[2] + self.radius)
        return mn, mx

    def _in_water(self, world) -> bool:
        mid_y = int(math.floor(self.pos[1] + self.current_height() * 0.5))
        feet_y = int(math.floor(self.pos[1] + 0.1))
        px = int(math.floor(self.pos[0]))
        pz = int(math.floor(self.pos[2]))
        return (world.get_block(px, mid_y, pz) == BLOCK_WATER or
                world.get_block(px, feet_y, pz) == BLOCK_WATER)

    def _head_in_water(self, world) -> bool:
        head_y = int(math.floor(self.pos[1] + self.current_height() * 0.9))
        px = int(math.floor(self.pos[0]))
        pz = int(math.floor(self.pos[2]))
        return world.get_block(px, head_y, pz) == BLOCK_WATER

    def _in_lava(self, world) -> bool:
        mid_y = int(math.floor(self.pos[1] + self.current_height() * 0.5))
        feet_y = int(math.floor(self.pos[1] + 0.1))
        px = int(math.floor(self.pos[0]))
        pz = int(math.floor(self.pos[2]))
        return (world.get_block(px, mid_y, pz) == BLOCK_LAVA or
                world.get_block(px, feet_y, pz) == BLOCK_LAVA)

    def _has_ground_at(self, world, dx: float, dz: float) -> bool:
        check_y = int(math.floor(self.pos[1])) - 1
        corners = [
            (self.pos[0] + dx - self.radius, self.pos[2] + dz - self.radius),
            (self.pos[0] + dx + self.radius, self.pos[2] + dz - self.radius),
            (self.pos[0] + dx - self.radius, self.pos[2] + dz + self.radius),
            (self.pos[0] + dx + self.radius, self.pos[2] + dz + self.radius),
        ]
        return any(
            is_solid(world.get_block(int(math.floor(cx)), check_y, int(math.floor(cz))))
            for cx, cz in corners
        )

    def update_look(self, dt: float, world, inp: InputState):
        """Per-FRAME update: camera look, hotbar selection, raycast target, and
        edge-triggered actions (place / break / attack / pick). Physics lives in
        tick() and runs at a fixed 20 TPS independent of frame rate."""
        if not self.alive:
            self.death_timer += dt
            return

        self._elapsed += dt
        self._crouching = bool(inp.crouch)
        self.yaw += float(inp.mouse_dx) * self.sensitivity
        self.pitch += float(inp.mouse_dy) * self.sensitivity
        self.pitch = clamp(self.pitch, -1.55, 1.55)

        if inp.hotbar_index is not None:
            self.active_slot = int(clamp(inp.hotbar_index, 0, len(self.hotbar) - 1))
            self.inventory.active_slot = self.active_slot
        if inp.scroll_delta:
            self.active_slot = (self.active_slot - inp.scroll_delta) % len(self.hotbar)
            self.inventory.active_slot = self.active_slot

        # 8C: Double-tap space to toggle flying in creative mode
        if self.game_mode == "creative":
            jump_edge = bool(inp.jump) and not self._space_was_down
            if jump_edge:
                if self._elapsed - self._last_space_press < 0.35:
                    self.flying = not self.flying
                    if self.flying:
                        self.vel[1] = 0.0
                self._last_space_press = self._elapsed
            self._space_was_down = bool(inp.jump)
        else:
            # Force flying off when leaving creative
            self.flying = False
            self._space_was_down = bool(inp.jump)

        self._attack_cooldown = max(0.0, self._attack_cooldown - dt)
        self.damage_flash_timer = max(0.0, self.damage_flash_timer - dt)

        # Raycast every frame (after look) so place/break/attack use a fresh target.
        self.target = self.raycast(world)

        if inp.pick_pressed and self.target and self.target.hit:
            if self.target.block_id in self.hotbar:
                self.active_slot = self.hotbar.index(self.target.block_id)

        if inp.place_pressed:
            self.place(world)

        if inp.attack_pressed and self._attack_cooldown <= 0.0:
            self._try_attack(world)
            self._attack_cooldown = 0.5

        if inp.break_held:
            self.break_tick(world, dt)
        else:
            self.break_pos = None
            self.break_progress = 0.0

    def tick(self, world, inp: InputState):
        """Fixed 20 TPS physics step (Minecraft-style slipperiness + gravity).
        Called 0..5 times per frame from the accumulator in Game.run()."""
        if not self.alive:
            return

        self.prev_pos = self.pos.copy()
        self._crouching = bool(inp.crouch)
        dt = TICK
        self._hurt_cd = max(0.0, self._hurt_cd - dt)

        forward, right = self.forward_right()
        f2 = np.array([forward[0], 0.0, forward[2]], dtype="f4")
        rn = float(np.linalg.norm(f2))
        if rn > 0:
            f2 /= rn
        move = f2 * float(inp.move_z) + right * float(inp.move_x)
        mn = float(np.linalg.norm(move))
        if mn > 0.0:
            move /= mn

        in_water = self._in_water(world)
        if in_water:
            # Water breaks fall — reset peak so future ground impact does no damage
            self._air_y_peak = float(self.pos[1])

        # Target horizontal speed (blocks/sec) — Minecraft reference values.
        if self.flying:
            target_speed = FLY_SPRINT_SPEED if inp.sprint else FLY_SPEED
        elif self._crouching:
            target_speed = SNEAK_SPEED
        elif inp.sprint:
            target_speed = SPRINT_SPEED
        else:
            target_speed = WALK_SPEED
        if in_water and not self.flying:
            target_speed *= SWIM_SPEED_MULT

        # Sneak edge-protection: don't step off a ledge while crouching.
        if self._crouching and self.on_ground and not self.flying:
            nx_step = move[0] * target_speed * dt
            nz_step = move[2] * target_speed * dt
            if not self._has_ground_at(world, nx_step, nz_step):
                move[0] = 0.0
                move[2] = 0.0

        if self.flying:
            # Creative flight: snappy approach, no gravity. Space up / crouch down.
            desired = move * target_speed
            self.vel[0] = approach(self.vel[0], desired[0], FLY_ACCEL * dt)
            self.vel[2] = approach(self.vel[2], desired[2], FLY_ACCEL * dt)
            vy_t = FLY_VERT_SPEED if inp.jump else (-FLY_VERT_SPEED if inp.crouch else 0.0)
            self.vel[1] = approach(self.vel[1], vy_t, FLY_ACCEL * dt)
            self._move_and_collide(world, dt)
        else:
            # Effective horizontal slipperiness of the surface (or air).
            if self.on_ground:
                slip = SLIPPERINESS.get(self._block_below(world), DEFAULT_SLIP) * AIR_DRAG
            else:
                slip = AIR_DRAG
            # Accelerate toward the steady-state target speed for this slip value.
            accel = target_speed * (1.0 - slip) / slip
            if not self.on_ground:
                accel *= AIR_CONTROL
            self.vel[0] += move[0] * accel
            self.vel[2] += move[2] * accel

            # Jump impulse BEFORE the move so the displacement uses full launch
            # velocity (Minecraft applies gravity after moving -> ~1.25 block apex).
            if in_water:
                if inp.jump:
                    self.vel[1] = WATER_JUMP_VELOCITY
            elif self.on_ground and inp.jump:
                self.vel[1] = JUMP_VELOCITY
                self.on_ground = False
                self._air_y_peak = float(self.pos[1])
                if inp.sprint and mn > 0.0:
                    self.vel[0] += move[0] * SPRINT_JUMP_BOOST
                    self.vel[2] += move[2] * SPRINT_JUMP_BOOST

            # Don't fall into ungenerated chunks.
            if self.vel[1] < -5.0:
                px_cx, px_cz = world.chunk_coords(int(self.pos[0]), int(self.pos[2]))
                if world.chunks.get((px_cx, px_cz)) is None:
                    self.vel[1] = max(self.vel[1], -5.0)

            self._move_and_collide(world, dt)

            # Gravity + friction applied AFTER moving (for the next tick).
            if in_water:
                self.vel[1] = (self.vel[1] - GRAVITY_PER_TICK * WATER_GRAV_MULT) * WATER_DRAG
                self.vel[1] = clamp(self.vel[1], -WATER_TERMINAL, WATER_TERMINAL)
                self.vel[0] *= WATER_DRAG
                self.vel[2] *= WATER_DRAG
            else:
                self.vel[1] = (self.vel[1] - GRAVITY_PER_TICK) * VERTICAL_DRAG
                if self.vel[1] < TERMINAL_VELOCITY:
                    self.vel[1] = TERMINAL_VELOCITY
                self.vel[0] *= slip
                self.vel[2] *= slip

        # Environment effects (hunger / starvation / lava / drowning).
        if self.game_mode != "creative":
            self._hunger_drain_timer += dt
            if self._hunger_drain_timer >= 30.0:
                self._hunger_drain_timer = 0.0
                self.hunger = max(0.0, self.hunger - 1.0)

            if self.hunger <= 0.0:
                self.health = max(1.0, self.health - 2.0 * dt)

            if self._in_lava(world):
                self.take_damage(4.0 * dt, is_attack=False)

            # Drowning: head submerged depletes air (10s), then deals 2 dmg every 2s
            if self._head_in_water(world):
                self.air = max(0.0, self.air - dt)
                if self.air <= 0.0:
                    self._drown_timer += dt
                    if self._drown_timer >= 2.0:
                        self.take_damage(2.0, is_attack=False)
                        self._drown_timer = 0.0
            else:
                self.air = min(10.0, self.air + dt * 4.0)
                self._drown_timer = 0.0

        if self.pos[1] < -64.0:
            self.die()

    def take_damage(self, amount: float, source_pos=None, is_attack: bool = True) -> None:
        # 8C: invulnerable in creative mode
        if self.game_mode == "creative":
            return
        # Minecraft invulnerability frames: 0.5s after an attack hit. Continuous
        # environment damage (lava/drowning/starvation) bypasses this with
        # is_attack=False so it still applies every tick.
        if is_attack:
            if self._hurt_cd > 0.0:
                return
            self._hurt_cd = 0.5
        # Minecraft armor: defense points reduce incoming damage (full set = 20 pts = 80%).
        if amount > 0:
            armor = self.inventory.total_armor_points()
            if armor > 0:
                amount *= (1.0 - min(20, armor) / 25.0)
                self._damage_armor()
        self.health = max(0.0, self.health - amount)
        self.damage_flash_timer = 0.3
        if source_pos is not None:
            dx = float(self.pos[0]) - float(source_pos[0])
            dz = float(self.pos[2]) - float(source_pos[2])
            d = math.sqrt(dx * dx + dz * dz) + 1e-6
            self.vel[0] += dx / d * 4.0
            self.vel[2] += dz / d * 4.0
            self.vel[1] = 3.0
        if self.health <= 0.0:
            self.die()

    def _damage_armor(self) -> None:
        """Each equipped armor piece loses 1 durability per hit; breaks at 0 (Minecraft-style)."""
        from .inventory import ItemStack
        for i, s in enumerate(self.inventory.armor):
            if s.is_empty():
                continue
            defn = get_definition(s.block_id)
            if defn.max_durability <= 0:
                continue
            if s.durability <= 0:  # legacy/edge: treat unset durability as full
                s.durability = defn.max_durability
            s.durability -= 1
            if s.durability <= 0:
                self.inventory.armor[i] = ItemStack()

    def _recalc_xp(self) -> None:
        xp_per_level = 50
        self.xp_level = self.xp // xp_per_level
        self.xp_progress = (self.xp % xp_per_level) / xp_per_level

    def _try_attack(self, world) -> None:
        cam = self.camera()
        cam_pos = np.array(cam["pos"], dtype="f4")
        # Minecraft survival melee reach is 3.0 blocks (block reach 4.5 is separate).
        ATTACK_REACH = 3.0
        damage = 1.0
        held_id = self.inventory.active_block_id()
        if held_id != BLOCK_AIR and is_item_id(held_id):
            def_ = get_definition(held_id)
            if def_.tool_type == ToolType.SWORD:
                damage = 7.0
            elif def_.tool_type == ToolType.AXE:
                damage = 5.0
            elif def_.tool_type == ToolType.PICKAXE:
                damage = 2.0

        entities = getattr(world, 'entities', [])
        best_dist = ATTACK_REACH
        best_ent = None
        for ent in entities:
            if not getattr(ent, 'alive', False):
                continue
            d = float(np.linalg.norm(ent.pos - cam_pos))
            if d < best_dist:
                best_dist = d
                best_ent = ent

        if best_ent is not None and isinstance(best_ent, Mob):
            spawn_buf = []
            best_ent.take_damage(damage, tuple(self.pos.tolist()), spawn_buf, is_attack=True)
            for new_ent in spawn_buf:
                entities.append(new_ent)

    def die(self):
        if self.alive:
            self.alive = False
            self.death_timer = 0.0
            self.vel[:] = 0.0
            print("Player died!")

    def respawn(self, spawn_pos: Tuple[float, float, float]):
        self.pos[:] = spawn_pos
        self.vel[:] = 0.0
        self.alive = True
        self.death_timer = 0.0
        self.on_ground = False
        self.health = 20.0
        self.hunger = 20.0
        self._air_y_peak = spawn_pos[1]
        print(f"Player respawned at {spawn_pos}")

    def _move_and_collide(self, world, dt: float):
        self.on_ground = False
        dx, dy, dz = (float(self.vel[0] * dt), float(self.vel[1] * dt), float(self.vel[2] * dt))
        # Track peak height for fall damage
        if not self.on_ground and self.vel[1] > 0:
            self._air_y_peak = max(self._air_y_peak, float(self.pos[1]))
        self._move_axis(world, 0, dx)
        self._move_axis(world, 2, dz)
        self._move_axis(world, 1, dy)

    def _move_axis(self, world, axis: int, delta: float):
        if delta == 0.0:
            return
        sign = 1.0 if delta > 0.0 else -1.0
        remaining = abs(delta)
        step = 0.03
        while remaining > 1e-6:
            move = sign * min(step, remaining)
            self.pos[axis] = float(self.pos[axis]) + move
            if self._collides(world):
                self.pos[axis] = float(self.pos[axis]) - move
                if axis == 1:
                    if sign < 0.0:
                        self.on_ground = True
                        fall_dist = self._air_y_peak - float(self.pos[1])
                        # 8C: no fall damage in creative or flying
                        if fall_dist > 4.0 and self.game_mode != "creative" and not self.flying:
                            dmg = (fall_dist - 4.0) * 1.5
                            self.health = max(0.0, self.health - dmg)
                            if self.health <= 0.0:
                                self.die()
                        self._air_y_peak = float(self.pos[1])
                    self.vel[1] = 0.0
                elif axis != 1 and self.on_ground:
                    # Minecraft auto-step height is 0.6 blocks (slabs/single steps).
                    self.pos[1] += 0.6
                    self.pos[axis] += move
                    if not self._collides(world):
                        remaining = 0.0
                        continue
                    self.pos[axis] -= move
                    self.pos[1] -= 0.6
                    self.vel[axis] = 0.0
                    return
                else:
                    self.vel[axis] = 0.0
                return
            remaining -= abs(move)

    def _collides(self, world) -> bool:
        mn, mx = self.aabb()
        # Epsilon inset prevents boundary false-negatives (rounding error on block faces)
        eps = 1e-4
        x0 = int(math.floor(mn[0] + eps))
        x1 = int(math.floor(mx[0] - eps))
        y0 = int(math.floor(mn[1] + eps))
        y1 = int(math.floor(mx[1] - eps))
        z0 = int(math.floor(mn[2] + eps))
        z1 = int(math.floor(mx[2] - eps))

        for y in range(y0, y1 + 1):
            if y < 0 or y >= 256:
                continue
            for x in range(x0, x1 + 1):
                for z in range(z0, z1 + 1):
                    cx, cz = world.chunk_coords(x, z)
                    chunk = world.chunks.get((cx, cz))
                    if chunk is None:
                        continue
                    lx = x - cx * 16
                    lz = z - cz * 16
                    bid = chunk.get_local(lx, y, lz)
                    if is_solid(bid):
                        return True
        return False

    def raycast(self, world) -> TargetBlock:
        cam = self.camera()
        ox, oy, oz = cam["pos"]
        dx, dy, dz = cam["forward"]
        x = float(ox)
        y = float(oy)
        z = float(oz)

        ix = int(math.floor(x))
        iy = int(math.floor(y))
        iz = int(math.floor(z))

        step_x = 1 if dx > 0 else -1
        step_y = 1 if dy > 0 else -1
        step_z = 1 if dz > 0 else -1

        t_delta_x = abs(1.0 / dx) if dx != 0 else 1e9
        t_delta_y = abs(1.0 / dy) if dy != 0 else 1e9
        t_delta_z = abs(1.0 / dz) if dz != 0 else 1e9

        def intbound(s, ds):
            if ds == 0:
                return 1e9
            s = float(s)
            if ds > 0:
                return (math.floor(s + 1) - s) / ds
            return (s - math.floor(s)) / (-ds)

        t_max_x = intbound(x, dx)
        t_max_y = intbound(y, dy)
        t_max_z = intbound(z, dz)

        max_t = self.reach
        last = (ix, iy, iz)

        while True:
            bid = world.get_block(ix, iy, iz)
            if bid != BLOCK_AIR and bid != BLOCK_WATER:
                px, py, pz = last
                return TargetBlock(True, (ix, iy, iz), (px, py, pz), bid)

            last = (ix, iy, iz)

            if t_max_x < t_max_y:
                if t_max_x < t_max_z:
                    if t_max_x > max_t:
                        break
                    ix += step_x
                    t_max_x += t_delta_x
                else:
                    if t_max_z > max_t:
                        break
                    iz += step_z
                    t_max_z += t_delta_z
            else:
                if t_max_y < t_max_z:
                    if t_max_y > max_t:
                        break
                    iy += step_y
                    t_max_y += t_delta_y
                else:
                    if t_max_z > max_t:
                        break
                    iz += step_z
                    t_max_z += t_delta_z

        return TargetBlock(False, (0, 0, 0), (0, 0, 0), BLOCK_AIR)

    def drop_active(self, world, count: int = 1) -> bool:
        """Drop `count` items from the active hotbar slot into the world.
        Returns True if anything was dropped."""
        from .entity import ItemEntity
        from .inventory import ItemStack
        slot = self.inventory.hotbar[self.active_slot]
        if slot.is_empty():
            return False
        drop_count = min(int(count), int(slot.count))
        if drop_count <= 0:
            return False
        bid = int(slot.block_id)
        slot.count -= drop_count
        if slot.count <= 0:
            slot.block_id = BLOCK_AIR
            slot.count = 0
        fwd, _ = self.forward_right()
        drop_pos = (float(self.pos[0] + fwd[0] * 0.5),
                    float(self.pos[1] + 1.2),
                    float(self.pos[2] + fwd[2] * 0.5))
        e = ItemEntity(drop_pos, ItemStack(bid, drop_count))
        # Forward throw velocity (overrides ItemEntity's tiny scatter)
        e.vel[0] = float(fwd[0]) * 4.0
        e.vel[1] = 2.0
        e.vel[2] = float(fwd[2]) * 4.0
        world.entities.append(e)
        return True

    def place(self, world) -> None:
        if not self.target or not self.target.hit:
            return
        px, py, pz = self.target.place_pos
        if world.get_block(px, py, pz) != BLOCK_AIR:
            return
        block_id = self.inventory.active_block_id()
        if block_id == BLOCK_AIR:
            return
        # Items (64+: tools, food, spawn eggs, ...) are never placed as blocks.
        if is_item_id(block_id):
            return

        # Bed: 2-block placement
        from .chunk import BLOCK_BED
        if block_id == BLOCK_BED:
            self._try_place_bed(world, (px, py, pz))
            return

        mn, mx = self.aabb()
        if aabb_intersects_block(mn, mx, (px, py, pz)):
            return
        world.set_block(px, py, pz, block_id)
        # 8C: skip item consumption in creative mode
        if self.game_mode != "creative":
            self.inventory.consume_active(1)

    def _try_place_bed(self, world, foot_pos: Tuple[int, int, int]) -> bool:
        from .chunk import BLOCK_AIR, BLOCK_BED, is_solid
        # Determine facing from yaw (degrees): 0=+Z (south), 90=-X (west), etc.
        deg = (math.degrees(self.yaw) % 360.0 + 360.0) % 360.0
        if deg < 45 or deg >= 315:
            facing = "S"
            dx, dz = 0, 1
        elif deg < 135:
            facing = "W"
            dx, dz = -1, 0
        elif deg < 225:
            facing = "N"
            dx, dz = 0, -1
        else:
            facing = "E"
            dx, dz = 1, 0
        fx, fy, fz = foot_pos
        hx, hy, hz = fx + dx, fy, fz + dz
        if world.get_block(fx, fy, fz) != BLOCK_AIR: return False
        if world.get_block(hx, hy, hz) != BLOCK_AIR: return False
        if not is_solid(world.get_block(fx, fy - 1, fz)): return False
        if not is_solid(world.get_block(hx, hy - 1, hz)): return False
        # Don't place into player AABB
        mn, mx = self.aabb()
        if aabb_intersects_block(mn, mx, (fx, fy, fz)): return False
        if aabb_intersects_block(mn, mx, (hx, hy, hz)): return False
        world.set_block(fx, fy, fz, BLOCK_BED)
        world.set_block(hx, hy, hz, BLOCK_BED)
        entry = {"foot": (fx, fy, fz), "head": (hx, hy, hz), "facing": facing}
        world.bed_positions[(fx, fy, fz)] = entry
        world.bed_positions[(hx, hy, hz)] = entry
        if self.game_mode != "creative":
            self.inventory.consume_active(1)
        return True

    def _get_tool_info(self):
        """Return (tool_type, tool_tier) for the currently held item."""
        held_id = self.inventory.active_block_id()
        if held_id == BLOCK_AIR or not is_item_id(held_id):
            return ToolType.NONE, ToolTier.NONE
        def_ = get_definition(held_id)
        return def_.tool_type, def_.tool_tier

    def _spawn_drop_item(self, world, item_id: int, count: int, block_pos: Tuple[int, int, int]) -> None:
        """Spawn an ItemEntity at the broken-block position (used when inventory overflows)."""
        if item_id == BLOCK_AIR or count <= 0:
            return
        from .entity import ItemEntity
        from .inventory import ItemStack
        x, y, z = block_pos
        pos = (float(x) + 0.5, float(y) + 0.25, float(z) + 0.5)
        ent = ItemEntity(pos, ItemStack(int(item_id), int(count)))
        world.entities.append(ent)

    def break_tick(self, world, dt: float) -> None:
        if not self.target or not self.target.hit:
            self.break_pos = None
            self.break_progress = 0.0
            return

        bpos = self.target.block_pos
        if self.break_pos != bpos:
            self.break_pos = bpos
            self.break_progress = 0.0

        block_id = self.target.block_id

        # 8C: Creative mode breaks anything except bedrock instantly, no drops
        if self.game_mode == "creative" and block_id != BLOCK_BEDROCK and block_id != BLOCK_AIR:
            x, y, z = bpos
            world.set_block(x, y, z, BLOCK_AIR)
            world._water_pending = True
            self.break_progress = 0.0
            self.break_pos = None
            return

        # Instant-break
        if block_id in _INSTANT_BREAK:
            x, y, z = bpos
            broken_id = world.get_block(x, y, z)
            world.set_block(x, y, z, BLOCK_AIR)
            world._water_pending = True
            if broken_id != BLOCK_AIR:
                drop_id, drop_count = _get_drops(broken_id)
                if drop_count > 0:
                    self._spawn_drop_item(world, drop_id, drop_count, (x, y, z))
            self.break_progress = 0.0
            self.break_pos = None
            return

        # Unbreakable
        if block_id == BLOCK_BEDROCK:
            self.break_pos = None
            self.break_progress = 0.0
            return

        # Tool-based hardness
        tool_type, tool_tier = self._get_tool_info()
        hardness = effective_hardness(block_id, tool_type, tool_tier)

        self.break_progress += dt / hardness
        if self.break_progress >= 1.0:
            x, y, z = bpos
            broken_id = world.get_block(x, y, z)
            # Bed: remove both halves and drop one BLOCK_BED, clear spawn_point if it matched.
            from .chunk import BLOCK_BED as _BB
            if broken_id == _BB and hasattr(world, "bed_positions") and (x, y, z) in world.bed_positions:
                entry = world.bed_positions.pop((x, y, z))
                other = entry["head"] if entry["foot"] == (x, y, z) else entry["foot"]
                if other in world.bed_positions:
                    del world.bed_positions[other]
                world.set_block(*entry["foot"], BLOCK_AIR)
                world.set_block(*entry["head"], BLOCK_AIR)
                world._water_pending = True
                self._spawn_drop_item(world, _BB, 1, (x, y, z))
                sp = getattr(self, "spawn_point", None)
                if sp is not None:
                    sxi, syi, szi = int(sp[0]), int(sp[1]), int(sp[2])
                    if (sxi, syi, szi) == entry["foot"] or (sxi, syi, szi) == entry["head"]:
                        self.spawn_point = None
                self.break_progress = 0.0
                self.break_pos = None
                if hasattr(self, "stats") and isinstance(self.stats, dict):
                    self.stats["blocks_broken"] = int(self.stats.get("blocks_broken", 0)) + 1
                return
            world.set_block(x, y, z, BLOCK_AIR)
            world._water_pending = True
            # Check if using shears
            active_slot = self.inventory.active_stack()
            using_shears = (not active_slot.is_empty() and active_slot.block_id == ITEM_SHEARS)
            if broken_id != BLOCK_AIR:
                # Shears: leaves drop as block instead of nothing
                if using_shears and broken_id == BLOCK_LEAVES:
                    self._spawn_drop_item(world, BLOCK_LEAVES, 1, (x, y, z))
                else:
                    drop_id, drop_count = _get_drops(broken_id, tool_type, tool_tier)
                    if drop_count > 0:
                        self._spawn_drop_item(world, drop_id, drop_count, (x, y, z))
                    # 5% apple drop from leaves (no shears)
                    if broken_id == BLOCK_LEAVES and not using_shears and random.random() < 0.05:
                        self._spawn_drop_item(world, ITEM_APPLE, 1, (x, y, z))
                self.xp += 1
                self._recalc_xp()
                # Stats: count player-initiated block breaks
                if hasattr(self, "stats") and isinstance(self.stats, dict):
                    self.stats["blocks_broken"] = int(self.stats.get("blocks_broken", 0)) + 1
            # Shears durability (used as a tool even for soft blocks)
            if using_shears:
                slot = self.inventory.active_stack()
                if not slot.is_empty() and slot.block_id == ITEM_SHEARS:
                    defn = get_definition(slot.block_id)
                    if defn.max_durability > 0:
                        slot.durability -= 1
                        if slot.durability <= 0:
                            self.inventory.consume_active(1)
            # Decrement tool durability on successful break; remove when depleted
            elif tool_tier != ToolTier.NONE:
                slot = self.inventory.active_stack()
                if not slot.is_empty():
                    defn = get_definition(slot.block_id)
                    if defn.max_durability > 0:
                        slot.durability -= 1
                        if slot.durability <= 0:
                            self.inventory.consume_active(1)
            self.break_progress = 0.0
            self.break_pos = None


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def approach(cur: float, target: float, delta: float) -> float:
    if cur < target:
        return min(target, cur + delta)
    return max(target, cur - delta)


def aabb_intersects_block(mn, mx, bpos) -> bool:
    bx, by, bz = bpos
    bmn = (bx, by, bz)
    bmx = (bx + 1.0, by + 1.0, bz + 1.0)
    if mx[0] <= bmn[0] or mn[0] >= bmx[0]:
        return False
    if mx[1] <= bmn[1] or mn[1] >= bmx[1]:
        return False
    if mx[2] <= bmn[2] or mn[2] >= bmx[2]:
        return False
    return True