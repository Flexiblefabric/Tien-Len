"""Minimal Pygame interface for the Tiến Lên card game."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple, List, Callable, Optional
from enum import Enum, auto
import json

import pygame

from tien_len_full import Game, Card, detect_combo
import sound


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
    def __init__(self, view: 'GameView') -> None:
        super().__init__()
        w, h = view.screen.get_size()
        font = view.font
        bx = w // 2 - 120
        by = h // 2 - 220

        def cycle(attr: str, options: List, label: str) -> Callable[[], None]:
            btn: Button
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
        self.action_buttons: List[Button] = []
        self._create_action_buttons()
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
        self.apply_options()
        self._create_action_buttons()
        self.show_menu()

    # Animation helpers -------------------------------------------------
    def _draw_frame(self) -> None:
        """Redraw the game state."""
        self.screen.fill(self.table_color)
        self.draw_players()
        if self.overlay:
            overlay_surf = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
            overlay_surf.fill((0, 0, 0, 180))
            self.screen.blit(overlay_surf, (0, 0))
            self.overlay.draw(self.screen)
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

    def _animate_select(self, sprite: CardSprite, up: bool) -> None:
        offset = -10 if up else 10
        dest = (sprite.rect.centerx, sprite.rect.centery + offset)
        self._animate_sprites([sprite], dest, frames=5)

    def _highlight_turn(self, idx: int, frames: int = 10) -> None:
        """Flash the active player's name for visual emphasis."""
        x, y = self._player_pos(idx)
        rect = pygame.Rect(0, 0, 140, 30)
        rect.center = (x, y - 40)
        frames = max(1, int(frames / self.animation_speed))
        for i in range(frames):
            self._draw_frame()
            overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
            alpha = max(0, 200 - i * 20)
            overlay.fill((255, 255, 0, alpha))
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

    def _create_action_buttons(self) -> None:
        """Create or reposition the Play/Pass/Undo buttons."""
        center_x, pile_y = self._pile_center()
        _, hand_y = self._player_pos(0)
        mid_y = (pile_y + hand_y) // 2
        bx = center_x - 60
        by = mid_y - 60
        font = self.font
        self.action_buttons = [
            Button('Play', pygame.Rect(bx, by, 120, 40), self.play_selected, font),
            Button('Pass', pygame.Rect(bx, by + 50, 120, 40), self.pass_turn, font),
            Button('Undo', pygame.Rect(bx, by + 100, 120, 40), self.undo_move, font),
        ]

    # Overlay helpers -------------------------------------------------
    def show_menu(self) -> None:
        self.overlay = MenuOverlay(self)
        self.state = GameState.MENU

    def show_settings(self) -> None:
        self.overlay = SettingsOverlay(self)
        self.state = GameState.SETTINGS

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
        self.game = Game()
        self.game.setup()
        self.selected.clear()
        self.apply_options()
        self.close_overlay()

    # Option helpers --------------------------------------------------
    def _load_options(self) -> dict:
        try:
            with open(OPTIONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
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
        }
        try:
            with open(OPTIONS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception:
            pass

    def apply_options(self) -> None:
        self.table_color = TABLE_THEMES.get(self.table_color_name, TABLE_THEMES["darkgreen"])
        self.game.players[0].name = self.player_name
        self.game.players[0].sort_hand(self.sort_mode)
        self.game.set_ai_level(self.ai_level)
        self.game.set_personality(self.ai_personality)
        self.game.ai_lookahead = self.ai_lookahead
        sound.set_volume(self.volume)
        sound._ENABLED = self.sound_enabled
        if _mixer_ready():
            pygame.mixer.music.set_volume(self.volume)
            if self.music_enabled:
                pygame.mixer.music.unpause()
            else:
                pygame.mixer.music.pause()

    def show_game_over(self, winner: str) -> None:
        sound.play('win')
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
        self.update_hand_sprites()
        self._create_action_buttons()

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
        self.update_hand_sprites()
        self._create_action_buttons()

    # Event handling --------------------------------------------------
    def handle_mouse(self, pos):
        if self.state != GameState.PLAYING:
            if self.overlay:
                event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': pos})
                self.overlay.handle_event(event)
            return
        for btn in self.action_buttons:
            if btn.rect.collidepoint(pos):
                if btn.text == 'Undo' and len(self.game.snapshots) <= 1:
                    return
                btn.callback()
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
                return

    def handle_key(self, key):
        if self.state != GameState.PLAYING:
            if key == pygame.K_ESCAPE and self.state in {GameState.MENU, GameState.SETTINGS}:
                self.close_overlay()
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
            print(f"Invalid: {msg}")
            return
        if self.game.process_play(player, cards):
            self.show_game_over(player.name)
            return
        if detect_combo(cards) == 'bomb':
            sound.play('bomb')
        else:
            sound.play('click')
        self._animate_sprites(self.selected, self._pile_center())
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

    def draw_players(self):
        for idx, p in enumerate(self.game.players):
            x, y = self._player_pos(idx)
            txt = f"{p.name} ({len(p.hand)})"
            color = (255, 255, 0) if idx == self.game.current_idx else (255, 255, 255)
            img = self.font.render(txt, True, color)
            rect = img.get_rect(center=(x, y - 40))
            self.screen.blit(img, rect)

        self.hand_sprites.draw(self.screen)
        for group in self.ai_sprites:
            group.draw(self.screen)
        if self.game.pile:
            pl, cards = self.game.pile[-1]
            center = self._pile_center()
            spacing = min(40, self.card_width)
            start_x = center[0] - (len(cards) - 1) * spacing // 2
            for i, c in enumerate(cards):
                img = get_card_image(c, self.card_width)
                if img is None:
                    font = pygame.font.SysFont(None, 20)
                    img = font.render(str(c), True, (255, 255, 255), (0, 0, 0))
                rect = img.get_rect(center=(start_x + i * spacing, center[1]))
                self.screen.blit(img, rect)
            label = self.font.render(pl.name, True, (255, 255, 255))
            lrect = label.get_rect(center=(center[0], center[1] - self.card_width))
            self.screen.blit(label, lrect)

        if self.state == GameState.PLAYING:
            # Enable or disable Undo based on snapshot history
            undo_btn = next((b for b in self.action_buttons if b.text == 'Undo'), None)
            if undo_btn:
                undo_btn.enabled = len(self.game.snapshots) > 1
            for btn in self.action_buttons:
                btn.draw(self.screen)

    def run(self):
        self.update_hand_sprites()
        self._highlight_turn(self.game.current_idx)
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.on_resize(event.w, event.h)
                elif self.state == GameState.PLAYING:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        self.handle_mouse(event.pos)
                    elif event.type == pygame.KEYDOWN:
                        self.handle_key(event.key)
                else:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        self.handle_mouse(event.pos)
                    elif event.type == pygame.KEYDOWN:
                        self.handle_key(event.key)

            self._draw_frame()
            self.clock.tick(30)
        pygame.quit()


def main() -> None:
    GameView().run()


if __name__ == "__main__":
    main()
