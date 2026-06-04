from __future__ import annotations

import math
import random
from typing import List, Optional, Tuple

import numpy as np

from .chunk import BLOCK_AIR, BLOCK_BEDROCK, BLOCK_LAVA, BLOCK_WATER, is_solid
from .inventory import ItemStack

# Fixed simulation step — entities tick at a fixed 20 TPS, in lockstep with the
# player, so behaviour is frame-rate independent (see Game.run()).
FIXED_DT = 1.0 / 20.0
from .items import (
    ITEM_BONE,
    ITEM_CHICKEN,
    ITEM_FEATHER,
    ITEM_GUNPOWDER,
    ITEM_LEATHER,
    ITEM_PORKCHOP,
    ITEM_RAW_BEEF,
    ITEM_ROTTEN_FLESH,
    ITEM_STRING,
    ITEM_WOOL,
)


# ---------------------------------------------------------------------------
# Mob type constants
# ---------------------------------------------------------------------------

MOB_COW = "cow"
MOB_PIG = "pig"
MOB_CHICKEN = "chicken"
MOB_SHEEP = "sheep"
MOB_ZOMBIE = "zombie"
MOB_SKELETON = "skeleton"
MOB_SPIDER = "spider"
MOB_CREEPER = "creeper"
MOB_VILLAGER = "villager"

PASSIVE_MOBS = (MOB_COW, MOB_PIG, MOB_CHICKEN, MOB_SHEEP)
HOSTILE_MOBS = (MOB_ZOMBIE, MOB_SKELETON, MOB_SPIDER, MOB_CREEPER)
VILLAGE_MOBS = (MOB_VILLAGER,)

MOB_DEFS = {
    MOB_COW:      {"health": 10, "attack": 0.0, "attack_range": 0.0, "speed": 2.5,
                   "hostile": False, "color": (0.55, 0.45, 0.30, 1.0),
                   "drops": [(ITEM_RAW_BEEF, 1, 3), (ITEM_LEATHER, 0, 2)], "height": 1.4, "width": 0.9},
    MOB_PIG:      {"health": 10, "attack": 0.0, "attack_range": 0.0, "speed": 2.5,
                   "hostile": False, "color": (0.90, 0.65, 0.65, 1.0),
                   "drops": [(ITEM_PORKCHOP, 1, 3)], "height": 0.9, "width": 0.9},
    MOB_CHICKEN:  {"health":  4, "attack": 0.0, "attack_range": 0.0, "speed": 2.0,
                   "hostile": False, "color": (0.95, 0.95, 0.90, 1.0),
                   "drops": [(ITEM_CHICKEN, 1, 1), (ITEM_FEATHER, 0, 2)], "height": 0.7, "width": 0.4},
    MOB_SHEEP:    {"health":  8, "attack": 0.0, "attack_range": 0.0, "speed": 2.5,
                   "hostile": False, "color": (0.80, 0.80, 0.80, 1.0),
                   "drops": [(ITEM_WOOL, 1, 2)], "height": 1.3, "width": 0.9},
    MOB_ZOMBIE:   {"health": 20, "attack": 3.0, "attack_range": 1.5, "speed": 2.0,
                   "hostile": True, "color": (0.30, 0.65, 0.25, 1.0),
                   "drops": [(ITEM_ROTTEN_FLESH, 0, 2)], "height": 1.8, "width": 0.6},
    MOB_SKELETON: {"health": 20, "attack": 4.0, "attack_range": 1.5, "speed": 2.5,
                   "hostile": True, "color": (0.85, 0.85, 0.85, 1.0),
                   "drops": [(ITEM_BONE, 0, 2)], "height": 1.8, "width": 0.6},
    MOB_SPIDER:   {"health": 16, "attack": 2.0, "attack_range": 1.5, "speed": 3.0,
                   "hostile": True, "color": (0.20, 0.15, 0.15, 1.0),
                   "drops": [(ITEM_STRING, 0, 2)], "height": 0.9, "width": 1.4},
    MOB_CREEPER:  {"health": 20, "attack": 0.0, "attack_range": 0.0, "speed": 2.2,
                   "hostile": True, "color": (0.35, 0.70, 0.30, 1.0),
                   "drops": [(ITEM_GUNPOWDER, 0, 2)], "height": 1.7, "width": 0.6},
    MOB_VILLAGER: {"health": 20, "attack": 0.0, "attack_range": 0.0, "speed": 1.5,
                   "hostile": False, "color": (0.55, 0.42, 0.30, 1.0),
                   "drops": [], "height": 1.8, "width": 0.6},
}

