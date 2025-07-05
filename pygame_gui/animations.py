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
        duration: float = 0.25,
    ):
        """Yield steps that move ``sprites`` toward ``dest`` over ``duration``."""
        if not sprites:
            return
        total = duration / self.animation_speed
        starts = [sp.rect.center for sp in sprites]
        elapsed = 0.0
        dt = yield
        while elapsed < total:
            elapsed += dt
            t = ease(min(elapsed / total, 1.0))
            for sp, (sx, sy) in zip(sprites, starts):
                sp.rect.center = (
                    int(sx + (dest[0] - sx) * t),
                    int(sy + (dest[1] - sy) * t),
                )
            dt = yield

    def _animate_bounce(
        self,
        sprites: List[CardSprite],
        scale: float = 1.2,
        duration: float = 0.1,
    ):
        """Yield a brief bounce animation for ``sprites``."""
        if not sprites:
            return
        originals = [(sp.image, sp.rect.copy()) for sp in sprites]
        total = duration / self.animation_speed
        half = total / 2
        dt = yield
        elapsed = 0.0
        while elapsed < total:
            elapsed += dt
            if elapsed < half:
                progress = elapsed / half
            else:
                progress = (total - elapsed) / half
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
            dt = yield
        for sp, (img, rect) in zip(sprites, originals):
            sp.image = img
            sp.rect = rect

    def _animate_back(
        self,
        start: Tuple[int, int],
        dest: Tuple[int, int],
        duration: float = 0.25,
    ):
        """Yield an animation for a moving card back image."""
        img = get_card_back(self.card_back_name)
        if img is None:
            return
        rect = img.get_rect(center=start)
        total = duration / self.animation_speed
        elapsed = 0.0
        dt = yield
        while elapsed < total:
            elapsed += dt
            t = ease(min(elapsed / total, 1.0))
            rect.center = (
                int(start[0] + (dest[0] - start[0]) * t),
                int(start[1] + (dest[1] - start[1]) * t),
            )
            self.screen.blit(img, rect)
            dt = yield
        dummy = types.SimpleNamespace(image=img, rect=rect)
        bounce = self._animate_bounce([dummy])
        next(bounce)
        dt = yield
        while True:
            try:
                bounce.send(dt)
            except StopIteration:
                break
            self.screen.blit(dummy.image, dummy.rect)
            dt = yield

    def _animate_fade_out(
        self,
        sprites: List[types.SimpleNamespace],
        duration: float = 0.25,
    ):
        """Yield a fade-out animation for ``sprites``."""
        if not sprites:
            return
        originals = [sp.image for sp in sprites]
        rects = [sp.rect.copy() for sp in sprites]
        total = duration / self.animation_speed
        elapsed = 0.0
        dt = yield
        while elapsed < total:
            elapsed += dt
            progress = min(elapsed / total, 1.0)
            alpha = max(0, 255 - int(progress * 255))
            for img, rect in zip(originals, rects):
                surf = img.copy()
                surf.set_alpha(alpha)
                self.screen.blit(surf, rect)
            dt = yield

    def _animate_flip(
        self,
        sprites: List[CardSprite],
        dest: Tuple[int, int],
        duration: float = 0.25,
    ):
        """Yield a flip animation moving to ``dest``."""
        if not sprites:
            return
        total = duration / self.animation_speed
        starts = [sp.rect.center for sp in sprites]
        fronts = [sp.image for sp in sprites]
        back = get_card_back(self.card_back_name, sprites[0].rect.width)
        elapsed = 0.0
        dt = yield
        while elapsed < total:
            elapsed += dt
            t = ease(min(elapsed / total, 1.0))
            for sp, (sx, sy) in zip(sprites, starts):
                sp.rect.center = (
                    int(sx + (dest[0] - sx) * t),
                    int(sy + (dest[1] - sy) * t),
                )
            for sp, front in zip(sprites, fronts):
                img = back if back is not None and t < 0.5 else front
                rect = img.get_rect(center=sp.rect.center)
                self.screen.blit(img, rect)
            dt = yield
        bounce = self._animate_bounce(sprites)
        next(bounce)
        dt = yield
        while True:
            try:
                bounce.send(dt)
            except StopIteration:
                break
            dt = yield

    def _animate_select(self, sprite: CardSprite, up: bool, duration: float = 5 / 60):
        offset = -10 if up else 10
        dest = (sprite.rect.centerx, sprite.rect.centery + offset)
        anim = self._animate_sprites([sprite], dest, duration)
        next(anim)
        dt = yield
        while True:
            try:
                anim.send(dt)
            except StopIteration:
                break
            dt = yield

    def _animate_shake(
        self,
        sprites: List[CardSprite],
        amplitude: int = 5,
        cycles: int = 3,
        duration: float = 0.25,
    ):
        """Yield a horizontal shake animation for ``sprites``."""
        if not sprites:
            return
        starts = [sp.rect.center for sp in sprites]
        total = duration / self.animation_speed
        elapsed = 0.0
        dt = yield
        while elapsed < total:
            elapsed += dt
            t = min(elapsed / total, 1.0)
            offset = int(math.sin(t * cycles * 2 * math.pi) * amplitude)
            for sp, (sx, sy) in zip(sprites, starts):
                sp.rect.centerx = sx + offset
            dt = yield
        for sp, (sx, sy) in zip(sprites, starts):
            sp.rect.centerx = sx

    def _highlight_turn(self, idx: int, duration: float = 10 / 60):
        """Yield an animation highlighting the active player."""
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
        total = duration / self.animation_speed
        elapsed = 0.0
        overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
        center = overlay.get_rect().center
        dt = yield
        while elapsed < total:
            elapsed += dt
            progress = min(elapsed / total, 1.0)
            overlay.fill((0, 0, 0, 0))
            alpha = max(0, 200 - int(progress * 200))
            radius = 11 + int(3 * math.sin(math.pi * progress))
            if hasattr(overlay, "get_width"):
                pygame.draw.circle(
                    overlay, (255, 255, 0, alpha), center, radius, width=3
                )
            self.screen.blit(overlay, rect.topleft)
            dt = yield

    def _transition_overlay(
        self,
        old: Optional[Overlay],
        new: Overlay,
        duration: float = 20 / 60,
        slide: bool = False,
    ):
        """Yield animation transitioning between two overlays."""
        if old is None:
            return
        total = duration / self.animation_speed
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
        base = self.screen.copy()
        self.overlay = current
        elapsed = 0.0
        dt = yield
        while elapsed < total:
            elapsed += dt
            progress = min(elapsed / total, 1.0)
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
            dt = yield
        self.overlay = new

    def _animate_deal(
        self,
        duration: float = 0.25,
        delay: float = 5 / 60,
    ):
        """Yield a simple dealing animation for all current hand sprites."""
        groups = [self.hand_sprites.sprites()] + [g.sprites() for g in self.ai_sprites]
        if not any(groups):
            return

        start = self._pile_center()
        destinations = [[sp.rect.center for sp in grp] for grp in groups]
        for grp in groups:
            for sp in grp:
                sp.rect.center = start

        max_len = max(len(g) for g in groups)
        pause_total = delay / self.animation_speed

        dt = yield
        for i in range(max_len):
            for g_idx, grp in enumerate(groups):
                if i >= len(grp):
                    continue
                sp = grp[i]
                dest = destinations[g_idx][i]
                anim = self._animate_sprites([sp], dest, duration)
                next(anim)
                while True:
                    try:
                        anim.send(dt)
                    except StopIteration:
                        break
                    dt = yield
                elapsed = 0.0
                while elapsed < pause_total:
                    elapsed += dt
                    dt = yield

    def _animate_return(
        self,
        player_idx: int,
        count: int,
        duration: float = 0.25,
        delay: float = 5 / 60,
    ):
        """Yield an animation returning ``count`` card backs to ``player_idx``."""
        if count <= 0:
            return

        start = self._pile_center()
        dest = self._player_pos(player_idx)
        pause_total = delay / self.animation_speed

        dt = yield
        for _ in range(count):
            anim = self._animate_back(start, dest, duration)
            next(anim)
            while True:
                try:
                    anim.send(dt)
                except StopIteration:
                    break
                dt = yield
            elapsed = 0.0
            while elapsed < pause_total:
                elapsed += dt
                dt = yield

