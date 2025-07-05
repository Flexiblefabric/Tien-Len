import pytest

pytest.importorskip("pygame")

import pygame  # noqa: E402
import pygame_gui  # noqa: E402


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
    pygame_gui.clear_font_cache()

    pygame_gui.get_font(12)
    assert calls == [True]


def test_get_font_reinitializes_after_quit(monkeypatch):
    pygame.font.init()
    monkeypatch.setattr(pygame.font, "SysFont", lambda name, size: DummyFont())
    pygame_gui.clear_font_cache()

    first = pygame_gui.get_font(12)
    pygame.font.quit()

    calls = []
    orig_init = pygame.font.init

    def fake_init():
        calls.append(True)
        orig_init()

    monkeypatch.setattr(pygame.font, "init", fake_init)

    second = pygame_gui.get_font(12)

    assert calls == [True]
    assert second is not first
