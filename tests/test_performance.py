import os
import time
import pytest
pytest.importorskip("pygame")

import pygame
import pygame_gui
from unittest.mock import patch

# Use dummy video driver so no window is opened
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")


class DummyFont:
    def render(self, *args, **kwargs):
        return pygame.Surface((1, 1))


class PerfClock:
    def __init__(self):
        self.times = []
        self.last = time.perf_counter()

    def tick(self, *args, **kwargs):
        now = time.perf_counter()
        self.times.append(now - self.last)
        self.last = now


def make_view():
    pygame.display.init()
    clock = PerfClock()
    with patch("pygame.display.set_mode", return_value=pygame.Surface((1, 1))):
        with patch("pygame.font.SysFont", return_value=DummyFont()):
            with patch.object(pygame_gui, "load_card_images"):
                with patch("pygame.time.Clock", return_value=clock):
                    view = pygame_gui.GameView(1, 1)
    # Avoid GUI operations during tests
    view._highlight_turn = lambda *a, **k: None
    view._draw_frame = lambda: None
    return view, clock


def test_average_frame_time_below_threshold():
    view, clock = make_view()
    frames = 10

    def side_effect():
        nonlocal frames
        if frames:
            frames -= 1
            return []
        return [pygame.event.Event(pygame.QUIT, {})]

    with patch("pygame.event.get", side_effect=side_effect), patch("pygame.quit"):
        view.run()

    avg = sum(clock.times) / len(clock.times)
    assert avg < 0.05
    pygame.quit()

