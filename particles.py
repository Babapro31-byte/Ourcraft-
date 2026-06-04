from __future__ import annotations

import random
from typing import List, Optional, Tuple

import numpy as np


class ParticleSystem:
    """Lightweight CPU-driven particle system for block-break debris."""

    __slots__ = ("max_particles", "_pos", "_vel", "_uv", "_size", "_life", "_life_max",
                 "_active", "_count")

    def __init__(self, max_particles: int = 512):
        self.max_particles = int(max_particles)
        n = self.max_particles
        self._pos = np.zeros((n, 3), dtype="f4")
        self._vel = np.zeros((n, 3), dtype="f4")
        self._uv = np.zeros((n, 2), dtype="f4")   # base atlas UV (u0,v0) of the tile
        self._size = np.zeros(n, dtype="f4")
        self._life = np.zeros(n, dtype="f4")
        self._life_max = np.zeros(n, dtype="f4")
        self._active = np.zeros(n, dtype=bool)
        self._count = 0

    def spawn_block_break(self, world_pos: Tuple[float, float, float],
                          block_id: int, uv_by_block_face) -> None:
        """Spawn ~10 particles for a broken block at world_pos."""
        bx, by, bz = float(world_pos[0]), float(world_pos[1]), float(world_pos[2])
        # Pick top face UV; fall back to side face.
        uv = uv_by_block_face.get((block_id, 4))
        if uv is None:
            uv = uv_by_block_face.get((block_id, 0))
        if uv is None:
            return
        u0, v0, u1, v1 = uv
        # We'll randomize within the tile by emitting a small UV box around a random point
        rng = random.Random()
        n_to_spawn = 10
        for _ in range(n_to_spawn):
            idx = self._find_slot()
            if idx < 0:
                return
            # Particle randomized position inside the block volume.
            px = bx + 0.5 + rng.uniform(-0.35, 0.35)
            py = by + 0.5 + rng.uniform(-0.35, 0.35)
            pz = bz + 0.5 + rng.uniform(-0.35, 0.35)
            # Velocity: random sphere with upward bias
            vx = rng.uniform(-2.0, 2.0)
            vy = rng.uniform(0.5, 3.0)
            vz = rng.uniform(-2.0, 2.0)
            # Random size and lifetime
            sz = rng.uniform(0.06, 0.12)
            life = rng.uniform(0.6, 1.2)
            # Pick a small sub-region of the tile texel for variety
            # Bias toward center; we use simple jitter
            jitter_u = rng.uniform(0.05, 0.95)
            jitter_v = rng.uniform(0.05, 0.95)
            sub_u = u0 + (u1 - u0) * jitter_u
            sub_v = v0 + (v1 - v0) * jitter_v
            self._pos[idx] = (px, py, pz)
            self._vel[idx] = (vx, vy, vz)
            self._uv[idx] = (sub_u, sub_v)
            self._size[idx] = sz
            self._life[idx] = life
            self._life_max[idx] = life
            self._active[idx] = True
            self._count += 1

    def _find_slot(self) -> int:
        # Linear scan for an inactive slot; for max_particles=512 this is cheap.
        for i in range(self.max_particles):
            if not self._active[i]:
                return i
        # Overwrite the oldest particle if all slots full
        return int(np.argmin(self._life))

    def update(self, dt: float, world) -> None:
        """Integrate gravity + simple ground collision; cull dead particles."""
        if self._count == 0:
            return
        active = self._active
        # Gravity
        self._vel[active, 1] -= 9.8 * dt
        # Air drag
        self._vel[active] *= (1.0 - 1.5 * dt)
        # Integrate
        self._pos[active] += self._vel[active] * dt
        # Lifetime
        self._life[active] -= dt
        # Simple collision: check if next position is solid (cheap; only y stop)
        # We sample world.get_block; if solid, clamp y and zero v.y
        if world is not None:
            idxs = np.where(active)[0]
            for i in idxs:
                px, py, pz = float(self._pos[i, 0]), float(self._pos[i, 1]), float(self._pos[i, 2])
                bx = int(np.floor(px))
                by = int(np.floor(py))
                bz = int(np.floor(pz))
                bid = world.get_block(bx, by, bz)
                if bid not in (0, 7):  # AIR=0, WATER=7
                    # Snap up and damp
                    self._pos[i, 1] = by + 1.001
                    if self._vel[i, 1] < 0:
                        self._vel[i, 1] = 0.0
                    # Horizontal friction
                    self._vel[i, 0] *= 0.5
                    self._vel[i, 2] *= 0.5
        # Cull
        dead = active & (self._life <= 0.0)
        if dead.any():
            self._active[dead] = False
            self._count = int(self._active.sum())

    def build_vertex_data(self) -> Optional[np.ndarray]:
        """Build per-vertex array for billboard quads. Returns None if no active."""
        if self._count == 0:
            return None
        idxs = np.where(self._active)[0]
        n = len(idxs)
        if n == 0:
            return None
        # 6 verts per particle, each vert: (center.xyz, offset.xy, uv.xy, size, life_norm)
        # Total floats per vertex = 3 + 2 + 2 + 1 + 1 = 9
        # We'll bake offset (-1..1) and tiny uv jitter inline.
        verts = np.empty((n * 6, 9), dtype="f4")
        # Pre-compute tile half-pixel UV box around the (sub_u, sub_v) center.
        TILE_UV = 0.004   # small UV size — particle samples a tiny region
        for i, pi in enumerate(idxs):
            cx, cy, cz = float(self._pos[pi, 0]), float(self._pos[pi, 1]), float(self._pos[pi, 2])
            su, sv = float(self._uv[pi, 0]), float(self._uv[pi, 1])
            sz = float(self._size[pi])
            life_norm = float(self._life[pi] / self._life_max[pi]) if self._life_max[pi] > 0 else 0.0
            # Quad corners: (-1,-1),(1,-1),(1,1),(-1,-1),(1,1),(-1,1)
            corners = [
                (-1.0, -1.0, su,           sv + TILE_UV),
                ( 1.0, -1.0, su + TILE_UV, sv + TILE_UV),
                ( 1.0,  1.0, su + TILE_UV, sv),
                (-1.0, -1.0, su,           sv + TILE_UV),
                ( 1.0,  1.0, su + TILE_UV, sv),
                (-1.0,  1.0, su,           sv),
            ]
            base = i * 6
            for k, (ox, oy, uu, vv) in enumerate(corners):
                verts[base + k] = (cx, cy, cz, ox, oy, uu, vv, sz, life_norm)
        return verts
