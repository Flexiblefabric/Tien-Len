from pathlib import Path

import pygame
import pytest

import tienlen_gui

pytest.importorskip("pygame")

pytestmark = pytest.mark.gui


def test_get_font_initializes_pygame_font(monkeypatch):
    pygame.font.quit()
    calls = []
    orig_init = pygame.font.init

    def fake_init():
        calls.append(True)
        orig_init()

    monkeypatch.setattr(pygame.font, "init", fake_init)

    tienlen_gui.clear_font_cache()
    font = tienlen_gui.get_font(12)

    assert calls == [True]
    assert isinstance(font, pygame.font.Font)


def test_get_font_reinitializes_after_quit(monkeypatch):
    pygame.font.init()
    tienlen_gui.clear_font_cache()

    first = tienlen_gui.get_font(12)
    pygame.font.quit()

    calls = []
    orig_init = pygame.font.init

    def fake_init():
        calls.append(True)
        orig_init()

    monkeypatch.setattr(pygame.font, "init", fake_init)

    second = tienlen_gui.get_font(12)

    assert calls == [True]
    assert second is not first
    assert isinstance(second, pygame.font.Font)


def test_get_font_falls_back_to_sysfont_when_missing(monkeypatch):
    sysfont_calls = []
    orig_sysfont = pygame.font.SysFont

    def fake_sysfont(name, size):
        sysfont_calls.append(True)
        return orig_sysfont(name, size)

    monkeypatch.setattr(pygame.font, "SysFont", fake_sysfont)
    monkeypatch.setattr(tienlen_gui.helpers, "FONT_FILE", Path("nonexistent.ttf"))

    tienlen_gui.clear_font_cache()
    font = tienlen_gui.get_font(12)

    assert sysfont_calls == [True]
    assert isinstance(font, pygame.font.Font)
