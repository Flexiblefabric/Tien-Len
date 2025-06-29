"""Minimal Pygame interface for the Tiến Lên card game."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple, List, Callable, Optional
from enum import Enum, auto
import json
import logging
import math
import types

import pygame

from tien_len_full import Game, Card, detect_combo
import sound

LOG_FILE = "tien_len_game.log"

logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def _mixer_ready() -> bool:
    """Return True if pygame's mixer is initialised."""
    return bool(pygame.mixer.get_init())


TABLE_THEMES = {
    "darkgreen": (0, 100, 0),
    "saddlebrown": (139, 69, 19),
    "navy": (0, 0, 128),
    "darkred": (139, 0, 0),
}

OPTIONS_FILE = Path(__file__).with_name("options.json")

# Default distance between cards in a player's hand
HAND_SPACING = 30


# ---------------------------------------------------------------------------
# Helpers for loading and caching card images
# ---------------------------------------------------------------------------

_CARD_CACHE: Dict[Tuple[str, int], pygame.Surface] = {}
_BASE_IMAGES: Dict[str, pygame.Surface] = {}


class GameState(Enum):
    """Simple enum representing the game's current state."""

    MENU = auto()
    PLAYING = auto()
    SETTINGS = auto()
    GAME_OVER = auto()


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
    for img in assets.glob("card_back*.png"):
        _BASE_IMAGES[img.stem] = pygame.image.load(str(img)).convert_alpha()
    for key, base in _BASE_IMAGES.items():
        ratio = width / base.get_width()
        _CARD_CACHE[(key, width)] = pygame.transform.smoothscale(
            base, (width, int(base.get_height() * ratio))
        )


def get_card_back(name: str = "card_back", width: int = 80) -> Optional[pygame.Surface]:
    if name not in _BASE_IMAGES:
        return None
    key = (name, width)
    if key not in _CARD_CACHE:
        base = _BASE_IMAGES[name]
        ratio = width / base.get_width()
        _CARD_CACHE[key] = pygame.transform.smoothscale(
            base, (width, int(base.get_height() * ratio))
        )
    return _CARD_CACHE[key]


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
        offset = -10 if self.selected else 10
        self.rect.move_ip(0, offset)

    def draw_shadow(
        self,
        surface: pygame.Surface,
        offset: Tuple[int, int] = (5, 5),
        blur: int = 2,
        alpha: int = 80,
    ) -> None:
        """Draw a simple blurred shadow beneath the card."""
        shadow = pygame.Surface(self.image.get_size(), pygame.SRCALPHA)
        shadow.fill((0, 0, 0))
        shadow.set_alpha(alpha)
        for dx in range(-blur, blur + 1):
            for dy in range(-blur, blur + 1):
                rect = self.rect.move(offset[0] + dx, offset[1] + dy)
                surface.blit(shadow, rect)


class CardBackSprite(pygame.sprite.Sprite):
    def __init__(
        self, pos: Tuple[int, int], width: int = 80, name: str = "card_back"
    ) -> None:
        super().__init__()
        img = get_card_back(name, width)
        if img is None:
            font = pygame.font.SysFont(None, 20)
            img = font.render("[]", True, (0, 0, 0), (255, 255, 255))
        self.image = img
        self.rect = self.image.get_rect(topleft=pos)


# ---------------------------------------------------------------------------
# Simple button and overlay helpers
# ---------------------------------------------------------------------------


class Button:
    """Basic rectangular button used by overlays."""

    def __init__(
        self,
        text: str,
        rect: pygame.Rect,
        callback: Callable[[], None],
        font: pygame.font.Font,
        enabled: bool = True,
    ) -> None:
        self.text = text
        self.rect = rect
        self.callback = callback
        self.font = font
        self.enabled = enabled
        self.hovered = False
        self.selected = False

    def draw(self, surface: pygame.Surface) -> None:
        if not self.enabled:
            color = (150, 150, 150)
            text_color = (100, 100, 100)
        elif self.selected:
            color = (255, 220, 120)
            text_color = (0, 0, 0)
        elif self.hovered:
            color = (220, 220, 220)
            text_color = (0, 0, 0)
        else:
            color = (200, 200, 200)
            text_color = (0, 0, 0)
        pygame.draw.rect(surface, color, self.rect)
        pygame.draw.rect(surface, (0, 0, 0), self.rect, 2)
        txt = self.font.render(self.text, True, text_color)
        surface.blit(txt, txt.get_rect(center=self.rect.center))

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        if (
            self.enabled
            and event.type == pygame.MOUSEBUTTONDOWN
            and self.rect.collidepoint(event.pos)
        ):
            self.callback()


class Overlay:
    """Base overlay class managing a list of buttons."""

    def __init__(
        self, view: "GameView", back_cb: Optional[Callable[[], None]] = None
    ) -> None:
        self.view = view
        self.buttons: List[Button] = []
        self.focus_idx = 0
        self.back_callback = back_cb

    def resize(self) -> None:
        """Recalculate layout based on the current screen size."""
        pass

    def draw(self, surface: pygame.Surface) -> None:
        for idx, btn in enumerate(self.buttons):
            btn.selected = idx == self.focus_idx
            btn.draw(surface)

    def back(self) -> None:
        if self.back_callback:
            self.back_callback()

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            for i, btn in enumerate(self.buttons):
                if btn.rect.collidepoint(event.pos):
                    self.focus_idx = i
        for btn in self.buttons:
            btn.handle_event(event)

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_DOWN, pygame.K_s):
                self.focus_idx = (self.focus_idx + 1) % len(self.buttons)
            elif event.key in (pygame.K_UP, pygame.K_w):
                self.focus_idx = (self.focus_idx - 1) % len(self.buttons)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                btn = self.buttons[self.focus_idx]
                if btn.enabled:
                    btn.callback()
            elif event.key == pygame.K_ESCAPE:
                self.back()
        elif event.type == pygame.JOYHATMOTION:
            if event.value[1] > 0:
                self.focus_idx = (self.focus_idx - 1) % len(self.buttons)
            elif event.value[1] < 0:
                self.focus_idx = (self.focus_idx + 1) % len(self.buttons)
        elif event.type == pygame.JOYBUTTONDOWN:
            if event.button == 0:
                btn = self.buttons[self.focus_idx]
                if btn.enabled:
                    btn.callback()
            elif event.button == 1:
                self.back()


