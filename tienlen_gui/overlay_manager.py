from __future__ import annotations

from typing import Optional

from .helpers import GameState
from .overlays import (
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


class OverlayMixin:
    """Mixin adding overlay management helpers for :class:`GameView`."""

    def _activate_overlay(self, overlay: Overlay, state: GameState) -> None:
        """Switch to ``overlay`` using a brief transition."""
        old = self.overlay
        if old is not overlay:
            self._start_animation(self._transition_overlay(old, overlay))
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

    def close_overlay(self) -> None:
        had = self.overlay is not None
        self.overlay = None
        if had:
            self._save_options()
            self.state = GameState.PLAYING
            self.ai_turns()

    def show_game_over(self, winner: str) -> None:
        import sound

        sound.play("win")
        self.win_counts[winner] = self.win_counts.get(winner, 0) + 1
        self._activate_overlay(GameOverOverlay(self, winner), GameState.GAME_OVER)