MOB_TEXTURE_NAMES: dict = {
    MOB_COW:      "mob_cow",
    MOB_PIG:      "mob_pig",
    MOB_SHEEP:    "mob_sheep",
    MOB_CHICKEN:  "mob_chicken",
    MOB_ZOMBIE:   "mob_zombie",
    MOB_SKELETON: "mob_skeleton",
    MOB_SPIDER:   "mob_spider",
    MOB_CREEPER:  "mob_creeper",
    MOB_VILLAGER: "mob_villager",
}

# 3D box model definitions — Minecraft-style articulated parts.
# offset: (x, y, z) of part center relative to mob origin (feet).
# size:   (w, h, d) in blocks.
# tex:    atlas texture name for the 6 faces.
# animated: True → leg/arm swing with walk phase.
# phase:    0.0–1.0 offset in walk cycle (opposite pairs use 0.5).
MOB_BOX_MODELS: dict = {
    MOB_COW: [
        dict(name="head",   offset=( 0.00, 1.00, 0.50), size=(0.50, 0.48, 0.48), tex="mob_cow_head", face_front="mob_cow_head_front"),
        dict(name="body",   offset=( 0.00, 0.62, 0.00), size=(0.70, 0.52, 1.00), tex="mob_cow_body"),
        dict(name="leg_fl", offset=(-0.20, 0.22, 0.32), size=(0.20, 0.44, 0.20), tex="mob_cow_leg",  animated=True, phase=0.0),
        dict(name="leg_fr", offset=( 0.20, 0.22, 0.32), size=(0.20, 0.44, 0.20), tex="mob_cow_leg",  animated=True, phase=0.5),
        dict(name="leg_bl", offset=(-0.20, 0.22,-0.32), size=(0.20, 0.44, 0.20), tex="mob_cow_leg",  animated=True, phase=0.5),
        dict(name="leg_br", offset=( 0.20, 0.22,-0.32), size=(0.20, 0.44, 0.20), tex="mob_cow_leg",  animated=True, phase=0.0),
    ],
    MOB_PIG: [
        dict(name="head",   offset=( 0.00, 0.70, 0.42), size=(0.52, 0.46, 0.48), tex="mob_pig_head", face_front="mob_pig_head_front"),
        dict(name="body",   offset=( 0.00, 0.48, 0.00), size=(0.72, 0.46, 0.88), tex="mob_pig_body"),
        dict(name="leg_fl", offset=(-0.22, 0.19, 0.28), size=(0.20, 0.38, 0.20), tex="mob_pig_leg",  animated=True, phase=0.0),
        dict(name="leg_fr", offset=( 0.22, 0.19, 0.28), size=(0.20, 0.38, 0.20), tex="mob_pig_leg",  animated=True, phase=0.5),
        dict(name="leg_bl", offset=(-0.22, 0.19,-0.28), size=(0.20, 0.38, 0.20), tex="mob_pig_leg",  animated=True, phase=0.5),
        dict(name="leg_br", offset=( 0.22, 0.19,-0.28), size=(0.20, 0.38, 0.20), tex="mob_pig_leg",  animated=True, phase=0.0),
    ],
    MOB_SHEEP: [
        dict(name="head",   offset=( 0.00, 1.00, 0.48), size=(0.50, 0.46, 0.46), tex="mob_sheep_head", face_front="mob_sheep_head_front"),
        dict(name="body",   offset=( 0.00, 0.64, 0.00), size=(0.80, 0.58, 1.00), tex="mob_sheep_wool"),
        dict(name="leg_fl", offset=(-0.22, 0.22, 0.30), size=(0.20, 0.44, 0.20), tex="mob_sheep_leg", animated=True, phase=0.0),
        dict(name="leg_fr", offset=( 0.22, 0.22, 0.30), size=(0.20, 0.44, 0.20), tex="mob_sheep_leg", animated=True, phase=0.5),
        dict(name="leg_bl", offset=(-0.22, 0.22,-0.30), size=(0.20, 0.44, 0.20), tex="mob_sheep_leg", animated=True, phase=0.5),
        dict(name="leg_br", offset=( 0.22, 0.22,-0.30), size=(0.20, 0.44, 0.20), tex="mob_sheep_leg", animated=True, phase=0.0),
    ],
    MOB_CHICKEN: [
        dict(name="head",   offset=( 0.00, 0.60, 0.24), size=(0.32, 0.30, 0.30), tex="mob_chicken_head", face_front="mob_chicken_head_front"),
        dict(name="body",   offset=( 0.00, 0.36, 0.00), size=(0.42, 0.36, 0.60), tex="mob_chicken_body"),
        dict(name="wing_l", offset=(-0.28, 0.44, 0.00), size=(0.10, 0.34, 0.56), tex="mob_chicken_wing"),
        dict(name="wing_r", offset=( 0.28, 0.44, 0.00), size=(0.10, 0.34, 0.56), tex="mob_chicken_wing"),
        dict(name="leg_l",  offset=(-0.10, 0.12, 0.10), size=(0.12, 0.25, 0.12), tex="mob_chicken_leg",  animated=True, phase=0.0),
        dict(name="leg_r",  offset=( 0.10, 0.12, 0.10), size=(0.12, 0.25, 0.12), tex="mob_chicken_leg",  animated=True, phase=0.5),
    ],
    MOB_ZOMBIE: [
        dict(name="head",   offset=( 0.00, 1.62, 0.00), size=(0.50, 0.50, 0.50), tex="mob_zombie_head", face_front="mob_zombie_head_front"),
        dict(name="body",   offset=( 0.00, 1.05, 0.00), size=(0.50, 0.60, 0.25), tex="mob_zombie_body"),
        dict(name="arm_l",  offset=(-0.35, 1.00, 0.00), size=(0.25, 0.60, 0.25), tex="mob_zombie_arm",   animated=True, phase=0.0),
        dict(name="arm_r",  offset=( 0.35, 1.00, 0.00), size=(0.25, 0.60, 0.25), tex="mob_zombie_arm",   animated=True, phase=0.5),
        dict(name="leg_l",  offset=(-0.15, 0.44, 0.00), size=(0.25, 0.60, 0.25), tex="mob_zombie_leg",   animated=True, phase=0.0),
        dict(name="leg_r",  offset=( 0.15, 0.44, 0.00), size=(0.25, 0.60, 0.25), tex="mob_zombie_leg",   animated=True, phase=0.5),
    ],
    MOB_SKELETON: [
        dict(name="head",   offset=( 0.00, 1.62, 0.00), size=(0.50, 0.50, 0.50), tex="mob_skeleton_head", face_front="mob_skeleton_head_front"),
        dict(name="body",   offset=( 0.00, 1.05, 0.00), size=(0.40, 0.60, 0.22), tex="mob_skeleton_body"),
        dict(name="arm_l",  offset=(-0.32, 1.00, 0.00), size=(0.20, 0.60, 0.20), tex="mob_skeleton_arm",   animated=True, phase=0.0),
        dict(name="arm_r",  offset=( 0.32, 1.00, 0.00), size=(0.20, 0.60, 0.20), tex="mob_skeleton_arm",   animated=True, phase=0.5),
        dict(name="leg_l",  offset=(-0.12, 0.44, 0.00), size=(0.20, 0.60, 0.20), tex="mob_skeleton_leg",   animated=True, phase=0.0),
        dict(name="leg_r",  offset=( 0.12, 0.44, 0.00), size=(0.20, 0.60, 0.20), tex="mob_skeleton_leg",   animated=True, phase=0.5),
    ],
    MOB_SPIDER: [
        dict(name="head",   offset=( 0.00, 0.52, 0.56), size=(0.52, 0.44, 0.52), tex="mob_spider_head", face_front="mob_spider_head_front"),
        dict(name="body",   offset=( 0.00, 0.46, 0.00), size=(0.96, 0.44, 0.84), tex="mob_spider_body"),
        # 4 legs per side (short spider legs)
        dict(name="leg_l1", offset=(-0.68, 0.46, 0.30), size=(0.60, 0.12, 0.12), tex="mob_spider_leg",  animated=True, phase=0.0),
        dict(name="leg_l2", offset=(-0.68, 0.42, 0.10), size=(0.60, 0.12, 0.12), tex="mob_spider_leg",  animated=True, phase=0.25),
        dict(name="leg_l3", offset=(-0.68, 0.42,-0.10), size=(0.60, 0.12, 0.12), tex="mob_spider_leg",  animated=True, phase=0.5),
        dict(name="leg_l4", offset=(-0.68, 0.46,-0.30), size=(0.60, 0.12, 0.12), tex="mob_spider_leg",  animated=True, phase=0.75),
        dict(name="leg_r1", offset=( 0.68, 0.46, 0.30), size=(0.60, 0.12, 0.12), tex="mob_spider_leg",  animated=True, phase=0.5),
        dict(name="leg_r2", offset=( 0.68, 0.42, 0.10), size=(0.60, 0.12, 0.12), tex="mob_spider_leg",  animated=True, phase=0.75),
        dict(name="leg_r3", offset=( 0.68, 0.42,-0.10), size=(0.60, 0.12, 0.12), tex="mob_spider_leg",  animated=True, phase=0.0),
        dict(name="leg_r4", offset=( 0.68, 0.46,-0.30), size=(0.60, 0.12, 0.12), tex="mob_spider_leg",  animated=True, phase=0.25),
    ],
    MOB_CREEPER: [
        dict(name="head",   offset=( 0.00, 1.48, 0.00), size=(0.50, 0.50, 0.50), tex="mob_creeper_head", face_front="mob_creeper_head_front"),
        dict(name="body",   offset=( 0.00, 0.90, 0.00), size=(0.42, 0.56, 0.26), tex="mob_creeper_body"),
        dict(name="leg_fl", offset=(-0.12, 0.34, 0.15), size=(0.22, 0.44, 0.22), tex="mob_creeper_leg",  animated=True, phase=0.0),
        dict(name="leg_fr", offset=( 0.12, 0.34, 0.15), size=(0.22, 0.44, 0.22), tex="mob_creeper_leg",  animated=True, phase=0.5),
        dict(name="leg_bl", offset=(-0.12, 0.34,-0.15), size=(0.22, 0.44, 0.22), tex="mob_creeper_leg",  animated=True, phase=0.5),
        dict(name="leg_br", offset=( 0.12, 0.34,-0.15), size=(0.22, 0.44, 0.22), tex="mob_creeper_leg",  animated=True, phase=0.0),
    ],
    MOB_VILLAGER: [
        dict(name="head",   offset=( 0.00, 1.62, 0.00), size=(0.50, 0.50, 0.50), tex="mob_villager_head", face_front="mob_villager_head_front"),
        dict(name="body",   offset=( 0.00, 1.02, 0.00), size=(0.56, 0.64, 0.28), tex="mob_villager_body"),
        dict(name="arm_l",  offset=(-0.40, 1.00, 0.00), size=(0.28, 0.60, 0.28), tex="mob_villager_arm",  animated=True, phase=0.0),
        dict(name="arm_r",  offset=( 0.40, 1.00, 0.00), size=(0.28, 0.60, 0.28), tex="mob_villager_arm",  animated=True, phase=0.5),
        dict(name="leg_l",  offset=(-0.14, 0.40, 0.00), size=(0.26, 0.60, 0.26), tex="mob_villager_leg",  animated=True, phase=0.0),
        dict(name="leg_r",  offset=( 0.14, 0.40, 0.00), size=(0.26, 0.60, 0.26), tex="mob_villager_leg",  animated=True, phase=0.5),
    ],
}


