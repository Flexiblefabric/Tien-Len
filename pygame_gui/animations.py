from __future__ import annotations

import math
import types
from typing import List, Tuple, Optional

import pygame

from .helpers import CardSprite
from .overlays import Overlay


def ease(t: float) -> float:
    """Simple ease-in/out function."""
    return t * t * (3 - 2 * t)


def get_card_back(*args, **kwargs):
    """Proxy to pygame_gui.get_card_back for easy patching in tests."""
    import pygame_gui

    return pygame_gui.get_card_back(*args, **kwargs)


class AnimationMixin:
    def _animate_sprites(
        self,
        sprites: List[CardSprite],
        dest: Tuple[int, int],
        frames: int = 15,
        dt: float = 1 / 60,
    ) -> None:
        """Move ``sprites`` toward ``dest`` over ``frames`` steps."""
        if not sprites:
            return
        duration = (frames / 60) / self.animation_speed
        starts = [sp.rect.center for sp in sprites]
        elapsed = 0.0
        while elapsed < duration:
            elapsed += dt
            t = ease(min(elapsed / duration, 1.0))
            for sp, (sx, sy) in zip(sprites, starts):
                sp.rect.center = (
                    int(sx + (dest[0] - sx) * t),
                    int(sy + (dest[1] - sy) * t),
                )
            self._draw_frame()
            pygame.event.pump()

    def _animate_bounce(
        self,
        sprites: List[CardSprite],
        scale: float = 1.2,
        frames: int = 6,
        dt: float = 1 / 60,
    ) -> None:
        """Briefly scale ``sprites`` up then back down for a bounce effect."""
        if not sprites:
            return
        duration = (frames / 60) / self.animation_speed
        half = duration / 2 or 0.01
        originals = [(sp.image, sp.rect.copy()) for sp in sprites]
        elapsed = 0.0
        while elapsed < duration:
            progress = elapsed / half if elapsed < half else (duration - elapsed) / half
            t = max(0.0, min(progress, 1.0))
            factor = 1 + (scale - 1) * t
            for sp, (img, rect) in zip(sprites, originals):
                w, h = rect.size
                if isinstance(img, pygame.Surface):
                    scaled = pygame.transform.smoothscale(
                        img, (int(w * factor), int(h * factor))
                    )
                else:
                    scaled = img
                sp.image = scaled
                sp.rect = scaled.get_rect(center=rect.center)
            self._draw_frame()
            pygame.event.pump()
            elapsed += dt
        # restore originals
        for sp, (img, rect) in zip(sprites, originals):
            sp.image = img
            sp.rect = rect

    def _animate_back(
        self,
        start: Tuple[int, int],
        dest: Tuple[int, int],
        frames: int = 15,
        dt: float = 1 / 60,
    ) -> None:
        """Animate a card back image from ``start`` to ``dest``."""
        img = get_card_back(self.card_back_name)
        if img is None:
            return
        duration = (frames / 60) / self.animation_speed
        rect = img.get_rect(center=start)
        elapsed = 0.0
        while elapsed < duration:
            elapsed += dt
            t = ease(min(elapsed / duration, 1.0))
            rect.center = (
                int(start[0] + (dest[0] - start[0]) * t),
                int(start[1] + (dest[1] - start[1]) * t),
            )
            self._draw_frame()
            self.screen.blit(img, rect)
            pygame.display.flip()
            pygame.event.pump()
        dummy = types.SimpleNamespace(image=img, rect=rect)
        self._animate_bounce([dummy], dt=dt)

    def _animate_flip(
        self,
        sprites: List[CardSprite],
        dest: Tuple[int, int],
        frames: int = 15,
        dt: float = 1 / 60,
    ) -> None:
        """Move ``sprites`` to ``dest`` while flipping from back to front."""
        if not sprites:
            return
        duration = (frames / 60) / self.animation_speed
        starts = [sp.rect.center for sp in sprites]
        fronts = [sp.image for sp in sprites]
        back = get_card_back(self.card_back_name, sprites[0].rect.width)
        elapsed = 0.0
        while elapsed < duration:
            elapsed += dt
            t = ease(min(elapsed / duration, 1.0))
            for sp, (sx, sy) in zip(sprites, starts):
                sp.rect.center = (
                    int(sx + (dest[0] - sx) * t),
                    int(sy + (dest[1] - sy) * t),
                )
            self._draw_frame()
            for sp, front in zip(sprites, fronts):
                img = back if back is not None and t < 0.5 else front
                rect = img.get_rect(center=sp.rect.center)
                self.screen.blit(img, rect)
            pygame.display.flip()
            pygame.event.pump()
        self._animate_bounce(sprites, dt=dt)

    def _animate_select(self, sprite: CardSprite, up: bool, dt: float = 1 / 60) -> None:
        offset = -10 if up else 10
        dest = (sprite.rect.centerx, sprite.rect.centery + offset)
        self._animate_sprites([sprite], dest, frames=5, dt=dt)

    def _highlight_turn(self, idx: int, frames: int = 10, dt: float = 1 / 60) -> None:
        """Flash the active player's name for visual emphasis."""
        x, y = self._player_pos(idx)
        rect = pygame.Rect(0, 0, 140, 30)
        if idx == 0:
            rect.midbottom = (x, y)
        elif idx == 1:
            rect.midtop = (x, y)
        elif idx == 2:
            rect.midleft = (x, y)
        else:
            rect.midright = (x, y)
        duration = (frames / 60) / self.animation_speed
        elapsed = 0.0
        while elapsed < duration:
            progress = elapsed / duration
            self._draw_frame()
            overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
            alpha = max(0, 200 - int(progress * 200))
            center = overlay.get_rect().center
            radius = 11 + int(3 * math.sin(math.pi * progress))
            if hasattr(overlay, "get_width"):
                pygame.draw.circle(
                    overlay, (255, 255, 0, alpha), center, radius, width=3
                )
            self.screen.blit(overlay, rect.topleft)
            pygame.display.flip()
            pygame.event.pump()
            elapsed += dt

    def _transition_overlay(
        self,
        old: Optional[Overlay],
        new: Overlay,
        frames: int = 20,
        slide: bool = False,
        dt: float = 1 / 60,
    ) -> None:
        """Animate transition between two overlays."""
        if old is None:
            return
        duration = (frames / 60) / self.animation_speed
        w, h = self.screen.get_size()

        def render(ov: Overlay) -> pygame.Surface:
            surf = pygame.Surface((w, h), pygame.SRCALPHA)
            bg = pygame.Surface((w, h), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 180))
            surf.blit(bg, (0, 0))
            ov.draw(surf)
            return surf

        from_surf = render(old)
        to_surf = render(new)

        current = self.overlay
        # Draw the base screen once and reuse it during the animation
        self.overlay = None
        self._draw_frame()
        base = self.screen.copy()
        self.overlay = current
        elapsed = 0.0
        while elapsed < duration:
            elapsed += dt
            progress = min(elapsed / duration, 1.0)
            self.screen.blit(base, (0, 0))
            if slide:
                offset = int(w * (1 - progress))
                self.screen.blit(from_surf, (-offset, 0))
                self.screen.blit(to_surf, (w - offset, 0))
            else:
                fs = from_surf.copy()
                fs.set_alpha(int(255 * (1 - progress)))
                ts = to_surf.copy()
                ts.set_alpha(int(255 * progress))
                self.screen.blit(fs, (0, 0))
                self.screen.blit(ts, (0, 0))
            pygame.display.flip()
            pygame.event.pump()

        self.overlay = new
        self._draw_frame()
