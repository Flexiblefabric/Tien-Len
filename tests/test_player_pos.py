from unittest.mock import patch

import pygame
import pytest

import tienlen_gui

pytest.importorskip("pygame")

pytestmark = pytest.mark.gui


class DummyFont:
    def render(self, *args, **kwargs):
        return pygame.Surface((1, 1))


def make_view(width=200, height=200):
    pygame.init()
    pygame.font.init()
    pygame.display.init()
    tienlen_gui.clear_font_cache()
    with patch("pygame.display.set_mode", return_value=pygame.Surface((width, height))):
        with (
            patch("tienlen_gui.view.get_font", return_value=DummyFont()),
            patch("tienlen_gui.helpers.get_font", return_value=DummyFont()),
        ):
            with patch.object(tienlen_gui, "load_card_images"):
                view = tienlen_gui.GameView(width, height)
    # Avoid GUI operations during tests
    view._draw_frame = lambda *a, **k: None
    return view


def test_player_pos_returns_expected_coordinates():
    view = make_view(300, 200)
    w, h = view.screen.get_size()
    card_w = view.card_width
    card_h = int(card_w * 1.4)
    margin = min(60, max(40, int(card_w * 0.75)))
    expected = {
        0: (w // 2, view.hand_y),
        1: (w // 2, margin + card_h // 2),
        2: (margin + card_w // 2, h // 2),
        3: (w - margin - card_w // 2, h // 2),
    }
    for idx, pos in expected.items():
        assert view._player_pos(idx) == pos
    pygame.quit()
