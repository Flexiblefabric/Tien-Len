from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Dict, Tuple, List, Optional
import gc
import tracemalloc

import pygame
import types

from tien_len_full import Game, detect_combo, Player
import sound

from .helpers import (
    TABLE_THEMES,
    PLAYER_COLORS,
    HAND_SPACING,
    LABEL_PAD,
    BUTTON_HEIGHT,
    ZONE_GUTTER,
    ASSETS_DIR,
    SAVE_FILE,
    ZONE_BG,
    ZONE_HIGHLIGHT,
    GameState,
    calc_start_and_overlap,
    calc_hand_layout,
    horizontal_margin,
    bottom_margin,
    list_music_tracks,
    list_table_textures,
    CardSprite,
    CardBackSprite,
    draw_surface_shadow,
    draw_glow,
    draw_tiled,
    load_button_images,
    get_font,
)
from .overlays import (
    Button,
    Overlay,
    MainMenuOverlay,
    InGameMenuOverlay,
    SettingsOverlay,
    GameSettingsOverlay,
    GraphicsOverlay,
    AudioOverlay,
    RulesOverlay,
    HowToPlayOverlay,
    TutorialOverlay,
    SavePromptOverlay,
    ProfileOverlay,
    GameOverOverlay,
)
from .animations import AnimationMixin
from .anim_manager import AnimationManager
from .hud import HUDPanel, HUDMixin
from .overlay_manager import OverlayMixin

logger = logging.getLogger(__name__)


