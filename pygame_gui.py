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

    def draw_shadow(self, surface: pygame.Surface, offset: Tuple[int, int] = (5, 5),
                     blur: int = 2, alpha: int = 80) -> None:
        """Draw a simple blurred shadow beneath the card."""
        shadow = pygame.Surface(self.image.get_size(), pygame.SRCALPHA)
        shadow.fill((0, 0, 0))
        shadow.set_alpha(alpha)
        for dx in range(-blur, blur + 1):
            for dy in range(-blur, blur + 1):
                rect = self.rect.move(offset[0] + dx, offset[1] + dy)
                surface.blit(shadow, rect)


class CardBackSprite(pygame.sprite.Sprite):
    def __init__(self, pos: Tuple[int, int], width: int = 80, name: str = "card_back") -> None:
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

    def __init__(self, text: str, rect: pygame.Rect, callback: Callable[[], None],
                 font: pygame.font.Font, enabled: bool = True) -> None:
        self.text = text
        self.rect = rect
        self.callback = callback
        self.font = font
        self.enabled = enabled

    def draw(self, surface: pygame.Surface) -> None:
        color = (200, 200, 200) if self.enabled else (150, 150, 150)
        text_color = (0, 0, 0) if self.enabled else (100, 100, 100)
        pygame.draw.rect(surface, color, self.rect)
        pygame.draw.rect(surface, (0, 0, 0), self.rect, 2)
        txt = self.font.render(self.text, True, text_color)
        surface.blit(txt, txt.get_rect(center=self.rect.center))

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.enabled and event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos):
            self.callback()


class Overlay:
    """Base overlay class managing a list of buttons."""

    def __init__(self) -> None:
        self.buttons: List[Button] = []

    def draw(self, surface: pygame.Surface) -> None:
        for btn in self.buttons:
            btn.draw(surface)

    def handle_event(self, event: pygame.event.Event) -> None:
        for btn in self.buttons:
            btn.handle_event(event)


class MenuOverlay(Overlay):
    def __init__(self, view: 'GameView') -> None:
        super().__init__()
        w, h = view.screen.get_size()
        font = view.font
        bx = w // 2 - 100
        by = h // 2 - 70
        self.buttons = [
            Button('New Game', pygame.Rect(bx, by, 200, 40), view.restart_game, font),
            Button('Settings', pygame.Rect(bx, by + 50, 200, 40), view.show_settings, font),
            Button('Quit', pygame.Rect(bx, by + 100, 200, 40), view.quit_game, font),
        ]


class SettingsOverlay(Overlay):
    """Top level settings menu."""

    def __init__(self, view: 'GameView') -> None:
        super().__init__()
        w, h = view.screen.get_size()
        font = view.font
        bx = w // 2 - 120
        by = h // 2 - 180
        self.buttons = [
            Button('Return to Main Menu', pygame.Rect(bx, by, 240, 40), view.show_menu, font),
            Button('Save Game', pygame.Rect(bx, by + 50, 240, 40), view.save_game, font),
            Button('Load Game', pygame.Rect(bx, by + 100, 240, 40), view.load_game, font),
            Button('Quit Game', pygame.Rect(bx, by + 150, 240, 40), view.quit_game, font),
            Button('Graphics Settings', pygame.Rect(bx, by + 200, 240, 40), view.show_options, font),
            Button('Audio Settings', pygame.Rect(bx, by + 250, 240, 40), view.show_options, font),
            Button('Gameplay Settings', pygame.Rect(bx, by + 300, 240, 40), view.show_gameplay_settings, font),
        ]


