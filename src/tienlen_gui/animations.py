from __future__ import annotations

import math
import types
from typing import List, Tuple, Optional

from .tween import Tween, Timeline

import pygame

from .helpers import (
    CardSprite,
    calc_start_and_overlap,
    AVATAR_SIZE,
    LABEL_PAD,
    ZONE_HIGHLIGHT,
    get_scaled_surface,
)
from .overlays import Overlay


def get_card_back(*args, **kwargs):
    """Proxy to tienlen_gui.get_card_back for easy patching in tests."""
    import tienlen_gui

    return tienlen_gui.get_card_back(*args, **kwargs)


def draw_glow(*args, **kwargs):
    """Proxy to tienlen_gui.draw_glow for easy patching in tests."""
    import tienlen_gui

    return tienlen_gui.draw_glow(*args, **kwargs)


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
        starts = [
            (getattr(sp, "pos", pygame.math.Vector2(sp.rect.center)).x,
             getattr(sp, "pos", pygame.math.Vector2(sp.rect.center)).y)
            for sp in sprites
        ]
        tween = Tween(0.0, 1.0, total, 'smooth')
        dt = yield
        while True:
            t = tween.update(dt)
            for sp, (sx, sy) in zip(sprites, starts):
                nx = sx + (dest[0] - sx) * t
                ny = sy + (dest[1] - sy) * t
                if hasattr(sp, "pos"):
                    sp.pos.update(nx, ny)
                else:
                    sp.rect.center = (int(nx), int(ny))
            dt = yield
            if tween.finished:
                break

    def _animate_bounce(
        self,
        sprites: List[CardSprite],
        scale: float = 1.2,
        duration: float = 0.1,
    ):
        """Yield a brief bounce animation for ``sprites``."""
        if not sprites:
            return
        originals = []
        for sp in sprites:
            rect = sp.rect.copy()
            if hasattr(sp, "pos"):
                rect.center = (int(sp.pos.x), int(sp.pos.y))
            originals.append((sp.image, rect))
        total = duration / self.animation_speed
        tween = Tween(0.0, 1.0, total)
        dt = yield
        while True:
            raw = tween.update(dt)
            t = raw * 2 if raw < 0.5 else (1 - raw) * 2
            factor = 1 + (scale - 1) * t
            for sp, (img, rect) in zip(sprites, originals):
                w, h = rect.size
                if isinstance(img, pygame.Surface):
                    scaled = get_scaled_surface(
                        img, (int(w * factor), int(h * factor))
                    )
                else:
                    scaled = img
                sp.image = scaled
                sp.rect = scaled.get_rect(center=rect.center)
                if hasattr(sp, "pos"):
                    sp.pos.update(rect.center)
            dt = yield
            if tween.finished:
                break
        for sp, (img, rect) in zip(sprites, originals):
            sp.image = img
            sp.rect = rect
            if hasattr(sp, "pos"):
                sp.pos.update(rect.center)

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
        tween = Tween(0.0, 1.0, total, 'smooth')
        dt = yield
        while True:
            t = tween.update(dt)
            rect.center = (
                int(start[0] + (dest[0] - start[0]) * t),
                int(start[1] + (dest[1] - start[1]) * t),
            )
            dt = yield
            if tween.finished:
                break
        dummy = types.SimpleNamespace(image=img, rect=rect)
        bounce = self._animate_bounce([dummy])
        next(bounce)
        dt = yield
        while True:
            try:
                bounce.send(dt)
            except StopIteration:
                break
            dt = yield
        yield

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
        tween = Tween(0.0, 1.0, total)
        dt = yield
        while True:
            progress = tween.update(dt)
            alpha = max(0, 255 - int(progress * 255))
            for img, rect in zip(originals, rects):
                surf = img.copy()
                surf.set_alpha(alpha)
            dt = yield
            if tween.finished:
                break

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
        starts = [
            (getattr(sp, "pos", pygame.math.Vector2(sp.rect.center)).x,
             getattr(sp, "pos", pygame.math.Vector2(sp.rect.center)).y)
            for sp in sprites
        ]
        fronts = [sp.image for sp in sprites]
        back = get_card_back(self.card_back_name, sprites[0].rect.width)

        def update(t: float) -> None:
            for sp, (sx, sy) in zip(sprites, starts):
                nx = sx + (dest[0] - sx) * t
                ny = sy + (dest[1] - sy) * t
                if hasattr(sp, "pos"):
                    sp.pos.update(nx, ny)
                else:
                    sp.rect.center = (int(nx), int(ny))
            for sp, front in zip(sprites, fronts):
                img = back if back is not None and t < 0.5 else front
                center = (
                    int(sp.pos.x),
                    int(sp.pos.y),
                ) if hasattr(sp, "pos") else sp.rect.center
                w, h = sp.rect.size
                scaled = get_scaled_surface(img, (w, h))
                sp.image = scaled
                sp.rect = scaled.get_rect(center=center)
                if hasattr(sp, "pos"):
                    sp.pos.update(center)

        tl = Timeline()
        tl.add(Tween(0.0, 1.0, total, 'smooth'), update)
        tl.then(self._animate_bounce(sprites))
        gen = tl.play()
        next(gen)
        dt = yield
        while True:
            try:
                gen.send(dt)
            except StopIteration:
                break
            dt = yield
        yield

    def _animate_select(self, sprite: CardSprite, up: bool, duration: float = 5 / 60):
        offset = -10 if up else 10
        if hasattr(sprite, "pos"):
            dest = (sprite.pos.x, sprite.pos.y + offset)
        else:
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
        starts = [
            (getattr(sp, "pos", pygame.math.Vector2(sp.rect.center)).x,
             getattr(sp, "pos", pygame.math.Vector2(sp.rect.center)).y)
            for sp in sprites
        ]
        total = duration / self.animation_speed
        tween = Tween(0.0, 1.0, total)
        dt = yield
        while True:
            t = tween.update(dt)
            offset = int(math.sin(t * cycles * 2 * math.pi) * amplitude)
            for sp, (sx, sy) in zip(sprites, starts):
                nx = sx + offset
                if hasattr(sp, "pos"):
                    sp.pos.x = nx
                else:
                    sp.rect.centerx = nx
            dt = yield
            if tween.finished:
                break
        for sp, (sx, sy) in zip(sprites, starts):
            if hasattr(sp, "pos"):
                sp.pos.x = sx
            else:
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
        tween = Tween(0.0, 1.0, total)
        overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
        center = overlay.get_rect().center
        dt = yield
        while True:
            progress = tween.update(dt)
            overlay.fill((0, 0, 0, 0))
            alpha = max(0, 200 - int(progress * 200))
            radius = 11 + int(3 * math.sin(math.pi * progress))
            if hasattr(overlay, "get_width"):
                pygame.draw.circle(
                    overlay, (255, 255, 0, alpha), center, radius, width=3
                )
            dt = yield
            if tween.finished:
                break

    def _animate_avatar_blink(self, idx: int, duration: float = 0.3):
        """Yield a quick outline animation around ``idx``'s avatar."""
        player = self.game.players[idx]
        text_panel = self._hud_box([f"{player.name} ({len(player.hand)})"], padding=3, bg_image=self.panel_image)
        pw, ph = text_panel.get_size()
        aw = ah = AVATAR_SIZE
        panel_h = max(ah, ph)
        panel_w = aw + LABEL_PAD + pw
        x, y = self._player_pos(idx)
        card_h = int(self.card_width * 1.4)
        spacing = min(40, self.card_width)
        offset = card_h // 2 + spacing // 2 + LABEL_PAD
        rect = pygame.Rect(0, 0, panel_w, panel_h)
        if idx == 0:
            rect.midbottom = (x, y - offset)
        elif idx == 1:
            rect.midtop = (x, y + offset)
        elif idx == 2:
            rect.midleft = (x + offset, y)
        else:
            rect.midright = (x - offset, y)
        avatar_rect = pygame.Rect(
            rect.left,
            rect.top + (panel_h - ah) // 2,
            aw,
            ah,
        )
        overlay = pygame.Surface(avatar_rect.size, pygame.SRCALPHA)
        center = overlay.get_rect().center
        total = duration / self.animation_speed
        tween = Tween(0.0, 1.0, total)
        dt = yield
        while True:
            progress = tween.update(dt)
            overlay.fill((0, 0, 0, 0))
            alpha = max(0, 200 - int(progress * 200))
            radius = (aw // 2 + 2) + int(2 * math.sin(math.pi * progress))
            if hasattr(overlay, "get_width"):
                pygame.draw.circle(
                    overlay,
                    (*ZONE_HIGHLIGHT, alpha),
                    center,
                    radius,
                    width=3,
                )
            dt = yield
            if tween.finished:
                break

    def _animate_pass_text(self, idx: int, duration: float = 0.5):
        """Yield an animation showing "PASS" over ``idx``'s zone."""
        zone = self._player_zone_rect(idx)
        if zone.width <= 0 or zone.height <= 0:
            return
        panel = self._hud_box(["PASS"], bg_image=self.panel_image)
        rect = panel.get_rect(center=zone.center)
        start = rect.center
        dest = (rect.centerx, rect.centery - 30)
        total = duration / self.animation_speed
        tween = Tween(0.0, 1.0, total, 'smooth')
        dt = yield
        while True:
            t = tween.update(dt)
            rect.center = (
                int(start[0] + (dest[0] - start[0]) * t),
                int(start[1] + (dest[1] - start[1]) * t),
            )
            surf = panel.copy()
            surf.set_alpha(max(0, 255 - int(t * 255)))
            dt = yield
            if tween.finished:
                break

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
        # ``screen`` may be replaced with a mock during tests, so fetch the
        # size from the active display surface.
        surface = pygame.display.get_surface() or self.screen
        w, h = surface.get_size()

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
        self.overlay = current
        tween = Tween(0.0, 1.0, total)
        dt = yield
        while True:
            progress = tween.update(dt)
            if slide:
                fs = from_surf.copy()
                ts = to_surf.copy()
                overlay = pygame.Surface((w, h), pygame.SRCALPHA)
                fs_rect = fs.get_rect()
                ts_rect = ts.get_rect()
                fs_rect.x = int(-w * progress)
                ts_rect.x = int(w * (1 - progress))
                overlay.blit(fs, fs_rect)
                overlay.blit(ts, ts_rect)
            else:
                fs = from_surf.copy()
                fs.set_alpha(int(255 * (1 - progress)))
                ts = to_surf.copy()
                ts.set_alpha(int(255 * progress))
            dt = yield
            if tween.finished:
                break
        self.overlay = new

    def _animate_deal(
        self,
        duration: float = 0.25,
        delay: float = 5 / 60,
    ):
        """Yield a simple dealing animation for all current hand sprites."""
        groups = [
            (self.hand_sprites, self.hand_sprites.sprites())
        ] + [
            (g, g.sprites()) for g in self.ai_sprites
        ]
        if not any(s for _, s in groups):
            return

        start = self._pile_center()
        destinations = [
            [
                (
                    getattr(sp, "pos", pygame.math.Vector2(sp.rect.center)).x,
                    getattr(sp, "pos", pygame.math.Vector2(sp.rect.center)).y,
                )
                for sp in grp
            ]
            for _, grp in groups
        ]
        layers = [[getattr(sp, "_layer", idx) for idx, sp in enumerate(grp)] for _, grp in groups]
        for _, grp in groups:
            for sp in grp:
                if hasattr(sp, "pos"):
                    sp.pos.update(start)
                else:
                    sp.rect.center = start

        max_len = max(len(g) for _, g in groups)
        pause_total = delay / self.animation_speed

        move_dur = duration / self.animation_speed
        order = 0
        managers = []
        for i in range(max_len):
            for g_idx, (group, grp) in enumerate(groups):
                if i >= len(grp):
                    continue
                sp = grp[i]
                dest = destinations[g_idx][i]
                orig_layer = layers[g_idx][i]
                mgr = self._manager_for(sp)
                managers.append(mgr)

                start_delay = order * (move_dur + pause_total)
                order += 1

                tl = Timeline()
                if start_delay > 0:
                    tl.wait(start_delay)

                def start_move(sp=sp, dest=dest, group=group, mgr=mgr):
                    group.change_layer(sp, group.get_top_layer() + 1)
                    mgr.tween_position(dest, move_dur, 'smooth')

                def reset_layer(sp=sp, group=group, orig_layer=orig_layer):
                    group.change_layer(sp, orig_layer)

                tl.then(start_move).wait(move_dur).then(reset_layer)
                mgr.play(tl)

        dt = yield
        while any(m.active() for m in managers):
            for m in managers:
                m.update(dt)
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

        move_dur = duration / self.animation_speed
        bounce_dur = 0.1 / self.animation_speed

        timelines: List[Timeline] = []
        for i in range(count):
            tl = Timeline()
            start_delay = i * (move_dur + bounce_dur + pause_total)
            if start_delay > 0:
                tl.wait(start_delay)
            tl.then(self._animate_back(start, dest, duration))
            timelines.append(tl)

        dt = yield
        while any(tl.active for tl in timelines):
            for tl in timelines:
                tl.update(dt)
            dt = yield

    def _animate_glow(
        self,
        sprites: List[types.SimpleNamespace],
        color: Tuple[int, int, int],
        pulses: int = 2,
        duration: float = 0.5,
    ):
        """Yield a pulsing glow animation around ``sprites``."""
        if not sprites:
            return
        total = duration / self.animation_speed
        tween = Tween(0.0, 1.0, total)
        dt = yield
        while True:
            progress = tween.update(dt)
            _strength = math.sin(progress * pulses * math.pi) ** 2
            _ = 8 + int(4 * _strength)
            _ = int(100 * _strength)
            for sp in sprites:
                _ = sp.rect if hasattr(sp, "rect") else sp
            dt = yield
            if tween.finished:
                break

    def _bomb_reveal(self, duration: float = 0.25):
        """Yield a brief white flash when a bomb is played."""
        # ``screen`` may be swapped for a mock during tests. Use the active
        # display surface if available to determine the size.
        surface = pygame.display.get_surface() or self.screen
        w, h = surface.get_size()
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((255, 255, 255))
        total = duration / self.animation_speed
        tween = Tween(0.0, 1.0, total)
        dt = yield
        while True:
            progress = tween.update(dt)
            alpha = max(0, 255 - int(progress * 255))
            overlay.set_alpha(alpha)
            dt = yield
            if tween.finished:
                break

    def _animate_trick_clear(self, duration: float = 0.2):
        """Yield a slide-off and fade animation for ``current_trick``."""
        if not self.current_trick:
            return
        w, _ = self.screen.get_size()
        card_w = self.card_width
        start_rel, overlap = calc_start_and_overlap(
            w, len(self.current_trick), card_w, 25, card_w - 5
        )
        spacing = card_w - overlap
        start = start_rel + card_w // 2
        sprites: list[types.SimpleNamespace] = []
        dests: list[tuple[int, int]] = []
        for i, (_, img) in enumerate(self.current_trick):
            x = start + i * spacing
            rect = img.get_rect(center=(int(x), int(self.pile_y)))
            sprites.append(types.SimpleNamespace(image=img.copy(), rect=rect))
            dests.append((w + card_w // 2 + i * spacing, self.pile_y))

        total = duration / self.animation_speed
        starts = [sp.rect.center for sp in sprites]
        tween = Tween(0.0, 1.0, total, 'smooth')
        dt = yield
        while True:
            t = tween.update(dt)
            alpha = max(0, 255 - int(t * 255))
            for sp, (sx, sy), (dx, dy) in zip(sprites, starts, dests):
                sp.rect.center = (
                    int(sx + (dx - sx) * t),
                    int(sy + (dy - sy) * t),
                )
                surf = sp.image.copy()
                surf.set_alpha(alpha)
            dt = yield
            if tween.finished:
                break

    def _animate_thinking(self, idx: int, duration: float = 0.3):
        """Yield a short pause representing the AI 'thinking'."""
        total = duration / self.animation_speed
        tween = Tween(0.0, 1.0, total)
        dt = yield
        while not tween.finished:
            tween.update(dt)
            dt = yield

    def _animate_delay(self, duration: float = 0.2):
        """Yield a generic pause with no visual effect."""
        total = duration / self.animation_speed
        tween = Tween(0.0, 1.0, total)
        dt = yield
        while not tween.finished:
            tween.update(dt)
            dt = yield