# ---------------------------------------------------------------------------
# Base Entity
# ---------------------------------------------------------------------------

class Entity:
    def __init__(self, pos: Tuple[float, float, float], width: float = 0.6, height: float = 1.8):
        self.pos = np.array(pos, dtype="f4")
        self.vel = np.array([0.0, 0.0, 0.0], dtype="f4")
        # Fixed-tick render interpolation (see Entity.tick / renderer).
        self.prev_pos = self.pos.copy()
        self.render_pos = self.pos.copy()
        self.width = float(width)
        self.height = float(height)
        self.on_ground = False
        self.alive = True

    def tick(self, world, player) -> None:
        """Fixed 20 TPS step. Records prev_pos for interpolation then runs the
        per-entity update() at the fixed timestep."""
        self.prev_pos = self.pos.copy()
        self.update(FIXED_DT, world, player)

    def aabb(self):
        r = self.width * 0.5
        mn = (float(self.pos[0]) - r, float(self.pos[1]), float(self.pos[2]) - r)
        mx = (float(self.pos[0]) + r, float(self.pos[1]) + self.height, float(self.pos[2]) + r)
        return mn, mx

    def _collides(self, world) -> bool:
        mn, mx = self.aabb()
        x0 = int(math.floor(mn[0]))
        x1 = int(math.floor(mx[0]))
        y0 = int(math.floor(mn[1]))
        y1 = int(math.floor(mx[1] - 0.001))
        z0 = int(math.floor(mn[2]))
        z1 = int(math.floor(mx[2]))
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
                    if is_solid(chunk.get_local(lx, y, lz)):
                        return True
        return False

    def _move_axis(self, world, axis: int, delta: float):
        if abs(delta) < 1e-6:
            return
        sign = 1.0 if delta > 0.0 else -1.0
        remaining = abs(delta)
        step = 0.05
        while remaining > 1e-6:
            move = sign * min(step, remaining)
            self.pos[axis] = float(self.pos[axis]) + move
            if self._collides(world):
                self.pos[axis] = float(self.pos[axis]) - move
                if axis == 1 and sign < 0:
                    self.on_ground = True
                self.vel[axis] = 0.0
                return
            remaining -= abs(move)

    def _move_and_collide(self, world, dt: float):
        self.on_ground = False
        self._move_axis(world, 0, float(self.vel[0] * dt))
        self._move_axis(world, 2, float(self.vel[2] * dt))
        self._move_axis(world, 1, float(self.vel[1] * dt))

    def update(self, dt: float, world, player) -> None:
        pass


