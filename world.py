from __future__ import annotations

import math
import random
import threading
from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

import numpy as np

from .chunk import (
    BLOCK_AIR,
    BLOCK_GRASS,
    BLOCK_LAVA,
    BLOCK_LEAVES,
    BLOCK_LOG,
    BLOCK_SAND,
    BLOCK_SNOW,
    BLOCK_STONE,
    BLOCK_WATER,
    LIGHT_EMISSION,
    Chunk,
    is_solid,
)
from .world_generator import WorldGenerator


@dataclass(slots=True)
class TargetBlock:
    hit: bool
    block_pos: Tuple[int, int, int]
    place_pos: Tuple[int, int, int]
    block_id: int


class MobSpawnManager:
    """Vanilla-style ongoing mob spawning + distance despawn.

    Separate from World._spawn_mobs_for_chunk (which is the one-shot initial population
    when a chunk is first generated). This class is the ongoing population loop:
    every tick_interval seconds it tries to spawn passive mobs (always) and hostile
    mobs (night only) in a ring around the player up to the configured caps.
    """

    PASSIVE_BIOMES = (0, 1, 4, 8, 9)  # PLAINS, FOREST, TAIGA, JUNGLE, SAVANNA

    def __init__(self):
        # Minecraft-style caps (per-player ring). Passive mobs are sparse;
        # hostiles fill the dark. Lowered passive / kept hostile high.
        self.passive_cap = 10
        self.hostile_cap = 40
        self.tick_timer = 0.0
        self.tick_interval = 4.0
        self.despawn_timer = 0.0
        self.despawn_interval = 2.0

    @staticmethod
    def effective_light(world, x: int, y: int, z: int) -> int:
        """Minecraft-style effective light (0-15) used for spawn gating.
        Combines block light with sky light dimmed by the time of day, so a
        surface tile is bright at noon, dim at night, and a cave is always dark."""
        block_l = world.get_block_light(x, y, z)
        sky_l = world.get_sky_light(x, y, z)
        # Daylight factor 0 (night) .. 1 (noon). time_of_day: 0=midnight, 0.5=noon.
        day = max(0.0, math.sin(float(world.time_of_day) * math.pi))
        # Internal sky-light subtraction: 0 at noon, up to 11 at midnight (Minecraft).
        subtract = int(round((1.0 - day) * 11.0))
        eff_sky = max(0, sky_l - subtract)
        return max(block_l, eff_sky)

    def _count_mobs(self, world):
        from .entity import Mob
        p = h = 0
        for e in world.entities:
            if isinstance(e, Mob):
                if e.hostile:
                    h += 1
                else:
                    p += 1
        return p, h

    def _is_night(self, world) -> bool:
        t = world.time_of_day
        return t < 0.25 or t > 0.75

    def _pick_spot(self, world, player, rng) -> Optional[Tuple[int, int, int]]:
        # Pick a random point in a 24..48 block ring around the player.
        angle = rng.uniform(0.0, 2.0 * math.pi)
        radius = rng.uniform(24.0, 48.0)
        wx = int(float(player.pos[0]) + math.cos(angle) * radius)
        wz = int(float(player.pos[2]) + math.sin(angle) * radius)
        surf_y = world.terrain_height(wx, wz)
        if surf_y < 1 or surf_y > 200:
            return None
        return (wx, surf_y, wz)

    def _try_spawn_passive(self, world, player, rng):
        from .entity import Mob, PASSIVE_MOBS
        from .chunk import BLOCK_GRASS, BLOCK_AIR
        spot = self._pick_spot(world, player, rng)
        if spot is None:
            return
        wx, surf_y, wz = spot
        if surf_y < world.sea_level + 1:
            return
        # Need grass surface + 2 air above
        if world.get_block(wx, surf_y, wz) != BLOCK_GRASS:
            return
        if world.get_block(wx, surf_y + 1, wz) != BLOCK_AIR:
            return
        if world.get_block(wx, surf_y + 2, wz) != BLOCK_AIR:
            return
        biome = world.get_biome(wx, wz)
        if biome not in self.PASSIVE_BIOMES:
            return
        # Minecraft: passive animals spawn only in reasonably bright daylight.
        if world.get_sky_light(wx, surf_y + 1, wz) < 8:
            return
        # Cluster of 2-4 of the same species
        mob_type = rng.choice(PASSIVE_MOBS)
        n = rng.randint(2, 4)
        for _ in range(n):
            ox = wx + rng.randint(-2, 2)
            oz = wz + rng.randint(-2, 2)
            oy = world.terrain_height(ox, oz)
            if oy >= world.sea_level + 1 and world.get_block(ox, oy + 1, oz) == BLOCK_AIR:
                world.entities.append(Mob((ox + 0.5, oy + 1.0, oz + 0.5), mob_type))

    def _pick_hostile_floor(self, world, player, rng):
        """Pick a valid hostile standing spot in the ring: surface or, half the
        time, an underground cave pocket. Returns the FLOOR block (mob stands on
        floor+1) or None. This is what lets hostiles spawn in dark caves by day."""
        from .chunk import BLOCK_AIR
        angle = rng.uniform(0.0, 2.0 * math.pi)
        radius = rng.uniform(24.0, 48.0)
        wx = int(float(player.pos[0]) + math.cos(angle) * radius)
        wz = int(float(player.pos[2]) + math.sin(angle) * radius)
        surf_y = world.terrain_height(wx, wz)
        if surf_y < 2 or surf_y > 200:
            return None
        if rng.random() < 0.5:
            candidates = (surf_y,)
        else:
            # Underground cave attempt: probe a few random depths for a floor.
            lo = 6
            hi = max(lo, surf_y - 4)
            candidates = tuple(rng.randint(lo, hi) for _ in range(3))
        for fy in candidates:
            if fy < 1 or fy >= 250:
                continue
            if (is_solid(world.get_block(wx, fy, wz))
                    and world.get_block(wx, fy + 1, wz) == BLOCK_AIR
                    and world.get_block(wx, fy + 2, wz) == BLOCK_AIR):
                return (wx, fy, wz)
        return None

    def _try_spawn_hostile(self, world, player, rng):
        from .entity import Mob, HOSTILE_MOBS
        from .chunk import BLOCK_AIR
        spot = self._pick_hostile_floor(world, player, rng)
        if spot is None:
            return
        wx, fy, wz = spot
        # Minecraft: hostiles only spawn where the effective light level is <= 7.
        if self.effective_light(world, wx, fy + 1, wz) > 7:
            return
        mob_type = rng.choice(HOSTILE_MOBS)
        n = rng.randint(1, 3)
        for _ in range(n):
            ox = wx + rng.randint(-2, 2)
            oz = wz + rng.randint(-2, 2)
            # Spawn the cluster near the chosen floor height (same level).
            if (is_solid(world.get_block(ox, fy, oz))
                    and world.get_block(ox, fy + 1, oz) == BLOCK_AIR
                    and world.get_block(ox, fy + 2, oz) == BLOCK_AIR
                    and self.effective_light(world, ox, fy + 1, oz) <= 7):
                world.entities.append(Mob((ox + 0.5, fy + 1.0, oz + 0.5), mob_type))

    def update(self, dt: float, world, player) -> None:
        self.tick_timer += dt
        self.despawn_timer += dt

        if self.despawn_timer >= self.despawn_interval:
            self.despawn_timer = 0.0
            self._despawn_far(world, player)

        if self.tick_timer < self.tick_interval:
            return
        self.tick_timer = 0.0

        passive, hostile = self._count_mobs(world)
        rng = random.Random()
        if passive < self.passive_cap:
            self._try_spawn_passive(world, player, rng)
        # Hostiles are gated by effective light (<=7) inside _try_spawn_hostile,
        # so they spawn at night on the surface AND in dark caves during the day.
        if hostile < self.hostile_cap:
            self._try_spawn_hostile(world, player, rng)

    def _despawn_far(self, world, player) -> None:
        from .entity import Mob
        px = float(player.pos[0])
        pz = float(player.pos[2])
        cull = []
        for e in world.entities:
            if isinstance(e, Mob):
                dx = float(e.pos[0]) - px
                dz = float(e.pos[2]) - pz
                if dx * dx + dz * dz > 128.0 * 128.0:
                    cull.append(e)
        for e in cull:
            try:
                world.entities.remove(e)
            except ValueError:
                pass


