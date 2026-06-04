from __future__ import annotations

import json
import os
from typing import Optional

import numpy as np

SAVE_ROOT = os.path.join(os.path.expanduser("~"), ".ourcraft2", "worlds")


class SaveManager:
    def __init__(self, seed: int):
        self.seed = int(seed)
        self.world_dir = os.path.join(SAVE_ROOT, str(self.seed))
        os.makedirs(self.world_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # World listing (for world-select UI)
    # ------------------------------------------------------------------

    @staticmethod
    def list_worlds() -> list:
        """Return [(seed, mtime, player_pos)] sorted newest first.

        player_pos may be None if no player.json exists yet.
        """
        try:
            os.makedirs(SAVE_ROOT, exist_ok=True)
            names = os.listdir(SAVE_ROOT)
        except Exception:
            return []
        result = []
        for name in names:
            wpath = os.path.join(SAVE_ROOT, name)
            if not os.path.isdir(wpath):
                continue
            try:
                seed = int(name)
            except ValueError:
                continue
            try:
                mtime = os.path.getmtime(wpath)
            except OSError:
                mtime = 0.0
            player_pos = None
            ppath = os.path.join(wpath, "player.json")
            if os.path.isfile(ppath):
                try:
                    with open(ppath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    pos = data.get("pos")
                    if isinstance(pos, list) and len(pos) == 3:
                        player_pos = (float(pos[0]), float(pos[1]), float(pos[2]))
                except Exception:
                    pass
            result.append((seed, mtime, player_pos))
        result.sort(key=lambda r: r[1], reverse=True)
        return result

    @staticmethod
    def delete_world(seed: int) -> bool:
        """Remove a world directory entirely. Returns True on success."""
        import shutil
        wpath = os.path.join(SAVE_ROOT, str(int(seed)))
        if not os.path.isdir(wpath):
            return False
        try:
            shutil.rmtree(wpath)
            return True
        except Exception as e:
            print(f"Warning: failed to delete world {seed}: {e}")
            return False

    # ------------------------------------------------------------------
    # Chunk persistence
    # ------------------------------------------------------------------

    def chunk_path(self, cx: int, cz: int) -> str:
        return os.path.join(self.world_dir, f"chunk_{cx}_{cz}.npz")

    def chunk_exists(self, cx: int, cz: int) -> bool:
        return os.path.isfile(self.chunk_path(cx, cz))

    def save_chunk(self, chunk) -> None:
        if not chunk.modified:
            return
        path = self.chunk_path(chunk.cx, chunk.cz)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        np.savez_compressed(path, blocks=chunk.blocks, light=chunk.light)

    def load_chunk(self, cx: int, cz: int) -> Optional[tuple[np.ndarray, np.ndarray]]:
        path = self.chunk_path(cx, cz)
        if not os.path.isfile(path):
            return None
        try:
            data = np.load(path)
            blocks = data["blocks"].astype(np.uint8)
            # Support old save format without light data
            light = data.get("light", np.zeros((16, 256, 16), dtype=np.uint8)).astype(np.uint8)
            return blocks, light
        except Exception as e:
            print(f"Warning: failed to load chunk ({cx},{cz}): {e}")
            return None

    # ------------------------------------------------------------------
    # Player persistence
    # ------------------------------------------------------------------

    def _player_path(self) -> str:
        return os.path.join(self.world_dir, "player.json")

    def save_player(self, player) -> None:
        inv = player.inventory
        def stack_dict(s):
            return {"id": int(s.block_id), "count": int(s.count), "dur": int(getattr(s, 'durability', 0))}

        sp = getattr(player, 'spawn_point', None)
        data = {
            "pos": [float(player.pos[0]), float(player.pos[1]), float(player.pos[2])],
            "vel": [float(player.vel[0]), float(player.vel[1]), float(player.vel[2])],
            "yaw": float(player.yaw),
            "pitch": float(player.pitch),
            "health": float(player.health),
            "hunger": float(player.hunger),
            "active_slot": int(player.active_slot),
            "hotbar": [stack_dict(s) for s in inv.hotbar],
            "main": [stack_dict(s) for s in inv.main],
            "armor": [stack_dict(s) for s in inv.armor],
            "xp": int(getattr(player, 'xp', 0)),
            "xp_level": int(getattr(player, 'xp_level', 0)),
            "game_mode": str(getattr(player, 'game_mode', 'survival')),
            "stats": dict(getattr(player, 'stats', {})),
            "spawn_point": list(sp) if sp else None,
        }
        try:
            with open(self._player_path(), "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: failed to save player: {e}")

    def load_player(self, player) -> bool:
        path = self._player_path()
        if not os.path.isfile(path):
            return False
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            player.pos[:] = data["pos"]
            player.vel[:] = data.get("vel", [0.0, 0.0, 0.0])
            player.yaw = float(data.get("yaw", 0.0))
            player.pitch = float(data.get("pitch", 0.0))
            player.health = float(data.get("health", 20.0))
            player.hunger = float(data.get("hunger", 20.0))
            player.active_slot = int(data.get("active_slot", 0))
            player.inventory.active_slot = player.active_slot

            from .inventory import ItemStack
            for i, sd in enumerate(data.get("hotbar", [])):
                if i < len(player.inventory.hotbar):
                    player.inventory.hotbar[i] = ItemStack(sd["id"], sd["count"], sd.get("dur", 0))
            for i, sd in enumerate(data.get("main", [])):
                if i < len(player.inventory.main):
                    player.inventory.main[i] = ItemStack(sd["id"], sd["count"], sd.get("dur", 0))
            for i, sd in enumerate(data.get("armor", [])):
                if i < len(player.inventory.armor):
                    player.inventory.armor[i] = ItemStack(sd["id"], sd["count"], sd.get("dur", 0))

            if hasattr(player, 'xp'):
                player.xp = int(data.get("xp", 0))
                player.xp_level = int(data.get("xp_level", 0))

            if hasattr(player, 'game_mode'):
                player.game_mode = str(data.get("game_mode", "survival"))
                player.flying = (player.game_mode == "creative")

            saved_stats = data.get("stats")
            if isinstance(saved_stats, dict):
                player._loaded_stats = saved_stats

            sp = data.get("spawn_point")
            if isinstance(sp, list) and len(sp) == 3:
                player.spawn_point = (float(sp[0]), float(sp[1]), float(sp[2]))
            else:
                player.spawn_point = None

            return True
        except Exception as e:
            print(f"Warning: failed to load player save: {e}")
            return False

    # ------------------------------------------------------------------
    # World metadata persistence
    # ------------------------------------------------------------------

    def _meta_path(self) -> str:
        return os.path.join(self.world_dir, "world.json")

    def save_meta(self, world) -> None:
        data = {
            "seed": self.seed,
            "time_of_day": float(world.time_of_day),
            "world_spawn": list(world.world_spawn) if getattr(world, "world_spawn", None) else None,
        }
        try:
            with open(self._meta_path(), "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: failed to save world meta: {e}")

    def load_meta(self, world) -> None:
        path = self._meta_path()
        if not os.path.isfile(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            world.time_of_day = float(data.get("time_of_day", 0.5))
            ws = data.get("world_spawn")
            if isinstance(ws, list) and len(ws) == 3:
                world.world_spawn = (float(ws[0]), float(ws[1]), float(ws[2]))
            else:
                world.world_spawn = None
        except Exception as e:
            print(f"Warning: failed to load world meta: {e}")

    # ------------------------------------------------------------------
    # Entity persistence
    # ------------------------------------------------------------------

    def _entities_path(self) -> str:
        return os.path.join(self.world_dir, "entities.json")

    def save_entities(self, entities: list) -> None:
        data = []
        for e in entities:
            if getattr(e, 'alive', False) and hasattr(e, 'mob_type'):
                data.append({
                    "type": "mob",
                    "mob_type": e.mob_type,
                    "pos": [float(e.pos[0]), float(e.pos[1]), float(e.pos[2])],
                    "health": float(e.health),
                })
        try:
            with open(self._entities_path(), "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception as ex:
            print(f"Warning: failed to save entities: {ex}")

    def load_entities(self) -> list:
        from .entity import Mob
        path = self._entities_path()
        if not os.path.isfile(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            result = []
            for d in data:
                if d.get("type") == "mob":
                    mob = Mob(tuple(d["pos"]), d["mob_type"])
                    mob.health = float(d.get("health", mob.max_health))
                    result.append(mob)
            return result
        except Exception as ex:
            print(f"Warning: failed to load entities: {ex}")
            return []

    # ------------------------------------------------------------------
    # Bulk save
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Chest persistence
    # ------------------------------------------------------------------

    def _chests_path(self) -> str:
        return os.path.join(self.world_dir, "chests.json")

    def save_chests(self, chest_inventories: dict) -> None:
        data = {}
        for pos, slots in chest_inventories.items():
            key = f"{pos[0]},{pos[1]},{pos[2]}"
            data[key] = [{"id": int(s.block_id), "count": int(s.count)} for s in slots]
        try:
            with open(self._chests_path(), "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Warning: failed to save chests: {e}")

    def load_chests(self) -> dict:
        from .inventory import ItemStack
        path = self._chests_path()
        if not os.path.isfile(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            result = {}
            for key, slots in raw.items():
                coords = tuple(int(v) for v in key.split(","))
                result[coords] = [ItemStack(s["id"], s["count"]) for s in slots]
            return result
        except Exception as e:
            print(f"Warning: failed to load chests: {e}")
            return {}

    # ------------------------------------------------------------------
    # Furnace persistence
    # ------------------------------------------------------------------

    def _furnaces_path(self) -> str:
        return os.path.join(self.world_dir, "furnaces.json")

    def save_furnaces(self, furnace_states: dict) -> None:
        data = {}
        for pos, fs in furnace_states.items():
            key = f"{pos[0]},{pos[1]},{pos[2]}"
            def _s(stack):
                return {"id": int(stack.block_id), "count": int(stack.count)}
            data[key] = {
                "input": _s(fs['input']), "fuel": _s(fs['fuel']), "output": _s(fs['output']),
                "progress": float(fs['progress']), "fuel_left": float(fs['fuel_left']),
                "fuel_max": float(fs['fuel_max']),
            }
        try:
            with open(self._furnaces_path(), "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Warning: failed to save furnaces: {e}")

    def load_furnaces(self) -> dict:
        from .inventory import ItemStack
        path = self._furnaces_path()
        if not os.path.isfile(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            result = {}
            for key, fs in raw.items():
                coords = tuple(int(v) for v in key.split(","))
                def _s(d):
                    return ItemStack(d["id"], d["count"])
                result[coords] = {
                    'input': _s(fs['input']), 'fuel': _s(fs['fuel']), 'output': _s(fs['output']),
                    'progress': float(fs['progress']), 'fuel_left': float(fs['fuel_left']),
                    'fuel_max': float(fs.get('fuel_max', 1.0)),
                }
            return result
        except Exception as e:
            print(f"Warning: failed to load furnaces: {e}")
            return {}

    # ------------------------------------------------------------------
    # Bed persistence
    # ------------------------------------------------------------------

    def _beds_path(self) -> str:
        return os.path.join(self.world_dir, "beds.json")

    def save_beds(self, bed_positions: dict) -> None:
        # Dedupe by foot pos (head and foot share the same entry).
        seen = set()
        data = []
        for pos, entry in bed_positions.items():
            foot = tuple(entry.get("foot", ()))
            if not foot or foot in seen:
                continue
            seen.add(foot)
            data.append({
                "head": list(entry["head"]),
                "foot": list(entry["foot"]),
                "facing": str(entry.get("facing", "N")),
            })
        try:
            with open(self._beds_path(), "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Warning: failed to save beds: {e}")

    def load_beds(self) -> dict:
        path = self._beds_path()
        if not os.path.isfile(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            result = {}
            for d in raw:
                entry = {
                    "head": tuple(int(v) for v in d["head"]),
                    "foot": tuple(int(v) for v in d["foot"]),
                    "facing": str(d.get("facing", "N")),
                }
                result[entry["head"]] = entry
                result[entry["foot"]] = entry
            return result
        except Exception as e:
            print(f"Warning: failed to load beds: {e}")
            return {}

    # ------------------------------------------------------------------
    # Bulk save
    # ------------------------------------------------------------------

    def save_all_modified(self, world, player) -> None:
        """Save player, meta, all modified chunks, and entities."""
        self.save_player(player)
        self.save_meta(world)
        for chunk in world.chunks.values():
            if chunk.modified:
                self.save_chunk(chunk)
        entities = getattr(world, 'entities', [])
        self.save_entities(entities)
        self.save_chests(getattr(world, 'chest_inventories', {}))
        self.save_furnaces(getattr(world, 'furnace_states', {}))
        self.save_beds(getattr(world, 'bed_positions', {}))
