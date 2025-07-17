from __future__ import annotations

import pygame
from typing import List, Callable, Optional, TYPE_CHECKING

from tienlen import sound

from .helpers import (
    list_card_back_colors,
    list_table_textures,
    get_card_back,
    list_music_tracks,
    TABLE_THEMES,
    load_button_images,
    draw_nine_patch,
)

if TYPE_CHECKING:
    from .view import GameView


class Button:
    """Basic rectangular button used by overlays."""

    def __init__(
        self,
        text: str,
        rect: pygame.Rect,
        callback: Callable[[], None],
        font: pygame.font.Font,
        enabled: bool = True,
        idle_image: Optional[pygame.Surface] = None,
        hover_image: Optional[pygame.Surface] = None,
        pressed_image: Optional[pygame.Surface] = None,
    ) -> None:
        self.text = text
        self.rect = rect
        self.callback = callback
        self.font = font
        self.enabled = enabled
        self.idle_image = idle_image
        self.hover_image = hover_image
        self.pressed_image = pressed_image
        self.hovered = False
        self.selected = False

    def draw(self, surface: pygame.Surface) -> None:
        if self.idle_image:
            if not self.enabled:
                img = self.idle_image
            elif self.selected:
                img = self.pressed_image or self.idle_image
            elif self.hovered:
                img = self.hover_image or self.idle_image
            else:
                img = self.idle_image
            draw_nine_patch(surface, img, self.rect)
            text_color = (0, 0, 0)
        else:
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
            sound.play("click")
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

    def _button_size(self) -> tuple[int, int]:
        """Return (width, height) for buttons based on screen size."""
        w, _ = self.view.screen.get_size()
        width = max(int(w * 0.35), 150)
        height = max(width // 5, 30)
        return width, height

    def _spacing(self) -> int:
        """Vertical spacing between buttons."""
        _, h = self._button_size()
        return h + 10


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
        bw, bh = self._button_size()
        spacing = self._spacing()
        bx = w // 2 - bw // 2
        by = h // 2 - int(spacing * 2.4)
        self.buttons = [
            Button(
                "New Game",
                pygame.Rect(bx, by, bw, bh),
                self.view.restart_game,
                font,
                **load_button_images("button_new_game", alt=True),
            ),
            Button(
                "Load Game",
                pygame.Rect(bx, by + spacing, bw, bh),
                self.view.load_game,
                font,
                **load_button_images("button_load_game"),
            ),
            Button(
                "Switch Profile",
                pygame.Rect(bx, by + spacing * 2, bw, bh),
                self.view.show_profile_select,
                font,
                **load_button_images("button_switch_profile"),
            ),
            Button(
                "Settings",
                pygame.Rect(bx, by + spacing * 3, bw, bh),
                self.view.show_settings,
                font,
                **load_button_images("button_settings"),
            ),
            Button(
                "How to Play",
                pygame.Rect(bx, by + spacing * 4, bw, bh),
                lambda: self.view.show_how_to_play(from_menu=True),
                font,
                **load_button_images("button_how_to_play"),
            ),
            Button(
                "Quit",
                pygame.Rect(bx, by + spacing * 5, bw, bh),
                self.view.quit_game,
                font,
                **load_button_images("button_quit"),
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
        bw, bh = self._button_size()
        spacing = self._spacing()
        bx = w // 2 - bw // 2
        by = h // 2 - int(spacing * 4)
        self.buttons = [
            Button(
                "Resume Game",
                pygame.Rect(bx, by, bw, bh),
                self.view.close_overlay,
                font,
            ),
            Button(
                "Save Game",
                pygame.Rect(bx, by + spacing, bw, bh),
                self.view.save_game,
                font,
            ),
            Button(
                "Load Game",
                pygame.Rect(bx, by + spacing * 2, bw, bh),
                self.view.load_game,
                font,
                **load_button_images("button_load_game"),
            ),
            Button(
                "Game Settings",
                pygame.Rect(bx, by + spacing * 3, bw, bh),
                self.view.show_settings,
                font,
            ),
            Button(
                "Return to Main Menu",
                pygame.Rect(bx, by + spacing * 4, bw, bh),
                self.view.confirm_return_to_menu,
                font,
            ),
            Button(
                "Quit Game",
                pygame.Rect(bx, by + spacing * 5, bw, bh),
                self.view.confirm_quit,
                font,
                **load_button_images("button_quit"),
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
        bw, bh = self._button_size()
        spacing = self._spacing()
        bx = w // 2 - bw // 2
        by = h // 2 - int(spacing * 2.4)
        self.buttons = [
            Button(
                "Game Settings",
                pygame.Rect(bx, by, bw, bh),
                self.view.show_game_settings,
                font,
            ),
            Button(
                "Graphics",
                pygame.Rect(bx, by + spacing, bw, bh),
                self.view.show_graphics,
                font,
            ),
            Button(
                "Audio", pygame.Rect(bx, by + spacing * 2, bw, bh), self.view.show_audio, font
            ),
            Button(
                "Game Tutorial",
                pygame.Rect(bx, by + spacing * 3, bw, bh),
                lambda: self.view.show_tutorial(from_menu=False),
                font,
            ),
            Button(
                "Back",
                pygame.Rect(bx, by + spacing * 4, bw, bh),
                self.view.close_overlay,
                font,
                **load_button_images("button_back"),
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
        bw, bh = self._button_size()
        spacing = self._spacing()
        bx = w // 2 - bw // 2
        by = h // 2 - int(spacing * 4.4)

        def cycle(attr: str, options: List, label: str) -> Callable[[], None]:
            def callback(b: Button) -> Callable[[], None]:
                def inner() -> None:
                    cur = getattr(self.view, attr)
                    idx = options.index(cur)
                    cur = options[(idx + 1) % len(options)]
                    setattr(self.view, attr, cur)
                    if attr == "use_global_ai_settings" and cur:
                        self.view.player_ai_levels.clear()
                        self.view.player_ai_personality.clear()
                    self.view.apply_options()
                    if attr == "use_global_ai_settings":
                        self._layout()
                    else:
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
                pygame.Rect(bx, by + offset, bw, bh),
                lambda: None,
                font,
            )
            btn.callback = cycle(attr, opts, label)(btn)
            self.buttons.append(btn)

        make_button(0, "ai_level", ["Easy", "Normal", "Hard", "Expert", "Master"], "AI Level")
        make_button(
            spacing,
            "ai_personality",
            ["balanced", "aggressive", "defensive", "random"],
            "Personality",
        )
        make_button(spacing * 2, "ai_lookahead", [False, True], "Lookahead")
        make_button(spacing * 3, "ai_depth", [1, 2, 3], "AI Depth")
        make_button(spacing * 4, "animation_speed", [0.5, 1.0, 2.0], "Anim Speed")
        make_button(spacing * 5, "sort_mode", ["rank", "suit"], "Sort Mode")
        make_button(spacing * 6, "developer_mode", [False, True], "Dev Mode")
        make_button(spacing * 7, "use_global_ai_settings", [False, True], "Use Global AI")
        if not self.view.use_global_ai_settings:
            ai_setup_btn = Button(
                "AI Setup",
                pygame.Rect(bx, by + spacing * 8, bw, bh),
                self.view.show_ai_setup,
                font,
            )
            self.buttons.append(ai_setup_btn)
            offset_extra = 1
        else:
            offset_extra = 0
        self.buttons.append(
            Button(
                "House Rules",
                pygame.Rect(bx, by + spacing * (8 + offset_extra), bw, bh),
                lambda: self.view.show_rules(from_menu=False),
                font,
            )
        )
        btn = Button(
            "Back",
            pygame.Rect(bx, by + spacing * (9 + offset_extra), bw, bh),
            self.view.show_settings,
            font,
            **load_button_images("button_back"),
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
        bw, bh = self._button_size()
        spacing = self._spacing()
        bx = w // 2 - bw // 2
        by = h // 2 - int(spacing * 2.4)

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
        make_card_color = list_card_back_colors() or ["blue"]
        make_table_tex = list_table_textures() or ["table_img"]

        self.buttons = []

        def make_button(offset: int, attr: str, opts: List, label: str) -> None:
            text = getattr(self.view, attr)
            btn = Button(
                f"{label}: {text}",
                pygame.Rect(bx, by + offset, bw, bh),
                lambda: None,
                font,
            )
            btn.callback = cycle(attr, opts, label)(btn)
            self.buttons.append(btn)

        make_button(0, "table_color_name", make_color, "Table Color")
        make_button(spacing, "card_color", make_card_color, "Card Back")
        make_button(spacing * 2, "table_texture_name", make_table_tex, "Table Tex")
        make_button(spacing * 3, "colorblind_mode", [False, True], "Colorblind")
        make_button(spacing * 4, "fullscreen", [False, True], "Fullscreen")
        make_button(spacing * 5, "fps_limit", [30, 60, 120], "FPS Limit")
        btn = Button(
            "Back",
            pygame.Rect(bx, by + spacing * 6, bw, bh),
            self.view.show_settings,
            font,
            **load_button_images("button_back"),
        )
        self.buttons.append(btn)

        self.table_preview_rect = pygame.Rect(bx + bw + 10, by, 60, 40)
        self.back_preview_rect = pygame.Rect(bx + bw + 10, by + spacing, 40, 60)

    def draw(self, surface: pygame.Surface) -> None:
        super().draw(surface)
        if self.view.table_image:
            tex = pygame.transform.smoothscale(
                self.view.table_image, self.table_preview_rect.size
            )
            surface.blit(tex, self.table_preview_rect)
        else:
            pygame.draw.rect(surface, self.view.table_color, self.table_preview_rect)

        back = get_card_back(self.view.card_back_name, self.back_preview_rect.width)
        if back:
            img = pygame.transform.smoothscale(back, self.back_preview_rect.size)
            surface.blit(img, self.back_preview_rect)


class AudioOverlay(Overlay):
    def __init__(self, view: "GameView") -> None:
        super().__init__(view, view.show_settings)
        self._layout()

    def resize(self) -> None:
        self._layout()

    def _layout(self) -> None:
        w, h = self.view.screen.get_size()
        font = self.view.font
        bw, bh = self._button_size()
        spacing = self._spacing()
        bx = w // 2 - bw // 2
        by = h // 2 - int(spacing * 2.4)

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
                pygame.Rect(bx, by + offset, bw, bh),
                lambda: None,
                font,
            )
            btn.callback = cycle(attr, opts, label)(btn)
            self.buttons.append(btn)

        make_button(0, "sound_enabled", [True, False], "Sound")
        make_button(spacing, "music_enabled", [True, False], "Music")
        make_button(spacing * 2, "fx_volume", [0.5, 0.75, 1.0], "FX Vol")
        make_button(spacing * 3, "music_volume", [0.5, 0.75, 1.0], "Music Vol")
        make_button(
            spacing * 4,
            "music_track",
            list_music_tracks() or [self.view.music_track],
            "Track",
        )
        btn = Button(
            "Back",
            pygame.Rect(bx, by + spacing * 5, bw, bh),
            self.view.show_settings,
            font,
            **load_button_images("button_back"),
        )
        self.buttons.append(btn)


class AiSetupOverlay(Overlay):
    """Cycle difficulty and personality for each AI opponent."""

    DIFFICULTIES = ["Easy", "Normal", "Hard", "Expert", "Master"]
    PERSONALITIES = ["balanced", "aggressive", "defensive", "random"]

    def __init__(self, view: "GameView") -> None:
        super().__init__(view, view.show_game_settings)
        self._personality_callbacks: dict[Button, Callable[[], None]] = {}
        self._layout()

    def resize(self) -> None:
        self._layout()

    def _layout(self) -> None:
        w, h = self.view.screen.get_size()
        font = self.view.font
        bw, bh = self._button_size()
        spacing = self._spacing()
        bx = w // 2 - bw // 2
        ai_players = [p for p in self.view.game.players if not p.is_human]
        by = h // 2 - int(spacing * (len(ai_players) - 0.2)) // 2
        self.buttons = []
        self._personality_callbacks.clear()

        for i, player in enumerate(ai_players):
            lvl = self.view.player_ai_levels.get(
                player.name, player.ai_level or self.view.ai_level
            )
            per = self.view.player_ai_personality.get(
                player.name, player.ai_personality or self.view.ai_personality
            )
            btn = Button(
                f"{player.name}: {lvl} / {per}",
                pygame.Rect(bx, by + i * spacing, bw, bh),
                lambda p=player, b=None: None,
                font,
            )
            btn.callback = self._make_level_callback(player, btn)
            self._personality_callbacks[btn] = self._make_personality_callback(
                player, btn
            )
            self.buttons.append(btn)

        back_btn = Button(
            "Back",
            pygame.Rect(bx, by + spacing * len(ai_players), bw, bh),
            self.view.show_game_settings,
            font,
            **load_button_images("button_back"),
        )
        self.buttons.append(back_btn)

    def _make_level_callback(self, player, btn):
        def inner() -> None:
            cur = self.view.player_ai_levels.get(
                player.name, player.ai_level or self.view.ai_level
            )
            idx = self.DIFFICULTIES.index(cur)
            new = self.DIFFICULTIES[(idx + 1) % len(self.DIFFICULTIES)]
            self.view.player_ai_levels[player.name] = new
            self.view.game.set_player_ai_level(player.name, new)
            per = self.view.player_ai_personality.get(
                player.name, player.ai_personality or self.view.ai_personality
            )
            btn.text = f"{player.name}: {new} / {per}"
            self.view.apply_options()

        return inner

    def _make_personality_callback(self, player, btn):
        def inner() -> None:
            cur = self.view.player_ai_personality.get(
                player.name, player.ai_personality or self.view.ai_personality
            )
            idx = self.PERSONALITIES.index(cur)
            new = self.PERSONALITIES[(idx + 1) % len(self.PERSONALITIES)]
            self.view.player_ai_personality[player.name] = new
            self.view.game.set_player_personality(player.name, new)
            lvl = self.view.player_ai_levels.get(
                player.name, player.ai_level or self.view.ai_level
            )
            btn.text = f"{player.name}: {lvl} / {new}"
            self.view.apply_options()

        return inner

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            for i, btn in enumerate(self.buttons[:-1]):
                if btn.rect.collidepoint(event.pos):
                    self.focus_idx = i
                    self._personality_callbacks[btn]()
                    return
        super().handle_event(event)

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
        bw, bh = self._button_size()
        spacing = self._spacing()
        bx = w // 2 - bw // 2
        by = h // 2 - int(spacing * 3)

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
                text, pygame.Rect(bx, by + offset, bw, bh), lambda: None, font
            )
            btn.callback = toggle(attr, label)(btn)
            self.buttons.append(btn)

        make_button(0, "rule_flip_suit_rank", "Flip Suit Rank")
        make_button(spacing, "rule_no_2s", "No 2s in straights")
        make_button(spacing * 2, "rule_bomb_override", "Chặt bomb")
        make_button(spacing * 3, "rule_chain_cutting", "Chain cutting")
        make_button(spacing * 4, "rule_bomb_hierarchy", "Tứ Quý hierarchy")
        self.buttons.append(
            Button(
                "Back",
                pygame.Rect(bx, by + spacing * 5, bw, bh),
                self.back_callback,
                font,
                **load_button_images("button_back"),
            )
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
        bw, bh = self._button_size()
        spacing = self._spacing()
        bx = w // 2 - bw // 2
        by = h // 2 + int(spacing * -1.2)
        self.buttons = [
            Button(
                "Back",
                pygame.Rect(bx, by, bw, bh),
                self.back_callback,
                font,
                **load_button_images("button_back"),
            )
        ]

    def draw(self, surface: pygame.Surface) -> None:
        super().draw(surface)
        w, h = surface.get_size()
        lines = [
            "Each player starts with 13 cards.",
            "Play higher combinations to beat opponents.",
            "First to shed all cards wins the round.",
        ]
        panel = self.view._hud_box(
            lines,
            padding=10,
            bg_image=self.view.menu_background or self.view.panel_image,
        )
        rect = panel.get_rect(center=(w // 2, h // 2 - 20))
        surface.blit(panel, rect)


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
        bw, bh = self._button_size()
        spacing = self._spacing()
        bx = w // 2 - bw // 2
        by = h // 2 + int(spacing * -1.2)
        self.buttons = [
            Button(
                "Back",
                pygame.Rect(bx, by, bw, bh),
                self.back_callback,
                font,
                **load_button_images("button_back"),
            )
        ]

    def draw(self, surface: pygame.Surface) -> None:
        super().draw(surface)
        w, h = surface.get_size()
        steps = [
            "1. Select cards with mouse or arrow keys.",
            "2. Press Play to submit your move.",
            "3. Beat opponents until you run out of cards.",
        ]
        panel = self.view._hud_box(
            steps,
            padding=10,
            bg_image=self.view.menu_background or self.view.panel_image,
        )
        rect = panel.get_rect(center=(w // 2, h // 2 - 20))
        surface.blit(panel, rect)


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
        bw, bh = self._button_size()
        spacing = self._spacing()
        bx = w // 2 - bw // 2
        by = h // 2
        self.buttons = [
            Button(
                f"Save and {self.label}",
                pygame.Rect(bx, by, bw, bh),
                self._save_then_action,
                font,
            ),
            Button(
                f"{self.label} Without Saving",
                pygame.Rect(bx, by + spacing, bw, bh),
                self.action,
                font,
            ),
            Button(
                "Cancel",
                pygame.Rect(bx, by + spacing * 2, bw, bh),
                self.view.close_overlay,
                font,
            ),
        ]

    def _save_then_action(self) -> None:
        self.view.save_game()
        self.action()

    def draw(self, surface: pygame.Surface) -> None:
        w, h = surface.get_size()
        msg = f"Save your game before {self.label.lower()}?"
        panel = self.view._hud_box(
            [msg],
            padding=10,
            bg_image=self.view.menu_background or self.view.panel_image,
        )
        rect = panel.get_rect(center=(w // 2, h // 2 - 60))
        surface.blit(panel, rect)
        super().draw(surface)


class ProfileOverlay(Overlay):
    """Select or create a player profile."""

    def __init__(self, view: "GameView") -> None:
        super().__init__(view, None)
        self._layout()

    def resize(self) -> None:
        self._layout()

    def _layout(self) -> None:
        w, h = self.view.screen.get_size()
        font = self.view.font
        names = list(self.view.win_counts.keys())
        bw, bh = self._button_size()
        spacing = self._spacing()
        bx = w // 2 - bw // 2
        start_y = h // 2 - int((len(names) + 1) * spacing / 2)
        self.buttons = [
            Button(
                name,
                pygame.Rect(bx, start_y + i * spacing, bw, bh),
                lambda n=name: self.select(n),
                font,
            )
            for i, name in enumerate(names)
        ]
        self.buttons.append(
            Button(
                "New Profile",
                pygame.Rect(bx, start_y + len(names) * spacing, bw, bh),
                self.new_profile,
                font,
            )
        )

    def select(self, name: str) -> None:
        self.view.player_name = name
        self.view.apply_options()
        self.view._save_options()
        self.view.show_menu()

    def new_profile(self) -> None:
        base = "Player"
        idx = 1
        names = set(self.view.win_counts)
        while f"{base}{idx}" in names:
            idx += 1
        name = f"{base}{idx}"
        self.view.win_counts[name] = 0
        self.select(name)


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
        bw, bh = self._button_size()
        spacing = self._spacing()
        bx = w // 2 - bw // 2
        by = h // 2 + int(spacing * -0.8)
        self.buttons = [
            Button(
                "Play Again", pygame.Rect(bx, by, bw, bh), self.view.restart_game, font
            ),
            Button(
                "Quit",
                pygame.Rect(bx, by + spacing, bw, bh),
                self.view.quit_game,
                font,
                **load_button_images("button_quit"),
            ),
        ]

    def draw(self, surface: pygame.Surface) -> None:
        w, h = surface.get_size()
        lines = [f"{self.winner} wins!"] + [
            f"{i+1}. {n} ({c})" for i, (n, c) in enumerate(self.rankings)
        ]
        panel = self.view._hud_box(
            lines,
            padding=10,
            bg_image=self.view.menu_background or self.view.panel_image,
        )
        rect = panel.get_rect(center=(w // 2, h // 2 - 20))
        surface.blit(panel, rect)
        super().draw(surface)
