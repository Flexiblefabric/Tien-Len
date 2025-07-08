import os
from unittest.mock import patch, MagicMock
import pytest
import pygame
import tienlen_gui
from conftest import make_view, DummySprite, DummyCardSprite

pytest.importorskip("PIL")
pytest.importorskip("pygame")

# Use dummy video driver so no window is opened
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")


def test_handle_key_shortcuts():
    view, _ = make_view()
    view.state = tienlen_gui.GameState.PLAYING

    with patch.object(view, "play_selected") as play:
        view.handle_key(pygame.K_RETURN)
        play.assert_called_once()

    with patch.object(view, "pass_turn") as pass_turn:
        view.handle_key(pygame.K_SPACE)
        pass_turn.assert_called_once()

    with patch.object(view, "show_menu") as show_menu:
        view.handle_key(pygame.K_m)
        show_menu.assert_called_once()

    with patch.object(view, "show_settings") as show_settings:
        view.handle_key(pygame.K_o)
        show_settings.assert_called_once()
    pygame.quit()


def test_handle_mouse_select_and_overlay():
    view, _ = make_view()
    sprite = DummySprite()
    center = sprite.rect.center
    view.hand_sprites = pygame.sprite.LayeredUpdates(sprite)
    view.selected = []
    view.state = tienlen_gui.GameState.PLAYING
    view.action_buttons = []

    view.handle_mouse(center)
    assert sprite.selected is True
    assert sprite in view.selected

    view.handle_mouse(center)
    assert sprite.selected is False
    assert sprite not in view.selected

    view.state = tienlen_gui.GameState.MENU
    overlay = MagicMock()
    view.overlay = overlay
    view.handle_mouse((5, 5))
    event = overlay.handle_event.call_args[0][0]
    assert event.pos == (5, 5)
    pygame.quit()


def test_handle_mouse_selects_rightmost_sprite():
    view, _ = make_view()
    left = DummySprite((5, 5))
    right = DummySprite((5, 5))
    view.hand_sprites = pygame.sprite.LayeredUpdates(left, right)
    view.selected = []
    view.state = tienlen_gui.GameState.PLAYING
    view.action_buttons = []
    with patch.object(view, "update_play_button_state"), patch.object(
        view, "_highlight_turn"
    ), patch.object(view, "_animate_avatar_blink"):
        view.handle_mouse((5, 5))
    assert right.selected is True
    assert right in view.selected
    assert left.selected is False
    pygame.quit()


def test_update_play_button_state_enables_button_on_valid_selection():
    view, _ = make_view()
    card_sprite = DummyCardSprite()
    view.selected = [card_sprite]
    btn = view.action_buttons[0]
    with patch.object(view.game, "is_valid", return_value=(True, "")) as mock:
        view.update_play_button_state()
    mock.assert_called_once_with(
        view.game.players[view.game.current_idx],
        [card_sprite.card],
        view.game.current_combo,
    )
    assert btn.enabled is True


def test_update_play_button_state_disables_when_invalid():
    view, _ = make_view()
    card_sprite = DummyCardSprite()
    view.selected = [card_sprite]
    btn = view.action_buttons[0]
    with patch.object(view.game, "is_valid", return_value=(False, "bad")):
        view.update_play_button_state()
    assert btn.enabled is False


def test_handle_mouse_calls_update_play_button_state():
    view, _ = make_view()
    sprite = DummyCardSprite((5, 5))
    view.hand_sprites = pygame.sprite.LayeredUpdates(sprite)
    view.selected = []
    view.state = tienlen_gui.GameState.PLAYING
    view.action_buttons = []
    with patch.object(view, "update_play_button_state") as upd, patch.object(
        view, "_highlight_turn"
    ), patch.object(view, "_animate_avatar_blink"):
        view.handle_mouse(sprite.rect.center)
        upd.assert_called()


def test_update_hand_sprites_calls_update_play_button_state():
    view, _ = make_view()
    with patch.object(view, "update_play_button_state") as upd:
        view.update_hand_sprites()
        upd.assert_called_once()
