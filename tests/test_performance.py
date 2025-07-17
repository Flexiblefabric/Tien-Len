import time
from unittest.mock import patch

import pygame
import pytest

import tienlen_gui

pytest.importorskip("pygame")

pytestmark = pytest.mark.gui


class DummyFont:
    def render(self, *args, **kwargs):
        return pygame.Surface((1, 1))


class PerfClock:
    def __init__(self):
        self.times = []
        self.last = time.perf_counter()
        self.args = []

    def tick(self, *args, **kwargs):
        now = time.perf_counter()
        self.times.append(now - self.last)
        self.last = now
        if args:
            self.args.append(args[0])
        return int((self.times[-1]) * 1000)


def make_view():
    pygame.init()
    pygame.font.init()
    pygame.display.init()
    clock = PerfClock()
    tienlen_gui.clear_font_cache()
    with patch("pygame.display.set_mode", return_value=pygame.Surface((1, 1))):
        with (
            patch("tienlen_gui.view.get_font", return_value=DummyFont()),
            patch("tienlen_gui.helpers.get_font", return_value=DummyFont()),
        ):
            with patch.object(tienlen_gui, "load_card_images"):
                with patch("pygame.time.Clock", return_value=clock):
                    view = tienlen_gui.GameView(1, 1)
    # Avoid GUI operations during tests
    view._highlight_turn = lambda *a, **k: None
    view._animate_avatar_blink = lambda *a, **k: None
    view._draw_frame = lambda *a, **k: None
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


def test_custom_fps_limit_passed_to_clock():
    view, clock = make_view()
    view.fps_limit = 30

    with (
        patch(
            "pygame.event.get",
            return_value=[pygame.event.Event(pygame.QUIT, {})],
        ),
        patch("pygame.quit"),
    ):
        view.run()

    assert clock.args[0] == 30
    pygame.quit()
