from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from .helpers import LABEL_PAD, ZONE_HIGHLIGHT, draw_glow

if TYPE_CHECKING:  # pragma: no cover - used for type hints
    from .view import GameView
    from tien_len_full import Player


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
        panel = self.view._hud_box(lines, padding=5, bg_image=self.view.panel_image)
        avatar = self.view._avatar_for(self.player)
        aw, ah = avatar.get_size()
        pw, ph = panel.get_size()
        surf = pygame.Surface((aw + LABEL_PAD + pw, max(ah, ph)), pygame.SRCALPHA)
        surf.blit(avatar, (0, (surf.get_height() - ah) // 2))
        surf.blit(panel, (aw + LABEL_PAD, (surf.get_height() - ph) // 2))
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