class OptionsOverlay(Overlay):
    def __init__(self, view: 'GameView') -> None:
        super().__init__()
        w, h = view.screen.get_size()
        font = view.font
        bx = w // 2 - 120
        by = h // 2 - 220

        def cycle(attr: str, options: List, label: str) -> Callable[[], None]:
            def callback(b: Button) -> Callable[[], None]:
                def inner() -> None:
                    cur = getattr(view, attr)
                    idx = options.index(cur)
                    cur = options[(idx + 1) % len(options)]
                    setattr(view, attr, cur)
                    view.apply_options()
                    b.text = f"{label}: {cur if not isinstance(cur, bool) else ('On' if cur else 'Off')}"
                return inner
            return callback

        def make_button(offset: int, attr: str, opts: List, label: str) -> None:
            text = getattr(view, attr)
            if isinstance(text, bool):
                text = 'On' if text else 'Off'
            btn = Button(f"{label}: {text}", pygame.Rect(bx, by + offset, 240, 40), lambda: None, font)
            btn.callback = cycle(attr, opts, label)(btn)
            self.buttons.append(btn)

        make_button(0, 'ai_level', ['Easy', 'Normal', 'Hard'], 'AI Level')
        make_button(50, 'ai_personality', ['balanced', 'aggressive', 'defensive', 'random'], 'Personality')
        make_button(100, 'ai_lookahead', [False, True], 'Lookahead')
        make_button(150, 'animation_speed', [0.5, 1.0, 2.0], 'Anim Speed')
        make_button(200, 'sort_mode', ['rank', 'suit'], 'Sort Mode')
        make_button(250, 'sound_enabled', [True, False], 'Sound')
        make_button(300, 'music_enabled', [True, False], 'Music')
        btn = Button('Close', pygame.Rect(bx, by + 350, 240, 40), view.close_overlay, font)
        self.buttons.append(btn)