class GameView(AnimationMixin, HUDMixin, OverlayMixin):
    TABLE_COLOR = TABLE_THEMES["darkgreen"]

    def __init__(self, width: int = 1024, height: int = 768) -> None:
        pygame.init()
        pygame.font.init()
        pygame.display.set_caption("Tiến Lên - Pygame")
        self.window_width = width
        self.window_height = height
        flags = pygame.RESIZABLE | pygame.DOUBLEBUF
        self.screen = pygame.display.set_mode((width, height), flags)
        self.fullscreen = False
        self.card_width = self._calc_card_width(width)
        self.clock = pygame.time.Clock()
        self.dt = 1 / 60  # default frame time for tests
        self.fps_limit = 60
        self.animation_speed = 1.0
        self.animations: list = []
        self.anim_managers: Dict[pygame.sprite.Sprite, AnimationManager] = {}
        self.game = Game()
        self.game.setup()
        self._attach_reset_pile()
        self.font = get_font(self._get_font_size())
        self.avatars: Dict[str, pygame.Surface] = {}
        import tienlen_gui

        tienlen_gui.load_card_images(self.card_width)
        self.table_texture_name = list_table_textures()[0] if list_table_textures() else ""
        self.table_image: Optional[pygame.Surface] = None
        tex_path = ASSETS_DIR / "tables" / f"{self.table_texture_name}.png"
        if tex_path.exists():
            try:
                self.table_image = pygame.image.load(str(tex_path)).convert()
            except Exception:
                self.table_image = None
        self.main_menu_image: Optional[pygame.Surface] = None
        menu_path = ASSETS_DIR / "imgs" / "main_menu.png"
        if menu_path.exists():
            try:
                self.main_menu_image = pygame.image.load(str(menu_path)).convert()
            except Exception:
                self.main_menu_image = None

        # Shared background for score panel and overlays
        bg_path = ASSETS_DIR / "imgs" / "menu_background.png"
        try:
            self.menu_background = pygame.image.load(str(bg_path)).convert_alpha()
        except Exception:
            self.menu_background = None
        tile_path = ASSETS_DIR / "imgs" / "panel_tile.png"
        try:
            self.panel_tile = pygame.image.load(str(tile_path)).convert()
        except Exception:
            self.panel_tile = None
        self._table_surface: Optional[pygame.Surface] = None
        self._update_table_surface()
        self._background_needs_redraw = True
        self._layout_zones()
        self._load_avatars()
        self._create_huds()
        # Shared panel background for HUD and overlays
        self.panel_image = self.menu_background
        # Load sound effects and background music
        sdir = ASSETS_DIR / "sound"
        sound.load("click", sdir / "card-play.wav")
        sound.load("pass", sdir / "pass.wav")
        sound.load("bomb", sdir / "bomb.wav")
        sound.load("shuffle", sdir / "shuffle.wav")
        sound.load("win", sdir / "win.wav")
        self.music_track = list_music_tracks()[0] if list_music_tracks() else ""
        import tienlen_gui

        if tienlen_gui._mixer_ready() and self.music_track:
            music = ASSETS_DIR / "music" / self.music_track
            try:
                pygame.mixer.music.load(str(music))
                pygame.mixer.music.play(-1)
            except Exception:
                pass
        self.selected: List[CardSprite] = []
        self.current_trick: list[tuple[str, pygame.Surface]] = []
        self.ai_sprites: List[pygame.sprite.LayeredUpdates] = [
            pygame.sprite.LayeredUpdates() for _ in range(3)
        ]
        self.running = True
        self.overlay: Optional[Overlay] = None
        self.state: GameState = GameState.PLAYING
        self.ai_level = "Normal"
        self.ai_personality = "balanced"
        self.ai_lookahead = False
        self.ai_depth = 1
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
        self.rule_flip_suit_rank = False
        self.rule_no_2s = True
        self.score_visible = True
        self.developer_mode = False
        self.ai_debug_info: Dict[int, tuple[str, Optional[float]]] = {}
        self.score_pos: Tuple[int, int] = (10, 10)
        self.score_rect = pygame.Rect(self.score_pos, (0, 0))
        self.scoreboard_rect = pygame.Rect(0, 0, 0, 0)
        self.log_rect = pygame.Rect(0, 0, 0, 0)
        self.action_buttons: List[Button] = []
        self._create_action_buttons()
        self.settings_button: Button
        self._position_settings_button()
        self.score_button: Button
        self._position_score_button()
        opts = self._load_options()
        self.animation_speed = opts.get("animation_speed", self.animation_speed)
        self.table_color_name = opts.get("table_color", self.table_color_name)
        self.card_back_name = opts.get("card_back", self.card_back_name)
        self.table_texture_name = opts.get("table_texture", self.table_texture_name)
        self.music_track = opts.get("music_track", self.music_track)
        self.sort_mode = opts.get("sort_mode", self.sort_mode)
        self.player_name = opts.get("player_name", self.player_name)
        self.ai_level = opts.get("ai_level", self.ai_level)
        self.ai_personality = opts.get("ai_personality", self.ai_personality)
        self.ai_lookahead = opts.get("ai_lookahead", self.ai_lookahead)
        self.ai_depth = opts.get("ai_depth", self.ai_depth)
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
        self.rule_flip_suit_rank = opts.get(
            "rule_flip_suit_rank", self.rule_flip_suit_rank
        )
        self.rule_no_2s = opts.get("rule_no_2s", self.rule_no_2s)
        self.developer_mode = opts.get("developer_mode", self.developer_mode)
        self.score_visible = opts.get("score_visible", self.score_visible)
        self.score_pos = tuple(opts.get("score_pos", list(self.score_pos)))
        win_data = opts.get("win_counts", {})
        self.win_counts: Dict[str, int] = {
            p.name: int(win_data.get(p.name, 0)) for p in self.game.players
        }
        self.fps_limit = int(opts.get("fps_limit", self.fps_limit))
        if opts.get("fullscreen", False):
            self.toggle_fullscreen()
        self.apply_options()
        self.update_hand_sprites()
        self._start_animation(self._animate_deal())
        self._create_action_buttons()
        self.show_menu()

    # Animation helpers -------------------------------------------------
    def _draw_frame(self, flip: bool = True) -> List[pygame.Rect]:
        """Redraw the game state and return dirty rectangles.

        Parameters
        ----------
        flip:
            If ``True`` (default), ``pygame.display.update`` is called with all
            dirty rectangles after drawing. Animation helpers can pass ``False``
            to defer updating until additional elements are drawn.
        """
        dirty: List[pygame.Rect] = []
        if self.state == GameState.MENU and self.main_menu_image:
            bg = pygame.transform.smoothscale(
                self.main_menu_image, self.screen.get_size()
            )
            dirty.append(self.screen.blit(bg, (0, 0)))
        else:
            if self._background_needs_redraw:
                if self._table_surface:
                    dirty.append(self.screen.blit(self._table_surface, (0, 0)))
                else:
                    self.screen.fill(self.table_color)
                    dirty.append(self.screen.get_rect())
                self._background_needs_redraw = False

            w, h = self.screen.get_size()
            card_h = int(self.card_width * 1.4)
            top_h = int(self.card_width * 1.2)
            bottom_top = self.hand_y - card_h // 2 - LABEL_PAD
            side_w = self.settings_button.rect.width + LABEL_PAD * 2

            top_rect = pygame.Rect(0, 0, w, top_h)
            bottom_rect = pygame.Rect(0, bottom_top, w, h - bottom_top)
            side_rect = pygame.Rect(w - side_w, 0, side_w, top_h)

            if self.panel_tile:
                draw_tiled(self.screen, self.panel_tile, top_rect)
                draw_tiled(self.screen, self.panel_tile, bottom_rect)
                draw_tiled(self.screen, self.panel_tile, side_rect)
            else:
                pygame.draw.rect(self.screen, (0, 0, 0, 150), top_rect)
                pygame.draw.rect(self.screen, (0, 0, 0, 150), bottom_rect)
                pygame.draw.rect(self.screen, (0, 0, 0, 150), side_rect)
            dirty.extend([top_rect, bottom_rect, side_rect])

            dirty.extend(self.draw_players())
            if self.state == GameState.PLAYING:
                dirty.append(self.draw_scoreboard())
                dirty.append(self.draw_game_log())
        if self.overlay:
            overlay_surf = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
            overlay_surf.fill((0, 0, 0, 180))
            dirty.append(self.screen.blit(overlay_surf, (0, 0)))
            self.overlay.draw(self.screen)
            dirty.append(self.screen.get_rect())
        dirty.append(self.draw_score_overlay())
        if flip:
            pygame.display.update(dirty)
        return dirty

    def _start_animation(self, anim):
        """Prime and store ``anim`` to run during the main loop."""
        if anim is None:
            return
        try:
            next(anim)
        except StopIteration:
            return
        self.animations.append(anim)

    def _manager_for(self, sprite: pygame.sprite.Sprite) -> AnimationManager:
        manager = self.anim_managers.get(sprite)
        if manager is None:
            manager = AnimationManager(sprite)
            self.anim_managers[sprite] = manager
        return manager

    # Layout helpers --------------------------------------------------
    def _layout_zones(self) -> None:
        """Update stored vertical positions for hand, pile, and buttons."""
        card_h = int(self.card_width * 1.4)
        _, h = self.screen.get_size()
        margin = bottom_margin(self.card_width)
        self.hand_y = h - margin - card_h // 2
        self.pile_y = self.hand_y - card_h - ZONE_GUTTER
        self.button_y = self.hand_y + card_h // 2 + ZONE_GUTTER
        max_y = h - HAND_SPACING - BUTTON_HEIGHT
        if self.button_y > max_y:
            self.button_y = max_y

    def _player_pos(self, idx: int) -> Tuple[int, int]:
        """Return the centre position for player ``idx`` based on screen size."""
        w, h = self.screen.get_size()
        card_w = self.card_width
        card_h = int(self.card_width * 1.4)
        margin = bottom_margin(card_w)
        bottom_y = self.hand_y
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
        return w // 2, self.pile_y

    def _player_zone_rect(self, idx: int) -> pygame.Rect:
        """Return a rect covering the on-screen zone for player ``idx``."""
        if idx == 0:
            sprites = self.hand_sprites.sprites()
        else:
            if idx - 1 < len(self.ai_sprites):
                sprites = self.ai_sprites[idx - 1].sprites()
            else:
                sprites = []
        if not sprites:
            return pygame.Rect(0, 0, 0, 0)
        left = min(sp.rect.left for sp in sprites)
        top = min(sp.rect.top for sp in sprites)
        right = max(sp.rect.right for sp in sprites)
        bottom = max(sp.rect.bottom for sp in sprites)
        return pygame.Rect(left, top, right - left, bottom - top)


    def _calc_card_width(self, win_width: int) -> int:
        """Determine card width based on window width."""
        return max(30, win_width // 13)

    def _get_font_size(self) -> int:
        """Return a font size scaled to the current window size."""
        scale = min(self.window_width, self.window_height) // 20
        return max(12, scale)

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
        self._background_needs_redraw = True

    def _create_action_buttons(self) -> None:
        """Create or reposition the Play/Pass/Undo buttons."""
        w, h = self.screen.get_size()
        btn_w = 120
        spacing = max(10, self.card_width // 2)
        total = btn_w * 3 + spacing * 2
        start_x = w // 2 - total // 2

        y = self.button_y
        max_y = h - HAND_SPACING - BUTTON_HEIGHT
        if y > max_y:
            y = max_y

        font = self.font
        play_imgs = load_button_images("button_play")
        pass_imgs = load_button_images("button_pass")
        undo_imgs = load_button_images("button_undo")
        self.action_buttons = [
            Button(
                "Play",
                pygame.Rect(start_x, y, btn_w, BUTTON_HEIGHT),
                self.play_selected,
                font,
                **play_imgs,
            ),
            Button(
                "Pass",
                pygame.Rect(start_x + btn_w + spacing, y, btn_w, BUTTON_HEIGHT),
                self.pass_turn,
                font,
                **pass_imgs,
            ),
            Button(
                "Undo",
                pygame.Rect(start_x + 2 * (btn_w + spacing), y, btn_w, BUTTON_HEIGHT),
                self.undo_move,
                font,
                **undo_imgs,
            ),
        ]

    def _position_settings_button(self) -> None:
        """Position the persistent Settings button."""
        w, _ = self.screen.get_size()
        font = self.font
        if not hasattr(self, "settings_button"):
            imgs = load_button_images("button_settings")
            self.settings_button = Button(
                "Settings",
                pygame.Rect(0, 0, 100, 40),
                self.show_in_game_menu,
                font,
                **imgs,
            )
        else:
            self.settings_button.callback = self.show_in_game_menu
        margin = min(60, max(40, self.card_width // 3))
        self.settings_button.rect.topright = (w - margin, margin)

    def _position_score_button(self) -> None:
        """Create/position the scoreboard toggle button."""
        font = self.font
        if not hasattr(self, "score_button"):
            self.score_button = Button(
                "S", pygame.Rect(0, 0, 30, 30), self.toggle_score, font
            )
        else:
            self.score_button.callback = self.toggle_score
        self.score_button.rect.topleft = (5, 5)

    def _clamp_score_pos(self) -> None:
        """Ensure the score panel stays within the window bounds."""
        w, h = self.screen.get_size()
        max_x = max(0, w - self.score_rect.width)
        max_y = max(0, h - self.score_rect.height)
        x = min(max(self.score_pos[0], 0), max_x)
        y = min(max(self.score_pos[1], 0), max_y)
        self.score_pos = (x, y)
        self.score_rect.topleft = self.score_pos

    def toggle_score(self) -> None:
        """Toggle visibility of the score panel and save."""
        self.score_visible = not self.score_visible
        self._save_options()



    def save_game(self) -> None:
        try:
            SAVE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(SAVE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.game.to_dict(), f, indent=2)
        except OSError as exc:
            logger.warning("Failed to save game: %s", exc)

    def load_game(self) -> None:
        try:
            path = SAVE_FILE
            if not path.exists():
                legacy = Path(__file__).with_name("saved_game.json")
                if legacy.exists():
                    path.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        legacy.replace(path)
                    except OSError:
                        path = legacy
            with open(path, "r", encoding="utf-8") as f:
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
        self.game = Game()
        self.game.setup()
        self._attach_reset_pile()
        self.reset_scores()
        self.reset_current_trick()
        self.selected.clear()
        self.current_trick.clear()
        self.apply_options()
        self.update_hand_sprites()
        self._start_animation(self._animate_deal())
        self.close_overlay()

    def reset_scores(self) -> None:
        """Reset player win counts."""
        self.win_counts = {p.name: 0 for p in self.game.players}

    def reset_current_trick(self, animate: bool = True) -> None:
        """Clear the list of cards representing the current trick."""
        if animate and self.current_trick:
            self._start_animation(self._animate_trick_clear())
        self.current_trick.clear()

    def _attach_reset_pile(self) -> None:
        """Wrap the game's ``reset_pile`` method to fade out the trick."""

        original = self.game.reset_pile

        def wrapped_reset_pile(*args, **kwargs):
            to_fade: list[types.SimpleNamespace] = []
            if self.current_trick:
                w, _ = self.screen.get_size()
                card_w = self.card_width
                start_rel, overlap = calc_start_and_overlap(
                    w, len(self.current_trick), card_w, 25, card_w - 5
                )
                spacing = card_w - overlap
                start = start_rel + card_w // 2
                for i, (_, img) in enumerate(self.current_trick):
                    x = start + i * spacing
                    rect = img.get_rect(center=(int(x), int(self.pile_y)))
                    to_fade.append(types.SimpleNamespace(image=img.copy(), rect=rect))
            original(*args, **kwargs)
            if to_fade:
                def seq():
                    yield from self._animate_fade_out(to_fade)
                    yield from self._animate_trick_clear()
                    self.reset_current_trick(animate=False)

                self._start_animation(seq())
            else:
                self.reset_current_trick()

        self.game.reset_pile = wrapped_reset_pile

    # Option helpers --------------------------------------------------
    def _load_options(self) -> dict:
        try:
            import tienlen_gui
            path = tienlen_gui.OPTIONS_FILE
            default_path = Path.home() / ".tien_len" / "options.json"
            if os.getenv("PYTEST_CURRENT_TEST") and path == default_path and not path.exists():
                return {}
            if not path.exists():
                legacy = Path(__file__).with_name("options.json")
                if legacy.exists():
                    path.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        legacy.replace(path)
                    except OSError:
                        path = legacy
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "show_rules" in data and "show_rules_option" not in data:
                data["show_rules_option"] = data["show_rules"]
            if "win_counts" in data and isinstance(data["win_counts"], dict):
                data["win_counts"] = {
                    str(k): int(v) for k, v in data["win_counts"].items()
                }
            if "fps_limit" in data:
                try:
                    data["fps_limit"] = int(data["fps_limit"])
                except (TypeError, ValueError):
                    data["fps_limit"] = 60
            return data
        except Exception as exc:
            logger.warning("Failed to load options: %s", exc)
            return {}

    def _save_options(self) -> None:
        import tienlen_gui
        default_path = Path.home() / ".tien_len" / "options.json"
        if os.getenv("PYTEST_CURRENT_TEST") and tienlen_gui.OPTIONS_FILE == default_path:
            return

        data = {
            "animation_speed": self.animation_speed,
            "table_color": self.table_color_name,
            "card_back": self.card_back_name,
            "table_texture": self.table_texture_name,
            "music_track": self.music_track,
            "sort_mode": self.sort_mode,
            "player_name": self.player_name,
            "ai_level": self.ai_level,
            "ai_personality": self.ai_personality,
            "ai_lookahead": self.ai_lookahead,
            "ai_depth": self.ai_depth,
            "sound": self.sound_enabled,
            "music": self.music_enabled,
            "music_volume": self.music_volume,
            "fx_volume": self.fx_volume,
            "card_color": self.card_color,
            "colorblind_mode": self.colorblind_mode,
            "house_rules": self.house_rules,
            "tutorial_mode": self.tutorial_mode,
            "show_rules_option": self.show_rules_option,
            "rule_flip_suit_rank": self.rule_flip_suit_rank,
            "rule_no_2s": self.rule_no_2s,
            "developer_mode": self.developer_mode,
            "fullscreen": self.fullscreen,
            "fps_limit": self.fps_limit,
            "score_visible": self.score_visible,
            "score_pos": list(self.score_pos),
            "win_counts": self.win_counts,
        }
        try:
            tienlen_gui.OPTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(tienlen_gui.OPTIONS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception as exc:
            logger.warning("Failed to save options: %s", exc)

    def apply_options(self) -> None:
        self.table_color = TABLE_THEMES.get(
            self.table_color_name, TABLE_THEMES["darkgreen"]
        )
        if self.card_color == "blue":
            self.card_back_name = "card_back"
        else:
            self.card_back_name = f"card_back_{self.card_color}"

        tex_path = ASSETS_DIR / "tables" / f"{self.table_texture_name}.png"
        if tex_path.exists():
            try:
                self.table_image = pygame.image.load(str(tex_path)).convert()
            except Exception:
                self.table_image = None
        else:
            self.table_image = None
        self._update_table_surface()
        self.game.players[0].name = self.player_name
        self._load_avatars()
        self._create_huds()
        self.game.players[0].sort_hand(self.sort_mode, self.game.flip_suit_rank)
        self.game.set_ai_level(self.ai_level)
        self.game.set_personality(self.ai_personality)
        self.game.ai_lookahead = self.ai_lookahead
        self.game.ai_depth = self.ai_depth
        self.game.allow_2_in_sequence = not self.rule_no_2s
        self.game.flip_suit_rank = self.rule_flip_suit_rank
        sound.set_volume(self.fx_volume)
        sound.set_enabled(self.sound_enabled)
        import tienlen_gui

        if tienlen_gui._mixer_ready():
            pygame.mixer.music.set_volume(self.music_volume)
            if self.music_enabled:
                track = ASSETS_DIR / "music" / self.music_track
                if track.exists():
                    try:
                        pygame.mixer.music.load(str(track))
                        pygame.mixer.music.play(-1)
                    except Exception:
                        pass
                pygame.mixer.music.unpause()
            else:
                pygame.mixer.music.pause()
        if hasattr(self, "hand_sprites"):
            self._create_action_buttons()


    def set_ai_level(self, level: str) -> None:
        self.ai_level = level
        self.game.set_ai_level(level)

    def on_resize(self, width: int, height: int) -> None:
        """Handle window resize by recreating sprites."""
        flags = (
            pygame.FULLSCREEN | pygame.DOUBLEBUF
            if self.fullscreen
            else pygame.RESIZABLE | pygame.DOUBLEBUF
        )
        self.window_width = width
        self.window_height = height
        self.screen = pygame.display.set_mode((width, height), flags)
        self.card_width = self._calc_card_width(width)
        import tienlen_gui

        tienlen_gui.load_card_images(self.card_width)
        self.font = get_font(self._get_font_size())
        self._update_table_surface()
        self._layout_zones()
        self.update_hand_sprites()
        self._create_huds()
        self._create_action_buttons()
        self._position_score_button()
        self._clamp_score_pos()
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
        flags = (
            pygame.FULLSCREEN | pygame.DOUBLEBUF
            if self.fullscreen
            else pygame.RESIZABLE | pygame.DOUBLEBUF
        )
        size = self.screen.get_size()
        self.window_width, self.window_height = size
        self.screen = pygame.display.set_mode(size, flags)
        self.card_width = self._calc_card_width(size[0])
        import tienlen_gui

        tienlen_gui.load_card_images(self.card_width)
        self.font = get_font(self._get_font_size())
        self._update_table_surface()
        self._layout_zones()
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
                    self._start_animation(self._animate_select(sp, up))
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
                    self._start_animation(self._animate_select(sp, up))
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
        if key == pygame.K_ESCAPE and self.state == GameState.PLAYING:
            self.show_in_game_menu()
        elif key == pygame.K_RETURN:
            self.play_selected()
        elif key == pygame.K_SPACE:
            self.pass_turn()
        elif key == pygame.K_m:
            self.show_menu()
        elif key == pygame.K_o:
            self.show_settings()
        elif key == pygame.K_F11:
            self.toggle_fullscreen()
        elif key == pygame.K_F3:
            self.developer_mode = not self.developer_mode
            self._create_huds()

    # Game actions ----------------------------------------------------
    def play_selected(self):
        if not self.selected:
            return
        cards = [sp.card for sp in self.selected]
        player = self.game.players[self.game.current_idx]
        ok, msg = self.game.is_valid(player, cards, self.game.current_combo)
        if not ok:
            self._start_animation(self._animate_shake(list(self.selected)))
            logger.info("Invalid: %s", msg)
            return
        if self.game.process_play(player, cards):
            self.show_game_over(player.name)
            return
        for c in cards:
            import tienlen_gui

            img = tienlen_gui.get_card_image(c, self.card_width)
            if img is not None:
                self.current_trick.append((player.name, img))
        if detect_combo(cards) == "bomb":
            sound.play("bomb")
            self._start_animation(self._bomb_reveal())
        else:
            sound.play("click")
        sprites = list(self.selected)
        self._start_animation(self._animate_flip(sprites, self._pile_center()))
        self._start_animation(
            self._animate_glow(sprites, PLAYER_COLORS[self.game.current_idx])
        )
        self.game.next_turn()
        self.selected.clear()
        self.update_hand_sprites()
        self._start_animation(self._highlight_turn(self.game.current_idx))
        self._start_animation(self._animate_avatar_blink(self.game.current_idx))
        self.ai_turns()

    def pass_turn(self):
        if self.game.handle_pass():
            self.running = False
        else:
            self._start_animation(self._animate_shake(list(self.selected)))
            sound.play("pass")
            self._start_animation(
                self._animate_pass_text(self.game.current_idx)
            )
            self._start_animation(self._highlight_turn(self.game.current_idx))
            self._start_animation(self._animate_avatar_blink(self.game.current_idx))
            self.ai_turns()
        if not self.game.pile:
            self.current_trick.clear()

    def undo_move(self) -> None:
        """Undo the most recent move and refresh the display."""
        before = list(self.game.pile)
        if self.game.undo_last():
            removed = before[len(self.game.pile):]
            self.selected.clear()
            self.update_hand_sprites()
            for player, cards in removed:
                idx = next(
                    (i for i, p in enumerate(self.game.players) if p.name == player.name),
                    None,
                )
                if idx is not None:
                    self._start_animation(self._animate_return(idx, len(cards)))
            self._start_animation(self._highlight_turn(self.game.current_idx))

    def ai_turns(self):
        while not self.game.players[self.game.current_idx].is_human:
            self._start_animation(
                self._animate_thinking(self.game.current_idx)
            )
            idx = self.game.current_idx
            p = self.game.players[idx]
            cards = self.game.ai_play(self.game.current_combo)
            move_type = "pass"
            score_val: Optional[float] = None
            if cards:
                move_type = detect_combo(cards, self.game.allow_2_in_sequence)
                try:
                    score_val = sum(self.game.score_move(p, cards, self.game.current_combo))
                except Exception:
                    score_val = None
            self.ai_debug_info[idx] = (move_type, score_val)
            ok, _ = self.game.is_valid(p, cards, self.game.current_combo)
            if not ok:
                cards = []
            if cards:
                if self.game.process_play(p, cards):
                    self.show_game_over(p.name)
                    break
                for c in cards:
                    import tienlen_gui
                    img = tienlen_gui.get_card_image(c, self.card_width)
                    if img is not None:
                        self.current_trick.append((p.name, img))
                if detect_combo(cards) == "bomb":
                    sound.play("bomb")
                    self._start_animation(self._bomb_reveal())
                else:
                    sound.play("click")
                dest = self._pile_center()
                start_pos = self._player_pos(self.game.current_idx)
                glow_sprites = [
                    types.SimpleNamespace(rect=img.get_rect(center=dest))
                    for _, img in self.current_trick[-len(cards):]
                ]

                def seq():
                    for _ in cards:
                        yield from self._animate_back(start_pos, dest)
                        yield from self._animate_delay(0.2)
                    yield from self._animate_glow(
                        glow_sprites, PLAYER_COLORS[self.game.current_idx]
                    )

                self._start_animation(seq())
            else:
                sound.play("pass")
                self.game.process_pass(p)
                self._start_animation(
                    self._animate_pass_text(self.game.current_idx)
                )
            self.game.next_turn()
            self._start_animation(self._highlight_turn(self.game.current_idx))
            self._start_animation(self._animate_avatar_blink(self.game.current_idx))
            if not self.game.pile:
                self.current_trick.clear()
        self.update_hand_sprites()
        self._start_animation(self._highlight_turn(self.game.current_idx))
        self._start_animation(self._animate_avatar_blink(self.game.current_idx))

    # Rendering -------------------------------------------------------
    def update_hand_sprites(self):
        """Create card sprites for all players with a simple table layout."""

        self.hand_sprites = pygame.sprite.LayeredUpdates()
        self.ai_sprites = [pygame.sprite.LayeredUpdates() for _ in range(3)]
        self.anim_managers.clear()

        card_w = self.card_width
        card_h = int(card_w * 1.4)
        screen_w, screen_h = self.screen.get_size()

        # --- Human player at the bottom ---------------------------------
        player = self.game.players[0]
        start_x, spacing = calc_hand_layout(screen_w, card_w, len(player.hand))
        y = self.hand_y - card_h // 2
        for i, card in enumerate(player.hand):
            sprite = CardSprite(card, (start_x + i * spacing, y), card_w)
            sprite.pos.y = self.hand_y
            sprite.update()
            sprite._layer = i
            self._manager_for(sprite)
            self.hand_sprites.add(sprite, layer=i)

        margin_v = bottom_margin(card_w)

        # --- Top AI player (horizontal) ---------------------------------
        top_player = self.game.players[2]
        start_x, spacing = calc_hand_layout(screen_w, card_w, len(top_player.hand))
        for i in range(len(top_player.hand)):
            pos = (start_x + i * spacing, 40)
            sprite = CardBackSprite(pos, card_w, self.card_back_name)
            sprite._layer = i
            self._manager_for(sprite)
            self.ai_sprites[0].add(sprite, layer=i)

        # --- Left AI player (vertical) ----------------------------------
        left_player = self.game.players[1]
        start_rel, overlap_v = calc_start_and_overlap(
            screen_h - 2 * margin_v,
            len(left_player.hand),
            card_w,
            25,
            card_w - 5,
        )
        vert_spacing = card_w - overlap_v
        y_start = start_rel + margin_v
        margin_h = horizontal_margin(card_w)
        for i in range(len(left_player.hand)):
            pos = (margin_h, y_start + i * vert_spacing)
            sprite = CardBackSprite(
                pos, card_w, self.card_back_name, rotation=90
            )
            sprite._layer = i
            self._manager_for(sprite)
            self.ai_sprites[1].add(sprite, layer=i)

        # --- Right AI player (vertical) ---------------------------------
        right_player = self.game.players[3]
        start_rel, overlap_v = calc_start_and_overlap(
            screen_h - 2 * margin_v,
            len(right_player.hand),
            card_w,
            25,
            card_w - 5,
        )
        vert_spacing = card_w - overlap_v
        y_start = start_rel + margin_v
        x = screen_w - card_h - margin_h
        for i in range(len(right_player.hand)):
            pos = (x, y_start + i * vert_spacing)
            sprite = CardBackSprite(
                pos, card_w, self.card_back_name, rotation=-90
            )
            sprite._layer = i
            self._manager_for(sprite)
            self.ai_sprites[2].add(sprite, layer=i)

        self.update_play_button_state()
        self._create_huds()

    def draw_players(self) -> List[pygame.Rect]:
        """Draw all players and their current hands and return dirty rects."""

        dirty: List[pygame.Rect] = []

        card_w = self.card_width

        # Sync sprite rects with their vector positions
        self.hand_sprites.update()
        for group in self.ai_sprites:
            group.update()

        bg = self._table_surface
        if bg is None:
            bg = pygame.Surface(self.screen.get_size())
            bg.fill(self.table_color)

        # Clear previous sprite positions
        self.hand_sprites.clear(self.screen, bg)
        for group in self.ai_sprites:
            group.clear(self.screen, bg)

        # Draw semi-transparent zones behind each player's hand
        for idx in range(len(self.game.players)):
            rect = self._player_zone_rect(idx)
            if rect.width and rect.height:
                zone = pygame.Surface(rect.size, pygame.SRCALPHA)
                zone.fill(ZONE_BG)
                dirty.append(self.screen.blit(zone, rect.topleft))
                if idx == self.game.current_idx:
                    draw_glow(self.screen, rect, ZONE_HIGHLIGHT)
                    dirty.append(rect)

        # Draw shadows first for a little depth
        for sp in self.hand_sprites.sprites():
            if isinstance(sp, CardSprite):
                sp.draw_shadow(self.screen)
                dirty.append(sp.rect)
        for group in self.ai_sprites:
            for sp in group.sprites():
                if isinstance(sp, CardSprite):
                    sp.draw_shadow(self.screen)
                    dirty.append(sp.rect)

        # Draw the cards themselves
        dirty.extend(self.hand_sprites.draw(self.screen))
        for group in self.ai_sprites:
            dirty.extend(group.draw(self.screen))

        # Highlight currently selected cards
        if self.selected:
            player = self.game.players[self.game.current_idx]
            cards = [sp.card for sp in self.selected if hasattr(sp, "card")]
            valid = self.game.is_valid(player, cards, self.game.current_combo)[0]
            color = (0, 255, 0) if valid else (255, 0, 0)
            for sp in self.selected:
                pygame.draw.rect(self.screen, color, sp.rect, width=3)
                dirty.append(sp.rect)

        # HUD panels for AI players
        for hud in getattr(self, "huds", []):
            dirty.append(hud.draw(self.screen))

        dirty.extend(self.draw_center_pile())

        if self.state == GameState.PLAYING:
            undo_btn = next((b for b in self.action_buttons if b.text == "Undo"), None)
            if undo_btn:
                undo_btn.enabled = len(self.game.snapshots) > 1
            for btn in self.action_buttons:
                btn.draw(self.screen)
                dirty.append(btn.rect)
            self.settings_button.draw(self.screen)
            dirty.append(self.settings_button.rect)

        return dirty

    def draw_center_pile(self) -> List[pygame.Rect]:
        """Draw the cards currently in the centre pile and return dirty rects."""
        dirty: List[pygame.Rect] = []
        if not self.game.pile:
            if self.current_trick:
                self.current_trick.clear()
            return dirty

        w, _ = self.screen.get_size()
        y = self.pile_y
        card_w = self.card_width
        start_rel, overlap = calc_start_and_overlap(
            w, len(self.current_trick), card_w, 25, card_w - 5
        )
        spacing = card_w - overlap
        start = start_rel + card_w // 2
        for i, (name, img) in enumerate(self.current_trick):
            x = start + i * spacing
            rect = img.get_rect(center=(int(x), int(y)))
            player_idx = next(
                (idx for idx, p in enumerate(self.game.players) if p.name == name),
                0,
            )
            color = PLAYER_COLORS[player_idx]
            draw_glow(self.screen, rect, color)
            draw_surface_shadow(self.screen, img, rect)
            dirty.append(self.screen.blit(img, rect))
            dirty.append(rect)
        return dirty

    def draw_score_overlay(self) -> pygame.Rect:
        """Render a scoreboard panel showing total wins for each player."""
        lines = [
            f"{p.name}: {self.win_counts.get(p.name, 0)}"
            for p in self.game.players
        ]
        panel = self._hud_box(lines, padding=5, bg_image=self.menu_background)
        rect = panel.get_rect(topleft=self.score_pos)
        self.score_rect = rect
        if self.score_visible:
            dirty = [self.screen.blit(panel, rect.topleft)]
        else:
            dirty = []
        self.score_button.draw(self.screen)
        dirty.append(self.score_button.rect)
        return rect.unionall(dirty)

    def _handle_score_event(self, event: pygame.event.Event) -> bool:
        """Handle toggle interaction for the score panel."""
        if event.type == pygame.MOUSEBUTTONDOWN and self.score_button.rect.collidepoint(event.pos):
            self.toggle_score()
            return True
        return False

    def run(self):
        self.update_hand_sprites()
        self._start_animation(self._highlight_turn(self.game.current_idx))
        self._start_animation(self._animate_avatar_blink(self.game.current_idx))
        # Reset the clock after initialization so startup time isn't counted
        self.clock.tick(self.fps_limit)
        if hasattr(self.clock, "times"):
            self.clock.times.clear()
        while self.running:
            dt = self.clock.tick(self.fps_limit) / 1000.0
            self.dt = dt
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.on_resize(event.w, event.h)
                elif self._handle_score_event(event):
                    continue
                elif self._dispatch_overlay_event(event):
                    continue
                else:
                    self._dispatch_game_event(event)

            for anim in self.animations[:]:
                try:
                    anim.send(dt)
                except StopIteration:
                    self.animations.remove(anim)

            for manager in list(self.anim_managers.values()):
                manager.update(dt)

            self._draw_frame()
        pygame.event.clear()
        gc.collect()
        try:
            pygame.display.quit()
            pygame.font.quit()
            pygame.mixer.quit()
        except Exception:
            pass
        pygame.quit()
        if tracemalloc.is_tracing():
            tracemalloc.clear_traces()


def main() -> None:
    GameView().run()


if __name__ == "__main__":
    main()