# ---------------------------------------------------------------------------
# Item entity (dropped item)
# ---------------------------------------------------------------------------

class ItemEntity(Entity):
    def __init__(self, pos: Tuple[float, float, float], stack: ItemStack):
        super().__init__(pos, width=0.25, height=0.25)
        self.stack = stack
        self.age = 0.0
        self.pickup_delay = 1.0
        # Scatter on spawn
        self.vel[:] = [
            (random.random() - 0.5) * 0.3,
            0.4,
            (random.random() - 0.5) * 0.3,
        ]

    def update(self, dt: float, world, player) -> None:
        self.age += dt

        # Gravity
        self.vel[1] -= 16.0 * dt
        self.vel[1] = max(self.vel[1], -10.0)
        # Drag
        if self.on_ground:
            self.vel[0] *= 0.85 ** (dt * 20)
            self.vel[2] *= 0.85 ** (dt * 20)

        self._move_and_collide(world, dt)

        if self.age < self.pickup_delay:
            return

        dx = float(player.pos[0]) - float(self.pos[0])
        dy = float(player.pos[1]) - float(self.pos[1])
        dz = float(player.pos[2]) - float(self.pos[2])
        dist = math.sqrt(dx * dx + dy * dy + dz * dz)

        # Pickup
        if dist < 1.0:
            leftover = player.inventory.add_item(self.stack.block_id, self.stack.count)
            if leftover <= 0:
                self.alive = False
            else:
                self.stack.count = leftover
                self.pickup_delay = self.age + 0.5
            return

        # Magnetic pull
        if dist < 2.5 and dist > 0.01:
            pull = 5.0 * dt / dist
            self.vel[0] += dx * pull
            self.vel[2] += dz * pull
            self.vel[1] += dy * pull


