"""Persistent settings stored in ~/.ourcraft2/config.json."""

from __future__ import annotations

import json
import os
from typing import Any, Dict


CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".ourcraft2")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

# Pygame key constants as integers (avoid importing pygame at module level)
_K = {
    "w": 119, "a": 97, "s": 115, "d": 100,
    "space": 32, "lshift": 1073742049, "lctrl": 1073741881,
    "e": 101, "escape": 27, "f3": 1073741892, "f4": 1073741893,
    "q": 113,
    "1": 49, "2": 50, "3": 51, "4": 52, "5": 53,
    "6": 54, "7": 55, "8": 56, "9": 57,
}

DEFAULT_KEYBINDS: Dict[str, int] = {
    "move_forward": _K["w"],
    "move_back":    _K["s"],
    "move_left":    _K["a"],
    "move_right":   _K["d"],
    "jump":         _K["space"],
    "sneak":        _K["lshift"],
    "sprint":       _K["lctrl"],
    "inventory":    _K["e"],
    "drop":         _K["q"],
    "debug":        _K["f3"],
    "toggle_mode":  _K["f4"],
    "hotbar_1":     _K["1"],
    "hotbar_2":     _K["2"],
    "hotbar_3":     _K["3"],
    "hotbar_4":     _K["4"],
    "hotbar_5":     _K["5"],
    "hotbar_6":     _K["6"],
    "hotbar_7":     _K["7"],
    "hotbar_8":     _K["8"],
    "hotbar_9":     _K["9"],
}

DEFAULTS: Dict[str, Any] = {
    "render_distance": 6,
    "fov": 75.0,
    "sensitivity": 0.0023,
    "brightness": 1.0,
    "keybinds": DEFAULT_KEYBINDS,
}


def _ensure_dir() -> None:
    os.makedirs(CONFIG_DIR, exist_ok=True)


def load_config() -> Dict[str, Any]:
    """Return the current config dict, filling missing keys from DEFAULTS."""
    _ensure_dir()
    data = {}
    if os.path.isfile(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = {}
    # Merge top-level defaults
    for k, v in DEFAULTS.items():
        if k not in data:
            data[k] = v
    # Merge keybind defaults (fill missing actions without overwriting user binds)
    kb = data.setdefault("keybinds", {})
    for action, key in DEFAULT_KEYBINDS.items():
        if action not in kb:
            kb[action] = key
    return data


def save_config(data: Dict[str, Any]) -> None:
    """Persist config dict to disk."""
    _ensure_dir()
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)