class MainMenuOverlay(Overlay):
    """Initial game menu."""

    def __init__(self, view: "GameView") -> None:
        super().__init__(view, view.close_overlay)
        self._layout()

    def resize(self) -> None:
        self._layout()

    def _layout(self) -> None:
        w, h = self.view.screen.get_size()
        font = self.view.font
        bx = w // 2 - 100
        by = h // 2 - 120
        self.buttons = [
            Button(
                "New Game", pygame.Rect(bx, by, 200, 40), self.view.restart_game, font
            ),
            Button(
                "Save Game",
                pygame.Rect(bx, by + 50, 200, 40),
                self.view.save_game,
                font,
            ),
            Button(
                "Load Game",
                pygame.Rect(bx, by + 100, 200, 40),
                self.view.load_game,
                font,
            ),
            Button(
                "Settings",
                pygame.Rect(bx, by + 150, 200, 40),
                self.view.show_settings,
                font,
            ),
            Button(
                "How to Play",
                pygame.Rect(bx, by + 200, 200, 40),
                lambda: self.view.show_how_to_play(from_menu=True),
                font,
            ),
            Button(
                "Quit", pygame.Rect(bx, by + 250, 200, 40), self.view.quit_game, font
            ),
        ]
        if self.focus_idx >= len(self.buttons):
            self.focus_idx = max(0, len(self.buttons) - 1)


class InGameMenuOverlay(Overlay):
    """Menu accessible during gameplay via the Settings button."""

    def __init__(self, view: "GameView") -> None:
        super().__init__(view, view.close_overlay)
        self._layout()

    def resize(self) -> None:
        self._layout()

    def _layout(self) -> None:
        w, h = self.view.screen.get_size()
        font = self.view.font
        bx = w // 2 - 100
        by = h // 2 - 150
        self.buttons = [
            Button(
                "Resume Game",
                pygame.Rect(bx, by, 200, 40),
                self.view.close_overlay,
                font,
            ),
            Button(
                "Save Game",
                pygame.Rect(bx, by + 50, 200, 40),
                self.view.save_game,
                font,
            ),
            Button(
                "Load Game",
                pygame.Rect(bx, by + 100, 200, 40),
                self.view.load_game,
                font,
            ),
            Button(
                "Game Settings",
                pygame.Rect(bx, by + 150, 200, 40),
                self.view.show_settings,
                font,
            ),
            Button(
                "Return to Main Menu",
                pygame.Rect(bx, by + 200, 200, 40),
                self.view.confirm_return_to_menu,
                font,
            ),
            Button(
                "Quit Game",
                pygame.Rect(bx, by + 250, 200, 40),
                self.view.confirm_quit,
                font,
            ),
        ]
        if self.focus_idx >= len(self.buttons):
            self.focus_idx = max(0, len(self.buttons) - 1)


class SettingsOverlay(Overlay):
    """Top level settings menu."""

    def __init__(self, view: "GameView") -> None:
        super().__init__(view, view.close_overlay)
        self._layout()

    def resize(self) -> None:
        self._layout()

    def _layout(self) -> None:
        w, h = self.view.screen.get_size()
        font = self.view.font
        bx = w // 2 - 120
        by = h // 2 - 120
        self.buttons = [
            Button(
                "Game Settings",
                pygame.Rect(bx, by, 240, 40),
                self.view.show_game_settings,
                font,
            ),
            Button(
                "Graphics",
                pygame.Rect(bx, by + 50, 240, 40),
                self.view.show_graphics,
                font,
            ),
            Button(
                "Audio", pygame.Rect(bx, by + 100, 240, 40), self.view.show_audio, font
            ),
            Button(
                "Game Tutorial",
                pygame.Rect(bx, by + 150, 240, 40),
                lambda: self.view.show_tutorial(from_menu=False),
                font,
            ),
            Button(
                "Back",
                pygame.Rect(bx, by + 200, 240, 40),
                self.view.close_overlay,
                font,
            ),
        ]


class GameSettingsOverlay(Overlay):
    def __init__(self, view: "GameView") -> None:
        super().__init__(view, view.show_settings)
        self._layout()

    def resize(self) -> None:
        self._layout()

    def _layout(self) -> None:
        w, h = self.view.screen.get_size()
        font = self.view.font
        bx = w // 2 - 120
        by = h // 2 - 220

        def cycle(attr: str, options: List, label: str) -> Callable[[], None]:
            def callback(b: Button) -> Callable[[], None]:
                def inner() -> None:
                    cur = getattr(self.view, attr)
                    idx = options.index(cur)
                    cur = options[(idx + 1) % len(options)]
                    setattr(self.view, attr, cur)
                    self.view.apply_options()
                    b.text = f"{label}: {cur if not isinstance(cur, bool) else ('On' if cur else 'Off')}"

                return inner

            return callback

        self.buttons = []

        def make_button(offset: int, attr: str, opts: List, label: str) -> None:
            text = getattr(self.view, attr)
            if isinstance(text, bool):
                text = "On" if text else "Off"
            btn = Button(
                f"{label}: {text}",
                pygame.Rect(bx, by + offset, 240, 40),
                lambda: None,
                font,
            )
            btn.callback = cycle(attr, opts, label)(btn)
            self.buttons.append(btn)

        make_button(0, "ai_level", ["Easy", "Normal", "Hard"], "AI Level")
        make_button(
            50,
            "ai_personality",
            ["balanced", "aggressive", "defensive", "random"],
            "Personality",
        )
        make_button(100, "ai_lookahead", [False, True], "Lookahead")
        make_button(150, "animation_speed", [0.5, 1.0, 2.0], "Anim Speed")
        make_button(200, "sort_mode", ["rank", "suit"], "Sort Mode")
        self.buttons.append(
            Button(
                "House Rules",
                pygame.Rect(bx, by + 250, 240, 40),
                lambda: self.view.show_rules(from_menu=False),
                font,
            )
        )
        btn = Button(
            "Back", pygame.Rect(bx, by + 300, 240, 40), self.view.show_settings, font
        )
        self.buttons.append(btn)


class GraphicsOverlay(Overlay):
    def __init__(self, view: "GameView") -> None:
        super().__init__(view, view.show_settings)
        self._layout()

    def resize(self) -> None:
        self._layout()

    def _layout(self) -> None:
        w, h = self.view.screen.get_size()
        font = self.view.font
        bx = w // 2 - 120
        by = h // 2 - 120

        def cycle(attr: str, options: List, label: str) -> Callable[[], None]:
            def callback(btn: Button) -> Callable[[], None]:
                def inner() -> None:
                    cur = getattr(self.view, attr)
                    idx = options.index(cur)
                    cur = options[(idx + 1) % len(options)]
                    setattr(self.view, attr, cur)
                    self.view.apply_options()
                    if isinstance(cur, bool):
                        cur_txt = "On" if cur else "Off"
                    else:
                        cur_txt = cur
                    btn.text = f"{label}: {cur_txt}"

                return inner

            return callback

        make_color = list(TABLE_THEMES.keys())
        make_card_color = ["red", "blue", "green", "black"]

        self.buttons = []

        def make_button(offset: int, attr: str, opts: List, label: str) -> None:
            text = getattr(self.view, attr)
            btn = Button(
                f"{label}: {text}",
                pygame.Rect(bx, by + offset, 240, 40),
                lambda: None,
                font,
            )
            btn.callback = cycle(attr, opts, label)(btn)
            self.buttons.append(btn)

        make_button(0, "table_color_name", make_color, "Table Color")
        make_button(50, "card_color", make_card_color, "Card Color")
        make_button(100, "colorblind_mode", [False, True], "Colorblind")
        make_button(150, "fullscreen", [False, True], "Fullscreen")
        btn = Button(
            "Back", pygame.Rect(bx, by + 200, 240, 40), self.view.show_settings, font
        )
        self.buttons.append(btn)


