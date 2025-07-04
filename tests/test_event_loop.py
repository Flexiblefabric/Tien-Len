import pytest
pytest.importorskip("pygame")

import os
from unittest.mock import patch

import pygame
import pygame_gui

# Use dummy video driver so no window is opened
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')


class DummyFont:
    def render(self, *args, **kwargs):
        return pygame.Surface((1, 1))


class DummyClock:
    def __init__(self):
        self.count = 0

    def tick(self, *args, **kwargs):
        self.count += 1
        return 16


def make_view():
    pygame.init()
    pygame.font.init()
    pygame.display.init()
    pygame_gui.clear_font_cache()
    clock = DummyClock()
    with patch('pygame.display.set_mode', return_value=pygame.Surface((1, 1))):
        with patch('pygame_gui.view.get_font', return_value=DummyFont()), patch(
            'pygame_gui.helpers.get_font', return_value=DummyFont()
        ):
            with patch.object(pygame_gui, 'load_card_images'):
                with patch('pygame.time.Clock', return_value=clock):
                    with patch.object(pygame_gui.GameView, '_highlight_turn'):
                        view = pygame_gui.GameView(1, 1)
    # Ensure highlight_turn does not access the display during tests
    view._highlight_turn = lambda *a, **k: None
    view._draw_frame = lambda: None
    return view


def test_event_loop_handles_quit():
    view = make_view()

    seq = [
        [pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': (0, 0)})],
        [pygame.event.Event(pygame.QUIT, {})],
    ]

    def side_effect():
        return seq.pop(0) if seq else []

    with patch('pygame.event.get', side_effect=side_effect) as get_mock, \
         patch('pygame.quit') as quit_mock:
        view.run()
        assert get_mock.call_count >= 2
        quit_mock.assert_called_once()
    pygame.quit()
