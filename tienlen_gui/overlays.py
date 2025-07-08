from __future__ import annotations

import pygame
from typing import List, Callable, Optional, TYPE_CHECKING

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
                "New Game",
                pygame.Rect(bx, by, 200, 40),
                self.view.restart_game,
                font,
                **load_button_images("button_new_game", alt=True),
            ),
            Button(
                "Load Game",
                pygame.Rect(bx, by + 50, 200, 40),
                self.view.load_game,
                font,
                **load_button_images("button_load_game"),
            ),
            Button(
                "Switch Profile",
                pygame.Rect(bx, by + 100, 200, 40),
                self.view.show_profile_select,
                font,
                **load_button_images("button_switch_profile"),
            ),
            Button(
                "Settings",
                pygame.Rect(bx, by + 150, 200, 40),
                self.view.show_settings,
                font,
                **load_button_images("button_settings"),
            ),
            Button(
                "How to Play",
                pygame.Rect(bx, by + 200, 200, 40),
                lambda: self.view.show_how_to_play(from_menu=True),
                font,
                **load_button_images("button_how_to_play"),
            ),
            Button(
                "Quit",
                pygame.Rect(bx, by + 250, 200, 40),
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
                **load_button_images("button_load_game"),
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

        make_button(0, "ai_level", ["Easy", "Normal", "Hard", "Expert", "Master"], "AI Level")
        make_button(
            50,
            "ai_personality",
            ["balanced", "aggressive", "defensive", "random"],
            "Personality",
        )
        make_button(100, "ai_lookahead", [False, True], "Lookahead")
        make_button(150, "ai_depth", [1, 2, 3], "AI Depth")
        make_button(200, "animation_speed", [0.5, 1.0, 2.0], "Anim Speed")
        make_button(250, "sort_mode", ["rank", "suit"], "Sort Mode")
        make_button(300, "developer_mode", [False, True], "Dev Mode")
        self.buttons.append(
            Button(
                "House Rules",
                pygame.Rect(bx, by + 350, 240, 40),
                lambda: self.view.show_rules(from_menu=False),
                font,
            )
        )
        btn = Button(
            "Back",
            pygame.Rect(bx, by + 400, 240, 40),
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
        make_card_color = list_card_back_colors() or ["blue"]
        make_table_tex = list_table_textures() or ["table_img"]

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
        make_button(50, "card_color", make_card_color, "Card Back")
        make_button(100, "table_texture_name", make_table_tex, "Table Tex")
        make_button(150, "colorblind_mode", [False, True], "Colorblind")
        make_button(200, "fullscreen", [False, True], "Fullscreen")
        make_button(250, "fps_limit", [30, 60, 120], "FPS Limit")
        btn = Button(
            "Back",
            pygame.Rect(bx, by + 300, 240, 40),
            self.view.show_settings,
            font,
            **load_button_images("button_back"),
        )
        self.buttons.append(btn)

        self.table_preview_rect = pygame.Rect(bx + 250, by, 60, 40)
        self.back_preview_rect = pygame.Rect(bx + 250, by + 50, 40, 60)

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
        make_button(200, "music_track", list_music_tracks() or [self.view.music_track], "Track")
        btn = Button(
            "Back",
            pygame.Rect(bx, by + 250, 240, 40),
            self.view.show_settings,
            font,
            **load_button_images("button_back"),
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

        make_button(0, "rule_flip_suit_rank", "Flip Suit Rank")
        make_button(50, "rule_no_2s", "No 2s in straights")
        self.buttons.append(
            Button(
                "Back",
                pygame.Rect(bx, by + 100, 240, 40),
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
        bx = w // 2 - 100
        by = h // 2 + 60
        self.buttons = [
            Button(
                "Back",
                pygame.Rect(bx, by, 200, 40),
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
        bx = w // 2 - 100
        by = h // 2 + 60
        self.buttons = [
            Button(
                "Back",
                pygame.Rect(bx, by, 200, 40),
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
        bx = w // 2 - 100
        start_y = h // 2 - (len(names) + 1) * 25
        self.buttons = [
            Button(
                name,
                pygame.Rect(bx, start_y + i * 50, 200, 40),
                lambda n=name: self.select(n),
                font,
            )
            for i, name in enumerate(names)
        ]
        self.buttons.append(
            Button(
                "New Profile",
                pygame.Rect(bx, start_y + len(names) * 50, 200, 40),
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
        bx = w // 2 - 100
        by = h // 2 + 40
        self.buttons = [
            Button(
                "Play Again", pygame.Rect(bx, by, 200, 40), self.view.restart_game, font
            ),
            Button(
                "Quit",
                pygame.Rect(bx, by + 50, 200, 40),
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
