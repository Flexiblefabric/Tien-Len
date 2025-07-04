import pytest
pytest.importorskip("pygame")

import pygame
import pygame_gui

class DummyFont:
    def render(self, *args, **kwargs):
        return pygame.Surface((1, 1))


def test_get_font_initializes_pygame_font(monkeypatch):
    calls = []

    def fake_init():
        calls.append(True)

    monkeypatch.setattr(pygame.font, "init", fake_init)
    monkeypatch.setattr(pygame.font, "SysFont", lambda name, size: DummyFont())

    # Clear any cached fonts so the function creates a new one
    pygame_gui._FONT_CACHE.clear()

    pygame_gui.get_font(12)
    assert calls == [True]
