from __future__ import annotations

from typing import Callable

from .easing import EASING_FUNCTIONS, linear


class Tween:
    """Simple tween for numeric values."""

    def __init__(self, start: float, end: float, duration: float,
                 ease: str | Callable[[float], float] | None = None):
        self.start = start
        self.end = end
        self.duration = max(duration, 1e-8)
        if isinstance(ease, str):
            if ease not in EASING_FUNCTIONS:
                raise KeyError(f"Unknown easing '{ease}'")
            self.ease = EASING_FUNCTIONS[ease]
        else:
            self.ease = ease or linear
        self.elapsed = 0.0

    def update(self, dt: float) -> float:
        """Advance by ``dt`` seconds and return the current interpolated value."""
        self.elapsed = min(self.elapsed + dt, self.duration)
        progress = self.elapsed / self.duration
        eased = self.ease(progress)
        return self.start + (self.end - self.start) * eased

    @property
    def finished(self) -> bool:
        """Return ``True`` when the tween has reached its end value."""
        return self.elapsed + 1e-9 >= self.duration