class AudioOverlay(Overlay):
    def __init__(self, view: "GameView") -> None:
        super().__init__(view, view.show_settings)
        self._layout()

    def resize(self) -> None:
        self._layout()

    def _layout(self) -> None:
        w, h = self.view.screen.get_size()
        font = self.view.font
        bx = w // 2 - 120
        by = h // 2 - 120

        def cycle(attr: str, options: List, label: str) -> Callable[[], None]:
            def callback(btn: Button) -> Callable[[], None]:
                def inner() -> None:
                    cur = getattr(self.view, attr)
                    idx = options.index(cur)
                    cur = options[(idx + 1) % len(options)]
                    setattr(self.view, attr, cur)
                    self.view.apply_options()
                    btn.text = f"{label}: {cur if not isinstance(cur, bool) else ('On' if cur else 'Off')}"

                return inner

            return callback

        self.buttons = []

        def make_button(offset: int, attr: str, opts: List, label: str) -> None:
            text = getattr(self.view, attr)
            if isinstance(text, bool):
                text = "On" if text else "Off"
            btn = Button(
                f"{label}: {text}",
                pygame.Rect(bx, by + offset, 240, 40),
                lambda: None,
                font,
            )
            btn.callback = cycle(attr, opts, label)(btn)
            self.buttons.append(btn)

        make_button(0, "sound_enabled", [True, False], "Sound")
        make_button(50, "music_enabled", [True, False], "Music")
        make_button(100, "fx_volume", [0.5, 0.75, 1.0], "FX Vol")
        make_button(150, "music_volume", [0.5, 0.75, 1.0], "Music Vol")
        btn = Button(
            "Back", pygame.Rect(bx, by + 200, 240, 40), self.view.show_settings, font
        )
        self.buttons.append(btn)


class RulesOverlay(Overlay):
    """Overlay providing toggles for optional house rules."""

    def __init__(self, view: "GameView", back_cb: Callable[[], None]) -> None:
        super().__init__(view, back_cb)
        self._layout()

    def resize(self) -> None:
        self._layout()

    def _layout(self) -> None:
        w, h = self.view.screen.get_size()
        font = self.view.font
        bx = w // 2 - 120
        by = h // 2 - 150

        def toggle(attr: str, label: str) -> Callable[[Button], Callable[[], None]]:
            def cb(btn: Button) -> Callable[[], None]:
                def inner() -> None:
                    cur = getattr(self.view, attr)
                    setattr(self.view, attr, not cur)
                    self.view.apply_options()
                    btn.text = f"{label}: {'On' if getattr(self.view, attr) else 'Off'}"

                return inner

            return cb

        self.buttons = []

        def make_button(offset: int, attr: str, label: str) -> None:
            state = getattr(self.view, attr)
            text = f"{label}: {'On' if state else 'Off'}"
            btn = Button(
                text, pygame.Rect(bx, by + offset, 240, 40), lambda: None, font
            )
            btn.callback = toggle(attr, label)(btn)
            self.buttons.append(btn)

        make_button(0, "rule_chat_bomb", "“Chặt” Bomb")
        make_button(50, "rule_chain_cutting", "Chain Cutting")
        make_button(100, "rule_tu_quy_hierarchy", "Tứ Quý Hierarchy")
        make_button(150, "rule_flip_suit_rank", "Flip Suit Rank")
        make_button(200, "rule_no_2s", "No 2s in straights")
        self.buttons.append(
            Button("Back", pygame.Rect(bx, by + 250, 240, 40), self.back_callback, font)
        )


