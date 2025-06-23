"""Simple sound effect utilities using pygame's mixer."""
from __future__ import annotations

from pathlib import Path
import warnings

try:
    import pygame
    pygame.mixer.init()
    _ENABLED = True
except Exception:  # pragma: no cover - if mixer init fails
    pygame = None
    _ENABLED = False

_SOUNDS: dict[str, "pygame.mixer.Sound"] = {}
_VOLUME = 1.0


def load(name: str, path: str | Path) -> bool:
    """Load a sound effect from ``path`` under ``name``.

    Returns ``True`` on success.  Loading does nothing if the mixer is
    disabled or the file does not exist.
    """
    if not _ENABLED:
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
    if not _ENABLED:
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
    if not _ENABLED:
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
