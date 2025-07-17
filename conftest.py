import os
import sys
from unittest.mock import patch

import pytest

# Add repository root to Python path for tests
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

# Ensure Pygame can initialise a dummy display if available
try:  # Pygame is optional for some tests
    import pygame
except Exception:  # pragma: no cover - pygame may be missing
    pygame = None
else:
    pygame.init()
    pygame.font.init()
    pygame.display.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((1, 1))


class DummyFont:
    def render(self, *args, **kwargs):
        import pygame

        return pygame.Surface((1, 1))

    def get_linesize(self):
        return 1


class DummyClock:
    def __init__(self):
        self.count = 0

    def tick(self, *args, **kwargs):
        self.count += 1
        return 16


if pygame:
    class DummySprite(pygame.sprite.Sprite):
        """Minimal sprite used for input tests."""

        def __init__(self, pos=(0, 0)):
            super().__init__()
            self.image = pygame.Surface((1, 1))
            self.rect = self.image.get_rect(center=pos)
            self.pos = pygame.math.Vector2(self.rect.center)
            self.selected = False

        def toggle(self):
            self.selected = not self.selected

        def update(self):
            self.rect.center = (int(self.pos.x), int(self.pos.y))

    class DummyCardSprite(DummySprite):
        def __init__(self, pos=(0, 0)):
            super().__init__(pos)
            from tienlen import Card

            self.card = Card("Spades", "3")
else:  # pragma: no cover - pygame missing
    class DummySprite:
        def __init__(self, pos=(0, 0)):
            self.rect = None
            self.selected = False
            self.pos = pygame.math.Vector2(pos) if 'pygame' in globals() else pos

        def toggle(self):
            self.selected = not self.selected

        def update(self):
            pass

    class DummyCardSprite(DummySprite):
        def __init__(self, pos=(0, 0)):
            super().__init__(pos)
            self.card = None


if pygame:
    import tienlen_gui  # noqa: E402
else:  # pragma: no cover - pygame missing
    tienlen_gui = None


def make_view(width=1, height=1, clock=None):
    """Create a ``GameView`` instance with common patches applied."""

    if not pygame or not tienlen_gui:
        pytest.skip("pygame not available")

    pygame.init()
    pygame.font.init()
    pygame.display.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((width, height))
    tienlen_gui.clear_font_cache()
    clk = clock or DummyClock()
    with patch("pygame.display.set_mode", return_value=pygame.Surface((width, height))):
        with patch("tienlen_gui.view.get_font", return_value=DummyFont()), patch(
            "tienlen_gui.helpers.get_font", return_value=DummyFont()
        ), patch.object(tienlen_gui, "load_card_images"), patch(
            "pygame.time.Clock", return_value=clk
        ):
            view = tienlen_gui.GameView(width, height)
            # Ensure deterministic turn order for tests
            view.game.current_idx = 0
            view.game.start_idx = 0
    view._draw_frame = lambda *a, **k: None
    return view, clk