class GameplaySettingsOverlay(Overlay):
    """Gameplay specific settings."""

    def __init__(self, view: 'GameView') -> None:
        super().__init__()
        self.view = view
        w, h = view.screen.get_size()
        font = view.font
        bx = w // 2 - 120
        by = h // 2 - 90

        def toggle(attr: str, label: str) -> Callable[[], None]:
            def callback(btn: Button) -> Callable[[], None]:
                def inner() -> None:
                    val = not getattr(view, attr)
                    setattr(view, attr, val)
                    if attr == 'house_rules':
                        import tien_len_full as tl
                        tl.ALLOW_2_IN_SEQUENCE = not val
                    btn.text = f"{label}: {'On' if val else 'Off'}"
                return inner
            return callback

        def make_toggle(offset: int, attr: str, label: str) -> None:
            val = getattr(view, attr)
            btn = Button(f"{label}: {'On' if val else 'Off'}", pygame.Rect(bx, by + offset, 240, 40), lambda: None, font)
            btn.callback = toggle(attr, label)(btn)
            self.buttons.append(btn)

        make_toggle(0, 'house_rules', 'House Rules')
        make_toggle(50, 'tutorial_mode', 'Tutorial Mode')
        make_toggle(100, 'show_rules', 'Show Rules')
        back = Button('Back', pygame.Rect(bx, by + 150, 240, 40), view.show_settings, font)
        self.buttons.append(back)

    def draw(self, surface: pygame.Surface) -> None:
        super().draw(surface)
        if self.view.show_rules:
            w, h = surface.get_size()
            font = pygame.font.SysFont(None, 20)
            rules = [
                'Sequences must share a suit.',
                'Pairs, triples and bombs match ranks.',
                '2 cannot be used in sequences when house rules enabled.',
            ]
            y = h // 2 + 80
            for line in rules:
                img = font.render(line, True, (255, 255, 255))
                surface.blit(img, img.get_rect(center=(w // 2, y)))
                y += 24


class GameOverOverlay(Overlay):
    def __init__(self, view: 'GameView', winner: str) -> None:
        super().__init__()
        self.winner = winner
        self.rankings = view.game.get_rankings()
        w, h = view.screen.get_size()
        font = view.font
        bx = w // 2 - 100
        by = h // 2 + 40
        self.buttons = [
            Button('Play Again', pygame.Rect(bx, by, 200, 40), view.restart_game, font),
            Button('Quit', pygame.Rect(bx, by + 50, 200, 40), view.quit_game, font),
        ]

    def draw(self, surface: pygame.Surface) -> None:
        w, h = surface.get_size()
        font = pygame.font.SysFont(None, 32)
        txt = font.render(f'{self.winner} wins!', True, (255, 255, 255))
        surface.blit(txt, txt.get_rect(center=(w // 2, h // 2 - 60)))
        rank_lines = [f'{i+1}. {n} ({c})' for i, (n, c) in enumerate(self.rankings)]
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
        self.font = pygame.font.SysFont(None, 24)
        load_card_images(self.card_width)
        self.table_image: Optional[pygame.Surface] = None
        img_path = Path(__file__).with_name("assets") / "table_img.png"
        if img_path.exists():
            try:
                self.table_image = pygame.image.load(str(img_path)).convert()
            except Exception:
                self.table_image = None
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
        self.ai_sprites: List[pygame.sprite.Group] = [pygame.sprite.Group() for _ in range(3)]
        self.running = True
        self.overlay: Optional[Overlay] = None
        self.state: GameState = GameState.PLAYING
        self.ai_level = 'Normal'
        self.ai_personality = 'balanced'
        self.ai_lookahead = False
        self.sort_mode = 'rank'
        self.player_name = 'Player'
        self.card_back_name = 'card_back'
        self.table_color_name = 'darkgreen'
        self.table_color = TABLE_THEMES[self.table_color_name]
        self.sound_enabled = True
        self.music_enabled = True
        self.volume = 1.0
        self.house_rules = True
        self.tutorial_mode = False
        self.show_rules = False
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
        self.volume = opts.get("volume", self.volume)
        self.house_rules = opts.get("house_rules", self.house_rules)
        self.tutorial_mode = opts.get("tutorial_mode", self.tutorial_mode)
        self.show_rules = opts.get("show_rules", self.show_rules)
        self.apply_options()
        self.update_hand_sprites()
        self._create_action_buttons()
        self.win_counts: Dict[str, int] = {p.name: 0 for p in self.game.players}
        self.show_menu()

    # Animation helpers -------------------------------------------------
    def _draw_frame(self) -> None:
        """Redraw the game state."""
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

    def _animate_sprites(self, sprites: List[CardSprite], dest: Tuple[int, int], frames: int = 15) -> None:
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

    def _animate_bounce(self, sprites: List[CardSprite], scale: float = 1.2, frames: int = 6) -> None:
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
                    scaled = pygame.transform.smoothscale(img, (int(w * factor), int(h * factor)))
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

    def _animate_back(self, start: Tuple[int, int], dest: Tuple[int, int], frames: int = 15) -> None:
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
            rect.midtop = (x, y - spacing)
        elif idx == 1:
            rect.midbottom = (x, y + card_h + spacing)
        elif idx == 2:
            rect.midleft = (x + card_w + spacing, y)
        else:
            rect.midright = (x - spacing, y)
        frames = max(1, int(frames / self.animation_speed))
        for i in range(frames):
            self._draw_frame()
            overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
            alpha = max(0, 200 - i * 20)
            center = overlay.get_rect().center
            radius = 11 + int(3 * math.sin(math.pi * i / frames))
            if hasattr(overlay, "get_width"):
                pygame.draw.circle(overlay, (255, 255, 0, alpha), center, radius, width=3)
            self.screen.blit(overlay, rect.topleft)
            pygame.display.flip()
            pygame.event.pump()
            self.clock.tick(60)

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

    def _pile_center(self) -> Tuple[int, int]:
        w, h = self.screen.get_size()
        return w // 2, h // 2

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
        spacing = 20
        total = btn_w * 3 + spacing * 2
        start_x = w // 2 - total // 2

        # Position buttons relative to the player's hand
        _, hand_y = self._player_pos(0)
        sprites = getattr(self, 'hand_sprites', None)
        if sprites:
            card_h = sprites.sprites()[0].rect.height
        else:
            card_h = int(self.card_width * 1.4)
        hand_top_y = hand_y - card_h // 2
        control_spacing = min(40, self.card_width) // 2
        y = hand_top_y - control_spacing

        font = self.font
        self.action_buttons = [
            Button('Play', pygame.Rect(start_x, y, btn_w, 40), self.play_selected, font),
            Button('Pass', pygame.Rect(start_x + btn_w + spacing, y, btn_w, 40), self.pass_turn, font),
            Button('Undo', pygame.Rect(start_x + 2 * (btn_w + spacing), y, btn_w, 40), self.undo_move, font),
        ]

    def _position_settings_button(self) -> None:
        """Position the persistent Settings button."""
        w, _ = self.screen.get_size()
        font = self.font
        if not hasattr(self, 'settings_button'):
            self.settings_button = Button('Settings', pygame.Rect(0, 0, 100, 40), self.show_settings, font)
        self.settings_button.rect.topright = (w - 10, 10)

    # Overlay helpers -------------------------------------------------
    def show_menu(self) -> None:
        self.overlay = MenuOverlay(self)
        self.state = GameState.MENU

    def show_settings(self) -> None:
        self.overlay = SettingsOverlay(self)
        self.state = GameState.SETTINGS

    def show_options(self) -> None:
        self.overlay = OptionsOverlay(self)
        self.state = GameState.SETTINGS

    def show_gameplay_settings(self) -> None:
        self.overlay = GameplaySettingsOverlay(self)
        self.state = GameState.SETTINGS

    def save_game(self) -> None:
        try:
            with open(Path(__file__).with_name('saved_game.json'), 'w', encoding='utf-8') as f:
                f.write(self.game.to_json())
        except Exception:
            pass

    def load_game(self) -> None:
        try:
            with open(Path(__file__).with_name('saved_game.json'), 'r', encoding='utf-8') as f:
                data = f.read()
            self.game.from_json(data)
            self.update_hand_sprites()
        except Exception:
            pass

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
        self.selected.clear()
        self.apply_options()
        for p in self.game.players:
            counts.setdefault(p.name, 0)
        self.win_counts = counts
        self.close_overlay()

    # Option helpers --------------------------------------------------
    def _load_options(self) -> dict:
        try:
            with open(OPTIONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
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
            "volume": self.volume,
            "house_rules": self.house_rules,
            "tutorial_mode": self.tutorial_mode,
            "show_rules": self.show_rules,
        }
        try:
            with open(OPTIONS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception as exc:
            logger.warning("Failed to save options: %s", exc)

    def apply_options(self) -> None:
        self.table_color = TABLE_THEMES.get(self.table_color_name, TABLE_THEMES["darkgreen"])
        self.game.players[0].name = self.player_name
        self.game.players[0].sort_hand(self.sort_mode)
        self.game.set_ai_level(self.ai_level)
        self.game.set_personality(self.ai_personality)
        self.game.ai_lookahead = self.ai_lookahead
        import tien_len_full as tl
        tl.ALLOW_2_IN_SEQUENCE = not self.house_rules
        sound.set_volume(self.volume)
        sound._ENABLED = self.sound_enabled
        if _mixer_ready():
            pygame.mixer.music.set_volume(self.volume)
            if self.music_enabled:
                pygame.mixer.music.unpause()
            else:
                pygame.mixer.music.pause()
        if hasattr(self, 'hand_sprites'):
            self._create_action_buttons()

    def show_game_over(self, winner: str) -> None:
        sound.play('win')
        self.win_counts[winner] = self.win_counts.get(winner, 0) + 1
        self.overlay = GameOverOverlay(self, winner)
        self.state = GameState.GAME_OVER

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

    def toggle_fullscreen(self) -> None:
        """Toggle full-screen mode."""
        try:
            pygame.display.toggle_fullscreen()
        except Exception:
            pass
        self.fullscreen = not getattr(self, 'fullscreen', False)
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
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and \
                self.state in {GameState.MENU, GameState.SETTINGS}:
            self.close_overlay()
        elif self.overlay:
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
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': pos})
        if self._dispatch_overlay_event(event):
            return
        for btn in self.action_buttons:
            if btn.rect.collidepoint(pos):
                if btn.text == 'Undo' and len(self.game.snapshots) <= 1:
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
        event = pygame.event.Event(pygame.KEYDOWN, {'key': key})
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
        if detect_combo(cards) == 'bomb':
            sound.play('bomb')
        else:
            sound.play('click')
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
                if detect_combo(cards) == 'bomb':
                    sound.play('bomb')
                else:
                    sound.play('click')
                self._animate_back(self._player_pos(self.game.current_idx), self._pile_center())
            else:
                sound.play('pass')
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
        start_x, y = self._player_pos(0)
        card_w = self.card_width
        spacing = min(40, card_w)
        start_x -= (len(player.hand) - 1) * spacing // 2
        for i, c in enumerate(player.hand):
            sprite = CardSprite(c, (start_x + i * spacing, y), card_w)
            self.hand_sprites.add(sprite)

        self.ai_sprites = [pygame.sprite.Group() for _ in range(3)]
        for idx in range(1, 4):
            group = self.ai_sprites[idx - 1]
            opp = self.game.players[idx]
            x, y = self._player_pos(idx)
            if idx == 1:
                start = x - (len(opp.hand) - 1) * spacing // 2
                for i in range(len(opp.hand)):
                    sp = CardBackSprite((start + i * spacing, y), card_w, self.card_back_name)
                    group.add(sp)
            else:
                start = y - (len(opp.hand) - 1) * spacing // 2
                for i in range(len(opp.hand)):
                    sp = CardBackSprite((x, start + i * spacing), card_w, self.card_back_name)
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
                rect = img.get_rect(midtop=(x, y - spacing))
            elif idx == 1:
                rect = img.get_rect(midbottom=(x, y + card_h + spacing))
            elif idx == 2:
                rect = img.get_rect(midleft=(x + card_w + spacing, y))
            else:
                rect = img.get_rect(midright=(x - spacing, y))
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
            cards = [sp.card for sp in self.selected if hasattr(sp, 'card')]
            valid = self.game.is_valid(player, cards, self.game.current_combo)[0]
            color = (0, 255, 0) if valid else (255, 0, 0)
            for sp in self.selected:
                pygame.draw.rect(self.screen, color, sp.rect, width=3)
        if not self.game.pile:
            self.current_trick.clear()
        if self.current_trick:
            center = self._pile_center()
            radius = self.card_width * 1.5
            total = len(self.current_trick)
            for i, (name, img) in enumerate(self.current_trick):
                angle = math.tau * i / total - math.pi / 2
                x = center[0] + radius * math.cos(angle)
                y = center[1] + radius * math.sin(angle)
                rect = img.get_rect(center=(int(x), int(y)))
                self.screen.blit(img, rect)
                label = self.font.render(name, True, (255, 255, 255))
                lrect = label.get_rect(center=(int(x), int(y - self.card_width)))
                self.screen.blit(label, lrect)

        if self.state == GameState.PLAYING:
            # Enable or disable Undo based on snapshot history
            undo_btn = next((b for b in self.action_buttons if b.text == 'Undo'), None)
            if undo_btn:
                undo_btn.enabled = len(self.game.snapshots) > 1
            for btn in self.action_buttons:
                btn.draw(self.screen)
            self.settings_button.draw(self.screen)

    def draw_score_overlay(self) -> None:
        """Render a scoreboard panel with last hands played."""
        size = self.screen.get_size()
        if isinstance(size, (list, tuple)) and len(size) >= 2:
            w = size[0]
        else:
            w = 0
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
        rect = panel.get_rect(topright=(w - 10, 10))
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