class HowToPlayOverlay(Overlay):
    """Display a short summary of the basic rules."""

    def __init__(self, view: "GameView", back_cb: Callable[[], None]) -> None:
        super().__init__(view, back_cb)
        self._layout()

    def resize(self) -> None:
        self._layout()

    def _layout(self) -> None:
        w, h = self.view.screen.get_size()
        font = self.view.font
        bx = w // 2 - 100
        by = h // 2 + 60
        self.buttons = [
            Button("Back", pygame.Rect(bx, by, 200, 40), self.back_callback, font)
        ]

    def draw(self, surface: pygame.Surface) -> None:
        super().draw(surface)
        w, h = surface.get_size()
        font = pygame.font.SysFont(None, 20)
        lines = [
            "Each player starts with 13 cards.",
            "Play higher combinations to beat opponents.",
            "First to shed all cards wins the round.",
        ]
        y = h // 2 - 40
        for line in lines:
            img = font.render(line, True, (255, 255, 255))
            surface.blit(img, img.get_rect(center=(w // 2, y)))
            y += 24


class TutorialOverlay(Overlay):
    """Explain gameplay via numbered steps."""

    def __init__(self, view: "GameView", back_cb: Callable[[], None]) -> None:
        super().__init__(view, back_cb)
        self._layout()

    def resize(self) -> None:
        self._layout()

    def _layout(self) -> None:
        w, h = self.view.screen.get_size()
        font = self.view.font
        bx = w // 2 - 100
        by = h // 2 + 60
        self.buttons = [
            Button("Back", pygame.Rect(bx, by, 200, 40), self.back_callback, font)
        ]

    def draw(self, surface: pygame.Surface) -> None:
        super().draw(surface)
        w, h = surface.get_size()
        font = pygame.font.SysFont(None, 20)
        steps = [
            "1. Select cards with mouse or arrow keys.",
            "2. Press Play to submit your move.",
            "3. Beat opponents until you run out of cards.",
        ]
        y = h // 2 - 40
        for line in steps:
            img = font.render(line, True, (255, 255, 255))
            surface.blit(img, img.get_rect(center=(w // 2, y)))
            y += 24


class SavePromptOverlay(Overlay):
    """Prompt the user to save before performing an action."""

    def __init__(
        self, view: "GameView", action: Callable[[], None], label: str
    ) -> None:
        super().__init__(view, view.close_overlay)
        self.action = action
        self.label = label
        self._layout()

    def resize(self) -> None:
        self._layout()

    def _layout(self) -> None:
        w, h = self.view.screen.get_size()
        font = self.view.font
        bx = w // 2 - 120
        by = h // 2
        self.buttons = [
            Button(
                f"Save and {self.label}",
                pygame.Rect(bx, by, 240, 40),
                self._save_then_action,
                font,
            ),
            Button(
                f"{self.label} Without Saving",
                pygame.Rect(bx, by + 50, 240, 40),
                self.action,
                font,
            ),
            Button(
                "Cancel",
                pygame.Rect(bx, by + 100, 240, 40),
                self.view.close_overlay,
                font,
            ),
        ]

    def _save_then_action(self) -> None:
        self.view.save_game()
        self.action()

    def draw(self, surface: pygame.Surface) -> None:
        w, h = surface.get_size()
        font = pygame.font.SysFont(None, 24)
        msg = f"Save your game before {self.label.lower()}?"
        img = font.render(msg, True, (255, 255, 255))
        surface.blit(img, img.get_rect(center=(w // 2, h // 2 - 60)))
        super().draw(surface)


class GameOverOverlay(Overlay):
    def __init__(self, view: "GameView", winner: str) -> None:
        super().__init__(view, None)
        self.winner = winner
        self.rankings = view.game.get_rankings()
        self._layout()

    def resize(self) -> None:
        self._layout()

    def _layout(self) -> None:
        w, h = self.view.screen.get_size()
        font = self.view.font
        bx = w // 2 - 100
        by = h // 2 + 40
        self.buttons = [
            Button(
                "Play Again", pygame.Rect(bx, by, 200, 40), self.view.restart_game, font
            ),
            Button(
                "Quit", pygame.Rect(bx, by + 50, 200, 40), self.view.quit_game, font
            ),
        ]

    def draw(self, surface: pygame.Surface) -> None:
        w, h = surface.get_size()
        font = pygame.font.SysFont(None, 32)
        txt = font.render(f"{self.winner} wins!", True, (255, 255, 255))
        surface.blit(txt, txt.get_rect(center=(w // 2, h // 2 - 60)))
        rank_lines = [f"{i+1}. {n} ({c})" for i, (n, c) in enumerate(self.rankings)]
        y = h // 2 - 20
        for line in rank_lines:
            img = font.render(line, True, (255, 255, 255))
            surface.blit(img, img.get_rect(center=(w // 2, y)))
            y += 30
        super().draw(surface)


# ---------------------------------------------------------------------------
# Main game view
# ---------------------------------------------------------------------------


class GameView:
    TABLE_COLOR = TABLE_THEMES["darkgreen"]

    def __init__(self, width: int = 1024, height: int = 768) -> None:
        pygame.init()
        pygame.display.set_caption("Tiến Lên - Pygame")
        self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        self.fullscreen = False
        self.card_width = self._calc_card_width(width)
        self.clock = pygame.time.Clock()
        self.animation_speed = 1.0
        self.game = Game()
        self.game.setup()
        self._attach_reset_pile()
        self.font = pygame.font.SysFont(None, 24)
        load_card_images(self.card_width)
        self.table_image: Optional[pygame.Surface] = None
        img_path = Path(__file__).with_name("assets") / "table_img.png"
        if img_path.exists():
            try:
                self.table_image = pygame.image.load(str(img_path)).convert()
            except Exception:
                self.table_image = None
        self.main_menu_image: Optional[pygame.Surface] = None
        menu_path = Path(__file__).with_name("assets") / "main_menu.png"
        if menu_path.exists():
            try:
                self.main_menu_image = pygame.image.load(str(menu_path)).convert()
            except Exception:
                self.main_menu_image = None
        self._table_surface: Optional[pygame.Surface] = None
        self._update_table_surface()
        # Load sound effects and background music
        sdir = Path(__file__).with_name("assets") / "sound"
        sound.load("click", sdir / "card-play.wav")
        sound.load("pass", sdir / "pass.wav")
        sound.load("bomb", sdir / "bomb.wav")
        sound.load("shuffle", sdir / "shuffle.wav")
        sound.load("win", sdir / "win.wav")
        if _mixer_ready():
            music = sdir / "Ambush in Rattlesnake Gulch.mp3"
            try:
                pygame.mixer.music.load(str(music))
                pygame.mixer.music.play(-1)
            except Exception:
                pass
        self.selected: List[CardSprite] = []
        self.current_trick: list[tuple[str, pygame.Surface]] = []
        self.ai_sprites: List[pygame.sprite.Group] = [
            pygame.sprite.Group() for _ in range(3)
        ]
        self.running = True
        self.overlay: Optional[Overlay] = None
        self.state: GameState = GameState.PLAYING
        self.ai_level = "Normal"
        self.ai_personality = "balanced"
        self.ai_lookahead = False
        self.sort_mode = "rank"
        self.player_name = "Player"
        self.card_back_name = "card_back"
        self.table_color_name = "darkgreen"
        self.table_color = TABLE_THEMES[self.table_color_name]
        self.card_color = "red"
        self.colorblind_mode = False
        self.sound_enabled = True
        self.music_enabled = True
        self.music_volume = 1.0
        self.fx_volume = 1.0
        self.house_rules = True
        self.tutorial_mode = False
        self.show_rules_option = False
        # Additional house rule toggles
        self.rule_chat_bomb = False
        self.rule_chain_cutting = False
        self.rule_tu_quy_hierarchy = False
        self.rule_flip_suit_rank = False
        self.rule_no_2s = True
        self.action_buttons: List[Button] = []
        self._create_action_buttons()
        self.settings_button: Button
        self._position_settings_button()
        opts = self._load_options()
        self.animation_speed = opts.get("animation_speed", self.animation_speed)
        self.table_color_name = opts.get("table_color", self.table_color_name)
        self.card_back_name = opts.get("card_back", self.card_back_name)
        self.sort_mode = opts.get("sort_mode", self.sort_mode)
        self.player_name = opts.get("player_name", self.player_name)
        self.ai_level = opts.get("ai_level", self.ai_level)
        self.ai_personality = opts.get("ai_personality", self.ai_personality)
        self.ai_lookahead = opts.get("ai_lookahead", self.ai_lookahead)
        self.sound_enabled = opts.get("sound", self.sound_enabled)
        self.music_enabled = opts.get("music", self.music_enabled)
        self.music_volume = opts.get("music_volume", self.music_volume)
        self.fx_volume = opts.get("fx_volume", self.fx_volume)
        self.card_color = opts.get("card_color", self.card_color)
        self.colorblind_mode = opts.get("colorblind_mode", self.colorblind_mode)
        self.house_rules = opts.get("house_rules", self.house_rules)
        self.tutorial_mode = opts.get("tutorial_mode", self.tutorial_mode)
        self.show_rules_option = opts.get(
            "show_rules_option",
            opts.get("show_rules", self.show_rules_option),
        )
        self.rule_chat_bomb = opts.get("rule_chat_bomb", self.rule_chat_bomb)
        self.rule_chain_cutting = opts.get(
            "rule_chain_cutting", self.rule_chain_cutting
        )
        self.rule_tu_quy_hierarchy = opts.get(
            "rule_tu_quy_hierarchy", self.rule_tu_quy_hierarchy
        )
        self.rule_flip_suit_rank = opts.get(
            "rule_flip_suit_rank", self.rule_flip_suit_rank
        )
        self.rule_no_2s = opts.get("rule_no_2s", self.rule_no_2s)
        if opts.get("fullscreen", False):
            self.toggle_fullscreen()
        self.apply_options()
        self.update_hand_sprites()
        self._create_action_buttons()
        self.win_counts: Dict[str, int] = {p.name: 0 for p in self.game.players}
        self.show_menu()

    # Animation helpers -------------------------------------------------
    def _draw_frame(self) -> None:
        """Redraw the game state."""
        if self.state == GameState.MENU and self.main_menu_image:
            bg = pygame.transform.smoothscale(
                self.main_menu_image, self.screen.get_size()
            )
            self.screen.blit(bg, (0, 0))
        else:
            if self._table_surface:
                self.screen.blit(self._table_surface, (0, 0))
            else:
                self.screen.fill(self.table_color)
            self.draw_players()
        if self.overlay:
            overlay_surf = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
            overlay_surf.fill((0, 0, 0, 180))
            self.screen.blit(overlay_surf, (0, 0))
            self.overlay.draw(self.screen)
        self.draw_score_overlay()
        pygame.display.flip()

    def _animate_sprites(
        self, sprites: List[CardSprite], dest: Tuple[int, int], frames: int = 15
    ) -> None:
        """Move ``sprites`` toward ``dest`` over ``frames`` steps."""
        if not sprites:
            return
        frames = max(1, int(frames / self.animation_speed))
        starts = [sp.rect.center for sp in sprites]
        for i in range(frames):
            t = (i + 1) / frames
            for sp, (sx, sy) in zip(sprites, starts):
                sp.rect.center = (
                    int(sx + (dest[0] - sx) * t),
                    int(sy + (dest[1] - sy) * t),
                )
            self._draw_frame()
            pygame.event.pump()
            self.clock.tick(60)

    def _animate_bounce(
        self, sprites: List[CardSprite], scale: float = 1.2, frames: int = 6
    ) -> None:
        """Briefly scale ``sprites`` up then back down for a bounce effect."""
        if not sprites:
            return
        frames = max(1, int(frames / self.animation_speed))
        half = frames // 2 or 1
        originals = [(sp.image, sp.rect.copy()) for sp in sprites]
        for i in range(frames):
            # progress goes 0->1 then 1->0
            t = (i + 1) / half if i < half else (frames - i) / half
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
            self.clock.tick(60)
        # restore originals
        for sp, (img, rect) in zip(sprites, originals):
            sp.image = img
            sp.rect = rect

    def _animate_back(
        self, start: Tuple[int, int], dest: Tuple[int, int], frames: int = 15
    ) -> None:
        """Animate a card back image from ``start`` to ``dest``."""
        img = get_card_back(self.card_back_name)
        if img is None:
            return
        frames = max(1, int(frames / self.animation_speed))
        rect = img.get_rect(center=start)
        for i in range(frames):
            t = (i + 1) / frames
            rect.center = (
                int(start[0] + (dest[0] - start[0]) * t),
                int(start[1] + (dest[1] - start[1]) * t),
            )
            self._draw_frame()
            self.screen.blit(img, rect)
            pygame.display.flip()
            pygame.event.pump()
            self.clock.tick(60)
        dummy = types.SimpleNamespace(image=img, rect=rect)
        self._animate_bounce([dummy])

    def _animate_flip(
        self, sprites: List[CardSprite], dest: Tuple[int, int], frames: int = 15
    ) -> None:
        """Move ``sprites`` to ``dest`` while flipping from back to front."""
        if not sprites:
            return
        frames = max(1, int(frames / self.animation_speed))
        starts = [sp.rect.center for sp in sprites]
        fronts = [sp.image for sp in sprites]
        back = get_card_back(self.card_back_name, sprites[0].rect.width)
        for i in range(frames):
            t = (i + 1) / frames
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
            self.clock.tick(60)
        self._animate_bounce(sprites)

    def _animate_select(self, sprite: CardSprite, up: bool) -> None:
        offset = -10 if up else 10
        dest = (sprite.rect.centerx, sprite.rect.centery + offset)
        self._animate_sprites([sprite], dest, frames=5)

    def _highlight_turn(self, idx: int, frames: int = 10) -> None:
        """Flash the active player's name for visual emphasis."""
        x, y = self._player_pos(idx)
        card_w = self.card_width
        sprites = self.hand_sprites.sprites()
        card_h = sprites[0].rect.height if sprites else int(card_w * 1.4)
        spacing = min(40, card_w)
        rect = pygame.Rect(0, 0, 140, 30)
        if idx == 0:
            rect.midbottom = (x, y)
        elif idx == 1:
            rect.midtop = (x, y)
        elif idx == 2:
            rect.midleft = (x, y)
        else:
            rect.midright = (x, y)
        frames = max(1, int(frames / self.animation_speed))
        for i in range(frames):
            self._draw_frame()
            overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
            alpha = max(0, 200 - i * 20)
            center = overlay.get_rect().center
            radius = 11 + int(3 * math.sin(math.pi * i / frames))
            if hasattr(overlay, "get_width"):
                pygame.draw.circle(
                    overlay, (255, 255, 0, alpha), center, radius, width=3
                )
            self.screen.blit(overlay, rect.topleft)
            pygame.display.flip()
            pygame.event.pump()
            self.clock.tick(60)

    def _transition_overlay(
        self,
        old: Optional[Overlay],
        new: Overlay,
        frames: int = 10,
        slide: bool = False,
    ) -> None:
        """Animate transition between two overlays."""
        if old is None:
            return
        frames = max(1, int(frames / self.animation_speed))
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
        for i in range(frames):
            progress = (i + 1) / frames
            self.overlay = None
            self._draw_frame()
            self.overlay = current
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
            self.clock.tick(60)

        self.overlay = new
        self._draw_frame()

    # Layout helpers --------------------------------------------------
    def _player_pos(self, idx: int) -> Tuple[int, int]:
        """Return the centre position for player ``idx`` based on screen size."""
        w, h = self.screen.get_size()
        card_w = self.card_width
        card_h = int(card_w * 1.4)
        margin = min(60, max(40, int(card_w * 0.75)))
        bottom_y = h - margin - card_h // 2
        top_y = margin + card_h // 2
        left_x = margin + card_w // 2
        right_x = w - margin - card_w // 2
        if idx == 0:
            return w // 2, bottom_y
        if idx == 1:
            return w // 2, top_y
        if idx == 2:
            return left_x, h // 2
        return right_x, h // 2

    def _pile_center(self) -> Tuple[int, int]:
        w, h = self.screen.get_size()
        card_h = int(self.card_width * 1.4)
        spacing = max(10, self.card_width // 2)
        _, hand_y = self._player_pos(0)
        y = hand_y + spacing - card_h // 2
        return w // 2, y

    def _calc_card_width(self, win_width: int) -> int:
        """Determine card width based on window width."""
        return max(30, win_width // 13)

    def _update_table_surface(self) -> None:
        """Generate a tiled background surface if a table image is loaded."""
        if self.table_image is None:
            self._table_surface = None
            return
        w, h = self.screen.get_size()
        tile_size = max(50, self.card_width * 2)
        tile = pygame.transform.smoothscale(self.table_image, (tile_size, tile_size))
        surface = pygame.Surface((w, h))
        for x in range(0, w, tile.get_width()):
            for y in range(0, h, tile.get_height()):
                surface.blit(tile, (x, y))
        self._table_surface = surface

    def _create_action_buttons(self) -> None:
        """Create or reposition the Play/Pass/Undo buttons."""
        w, _ = self.screen.get_size()
        btn_w = 120
        spacing = max(10, self.card_width // 2)
        total = btn_w * 3 + spacing * 2
        start_x = w // 2 - total // 2

        # Position buttons relative to the pile location
        _, pile_y = self._pile_center()
        sprites = getattr(self, "hand_sprites", None)
        if sprites:
            card_h = sprites.sprites()[0].rect.height
        else:
            card_h = int(self.card_width * 1.4)
        y = pile_y + card_h

        font = self.font
        self.action_buttons = [
            Button(
                "Play", pygame.Rect(start_x, y, btn_w, 40), self.play_selected, font
            ),
            Button(
                "Pass",
                pygame.Rect(start_x + btn_w + spacing, y, btn_w, 40),
                self.pass_turn,
                font,
            ),
            Button(
                "Undo",
                pygame.Rect(start_x + 2 * (btn_w + spacing), y, btn_w, 40),
                self.undo_move,
                font,
            ),
        ]

    def _position_settings_button(self) -> None:
        """Position the persistent Settings button."""
        w, _ = self.screen.get_size()
        font = self.font
        if not hasattr(self, "settings_button"):
            self.settings_button = Button(
                "Settings", pygame.Rect(0, 0, 100, 40), self.show_in_game_menu, font
            )
        else:
            self.settings_button.callback = self.show_in_game_menu
        margin = min(60, max(40, self.card_width // 3))
        self.settings_button.rect.topright = (w - margin, margin)

    def _activate_overlay(self, overlay: Overlay, state: GameState) -> None:
        """Switch to ``overlay`` using a brief transition."""
        old = self.overlay
        if old is not overlay:
            self._transition_overlay(old, overlay)
        self.overlay = overlay
        self.state = state

    # Overlay helpers -------------------------------------------------
    def show_menu(self) -> None:
        self._activate_overlay(MainMenuOverlay(self), GameState.MENU)

    def show_in_game_menu(self) -> None:
        self._activate_overlay(InGameMenuOverlay(self), GameState.SETTINGS)

    def show_settings(self) -> None:
        self._activate_overlay(SettingsOverlay(self), GameState.SETTINGS)

    def show_game_settings(self) -> None:
        self._activate_overlay(GameSettingsOverlay(self), GameState.SETTINGS)

    # Legacy name kept for backwards compatibility
    def show_options(self) -> None:
        self.show_game_settings()

    def show_graphics(self) -> None:
        self._activate_overlay(GraphicsOverlay(self), GameState.SETTINGS)

    def show_audio(self) -> None:
        self._activate_overlay(AudioOverlay(self), GameState.SETTINGS)

    def show_rules(self, from_menu: bool = False) -> None:
        back_cb = self.show_menu if from_menu else self.show_game_settings
        self._activate_overlay(RulesOverlay(self, back_cb), GameState.SETTINGS)

    def show_how_to_play(self, from_menu: bool = False) -> None:
        back_cb = self.show_menu if from_menu else self.show_settings
        self._activate_overlay(HowToPlayOverlay(self, back_cb), GameState.SETTINGS)

    def show_tutorial(self, from_menu: bool = False) -> None:
        back_cb = self.show_menu if from_menu else self.show_settings
        self._activate_overlay(TutorialOverlay(self, back_cb), GameState.SETTINGS)

    def confirm_quit(self) -> None:
        self._activate_overlay(
            SavePromptOverlay(self, self.quit_game, "Quit"),
            GameState.SETTINGS,
        )

    def confirm_return_to_menu(self) -> None:
        self._activate_overlay(
            SavePromptOverlay(self, self.show_menu, "Return"),
            GameState.SETTINGS,
        )

    def save_game(self) -> None:
        try:
            with open(
                Path(__file__).with_name("saved_game.json"), "w", encoding="utf-8"
            ) as f:
                json.dump(self.game.to_dict(), f, indent=2)
        except OSError as exc:
            logger.warning("Failed to save game: %s", exc)

    def load_game(self) -> None:
        try:
            with open(
                Path(__file__).with_name("saved_game.json"), "r", encoding="utf-8"
            ) as f:
                data = json.load(f)
        except OSError as exc:
            logger.warning("Failed to load game: %s", exc)
            return

        try:
            game = Game()
            game.from_dict(data)
        except Exception as exc:
            logger.error("Invalid saved game: %s", exc)
            return

        self.game = game
        self._attach_reset_pile()
        self.update_hand_sprites()

    def close_overlay(self) -> None:
        had = self.overlay is not None
        self.overlay = None
        if had:
            self._save_options()
            self.state = GameState.PLAYING
            self.ai_turns()

    def quit_game(self) -> None:
        self.running = False

    def restart_game(self) -> None:
        counts = self.win_counts
        self.game = Game()
        self.game.setup()
        self._attach_reset_pile()
        self.reset_current_trick()
        self.selected.clear()
        self.apply_options()
        for p in self.game.players:
            counts.setdefault(p.name, 0)
        self.win_counts = counts
        self.close_overlay()

    def reset_current_trick(self) -> None:
        """Clear the list of cards representing the current trick."""
        self.current_trick.clear()

    def _attach_reset_pile(self) -> None:
        """Wrap the game's ``reset_pile`` method to clear the trick."""

        original = self.game.reset_pile

        def wrapped_reset_pile(*args, **kwargs):
            original(*args, **kwargs)
            self.reset_current_trick()

        self.game.reset_pile = wrapped_reset_pile

    # Option helpers --------------------------------------------------
    def _load_options(self) -> dict:
        try:
            with open(OPTIONS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "show_rules" in data and "show_rules_option" not in data:
                data["show_rules_option"] = data["show_rules"]
            return data
        except Exception as exc:
            logger.warning("Failed to load options: %s", exc)
            return {}

    def _save_options(self) -> None:
        data = {
            "animation_speed": self.animation_speed,
            "table_color": self.table_color_name,
            "card_back": self.card_back_name,
            "sort_mode": self.sort_mode,
            "player_name": self.player_name,
            "ai_level": self.ai_level,
            "ai_personality": self.ai_personality,
            "ai_lookahead": self.ai_lookahead,
            "sound": self.sound_enabled,
            "music": self.music_enabled,
            "music_volume": self.music_volume,
            "fx_volume": self.fx_volume,
            "card_color": self.card_color,
            "colorblind_mode": self.colorblind_mode,
            "house_rules": self.house_rules,
            "tutorial_mode": self.tutorial_mode,
            "show_rules_option": self.show_rules_option,
            "rule_chat_bomb": self.rule_chat_bomb,
            "rule_chain_cutting": self.rule_chain_cutting,
            "rule_tu_quy_hierarchy": self.rule_tu_quy_hierarchy,
            "rule_flip_suit_rank": self.rule_flip_suit_rank,
            "rule_no_2s": self.rule_no_2s,
            "fullscreen": self.fullscreen,
        }
        try:
            with open(OPTIONS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception as exc:
            logger.warning("Failed to save options: %s", exc)

    def apply_options(self) -> None:
        self.table_color = TABLE_THEMES.get(
            self.table_color_name, TABLE_THEMES["darkgreen"]
        )
        back_map = {
            "red": "card_back",
            "blue": "card_back",
            "green": "card_back_green",
            "black": "card_back_black",
        }
        self.card_back_name = back_map.get(self.card_color, "card_back")
        self.game.players[0].name = self.player_name
        self.game.players[0].sort_hand(self.sort_mode)
        self.game.set_ai_level(self.ai_level)
        self.game.set_personality(self.ai_personality)
        self.game.ai_lookahead = self.ai_lookahead
        import tien_len_full as tl

        tl.ALLOW_2_IN_SEQUENCE = not self.rule_no_2s
        tl.CHAT_BOMB = self.rule_chat_bomb
        tl.CHAIN_CUTTING = self.rule_chain_cutting
        tl.TU_QUY_HIERARCHY = self.rule_tu_quy_hierarchy
        tl.FLIP_SUIT_RANK = self.rule_flip_suit_rank
        sound.set_volume(self.fx_volume)
        sound.set_enabled(self.sound_enabled)
        if _mixer_ready():
            pygame.mixer.music.set_volume(self.music_volume)
            if self.music_enabled:
                pygame.mixer.music.unpause()
            else:
                pygame.mixer.music.pause()
        if hasattr(self, "hand_sprites"):
            self._create_action_buttons()

    def show_game_over(self, winner: str) -> None:
        sound.play("win")
        self.win_counts[winner] = self.win_counts.get(winner, 0) + 1
        self._activate_overlay(GameOverOverlay(self, winner), GameState.GAME_OVER)

    def set_ai_level(self, level: str) -> None:
        self.ai_level = level
        self.game.set_ai_level(level)

    def on_resize(self, width: int, height: int) -> None:
        """Handle window resize by recreating sprites."""
        flags = pygame.FULLSCREEN if self.fullscreen else pygame.RESIZABLE
        self.screen = pygame.display.set_mode((width, height), flags)
        self.card_width = self._calc_card_width(width)
        load_card_images(self.card_width)
        self._update_table_surface()
        self.update_hand_sprites()
        self._create_action_buttons()
        self._position_settings_button()
        if self.overlay:
            self.overlay.resize()

    def toggle_fullscreen(self) -> None:
        """Toggle full-screen mode."""
        try:
            pygame.display.toggle_fullscreen()
        except Exception:
            pass
        self.fullscreen = not getattr(self, "fullscreen", False)
        flags = pygame.FULLSCREEN if self.fullscreen else pygame.RESIZABLE
        size = self.screen.get_size()
        self.screen = pygame.display.set_mode(size, flags)
        self.card_width = self._calc_card_width(size[0])
        load_card_images(self.card_width)
        self._update_table_surface()
        self.update_hand_sprites()
        self._create_action_buttons()

    def update_play_button_state(self) -> None:
        """Enable the Play button only when the current selection is valid."""
        if not self.action_buttons:
            return
        cards = [sp.card for sp in self.selected]
        if not cards:
            self.action_buttons[0].enabled = False
            return
        player = self.game.players[self.game.current_idx]
        ok, _ = self.game.is_valid(player, cards, self.game.current_combo)
        self.action_buttons[0].enabled = ok

    # Event handling --------------------------------------------------
    def _dispatch_overlay_event(self, event: pygame.event.Event) -> bool:
        """Send events to the active overlay when the game isn't playing."""
        if self.state == GameState.PLAYING:
            return False
        if self.overlay:
            self.overlay.handle_event(event)
        return True

    def _dispatch_game_event(self, event: pygame.event.Event) -> bool:
        """Handle mouse or key events during gameplay."""
        if self.state != GameState.PLAYING:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.handle_mouse(event.pos)
        elif event.type == pygame.KEYDOWN:
            self.handle_key(event.key)
        return True

    def handle_mouse(self, pos):
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": pos})
        if self._dispatch_overlay_event(event):
            return
        for btn in self.action_buttons:
            if btn.rect.collidepoint(pos):
                if btn.text == "Undo" and len(self.game.snapshots) <= 1:
                    return
                btn.callback()
                return
        if self.settings_button.rect.collidepoint(pos):
            self.settings_button.callback()
            return
        for sp in reversed(self.selected):
            if sp.rect.collidepoint(pos):
                up = not sp.selected
                sp.toggle()
                if isinstance(sp, CardSprite):
                    self._animate_select(sp, up)
                if sp.selected:
                    self.selected.append(sp)
                else:
                    self.selected.remove(sp)
                self.update_play_button_state()
                return
        for sp in reversed(self.hand_sprites.sprites()):
            if sp.rect.collidepoint(pos):
                up = not sp.selected
                sp.toggle()
                if isinstance(sp, CardSprite):
                    self._animate_select(sp, up)
                if sp.selected and sp not in self.selected:
                    self.selected.append(sp)
                elif not sp.selected and sp in self.selected:
                    self.selected.remove(sp)
                self.update_play_button_state()
                return

    def handle_key(self, key):
        event = pygame.event.Event(pygame.KEYDOWN, {"key": key})
        if self._dispatch_overlay_event(event):
            return
        if key == pygame.K_RETURN:
            self.play_selected()
        elif key == pygame.K_SPACE:
            self.pass_turn()
        elif key == pygame.K_m:
            self.show_menu()
        elif key == pygame.K_o:
            self.show_settings()
        elif key == pygame.K_F11:
            self.toggle_fullscreen()

    # Game actions ----------------------------------------------------
    def play_selected(self):
        if not self.selected:
            return
        cards = [sp.card for sp in self.selected]
        player = self.game.players[self.game.current_idx]
        ok, msg = self.game.is_valid(player, cards, self.game.current_combo)
        if not ok:
            logger.info("Invalid: %s", msg)
            return
        if self.game.process_play(player, cards):
            self.show_game_over(player.name)
            return
        for c in cards:
            img = get_card_image(c, self.card_width)
            if img is not None:
                self.current_trick.append((player.name, img))
        if detect_combo(cards) == "bomb":
            sound.play("bomb")
        else:
            sound.play("click")
        self._animate_flip(list(self.selected), self._pile_center())
        self.game.next_turn()
        self.selected.clear()
        self.update_hand_sprites()
        self._highlight_turn(self.game.current_idx)
        self.ai_turns()

    def pass_turn(self):
        if self.game.handle_pass():
            self.running = False
        else:
            sound.play("pass")
            self._highlight_turn(self.game.current_idx)
            self.ai_turns()
        if not self.game.pile:
            self.current_trick.clear()

    def undo_move(self) -> None:
        """Undo the most recent move and refresh the display."""
        if self.game.undo_last():
            self.selected.clear()
            self.update_hand_sprites()
            self._highlight_turn(self.game.current_idx)

    def ai_turns(self):
        while not self.game.players[self.game.current_idx].is_human:
            p = self.game.players[self.game.current_idx]
            cards = self.game.ai_play(self.game.current_combo)
            ok, _ = self.game.is_valid(p, cards, self.game.current_combo)
            if not ok:
                cards = []
            if cards:
                if self.game.process_play(p, cards):
                    self.show_game_over(p.name)
                    break
                for c in cards:
                    img = get_card_image(c, self.card_width)
                    if img is not None:
                        self.current_trick.append((p.name, img))
                if detect_combo(cards) == "bomb":
                    sound.play("bomb")
                else:
                    sound.play("click")
                self._animate_back(
                    self._player_pos(self.game.current_idx), self._pile_center()
                )
            else:
                sound.play("pass")
                self.game.process_pass(p)
            self.game.next_turn()
            self._highlight_turn(self.game.current_idx)
            if not self.game.pile:
                self.current_trick.clear()
        self.update_hand_sprites()
        self._highlight_turn(self.game.current_idx)

    # Rendering -------------------------------------------------------
    def update_hand_sprites(self):
        player = self.game.players[0]
        self.hand_sprites = pygame.sprite.OrderedUpdates()
        w, h = self.screen.get_size()
        start_x, y = self._player_pos(0)
        card_w = self.card_width
        card_h = int(card_w * 1.4)
        spacing = HAND_SPACING
        margin = min(60, max(40, int(card_w * 0.75)))
        hand_w = card_w + (len(player.hand) - 1) * spacing
        start_x = w // 2 - hand_w // 2
        start_x = max(margin, min(start_x, w - margin - hand_w))
        for i, c in enumerate(player.hand):
            sprite = CardSprite(c, (start_x + i * spacing, y), card_w)
            self.hand_sprites.add(sprite)

        self.ai_sprites = [pygame.sprite.Group() for _ in range(3)]
        for idx in range(1, 4):
            group = self.ai_sprites[idx - 1]
            opp = self.game.players[idx]
            x, y = self._player_pos(idx)
            if idx == 1:
                hand_w = card_w + (len(opp.hand) - 1) * spacing
                start = w // 2 - hand_w // 2
                start = max(margin, min(start, w - margin - hand_w))
                for i in range(len(opp.hand)):
                    sp = CardBackSprite(
                        (start + i * spacing, y), card_w, self.card_back_name
                    )
                    group.add(sp)
            else:
                hand_h = card_h + (len(opp.hand) - 1) * spacing
                start = h // 2 - hand_h // 2
                start = max(margin, min(start, h - margin - hand_h))
                for i in range(len(opp.hand)):
                    sp = CardBackSprite(
                        (x, start + i * spacing), card_w, self.card_back_name
                    )
                    group.add(sp)
        self.update_play_button_state()

    def draw_players(self):
        card_w = self.card_width
        sprites = self.hand_sprites.sprites()
        card_h = sprites[0].rect.height if sprites else int(card_w * 1.4)
        spacing = min(40, card_w)

        for idx, p in enumerate(self.game.players):
            x, y = self._player_pos(idx)
            txt = f"{p.name} ({len(p.hand)})"
            color = (255, 255, 0) if idx == self.game.current_idx else (255, 255, 255)
            img = self.font.render(txt, True, color)
            if idx == 0:
                offset = card_h // 2 + spacing // 2
                rect = img.get_rect(midbottom=(x, y - offset))
            elif idx == 1:
                offset = card_h // 2 + spacing // 2
                rect = img.get_rect(midtop=(x, y + offset))
            elif idx == 2:
                offset = card_w // 2 + spacing // 2
                rect = img.get_rect(midleft=(x + offset, y))
            else:
                offset = card_w // 2 + spacing // 2
                rect = img.get_rect(midright=(x - offset, y))
            self.screen.blit(img, rect)

        for sp in self.hand_sprites.sprites():
            if isinstance(sp, CardSprite):
                sp.draw_shadow(self.screen)
        for group in self.ai_sprites:
            for sp in group.sprites():
                if isinstance(sp, CardSprite):
                    sp.draw_shadow(self.screen)

        self.hand_sprites.draw(self.screen)
        for group in self.ai_sprites:
            group.draw(self.screen)
        if self.selected:
            player = self.game.players[self.game.current_idx]
            cards = [sp.card for sp in self.selected if hasattr(sp, "card")]
            valid = self.game.is_valid(player, cards, self.game.current_combo)[0]
            color = (0, 255, 0) if valid else (255, 0, 0)
            for sp in self.selected:
                pygame.draw.rect(self.screen, color, sp.rect, width=3)
        if not self.game.pile:
            self.current_trick.clear()
        if self.current_trick:
            center_x, y = self._pile_center()
            card_w = self.card_width
            spacing = max(5, card_w - 25)
            total_w = card_w + (len(self.current_trick) - 1) * spacing
            start = center_x - total_w // 2 + card_w // 2
            for i, (name, img) in enumerate(self.current_trick):
                x = start + i * spacing
                rect = img.get_rect(center=(int(x), int(y)))
                self.screen.blit(img, rect)
                label = self.font.render(name, True, (255, 255, 255))
                lrect = label.get_rect(midbottom=(rect.centerx, rect.top))
                self.screen.blit(label, lrect)

        if self.state == GameState.PLAYING:
            # Enable or disable Undo based on snapshot history
            undo_btn = next((b for b in self.action_buttons if b.text == "Undo"), None)
            if undo_btn:
                undo_btn.enabled = len(self.game.snapshots) > 1
            for btn in self.action_buttons:
                btn.draw(self.screen)
            self.settings_button.draw(self.screen)

    def draw_score_overlay(self) -> None:
        """Render a scoreboard panel with last hands played."""
        line_height = getattr(self.font, "get_linesize", lambda: 20)()
        lines = [
            f"{p.name}: {len(p.hand)} ({self.win_counts.get(p.name, 0)})"
            for p in self.game.players
        ]
        last = self.game.get_last_hands()
        if any(cards for _, cards in last):
            lines.append("Last:")
            for name, cards in last:
                if cards:
                    text = " ".join(str(c) for c in cards)
                    lines.append(f"{name}: {text}")
        height = line_height * len(lines) + 10
        panel = pygame.Surface((200, height), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 150))
        y = 5
        for line in lines:
            img = self.font.render(line, True, (255, 255, 255))
            panel.blit(img, (5, y))
            y += line_height
        rect = panel.get_rect(topleft=(10, 10))
        self.screen.blit(panel, rect.topleft)

    def run(self):
        self.update_hand_sprites()
        self._highlight_turn(self.game.current_idx)
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.on_resize(event.w, event.h)
                elif self._dispatch_overlay_event(event):
                    continue
                else:
                    self._dispatch_game_event(event)

            self._draw_frame()
            self.clock.tick(30)
        pygame.quit()


def main() -> None:
    GameView().run()


if __name__ == "__main__":
    main()
