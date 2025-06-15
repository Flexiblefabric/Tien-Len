"""Simple sound effect utilities using pygame's mixer."""
from __future__ import annotations

from pathlib import Path

try:
    import pygame
    pygame.mixer.init()
    _ENABLED = True
except Exception:  # pragma: no cover - if mixer init fails
    pygame = None
    _ENABLED = False

_SOUNDS: dict[str, "pygame.mixer.Sound"] = {}


def load(name: str, path: str | Path) -> bool:
    """Load a sound effect from ``path`` under ``name``.

    Returns ``True`` on success.  Loading does nothing if the mixer is
    disabled or the file does not exist.
    """
    if not _ENABLED:
        return False
    p = Path(path)
    if not p.is_file():
        return False
    try:
        snd = pygame.mixer.Sound(str(p))
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
