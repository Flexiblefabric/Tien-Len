import tracemalloc
from unittest.mock import patch

import pygame
import pytest

import tienlen_gui

pytest.importorskip("pygame")

pytestmark = pytest.mark.gui


class DummyFont:
    def render(self, *args, **kwargs):
        return pygame.Surface((1, 1))


class DummyClock:
    def tick(self, *args, **kwargs):
        return 16


def make_view():
    pygame.init()
    pygame.font.init()
    pygame.display.init()
    tienlen_gui.clear_font_cache()
    clock = DummyClock()
    with patch("pygame.display.set_mode", return_value=pygame.Surface((1, 1))):
        with (
            patch("tienlen_gui.view.get_font", return_value=DummyFont()),
            patch("tienlen_gui.helpers.get_font", return_value=DummyFont()),
        ):
            with patch.object(tienlen_gui, "load_card_images"):
                with patch("pygame.time.Clock", return_value=clock):
                    with (
                        patch.object(tienlen_gui.GameView, "_highlight_turn"),
                        patch.object(tienlen_gui.GameView, "_animate_avatar_blink"),
                    ):
                        view = tienlen_gui.GameView(1, 1)
    # Ensure highlight_turn does not access the display during tests
    view._highlight_turn = lambda *a, **k: None
    view._animate_avatar_blink = lambda *a, **k: None
    view._draw_frame = lambda *a, **k: None
    return view


def test_run_memory_usage():
    view = make_view()
    frames = 5

    def side_effect():
        nonlocal frames
        if frames:
            frames -= 1
            return []
        return [pygame.event.Event(pygame.QUIT, {})]

    with patch("pygame.event.get", side_effect=side_effect), patch("pygame.quit"):
        tracemalloc.start()
        before = tracemalloc.take_snapshot()
        view.run()
        after = tracemalloc.take_snapshot()
        tracemalloc.stop()

    diff = after.compare_to(before, "filename")
    total = sum(stat.size_diff for stat in diff)
    assert abs(total) < 60_000
    pygame.quit()
