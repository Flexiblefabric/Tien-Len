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
