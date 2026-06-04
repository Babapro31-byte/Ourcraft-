"""Procedurally generated sound effects using numpy and pygame.mixer."""

from __future__ import annotations

import numpy as np
import pygame


class AudioManager:
    """Synthesizes and plays game sound effects procedurally."""

    def __init__(self, sample_rate: int = 22050):
        """Initialize audio system.

        Args:
            sample_rate: Sample rate in Hz (default 22050).
        """
        pygame.mixer.pre_init(sample_rate, -16, 1, 512)
        pygame.mixer.init()
        self.sample_rate = sample_rate
        self._sounds = {}
        self._build_sounds()

    def _make_sound(self, samples: np.ndarray) -> pygame.mixer.Sound:
        """Convert numpy float array to pygame Sound object."""
        arr = np.clip(samples * 32767, -32768, 32767).astype(np.int16)
        return pygame.sndarray.make_sound(arr)

    def _build_sounds(self) -> None:
        """Synthesize all game sounds."""
        # Block break (stone) — white noise with exponential decay
        t = np.linspace(0, 0.15, int(0.15 * self.sample_rate))
        noise = np.random.randn(len(t)) * 0.5
        decay = np.exp(-t * 30)
        self._sounds["break_stone"] = self._make_sound(noise * decay)

        # Block break (wood) — lower frequency, softer
        t = np.linspace(0, 0.12, int(0.12 * self.sample_rate))
        noise = np.random.randn(len(t)) * 0.3
        decay = np.exp(-t * 25)
        self._sounds["break_wood"] = self._make_sound(noise * decay)

        # Block place — short soft noise
        t = np.linspace(0, 0.08, int(0.08 * self.sample_rate))
        noise = np.random.randn(len(t)) * 0.3
        decay = np.exp(-t * 40)
        self._sounds["place"] = self._make_sound(noise * decay)

        # Footstep (grass) — low frequency soft noise
        t = np.linspace(0, 0.08, int(0.08 * self.sample_rate))
        noise = np.random.randn(len(t)) * 0.25
        decay = np.exp(-t * 30)
        self._sounds["step_grass"] = self._make_sound(noise * decay)

        # Mob hurt — buzzy tone with frequency drop
        t = np.linspace(0, 0.1, int(0.1 * self.sample_rate))
        freq_start = 400
        freq_end = 200
        freq = np.linspace(freq_start, freq_end, len(t))
        phase = 2.0 * np.pi * np.cumsum(freq) / self.sample_rate
        tone = np.sin(phase) * 0.4
        decay = np.exp(-t * 20)
        self._sounds["hurt"] = self._make_sound(tone * decay)

        # UI click — short sine pop
        t = np.linspace(0, 0.02, int(0.02 * self.sample_rate))
        freq = 440
        phase = 2.0 * np.pi * freq * t / self.sample_rate
        tone = np.sin(phase) * 0.3
        decay = np.exp(-t * 100)
        self._sounds["click"] = self._make_sound(tone * decay)

    def play_block_break(self, block_id: int) -> None:
        """Play block break sound."""
        from .chunk import BLOCK_LOG, BLOCK_LEAVES, BLOCK_PLANKS

        wood_blocks = (BLOCK_LOG, BLOCK_LEAVES, BLOCK_PLANKS)
        key = "break_wood" if block_id in wood_blocks else "break_stone"
        sound = self._sounds.get(key)
        if sound:
            sound.play()

    def play_block_place(self, block_id: int) -> None:
        """Play block placement sound."""
        sound = self._sounds.get("place")
        if sound:
            sound.play()

    def play_footstep(self, block_id: int) -> None:
        """Play footstep sound."""
        sound = self._sounds.get("step_grass")
        if sound:
            sound.set_volume(0.4)
            sound.play()
            sound.set_volume(1.0)

    def play_hurt(self, mob_type: int = 0) -> None:
        """Play mob hurt sound."""
        sound = self._sounds.get("hurt")
        if sound:
            sound.play()

    def play_click(self) -> None:
        """Play UI click sound."""
        sound = self._sounds.get("click")
        if sound:
            sound.set_volume(0.3)
            sound.play()
            sound.set_volume(1.0)
