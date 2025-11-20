"""Simple sound effect utilities using pygame's mixer."""
from __future__ import annotations

import os
import warnings
from pathlib import Path
from typing import Union

import pygame

_MIXER_CHECKED = False
_MIXER_AVAILABLE = False
_ENABLED = True

_SOUNDS: dict[str, "pygame.mixer.Sound"] = {}
_VOLUME = 1.0


def _init_mixer() -> bool:
    """Initialise the Pygame mixer lazily.

    Returns ``True`` if the mixer is available and initialised.  The
    initialisation is attempted at most once to avoid repeated log spam in
    headless environments.
    """

    global _MIXER_CHECKED, _MIXER_AVAILABLE

    if _MIXER_CHECKED:
        return _MIXER_AVAILABLE

    _MIXER_CHECKED = True
    if os.environ.get("SDL_AUDIODRIVER") == "dummy":
        _MIXER_AVAILABLE = False
        return False

    try:  # pragma: no cover - mixer init is environment-dependent
        pygame.mixer.init()
        _MIXER_AVAILABLE = True
    except Exception:
        _MIXER_AVAILABLE = False

    return _MIXER_AVAILABLE


def _ready() -> bool:
    """Return ``True`` when sounds can be played."""

    return _ENABLED and _init_mixer()


def load(name: str, path: Union[str, Path]) -> bool:
    """Load a sound effect from ``path`` under ``name``.

    Returns ``True`` on success.  Loading does nothing if the mixer is
    disabled or the file does not exist.
    """
    if not _ready():
        return False
    p = Path(path)
    if not p.is_file():
        warnings.warn(f"Sound file '{p}' not found", RuntimeWarning)
        return False
    try:
        snd = pygame.mixer.Sound(str(p))
        snd.set_volume(_VOLUME)
    except Exception:
        return False
    _SOUNDS[name] = snd
    return True


def play(name: str) -> None:
    """Play a loaded sound effect identified by ``name``."""
    if not _ready():
        return
    snd = _SOUNDS.get(name)
    if snd is None:
        return
    try:
        snd.play()
    except Exception:
        pass


def set_volume(vol: float) -> None:
    """Set volume for all loaded sound effects."""
    global _VOLUME
    _VOLUME = max(0.0, min(1.0, vol))
    if not _ready():
        return
    for snd in _SOUNDS.values():
        try:
            snd.set_volume(_VOLUME)
        except Exception:
            pass


def set_enabled(flag: bool) -> None:
    """Enable or disable all sound effects."""
    global _ENABLED
    _ENABLED = bool(flag)
    if _ENABLED:
        _init_mixer()
