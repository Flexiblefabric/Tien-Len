from __future__ import annotations

from typing import TYPE_CHECKING, List, Tuple, Optional

import pygame

from .helpers import LABEL_PAD, ZONE_HIGHLIGHT, draw_glow

if TYPE_CHECKING:  # pragma: no cover - used for type hints
    from .view import GameView
    from tienlen import Player


class HUDPanel:
    """Simple HUD panel showing info for a player."""

    def __init__(self, view: "GameView", idx: int) -> None:
        self.view = view
        self.idx = idx

    @property
    def player(self) -> "Player":
        return self.view.game.players[self.idx]

    def _last_move(self) -> str:
        name = self.player.name
        for _, text in reversed(self.view.game.history):
            if text.startswith(name):
                return text
        return ""

    def _status(self) -> str:
        if self.view.game.current_idx == self.idx:
            return "Your Turn" if self.player.is_human else "Thinking"
        last = self._last_move()
        if last.endswith("passes"):
            return "Passed"
        return ""

    def _create_surface(self) -> pygame.Surface:
        lines: list[str] = []
        lines.append(f"{self.player.name} ({len(self.player.hand)})")
        last = self._last_move()
        if last:
            lines.append(last)
        status = self._status()
        if status:
            lines.append(status)

        if not self.player.is_human:
            lvl = self.view.game._ai_level_for(self.player)
            per = self.view.game._ai_personality_for(self.player)
            lines.append(f"Difficulty: {lvl}")
            lines.append(f"Personality: {per}")

        info = self.view.ai_debug_info.get(self.idx)
        if self.view.developer_mode and info and not self.player.is_human:
            move, score = info
            lines.append(f"Move: {move}")
            if score is not None:
                lines.append(f"Score: {score:.2f}")

        panel = self.view._hud_box(lines, padding=5, bg_image=self.view.panel_image)
        avatar = self.view._avatar_for(self.player)
        aw, ah = avatar.get_size()
        pw, ph = panel.get_size()

        hand_imgs: list[pygame.Surface] = []
        hand_w = 0
        card_h = 0
        if self.view.developer_mode and not self.player.is_human:
            card_w = max(20, self.view.card_width // 3)
            card_h = int(card_w * 1.4)
            spacing = int(card_w * 0.4)
            import tienlen_gui

            for card in self.player.hand:
                img = tienlen_gui.get_card_image(card, card_w)
                if img is not None:
                    hand_imgs.append(img)
            if hand_imgs:
                hand_w = card_w + spacing * (len(hand_imgs) - 1)

        width = aw + LABEL_PAD + pw + (LABEL_PAD + hand_w if hand_w else 0)
        height = max(ah, ph, card_h)
        surf = pygame.Surface((width, height), pygame.SRCALPHA)
        surf.blit(avatar, (0, (height - ah) // 2))
        surf.blit(panel, (aw + LABEL_PAD, (height - ph) // 2))

        if hand_imgs:
            x = aw + LABEL_PAD + pw + LABEL_PAD
            y = (height - card_h) // 2
            spacing = int(card_w * 0.4)
            for i, img in enumerate(hand_imgs):
                surf.blit(img, (x + i * spacing, y))

        return surf

    def draw(self, surface: pygame.Surface) -> pygame.Rect:
        card_h = int(self.view.card_width * 1.4)
        spacing = min(40, self.view.card_width)
        offset = card_h // 2 + spacing // 2 + LABEL_PAD * 2
        x, y = self.view._player_pos(self.idx)
        panel = self._create_surface()
        if self.idx == 0:
            rect = panel.get_rect(midbottom=(x, y - offset))
        elif self.idx == 1:
            rect = panel.get_rect(midtop=(x, y + offset))
        elif self.idx == 2:
            rect = panel.get_rect(midleft=(x + offset, y))
        else:
            rect = panel.get_rect(midright=(x - offset, y))
        if self.view.game.current_idx == self.idx and not self.player.is_human:
            draw_glow(surface, rect, ZONE_HIGHLIGHT)
        surface.blit(panel, rect)
        return rect


class HUDMixin:
    """Mixin providing HUD rendering helpers for :class:`GameView`."""

    def _hud_box(
        self,
        lines: List[str],
        text_color: Tuple[int, int, int] = (255, 255, 255),
        padding: int = 5,
        bg_color: Tuple[int, int, int, int] = (0, 0, 0, 150),
        bg_image: Optional[pygame.Surface] = None,
    ) -> pygame.Surface:
        """Return a surface with ``lines`` rendered on a semi-transparent box."""
        line_height = getattr(self.font, "get_linesize", lambda: 20)()
        imgs = [self.font.render(line, True, text_color) for line in lines]
        width = max(int(img.get_width()) for img in imgs) + 2 * padding if imgs else 0
        height = line_height * len(imgs) + 2 * padding
        panel = pygame.Surface((max(1, width), max(1, height)), pygame.SRCALPHA)
        if bg_image:
            from .helpers import draw_nine_patch

            draw_nine_patch(panel, bg_image, panel.get_rect())
        else:
            panel.fill(bg_color)
        y = padding
        for img in imgs:
            panel.blit(img, (padding, y))
            y += line_height
        return panel

    def draw_scoreboard(self) -> pygame.Rect:
        """Display remaining cards and ranking at the top centre."""
        from .helpers import get_font

        font = get_font(14)
        old = self.font
        self.font = font
        counts = sorted((len(p.hand), p.name) for p in self.game.players)
        ranking = {name: i + 1 for i, (_, name) in enumerate(counts)}
        lines = [f"{p.name}: {len(p.hand)} (#{ranking[p.name]})" for p in self.game.players]
        panel = self._hud_box(lines, padding=5, bg_image=self.panel_tile)
        self.font = old
        w, _ = self.screen.get_size()
        rect = panel.get_rect(midtop=(w // 2, 5))
        self.scoreboard_rect = rect
        self.screen.blit(panel, rect.topleft)
        return rect

    def draw_game_log(self) -> pygame.Rect:
        """Render the latest history entries beside the scoreboard."""
        from .helpers import get_font, draw_tiled

        font = get_font(12)
        lines = [txt for _, txt in self.game.history[-4:]]
        line_height = font.get_linesize()
        width = max(font.size(line)[0] for line in lines) + 10 if lines else 0
        height = line_height * len(lines) + 10
        panel = pygame.Surface((max(1, width), max(1, height)), pygame.SRCALPHA)
        if self.panel_tile:
            draw_tiled(panel, self.panel_tile, panel.get_rect())
        else:
            panel.fill((0, 0, 0, 150))
        y = 5
        for i, line in enumerate(lines):
            color = (255, 255, 0) if i == len(lines) - 1 else (255, 255, 255)
            img = font.render(line, True, color)
            panel.blit(img, (5, y))
            y += line_height
        rect = panel.get_rect(
            topleft=(self.scoreboard_rect.right + LABEL_PAD, self.scoreboard_rect.top)
        )
        self.log_rect = rect
        self.screen.blit(panel, rect.topleft)
        return rect

    def draw_score_overlay(self) -> pygame.Rect:
        """Render a scoreboard panel showing total wins for each player."""
        lines = [f"{p.name}: {self.win_counts.get(p.name, 0)}" for p in self.game.players]
        panel = self._hud_box(lines, padding=5, bg_image=self.menu_background)
        rect = panel.get_rect(topleft=self.score_pos)
        self.score_rect = rect
        dirty = [self.screen.blit(panel, rect.topleft)] if self.score_visible else []
        self.score_button.draw(self.screen)
        dirty.append(self.score_button.rect)
        return rect.unionall(dirty)

    def _load_avatars(self) -> None:
        """Load avatar images for all players if available."""
        from .helpers import AVATAR_DIR, AVATAR_SIZE

        self.avatars.clear()
        for p in self.game.players:
            base = p.name.lower().replace(" ", "_")
            candidates = []
            if not getattr(p, "is_human", False):
                candidates.append(base + "_icon.png")
            candidates.append(base + ".png")
            for name in candidates:
                path = AVATAR_DIR / name
                if path.exists():
                    try:
                        img = pygame.image.load(str(path)).convert_alpha()
                        img = pygame.transform.smoothscale(img, (AVATAR_SIZE, AVATAR_SIZE))
                        self.avatars[p.name] = img
                        break
                    except Exception:
                        continue

    def _create_huds(self) -> None:
        """Create HUD panels for all players."""
        self.huds = [HUDPanel(self, i) for i in range(len(self.game.players))]

    def _avatar_for(self, player: "Player") -> pygame.Surface:
        """Return avatar image or a placeholder with player initials."""
        from .helpers import AVATAR_SIZE, get_font

        img = self.avatars.get(player.name)
        if img:
            return img
        initials = "".join(part[0] for part in player.name.split())[:2].upper()
        surf = pygame.Surface((AVATAR_SIZE, AVATAR_SIZE), pygame.SRCALPHA)
        pygame.draw.circle(surf, (80, 80, 80), (AVATAR_SIZE // 2, AVATAR_SIZE // 2), AVATAR_SIZE // 2)
        font = get_font(20)
        text = font.render(initials, True, (255, 255, 255))
        rect = text.get_rect(center=(AVATAR_SIZE // 2, AVATAR_SIZE // 2))
        surf.blit(text, rect)
        self.avatars[player.name] = surf
        return surf
