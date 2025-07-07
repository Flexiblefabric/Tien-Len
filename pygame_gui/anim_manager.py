from __future__ import annotations

from typing import Callable, List, Tuple

import pygame

from .tween import Tween


class AnimationManager:
    """Manage multiple Tweens for a single sprite."""

    def __init__(self, sprite: pygame.sprite.Sprite) -> None:
        self.sprite = sprite
        self._tweens: List[Tuple[Tween, Callable[[float], None]]] = []

    def add(self, tween: Tween, setter: Callable[[float], None]) -> Tween:
        """Register ``tween`` and apply ``setter`` each update."""
        self._tweens.append((tween, setter))
        return tween

    def tween_position(
        self, dest: Tuple[float, float], duration: float, ease: str | Callable[[float], float] | None = None
    ) -> Tuple[Tween, Tween]:
        """Animate the sprite's centre position."""
        if hasattr(self.sprite, "pos"):
            sx, sy = self.sprite.pos.x, self.sprite.pos.y

            def set_x(v: float) -> None:
                self.sprite.pos.x = v

            def set_y(v: float) -> None:
                self.sprite.pos.y = v
        else:
            sx, sy = self.sprite.rect.center

            def set_x(v: float) -> None:
                self.sprite.rect.centerx = int(v)

            def set_y(v: float) -> None:
                self.sprite.rect.centery = int(v)

        tx = Tween(sx, dest[0], duration, ease)
        ty = Tween(sy, dest[1], duration, ease)
        self.add(tx, set_x)
        self.add(ty, set_y)
        return tx, ty

    def tween_scale(
        self, dest: float, duration: float, ease: str | Callable[[float], float] | None = None
    ) -> Tween:
        start = getattr(self.sprite, "scale", 1.0)

        def setter(v: float) -> None:
            if hasattr(self.sprite, "set_scale"):
                self.sprite.set_scale(v)

        tw = Tween(start, dest, duration, ease)
        self.add(tw, setter)
        return tw

    def tween_alpha(
        self, dest: float, duration: float, ease: str | Callable[[float], float] | None = None
    ) -> Tween:
        start = self.sprite.image.get_alpha() or 255

        def setter(v: float) -> None:
            self.sprite.image.set_alpha(int(v))

        tw = Tween(start, dest, duration, ease)
        self.add(tw, setter)
        return tw

    def update(self, dt: float) -> None:
        remaining: List[Tuple[Tween, Callable[[float], None]]] = []
        for tw, setter in self._tweens:
            setter(tw.update(dt))
            if not tw.finished:
                remaining.append((tw, setter))
        self._tweens = remaining

    def active(self) -> bool:
        return bool(self._tweens)
