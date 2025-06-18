"""Minimal Pygame interface for the Tiến Lên card game."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple, List

import pygame

from tien_len_full import Game, Card, detect_combo


# ---------------------------------------------------------------------------
# Helpers for loading and caching card images
# ---------------------------------------------------------------------------

_CARD_CACHE: Dict[Tuple[str, int], pygame.Surface] = {}
_BASE_IMAGES: Dict[str, pygame.Surface] = {}


def _image_key(card: Card) -> str:
    rank_map = {"J": "jack", "Q": "queen", "K": "king", "A": "ace"}
    rank = rank_map.get(card.rank, card.rank.lower())
    suit = card.suit.lower()
    return f"{rank}_of_{suit}"


def load_card_images(width: int = 80) -> None:
    """Load all card images scaled to ``width`` pixels."""
    assets = Path(__file__).with_name("assets")
    for img in assets.glob("*_of_*.png"):
        key = img.stem
        base = pygame.image.load(str(img)).convert_alpha()
        _BASE_IMAGES[key] = base
    for key, base in _BASE_IMAGES.items():
        ratio = width / base.get_width()
        _CARD_CACHE[(key, width)] = pygame.transform.smoothscale(
            base, (width, int(base.get_height() * ratio))
        )


def get_card_image(card: Card, width: int) -> pygame.Surface:
    key = _image_key(card)
    if (key, width) not in _CARD_CACHE:
        base = _BASE_IMAGES.get(key)
        if base is None:
            return None
        ratio = width / base.get_width()
        _CARD_CACHE[(key, width)] = pygame.transform.smoothscale(
            base, (width, int(base.get_height() * ratio))
        )
    return _CARD_CACHE[(key, width)]


# ---------------------------------------------------------------------------
# Sprite classes
# ---------------------------------------------------------------------------

class CardSprite(pygame.sprite.Sprite):
    def __init__(self, card: Card, pos: Tuple[int, int], width: int = 80) -> None:
        super().__init__()
        img = get_card_image(card, width)
        if img is None:
            # Render a text fallback
            font = pygame.font.SysFont(None, 20)
            img = font.render(str(card), True, (0, 0, 0), (255, 255, 255))
        self.image = img
        self.rect = self.image.get_rect(topleft=pos)
        self.card = card
        self.selected = False

    def toggle(self) -> None:
        self.selected = not self.selected
        if self.selected:
            self.rect.move_ip(0, -10)
        else:
            self.rect.move_ip(0, 10)


# ---------------------------------------------------------------------------
# Main game view
# ---------------------------------------------------------------------------

class GameView:
    TABLE_COLOR = (0, 100, 0)

    def __init__(self, width: int = 1024, height: int = 768) -> None:
        pygame.init()
        pygame.display.set_caption("Tiến Lên - Pygame")
        self.screen = pygame.display.set_mode((width, height))
        self.clock = pygame.time.Clock()
        self.game = Game()
        self.game.setup()
        self.font = pygame.font.SysFont(None, 24)
        load_card_images()
        self.selected: List[CardSprite] = []
        self.running = True

    # Layout helpers --------------------------------------------------
    def _player_pos(self, idx: int) -> Tuple[int, int]:
        w, h = self.screen.get_size()
        if idx == 0:
            return w // 2, h - 150
        if idx == 1:
            return w // 2, 50
        if idx == 2:
            return 100, h // 2
        return w - 100, h // 2

    # Event handling --------------------------------------------------
    def handle_mouse(self, pos):
        for sp in self.selected:
            if sp.rect.collidepoint(pos):
                sp.toggle()
                if sp.selected:
                    self.selected.append(sp)
                else:
                    self.selected.remove(sp)
                return
        for sp in self.hand_sprites:
            if sp.rect.collidepoint(pos):
                sp.toggle()
                if sp.selected and sp not in self.selected:
                    self.selected.append(sp)
                elif not sp.selected and sp in self.selected:
                    self.selected.remove(sp)
                return

    def handle_key(self, key):
        if key == pygame.K_RETURN:
            self.play_selected()
        elif key == pygame.K_SPACE:
            self.pass_turn()

    # Game actions ----------------------------------------------------
    def play_selected(self):
        if not self.selected:
            return
        cards = [sp.card for sp in self.selected]
        player = self.game.players[self.game.current_idx]
        ok, msg = self.game.is_valid(player, cards, self.game.current_combo)
        if not ok:
            print(f"Invalid: {msg}")
            return
        if self.game.process_play(player, cards):
            self.running = False
        self.game.next_turn()
        self.selected.clear()
        self.update_hand_sprites()
        self.ai_turns()

    def pass_turn(self):
        if self.game.handle_pass():
            self.running = False
        else:
            self.ai_turns()

    def ai_turns(self):
        while not self.game.players[self.game.current_idx].is_human:
            p = self.game.players[self.game.current_idx]
            cards = self.game.ai_play(self.game.current_combo)
            ok, _ = self.game.is_valid(p, cards, self.game.current_combo)
            if not ok:
                cards = []
            if cards:
                if self.game.process_play(p, cards):
                    self.running = False
                    break
            else:
                self.game.process_pass(p)
            self.game.next_turn()
        self.update_hand_sprites()

    # Rendering -------------------------------------------------------
    def update_hand_sprites(self):
        player = self.game.players[0]
        self.hand_sprites = pygame.sprite.Group()
        start_x, y = self._player_pos(0)
        card_w = 80
        spacing = card_w + 10
        start_x -= (len(player.hand) * spacing) // 2
        for i, c in enumerate(player.hand):
            sprite = CardSprite(c, (start_x + i * spacing, y), card_w)
            self.hand_sprites.add(sprite)

    def draw_players(self):
        for idx, p in enumerate(self.game.players):
            x, y = self._player_pos(idx)
            txt = f"{p.name} ({len(p.hand)})"
            color = (255, 255, 0) if idx == self.game.current_idx else (255, 255, 255)
            img = self.font.render(txt, True, color)
            rect = img.get_rect(center=(x, y - 40))
            self.screen.blit(img, rect)

        self.hand_sprites.draw(self.screen)

        if self.game.pile:
            pl, cards = self.game.pile[-1]
            txt = f"Pile: {pl.name} -> {cards} ({detect_combo(cards)})"
            img = self.font.render(txt, True, (255, 255, 255))
            rect = img.get_rect(center=(self.screen.get_width() // 2, self.screen.get_height() // 2))
            self.screen.blit(img, rect)

    def run(self):
        self.update_hand_sprites()
        self.ai_turns()
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.handle_mouse(event.pos)
                elif event.type == pygame.KEYDOWN:
                    self.handle_key(event.key)

            self.screen.fill(self.TABLE_COLOR)
            self.draw_players()
            pygame.display.flip()
            self.clock.tick(30)
        pygame.quit()


def main() -> None:
    GameView().run()


if __name__ == "__main__":
    main()
