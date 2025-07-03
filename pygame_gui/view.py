from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Tuple, List, Optional

import pygame

from tien_len_full import Game, detect_combo, Player
import sound

from .helpers import (
    TABLE_THEMES,
    PLAYER_COLORS,
    HAND_SPACING,
    HORIZONTAL_MARGIN,
    LABEL_PAD,
    BUTTON_HEIGHT,
    ZONE_GUTTER,
    AVATAR_DIR,
    AVATAR_SIZE,
    OPTIONS_FILE,
    SAVE_FILE,
    GameState,
    calc_start_and_overlap,
    calc_hand_layout,
    list_music_tracks,
    list_table_textures,
    load_card_images,
    get_card_image,
    CardSprite,
    CardBackSprite,
    draw_glow,
    _mixer_ready,
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

logger = logging.getLogger(__name__)

class GameView(AnimationMixin):
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
        self.avatars: Dict[str, pygame.Surface] = {}
        load_card_images(self.card_width)
        self.table_texture_name = list_table_textures()[0] if list_table_textures() else ""
        self.table_image: Optional[pygame.Surface] = None
        tex_path = Path(__file__).with_name("assets") / "tables" / f"{self.table_texture_name}.png"
        if tex_path.exists():
            try:
                self.table_image = pygame.image.load(str(tex_path)).convert()
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
        self._layout_zones()
        self._load_avatars()
        # Load sound effects and background music
        sdir = Path(__file__).with_name("assets") / "sound"
        sound.load("click", sdir / "card-play.wav")
        sound.load("pass", sdir / "pass.wav")
        sound.load("bomb", sdir / "bomb.wav")
        sound.load("shuffle", sdir / "shuffle.wav")
        sound.load("win", sdir / "win.wav")
        self.music_track = list_music_tracks()[0] if list_music_tracks() else ""
        if _mixer_ready() and self.music_track:
            music = Path(__file__).with_name("assets") / "music" / self.music_track
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
        self.rule_flip_suit_rank = False
        self.rule_no_2s = True
        self.score_visible = True
        self.score_pos: Tuple[int, int] = (10, 10)
        self.score_rect = pygame.Rect(self.score_pos, (0, 0))
        self._dragging_score = False
        self._drag_offset = (0, 0)
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
        self.score_visible = opts.get("score_visible", self.score_visible)
        self.score_pos = tuple(opts.get("score_pos", list(self.score_pos)))
        win_data = opts.get("win_counts", {})
        self.win_counts: Dict[str, int] = {
            p.name: int(win_data.get(p.name, 0)) for p in self.game.players
        }
        if opts.get("fullscreen", False):
            self.toggle_fullscreen()
        self.apply_options()
        self.update_hand_sprites()
        self._create_action_buttons()
        self.show_profile_select()

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

    # Layout helpers --------------------------------------------------
    def _layout_zones(self) -> None:
        """Update stored vertical positions for hand, pile, and buttons."""
        card_h = int(self.card_width * 1.4)
        _, h = self.screen.get_size()
        margin = min(60, max(40, int(self.card_width * 0.75)))
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
        margin = min(60, max(40, int(card_w * 0.75)))
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

    def _hud_box(
        self,
        lines: list[str],
        text_color: Tuple[int, int, int] = (255, 255, 255),
        padding: int = 5,
        bg_color: Tuple[int, int, int, int] = (0, 0, 0, 150),
    ) -> pygame.Surface:
        """Return a surface with ``lines`` rendered on a semi-transparent box."""
        line_height = getattr(self.font, "get_linesize", lambda: 20)()
        imgs = [self.font.render(line, True, text_color) for line in lines]
        if imgs:
            width = max(int(img.get_width()) for img in imgs) + 2 * padding
        else:
            width = 0
        height = line_height * len(imgs) + 2 * padding
        panel = pygame.Surface((max(1, width), max(1, height)), pygame.SRCALPHA)
        panel.fill(bg_color)
        y = padding
        for img in imgs:
            panel.blit(img, (padding, y))
            y += line_height
        return panel

    def _load_avatars(self) -> None:
        """Load avatar images for all players if available."""
        self.avatars.clear()
        for p in self.game.players:
            filename = p.name.lower().replace(" ", "_") + ".png"
            path = AVATAR_DIR / filename
            if path.exists():
                try:
                    img = pygame.image.load(str(path)).convert_alpha()
                    img = pygame.transform.smoothscale(img, (AVATAR_SIZE, AVATAR_SIZE))
                    self.avatars[p.name] = img
                except Exception:
                    continue

    def _avatar_for(self, player: "Player") -> pygame.Surface:
        """Return avatar image or a placeholder with player initials."""
        img = self.avatars.get(player.name)
        if img:
            return img
        initials = "".join(part[0] for part in player.name.split())[:2].upper()
        surf = pygame.Surface((AVATAR_SIZE, AVATAR_SIZE), pygame.SRCALPHA)
        pygame.draw.circle(surf, (80, 80, 80), (AVATAR_SIZE // 2, AVATAR_SIZE // 2), AVATAR_SIZE // 2)
        font = pygame.font.SysFont(None, 20)
        text = font.render(initials, True, (255, 255, 255))
        rect = text.get_rect(center=(AVATAR_SIZE // 2, AVATAR_SIZE // 2))
        surf.blit(text, rect)
        self.avatars[player.name] = surf
        return surf

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
        self.action_buttons = [
            Button(
                "Play", pygame.Rect(start_x, y, btn_w, BUTTON_HEIGHT), self.play_selected, font
            ),
            Button(
                "Pass",
                pygame.Rect(start_x + btn_w + spacing, y, btn_w, BUTTON_HEIGHT),
                self.pass_turn,
                font,
            ),
            Button(
                "Undo",
                pygame.Rect(start_x + 2 * (btn_w + spacing), y, btn_w, BUTTON_HEIGHT),
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

    def toggle_score(self) -> None:
        """Toggle visibility of the score panel and save."""
        self.score_visible = not self.score_visible
        self._save_options()

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

    def show_profile_select(self) -> None:
        self._activate_overlay(ProfileOverlay(self), GameState.MENU)

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
        counts = self.win_counts
        self.game = Game()
        self.game.setup()
        self._attach_reset_pile()
        self.reset_current_trick()
        self.selected.clear()
        self.current_trick.clear()
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
            path = OPTIONS_FILE
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
            return data
        except Exception as exc:
            logger.warning("Failed to load options: %s", exc)
            return {}

    def _save_options(self) -> None:
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
            "fullscreen": self.fullscreen,
            "score_visible": self.score_visible,
            "score_pos": list(self.score_pos),
            "win_counts": self.win_counts,
        }
        try:
            OPTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(OPTIONS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception as exc:
            logger.warning("Failed to save options: %s", exc)

    def apply_options(self) -> None:
        self.table_color = TABLE_THEMES.get(
            self.table_color_name, TABLE_THEMES["darkgreen"]
        )
        back_map = {
            "red": "card_back_red",
            "green": "card_back_green",
            "black": "card_back_black",
            "blue": "card_back",
        }
        self.card_back_name = back_map.get(self.card_color, self.card_back_name)
        tex_path = Path(__file__).with_name("assets") / "tables" / f"{self.table_texture_name}.png"
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
        self.game.players[0].sort_hand(self.sort_mode, self.game.flip_suit_rank)
        self.game.set_ai_level(self.ai_level)
        self.game.set_personality(self.ai_personality)
        self.game.ai_lookahead = self.ai_lookahead
        self.game.allow_2_in_sequence = not self.rule_no_2s
        self.game.flip_suit_rank = self.rule_flip_suit_rank
        sound.set_volume(self.fx_volume)
        sound.set_enabled(self.sound_enabled)
        if _mixer_ready():
            pygame.mixer.music.set_volume(self.music_volume)
            if self.music_enabled:
                track = Path(__file__).with_name("assets") / "music" / self.music_track
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
        self._layout_zones()
        self.update_hand_sprites()
        self._create_action_buttons()
        self._position_score_button()
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
        """Create card sprites for all players with a simple table layout."""

        self.hand_sprites = pygame.sprite.Group()
        self.ai_sprites = [pygame.sprite.Group() for _ in range(3)]

        card_w = self.card_width
        card_h = int(card_w * 1.4)
        screen_w, screen_h = self.screen.get_size()

        # --- Human player at the bottom ---------------------------------
        player = self.game.players[0]
        start_x, spacing = calc_hand_layout(screen_w, card_w, len(player.hand))
        y = screen_h - card_h - 20
        for i, card in enumerate(player.hand):
            sprite = CardSprite(card, (start_x + i * spacing, y), card_w)
            self.hand_sprites.add(sprite)

        margin_v = min(60, max(40, int(card_w * 0.75)))

        # --- Top AI player (horizontal) ---------------------------------
        top_player = self.game.players[2]
        start_x, spacing = calc_hand_layout(screen_w, card_w, len(top_player.hand))
        for i in range(len(top_player.hand)):
            pos = (start_x + i * spacing, 40)
            sprite = CardBackSprite(pos, card_w, self.card_back_name)
            self.ai_sprites[0].add(sprite)

        # --- Left AI player (vertical) ----------------------------------
        left_player = self.game.players[1]
        start_rel, overlap_v = calc_start_and_overlap(
            screen_h - 2 * margin_v,
            len(left_player.hand),
            card_h,
            25,
            card_h - 5,
        )
        vert_spacing = card_h - overlap_v
        y_start = start_rel + margin_v
        for i in range(len(left_player.hand)):
            pos = (HORIZONTAL_MARGIN, y_start + i * vert_spacing)
            sprite = CardBackSprite(pos, card_w, self.card_back_name)
            self.ai_sprites[1].add(sprite)

        # --- Right AI player (vertical) ---------------------------------
        right_player = self.game.players[3]
        start_rel, overlap_v = calc_start_and_overlap(
            screen_h - 2 * margin_v,
            len(right_player.hand),
            card_h,
            25,
            card_h - 5,
        )
        vert_spacing = card_h - overlap_v
        y_start = start_rel + margin_v
        x = screen_w - card_w - HORIZONTAL_MARGIN
        for i in range(len(right_player.hand)):
            pos = (x, y_start + i * vert_spacing)
            sprite = CardBackSprite(pos, card_w, self.card_back_name)
            self.ai_sprites[2].add(sprite)

        self.update_play_button_state()

    def draw_players(self):
        """Draw all players and their current hands."""

        card_w = self.card_width
        sprites = self.hand_sprites.sprites()
        card_h = sprites[0].rect.height if sprites else int(card_w * 1.4)
        spacing = min(40, card_w)

        # Draw shadows first for a little depth
        for sp in self.hand_sprites.sprites():
            if isinstance(sp, CardSprite):
                sp.draw_shadow(self.screen)
        for group in self.ai_sprites:
            for sp in group.sprites():
                if isinstance(sp, CardSprite):
                    sp.draw_shadow(self.screen)

        # Draw the cards themselves
        self.hand_sprites.draw(self.screen)
        for group in self.ai_sprites:
            group.draw(self.screen)

        # Highlight currently selected cards
        if self.selected:
            player = self.game.players[self.game.current_idx]
            cards = [sp.card for sp in self.selected if hasattr(sp, "card")]
            valid = self.game.is_valid(player, cards, self.game.current_combo)[0]
            color = (0, 255, 0) if valid else (255, 0, 0)
            for sp in self.selected:
                pygame.draw.rect(self.screen, color, sp.rect, width=3)

        # Player labels and avatars
        for idx, p in enumerate(self.game.players):
            x, y = self._player_pos(idx)
            txt = f"{p.name} ({len(p.hand)})"
            color = (255, 255, 0) if idx == self.game.current_idx else (255, 255, 255)
            panel = self._hud_box([txt], text_color=color, padding=3)
            avatar = self._avatar_for(p)
            aw, ah = avatar.get_size()
            pw, ph = panel.get_size()
            combined = pygame.Surface((aw + LABEL_PAD + pw, max(ah, ph)), pygame.SRCALPHA)
            combined.blit(avatar, (0, (combined.get_height() - ah) // 2))
            combined.blit(panel, (aw + LABEL_PAD, (combined.get_height() - ph) // 2))
            panel = combined
            offset = card_h // 2 + spacing // 2 + LABEL_PAD
            if idx == 0:
                rect = panel.get_rect(midbottom=(x, y - offset))
            elif idx == 1:
                rect = panel.get_rect(midtop=(x, y + offset))
            elif idx == 2:
                rect = panel.get_rect(midleft=(x + offset, y))
            else:
                rect = panel.get_rect(midright=(x - offset, y))
            self.screen.blit(panel, rect)

        self.draw_center_pile()

        if self.state == GameState.PLAYING:
            undo_btn = next((b for b in self.action_buttons if b.text == "Undo"), None)
            if undo_btn:
                undo_btn.enabled = len(self.game.snapshots) > 1
            for btn in self.action_buttons:
                btn.draw(self.screen)
            self.settings_button.draw(self.screen)

    def draw_center_pile(self) -> None:
        """Draw the cards currently in the centre pile."""
        if not self.game.pile:
            if self.current_trick:
                self.current_trick.clear()
            return

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
            self.screen.blit(img, rect)

    def draw_score_overlay(self) -> None:
        """Render a scoreboard panel with last hands played."""
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
        panel = self._hud_box(lines, padding=5)
        rect = panel.get_rect(topleft=self.score_pos)
        self.score_rect = rect
        if self.score_visible:
            self.screen.blit(panel, rect.topleft)
        self.score_button.draw(self.screen)

    def _handle_score_event(self, event: pygame.event.Event) -> bool:
        """Handle toggle and drag interactions for the score panel."""
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.score_button.rect.collidepoint(event.pos):
                self.toggle_score()
                return True
            if self.score_visible and self.score_rect.collidepoint(event.pos):
                self._dragging_score = True
                self._drag_offset = (
                    event.pos[0] - self.score_pos[0],
                    event.pos[1] - self.score_pos[1],
                )
                return True
        elif event.type == pygame.MOUSEBUTTONUP:
            if self._dragging_score:
                self._dragging_score = False
                self._save_options()
                return True
        elif event.type == pygame.MOUSEMOTION and self._dragging_score:
            self.score_pos = (
                event.pos[0] - self._drag_offset[0],
                event.pos[1] - self._drag_offset[1],
            )
            return True
        return False

    def run(self):
        self.update_hand_sprites()
        self._highlight_turn(self.game.current_idx)
        while self.running:
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

            self._draw_frame()
            self.clock.tick(30)
        pygame.quit()


def main() -> None:
    GameView().run()


if __name__ == "__main__":
    main()