class _GenProxyWorld:
    """A thread-local stand-in for World, passed to the generator during async
    chunk generation so the worker never mutates shared World state.

    - ``chunks`` is empty, so every cross-chunk spill (e.g. a tree branch reaching
      into a neighbour) defers into the local ``pending_block_writes`` instead of
      writing into a live neighbour. The main thread replays these on integration.
    - Read-only generator helpers (seed, sea_level, terrain_height, get_biome, ...)
      are delegated to the real world via ``__getattr__``.
    """

    def __init__(self, real: "World"):
        self._real = real
        self.chunks: Dict[Tuple[int, int], Chunk] = {}
        self.pending_block_writes: Dict[Tuple[int, int], List[Tuple[int, int, int, int]]] = {}

    def __getattr__(self, name):
        # Only reached for attributes not set on the proxy itself.
        return getattr(self._real, name)

    def get_chunk(self, cx: int, cz: int, generate: bool = True):
        # Never generate neighbours from a worker thread; only report what the
        # (empty) proxy already holds.
        return self.chunks.get((int(cx), int(cz)))


class World:
    def __init__(self, seed: int):
        self.seed = int(seed)
        self.chunks: Dict[Tuple[int, int], Chunk] = {}
        self.sea_level = 64
        self.time_of_day = 0.5  # 0=midnight, 0.5=noon
        self.generator = WorldGenerator(self.seed, self.sea_level)
        self.save_manager = None  # set by Game._start_game after construction
        self.entities: List = []  # active Entity objects
        # Particle system (block break debris) — Game wires uv_by_block_face after init.
        from .particles import ParticleSystem
        self.particles = ParticleSystem(max_particles=512)
        self._uv_by_block_face = None

        # Pending chunks to generate (avoids lag spikes from generating many at once)
        self._pending_chunks: List[Tuple[int, int]] = []
        # Async chunk generation. The heavy noise/terrain work runs on a worker
        # thread so a single chunk no longer freezes the render loop. A lock
        # serialises the generator (whose `.world` back-ref is shared state); the
        # main thread integrates finished chunks (entities/chunks dict mutation).
        self._gen_lock = threading.Lock()
        self._gen_executor: Optional[ThreadPoolExecutor] = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="chunkgen")
        self._gen_futures: Dict[Tuple[int, int], Future] = {}
        self._gen_inflight_limit = 3        # how many chunks may be queued/running
        self._max_integrate_per_frame = 2   # cap remesh/spawn spikes on integration
        # Track last player chunk to avoid re-sorting every frame when standing still
        self._last_pcx = -999999
        self._last_pcz = -999999
        # Deferred cross-chunk block writes: written during generation before neighbor exists
        self.pending_block_writes: Dict[Tuple[int, int], List[Tuple[int, int, int, int]]] = {}
        # Loot to drop into chests placed by world generation (drained by Game when chunks load)
        self.pending_chest_loot: Dict[Tuple[int, int, int], List] = {}
        # Persistent world spawn (set once on first world start, restored from world.json)
        self.world_spawn: Optional[Tuple[float, float, float]] = None
        # Bed metadata: (x,y,z) → {"foot": (x,y,z), "head": (x,y,z), "facing": "N"|"S"|"E"|"W"}
        # Both foot and head keys map to the same entry for fast lookup.
        self.bed_positions: Dict[Tuple[int, int, int], dict] = {}
        # Ongoing mob spawning + distance despawn (vanilla style).
        self.spawn_manager = MobSpawnManager()

        # Water flow simulation
        self._water_sources: Set[Tuple[int, int, int]] = set()
        self._flowing_water: Set[Tuple[int, int, int]] = set()
        self._water_pending: bool = False
        self._water_timer: float = 0.0
        self._water_tick_interval: float = 0.25  # propagate 4× per second

    def chunk_coords(self, x: int, z: int) -> Tuple[int, int]:
        cx = math.floor(x / 16)
        cz = math.floor(z / 16)
        return int(cx), int(cz)

    def get_chunk(self, cx: int, cz: int, generate: bool = True) -> Optional[Chunk]:
        key = (int(cx), int(cz))
        c = self.chunks.get(key)
        if c is None and generate:
            # generate_chunk() integrates the chunk (adds to dict, drains pending
            # writes, dirties neighbours, spawns mobs) — no extra work needed here.
            c = self.generate_chunk(cx, cz)
        return c

    def get_block(self, x: int, y: int, z: int) -> int:
        if y < 0 or y >= 256:
            return BLOCK_AIR
        cx, cz = self.chunk_coords(x, z)
        c = self.get_chunk(cx, cz, generate=False)
        if c is None:
            return BLOCK_AIR
        lx = x - cx * 16
        lz = z - cz * 16
        return c.get_local(lx, y, lz)

    def set_block(self, x: int, y: int, z: int, block_id: int) -> None:
        if y < 0 or y >= 256:
            return
        cx, cz = self.chunk_coords(x, z)
        c = self.get_chunk(cx, cz, generate=True)
        lx = x - cx * 16
        lz = z - cz * 16
        before = c.get_local(lx, y, lz)
        if before == block_id:
            return
        # Spawn break particles when a non-air, non-water block is removed.
        if (block_id == BLOCK_AIR and before != BLOCK_AIR
                and before != 7  # water (avoid spam on bucket pickup)
                and self._uv_by_block_face is not None):
            try:
                self.particles.spawn_block_break((x, y, z), before, self._uv_by_block_face)
            except Exception:
                pass
        c.set_local(lx, y, lz, block_id)

        # Light-emitting blocks: recompute block light when an emitter (lava, …)
        # is placed or removed so the area lights up / darkens correctly.
        if before in LIGHT_EMISSION or block_id in LIGHT_EMISSION:
            self.update_block_light_for_edit(x, z)

        # Mark neighbor chunks dirty at borders
        if lx == 0:
            n = self.get_chunk(cx - 1, cz, generate=False)
            if n:
                n.dirty = True
        if lx == 15:
            n = self.get_chunk(cx + 1, cz, generate=False)
            if n:
                n.dirty = True
        if lz == 0:
            n = self.get_chunk(cx, cz - 1, generate=False)
            if n:
                n.dirty = True
        if lz == 15:
            n = self.get_chunk(cx, cz + 1, generate=False)
            if n:
                n.dirty = True

    def get_height(self, x: int, z: int) -> int:
        """Return the y-coordinate of the highest solid block at (x,z)."""
        for y in range(255, -1, -1):
            bid = self.get_block(x, y, z)
            if is_solid(bid):
                return y
        return 0

    def get_biome(self, x: int, z: int) -> int:
        return self.generator.get_biome(x, z)

    def terrain_height(self, x: int, z: int) -> int:
        return self.generator.terrain_height(x, z)

    def _generate_chunk_payload(self, cx: int, cz: int):
        """Pure-ish chunk production safe to run on a worker thread.

        Returns ``(chunk, captured_pending)`` where ``captured_pending`` are the
        cross-chunk block writes the generator produced (replayed on the main
        thread during integration). Does NOT touch shared World state except the
        generator, which is serialised by ``_gen_lock``. The chunk's ``.world`` is
        left unbound here and re-pointed at the real world during integration.
        """
        # Disk-load path: load + (re)light. Reads only; lock guards save_manager
        # against concurrent main-thread saves.
        with self._gen_lock:
            if self.save_manager and self.save_manager.chunk_exists(cx, cz):
                result = self.save_manager.load_chunk(cx, cz)
                if result is not None:
                    blocks, light = result
                    c = Chunk(cx, cz, None)
                    c.blocks = blocks
                    c.light = light
                    c.dirty = True
                    c.modified = False
                    if light is None or light.sum() == 0:
                        c.propagate_sky_light()
                        c.propagate_initial_block_light()
                    return c, {}
            # Fresh generation into a proxy world (captures spills locally).
            proxy = _GenProxyWorld(self)
            chunk = self.generator.generate_chunk(cx, cz, proxy)
            chunk.propagate_sky_light()  # chunk-local; safe off the main thread
            chunk.propagate_initial_block_light()  # seed emitter (lava) glow
            return chunk, proxy.pending_block_writes

    def _integrate_chunk(self, key: Tuple[int, int], chunk: Chunk,
                         captured_pending: Dict[Tuple[int, int], List]) -> None:
        """Main-thread integration of a finished chunk: bind it to the world,
        replay captured cross-chunk writes, drain queued writes, dirty neighbours
        and spawn its initial mobs."""
        cx, cz = key
        chunk.world = self                  # re-bind from proxy/None to the real world
        self.chunks[key] = chunk
        # Replay spills this chunk produced: apply to live neighbours, defer the rest.
        for nkey, writes in captured_pending.items():
            neighbor = self.chunks.get(nkey)
            if neighbor is not None:
                for (lx, y, lz, bid) in writes:
                    neighbor.set_local(lx, y, lz, bid)
                neighbor.dirty = True
            else:
                self.pending_block_writes.setdefault(nkey, []).extend(writes)
        # Apply writes other chunks previously queued for this chunk.
        self._drain_pending(chunk, key)
        # Dirty existing neighbours so the seam re-meshes.
        for _dx, _dz in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            n = self.chunks.get((cx + _dx, cz + _dz))
            if n:
                n.dirty = True
        # Initial mob population (mutates self.entities — main thread only).
        self._spawn_mobs_for_chunk(cx, cz)

    def generate_chunk(self, cx: int, cz: int) -> Chunk:
        """Synchronous generate + integrate (used for immediate, on-demand needs
        like raycasts, lighting and spawn-area pre-generation)."""
        chunk, captured = self._generate_chunk_payload(cx, cz)
        self._integrate_chunk((int(cx), int(cz)), chunk, captured)
        return chunk

    def shutdown_workers(self) -> None:
        """Stop the async generation executor (called on world teardown/quit)."""
        ex = self._gen_executor
        self._gen_executor = None
        self._gen_futures.clear()
        if ex is not None:
            ex.shutdown(wait=False, cancel_futures=True)

    def _spawn_mobs_for_chunk(self, cx: int, cz: int) -> None:
        """Deterministically spawn mobs when a chunk is first generated."""
        try:
            from .entity import Mob, PASSIVE_MOBS, HOSTILE_MOBS
        except Exception:
            return
        rng = random.Random(self.seed ^ (cx * 73856093) ^ (cz * 19349663))
        # 1-3 passive mobs on grass surface
        count = rng.randint(1, 3)
        for _ in range(count):
            lx = rng.randint(2, 13)
            lz = rng.randint(2, 13)
            wx = cx * 16 + lx
            wz = cz * 16 + lz
            surf_y = self.terrain_height(wx, wz)
            if surf_y < self.sea_level + 1:
                continue
            if self.get_block(wx, surf_y, wz) == BLOCK_GRASS:
                mob_type = rng.choice(PASSIVE_MOBS)
                self.entities.append(Mob((wx + 0.5, surf_y + 1.0, wz + 0.5), mob_type))
        # 0-1 hostile mob underground
        if rng.random() < 0.4:
            lx = rng.randint(2, 13)
            lz = rng.randint(2, 13)
            wx = cx * 16 + lx
            wz = cz * 16 + lz
            surf_y = self.terrain_height(wx, wz)
            cave_y = rng.randint(10, max(11, surf_y - 10))
            if self.get_block(wx, cave_y, wz) == 0 and self.get_block(wx, cave_y + 1, wz) == 0:
                mob_type = rng.choice(HOSTILE_MOBS)
                self.entities.append(Mob((wx + 0.5, cave_y, wz + 0.5), mob_type))

        # Village-resident villagers (decorative, wander+flee only)
        try:
            from .entity import MOB_VILLAGER
            spots = self.generator._village_builder.get_villager_spawn_positions(cx, cz)
            for (vx, vy, vz) in spots:
                self.entities.append(Mob((vx, vy, vz), MOB_VILLAGER))
        except (AttributeError, ImportError):
            pass

    def _drain_pending(self, chunk: Chunk, key: Tuple[int, int]) -> None:
        """Apply any deferred block writes that were queued for this chunk key."""
        pending = self.pending_block_writes.pop(key, None)
        if pending:
            for lx, y, lz, bid in pending:
                chunk.set_local(lx, y, lz, bid)
            chunk.dirty = True

    def update_streaming(self, player_pos: Tuple[float, float, float], render_distance_chunks: int) -> None:
        """Incremental chunk streaming: generates at most 1 new chunk per call to avoid lag spikes."""
        px, _, pz = player_pos
        pcx, pcz = self.chunk_coords(int(math.floor(px)), int(math.floor(pz)))
        r = int(_clamp(render_distance_chunks, 4, 12))

        # Compute wanted set
        wanted = set()
        for dz in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if dx * dx + dz * dz > (r + 0.5) * (r + 0.5):
                    continue
                wanted.add((pcx + dx, pcz + dz))

        # Drop chunks that are no longer wanted (save modified ones first)
        drop = [k for k in self.chunks.keys() if k not in wanted]
        for key in drop:
            chunk = self.chunks[key]
            if self.save_manager and chunk.modified:
                self.save_manager.save_chunk(chunk)
            del self.chunks[key]

        # If player moved, re-sort pending queue by distance to player
        if pcx != self._last_pcx or pcz != self._last_pcz:
            self._last_pcx = pcx
            self._last_pcz = pcz
            if self._pending_chunks:
                def dist(key):
                    dx = key[0] - pcx
                    dz = key[1] - pcz
                    return dx * dx + dz * dz
                self._pending_chunks.sort(key=dist)

        # Add missing chunks to pending queue
        missing = [k for k in wanted
                   if k not in self.chunks
                   and k not in self._pending_chunks
                   and k not in self._gen_futures]
        if missing:
            def dist(key):
                dx = key[0] - pcx
                dz = key[1] - pcz
                return dx * dx + dz * dz
            missing.sort(key=dist)
            self._pending_chunks.extend(missing)

        # --- Integrate completed async futures (main-thread only, capped per frame) ---
        integrated = 0
        done_keys = [k for k, f in self._gen_futures.items() if f.done()]
        for key in done_keys:
            if integrated >= self._max_integrate_per_frame:
                break
            fut = self._gen_futures.pop(key)
            try:
                chunk, captured = fut.result()
            except Exception as exc:
                # Generation failed on the worker; skip silently so we don't crash the
                # render loop.  The key is not in self.chunks so it stays in
                # _pending_chunks and will be retried on the next streaming pass.
                import traceback
                traceback.print_exc()
                continue
            if key not in self.chunks:
                self._integrate_chunk(key, chunk, captured)
                integrated += 1

        # --- Submit new generation tasks to the worker thread ---
        inflight = len(self._gen_futures)
        submitted = 0
        while (self._pending_chunks
               and inflight + submitted < self._gen_inflight_limit):
            key = self._pending_chunks.pop(0)
            if key in self.chunks or key in self._gen_futures:
                continue
            if self._gen_executor is None:
                break
            fut = self._gen_executor.submit(
                self._generate_chunk_payload, key[0], key[1])
            self._gen_futures[key] = fut
            submitted += 1

    def get_block_light(self, x: int, y: int, z: int) -> int:
        """Get block light level (0-15) at position."""
        if y < 0 or y >= 256:
            return 0
        cx, cz = self.chunk_coords(x, z)
        c = self.get_chunk(cx, cz, generate=False)
        if c is None:
            return 0
        lx = x - cx * 16
        lz = z - cz * 16
        return c.light[lx, y, lz] & 0x0F

    def get_sky_light(self, x: int, y: int, z: int) -> int:
        """Get sky light level (0-15) at position."""
        if y < 0 or y >= 256:
            return 15 if y >= 256 else 0
        cx, cz = self.chunk_coords(x, z)
        c = self.get_chunk(cx, cz, generate=False)
        if c is None:
            return 0
        lx = x - cx * 16
        lz = z - cz * 16
        return (c.light[lx, y, lz] >> 4) & 0x0F

    def set_block_light(self, x: int, y: int, z: int, level: int) -> None:
        """Set block light level (0-15) at position."""
        if y < 0 or y >= 256:
            return
        cx, cz = self.chunk_coords(x, z)
        c = self.get_chunk(cx, cz, generate=True)
        lx = x - cx * 16
        lz = z - cz * 16
        old = c.light[lx, y, lz]
        c.light[lx, y, lz] = (old & 0xF0) | (int(level) & 0x0F)
        c.dirty = True

    def update_block_light_for_edit(self, x: int, z: int) -> None:
        """Recompute block light across the 3x3 chunk region around an emitter
        edit. Light radius (15) is < chunk width (16), so clearing+reseeding this
        region is sufficient for a single placed/removed light source."""
        cx, cz = self.chunk_coords(x, z)
        sources = []
        for dcx in (-1, 0, 1):
            for dcz in (-1, 0, 1):
                ch = self.chunks.get((cx + dcx, cz + dcz))
                if ch is None:
                    continue
                ch.light &= 0xF0          # clear block-light nibble, keep sky light
                ch.dirty = True
                base_x = (cx + dcx) * 16
                base_z = (cz + dcz) * 16
                for bid, lvl in LIGHT_EMISSION.items():
                    for lx, yy, lz in np.argwhere(ch.blocks == bid):
                        sources.append((base_x + int(lx), int(yy), base_z + int(lz), lvl))
        if sources:
            self.propagate_block_light(sources)

    def propagate_block_light(self, sources: list) -> None:
        """Propagate block light from light sources using BFS.

        Args:
            sources: List of (x, y, z, level) tuples representing light sources.
        """
        from collections import deque
        from .chunk import TRANSPARENT_BLOCKS

        queue = deque(sources)
        visited = set()

        while queue:
            x, y, z, level = queue.popleft()
            if (x, y, z) in visited or level <= 0:
                continue
            visited.add((x, y, z))

            current_light = self.get_block_light(x, y, z)
            if level <= current_light:
                continue

            self.set_block_light(x, y, z, level)

            # Propagate to neighbors (6 adjacent blocks)
            for dx, dy, dz in [(1,0,0), (-1,0,0), (0,1,0), (0,-1,0), (0,0,1), (0,0,-1)]:
                nx, ny, nz = x + dx, y + dy, z + dz
                if (nx, ny, nz) not in visited:
                    neighbor_block = self.get_block(nx, ny, nz)
                    # Light propagates through transparent blocks and air
                    if neighbor_block in TRANSPARENT_BLOCKS:
                        queue.append((nx, ny, nz, level - 1))


    # ------------------------------------------------------------------
    # Water flow simulation
    # ------------------------------------------------------------------

    def place_water_source(self, x: int, y: int, z: int) -> None:
        """Mark (x,y,z) as a water source and schedule propagation."""
        self._water_sources.add((x, y, z))
        self._water_pending = True

    def remove_water(self, x: int, y: int, z: int) -> None:
        """Remove a water block (source or flowing) and schedule retraction."""
        self._water_sources.discard((x, y, z))
        self._flowing_water.discard((x, y, z))
        self._water_pending = True

    def tick_water(self, dt: float) -> None:
        """Time-gated BFS water propagation; call every frame."""
        self._water_timer += dt
        if self._water_timer < self._water_tick_interval:
            return
        self._water_timer = 0.0
        if not self._water_pending:
            return
        self._water_pending = False
        self._propagate_water()

    def _chunk_loaded(self, x: int, z: int) -> bool:
        cx, cz = self.chunk_coords(x, z)
        return (cx, cz) in self.chunks

    def _propagate_water(self) -> None:
        """BFS from all source blocks; fill/retract flowing water accordingly."""
        visited: Dict[Tuple[int, int, int], int] = {}  # pos -> level (0 = unlimited down)
        q: deque = deque()

        for src in self._water_sources:
            if self._chunk_loaded(src[0], src[2]):
                visited[src] = 0
                q.append((src, 0))

        node_cap = 1500  # safety cap against runaway BFS
        nodes = 0
        while q and nodes < node_cap:
            pos, level = q.popleft()
            nodes += 1

            bx, by, bz = pos
            # Flow DOWN first (gravity, unlimited)
            below = (bx, by - 1, bz)
            if below not in visited and self._chunk_loaded(bx, bz):
                bid = self.get_block(*below)
                if bid == BLOCK_AIR or bid == BLOCK_WATER:
                    visited[below] = 0
                    q.append((below, 0))
                elif bid == BLOCK_LAVA:
                    self.set_block(*below, BLOCK_STONE)

            # Flow HORIZONTAL (max 7 blocks from source)
            if level < 7:
                for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nb = (bx + dx, by, bz + dz)
                    if nb not in visited and self._chunk_loaded(nb[0], nb[2]):
                        bid = self.get_block(*nb)
                        if bid == BLOCK_AIR or bid == BLOCK_WATER:
                            visited[nb] = level + 1
                            q.append((nb, level + 1))
                        elif bid == BLOCK_LAVA:
                            self.set_block(*nb, BLOCK_STONE)

        # Determine new flowing set (everything reached that isn't a source)
        new_flowing: Set[Tuple[int, int, int]] = set()
        for pos in visited:
            if pos not in self._water_sources:
                new_flowing.add(pos)
                if self.get_block(*pos) == BLOCK_AIR:
                    self.set_block(*pos, BLOCK_WATER)

        # Retract blocks that are no longer reachable
        for pos in self._flowing_water - new_flowing:
            if self.get_block(*pos) == BLOCK_WATER:
                self.set_block(*pos, BLOCK_AIR)

        self._flowing_water = new_flowing


def _clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v