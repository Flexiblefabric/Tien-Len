from __future__ import annotations

import math
from typing import Callable, Dict


def linear(t: float) -> float:
    """Linear easing."""
    return t


def smooth(t: float) -> float:
    """Smoothstep easing for gentle ease-in/out."""
    return t * t * (3 - 2 * t)


def ease_out_cubic(t: float) -> float:
    """Cubic ease-out curve."""
    return 1 - (1 - t) ** 3


def elastic(t: float) -> float:
    """Elastic ease-out curve."""
    if t == 0 or t == 1:
        return t
    p = 0.3
    s = p / 4
    return math.pow(2, -10 * t) * math.sin((t - s) * (2 * math.pi) / p) + 1


EASING_FUNCTIONS: Dict[str, Callable[[float], float]] = {
    "linear": linear,
    "smooth": smooth,
    "ease-out-cubic": ease_out_cubic,
    "elastic": elastic,
}

__all__ = [
    "linear",
    "smooth",
    "ease_out_cubic",
    "elastic",
    "EASING_FUNCTIONS",
]