# ---------------------------------------------------------------------------
# Mob
# ---------------------------------------------------------------------------

class Mob(Entity):
    def __init__(self, pos: Tuple[float, float, float], mob_type: str):
        defn = MOB_DEFS[mob_type]
        super().__init__(pos, width=defn["width"], height=defn["height"])
        self.mob_type = mob_type
        self.health = float(defn["health"])
        self.max_health = self.health
        self.attack_damage = float(defn["attack"])
        self.attack_range = float(defn["attack_range"])
        self.speed = float(defn["speed"])
        self.hostile = bool(defn["hostile"])
        self.color = defn["color"]
        self.drops: List = list(defn["drops"])

        self._ai_timer = random.uniform(0.0, 3.0)
        self._wander_target: Optional[np.ndarray] = None
        self._attack_cooldown = 0.0
        self._hit_flash_timer = 0.0
        self._flee_timer = 0.0
        self._hurt_cd = 0.0      # invulnerability frames (0.5s after an attack hit)
        self._burn_timer = 0.0   # daylight burning accumulator (undead)
        self._fuse = 0.0         # creeper fuse timer
        self.is_fusing = False   # creeper swelling (used by renderer for flash)

    def take_damage(self, amount: float, source_pos: Optional[Tuple[float, float, float]] = None,
                    spawn_list: Optional[List] = None, is_attack: bool = True) -> None:
        # Invulnerability frames for attack hits; continuous environment damage
        # (lava) passes is_attack=False so it keeps applying every tick.
        if is_attack:
            if self._hurt_cd > 0.0:
                return
            self._hurt_cd = 0.5
        self.health -= amount
        self._hit_flash_timer = 0.15
        if source_pos is not None:
            dx = float(self.pos[0]) - source_pos[0]
            dz = float(self.pos[2]) - source_pos[2]
            d = math.sqrt(dx * dx + dz * dz) + 1e-6
            self.vel[0] += dx / d * 5.0
            self.vel[2] += dz / d * 5.0
            self.vel[1] = 3.5
            self._flee_timer = 2.0
        if self.health <= 0.0:
            self.alive = False
            self._drop_loot(spawn_list)

    def _drop_loot(self, spawn_list: Optional[List]) -> None:
        if spawn_list is None:
            return
        for (item_id, min_count, max_count) in self.drops:
            count = random.randint(min_count, max_count)
            if count > 0:
                spawn_list.append(ItemEntity(
                    (float(self.pos[0]), float(self.pos[1]) + 0.5, float(self.pos[2])),
                    ItemStack(item_id, count),
                ))

    def update(self, dt: float, world, player) -> None:
        if not self.alive:
            return

        self._ai_timer -= dt
        self._attack_cooldown -= dt
        self._hit_flash_timer = max(0.0, self._hit_flash_timer - dt)
        self._flee_timer = max(0.0, self._flee_timer - dt)
        self._hurt_cd = max(0.0, self._hurt_cd - dt)

        # Physics
        self.vel[1] -= 22.0 * dt
        self.vel[1] = max(self.vel[1], -20.0)
        if self.on_ground:
            self.vel[0] *= 0.80 ** (dt * 20)
            self.vel[2] *= 0.80 ** (dt * 20)

        # AI
        dx = float(player.pos[0]) - float(self.pos[0])
        dy = float(player.pos[1]) - float(self.pos[1])
        dz = float(player.pos[2]) - float(self.pos[2])
        dist_to_player = math.sqrt(dx * dx + dy * dy + dz * dz)

        if self.hostile:
            self._hostile_ai(dt, world, player, dist_to_player, dy)
        else:
            self._passive_ai(dt, world, player, dist_to_player)

        # Daylight burning for undead — Minecraft zombies/skeletons catch fire
        # when exposed to direct sky light during the day (unless in water).
        if self.alive and self.mob_type in (MOB_ZOMBIE, MOB_SKELETON):
            day = math.sin(float(getattr(world, 'time_of_day', 0.5)) * math.pi)
            hx = int(math.floor(float(self.pos[0])))
            hz = int(math.floor(float(self.pos[2])))
            head_y = int(math.floor(float(self.pos[1]) + self.height * 0.9))
            mid_y = int(math.floor(float(self.pos[1]) + self.height * 0.5))
            exposed = world.get_sky_light(hx, head_y, hz) >= 15
            in_water = world.get_block(hx, mid_y, hz) == BLOCK_WATER
            if day > 0.5 and exposed and not in_water:
                self._burn_timer += dt
                if self._burn_timer >= 1.0:
                    self._burn_timer = 0.0
                    self.take_damage(1.0, is_attack=False)
            else:
                self._burn_timer = 0.0

        # Lava damage (player._in_lava() ile aynı pattern)
        feet_y = int(math.floor(float(self.pos[1]) + 0.1))
        mid_y  = int(math.floor(float(self.pos[1]) + self.height * 0.5))
        px     = int(math.floor(float(self.pos[0])))
        pz     = int(math.floor(float(self.pos[2])))
        if (world.get_block(px, feet_y, pz) == BLOCK_LAVA or
                world.get_block(px, mid_y,  pz) == BLOCK_LAVA):
            self.take_damage(4.0 * dt, is_attack=False)

        self._move_and_collide(world, dt)

    def _hostile_ai(self, dt: float, world, player, dist: float, dy: float = 0.0) -> None:
        # Creepers have their own approach-and-detonate behaviour.
        if self.mob_type == MOB_CREEPER:
            self._creeper_ai(dt, world, player, dist)
            return
        # Minecraft hostile follow range is ~16 blocks.
        if dist > 16.0:
            return
        dx = float(player.pos[0]) - float(self.pos[0])
        dz = float(player.pos[2]) - float(self.pos[2])
        xz_dist = math.sqrt(dx * dx + dz * dz)
        if xz_dist > 0.5:
            nx, nz = dx / xz_dist, dz / xz_dist
            # Set forward velocity first; _steer_toward may hop or override it
            # with a sideways nudge when fully walled in.
            self.vel[0] = nx * self.speed
            self.vel[2] = nz * self.speed
            self._steer_toward(world, nx, nz, dy)
        # Attack using 3D distance
        if dist <= self.attack_range + 0.5 and self._attack_cooldown <= 0.0:
            if hasattr(player, 'take_damage'):
                player.take_damage(self.attack_damage, tuple(self.pos.tolist()), is_attack=True)
            self._attack_cooldown = 1.5

    def _steer_toward(self, world, nx: float, nz: float, dy: float) -> bool:
        """Jump over a 1-block obstacle ahead, or side-step a taller wall.
        Mutates nx/nz is not possible (floats), so callers re-read self.vel; here
        we set vertical jump and nudge the velocity sideways when fully walled."""
        if not self.on_ground:
            return False
        fx = int(math.floor(float(self.pos[0]) + nx))
        fy = int(math.floor(float(self.pos[1])))
        fz = int(math.floor(float(self.pos[2]) + nz))
        foot_blocked = is_solid(world.get_block(fx, fy, fz))
        head_blocked = is_solid(world.get_block(fx, fy + 1, fz))
        if foot_blocked and not head_blocked:
            self.vel[1] = 5.5          # hop up a single step
            return False
        if dy > 1.5 and is_solid(world.get_block(fx, fy - 1, fz)):
            self.vel[1] = 5.5          # climb toward a player above
            return False
        if foot_blocked and head_blocked:
            # Walled in: try side-stepping perpendicular to the approach.
            perp_x, perp_z = -nz, nx
            sx = int(math.floor(float(self.pos[0]) + perp_x))
            sz = int(math.floor(float(self.pos[2]) + perp_z))
            if not is_solid(world.get_block(sx, fy, sz)):
                self.vel[0] = perp_x * self.speed
                self.vel[2] = perp_z * self.speed
            else:
                self.vel[0] = -perp_x * self.speed
                self.vel[2] = -perp_z * self.speed
            return True
        return False

    def _creeper_ai(self, dt: float, world, player, dist: float) -> None:
        if dist > 16.0:
            self.is_fusing = False
            self._fuse = 0.0
            return
        dx = float(player.pos[0]) - float(self.pos[0])
        dz = float(player.pos[2]) - float(self.pos[2])
        xz = math.sqrt(dx * dx + dz * dz)
        if dist <= 3.0:
            # In range: stop and light the fuse (1.5s), then detonate.
            self.vel[0] *= 0.6
            self.vel[2] *= 0.6
            self.is_fusing = True
            self._fuse += dt
            if self._fuse >= 1.5:
                self._explode(world, player)
        else:
            # Chase; the fuse cools down if the player gets away.
            self.is_fusing = False
            self._fuse = max(0.0, self._fuse - dt * 0.5)
            if xz > 0.5:
                nx, nz = dx / xz, dz / xz
                self.vel[0] = nx * self.speed
                self.vel[2] = nz * self.speed
                self._steer_toward(world, nx, nz, 0.0)

    def _explode(self, world, player) -> None:
        if not self.alive:
            return
        self.alive = False
        cx = float(self.pos[0])
        cy = float(self.pos[1]) + 0.5
        cz = float(self.pos[2])
        R = 3.0
        r = int(math.ceil(R))
        ix, iy, iz = int(math.floor(cx)), int(math.floor(cy)), int(math.floor(cz))
        for ox in range(-r, r + 1):
            for oy in range(-r, r + 1):
                for oz in range(-r, r + 1):
                    if ox * ox + oy * oy + oz * oz > R * R:
                        continue
                    bx, by, bz = ix + ox, iy + oy, iz + oz
                    if by < 0 or by >= 256:
                        continue
                    bid = world.get_block(bx, by, bz)
                    if bid != BLOCK_AIR and bid != BLOCK_BEDROCK:
                        world.set_block(bx, by, bz, BLOCK_AIR)
        # Let fluids re-settle into the crater on the next world tick.
        try:
            world._water_pending = True
        except Exception:
            pass
        # Blast damage to the player with linear falloff.
        if hasattr(player, 'take_damage'):
            pdx = float(player.pos[0]) - cx
            pdy = float(player.pos[1]) - cy
            pdz = float(player.pos[2]) - cz
            pd = math.sqrt(pdx * pdx + pdy * pdy + pdz * pdz)
            blast = R + 2.0
            if pd <= blast:
                dmg = (1.0 - pd / blast) * 22.0
                if dmg > 0.0:
                    player.take_damage(dmg, (cx, cy, cz), is_attack=True)

    def _passive_ai(self, dt: float, world, player, dist: float) -> None:
        if self._flee_timer > 0.0 and dist < 8.0:
            # Flee from player
            dx = float(self.pos[0]) - float(player.pos[0])
            dz = float(self.pos[2]) - float(player.pos[2])
            d = math.sqrt(dx * dx + dz * dz) + 1e-6
            self.vel[0] = (dx / d) * self.speed * 1.5
            self.vel[2] = (dz / d) * self.speed * 1.5
            return

        if self._ai_timer <= 0:
            # Pick a new wander target or stand still
            self._ai_timer = random.uniform(2.0, 5.0)
            if random.random() < 0.6:
                angle = random.uniform(0, 2 * math.pi)
                dist_w = random.uniform(3.0, 10.0)
                tx = float(self.pos[0]) + math.cos(angle) * dist_w
                tz = float(self.pos[2]) + math.sin(angle) * dist_w
                self._wander_target = np.array([tx, tz], dtype="f4")
            else:
                self._wander_target = None

        if self._wander_target is not None:
            tdx = float(self._wander_target[0]) - float(self.pos[0])
            tdz = float(self._wander_target[1]) - float(self.pos[2])
            td = math.sqrt(tdx * tdx + tdz * tdz)
            if td > 0.5:
                self.vel[0] = (tdx / td) * self.speed
                self.vel[2] = (tdz / td) * self.speed
            else:
                self._wander_target = None
        else:
            self.vel[0] *= 0.5
            self.vel[2] *= 0.5
