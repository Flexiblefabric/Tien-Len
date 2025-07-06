import os
import sys
from unittest.mock import patch

import pytest

# Add repository root to Python path for tests
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Ensure Pygame can initialise a dummy display if available
try:  # Pygame is optional for some tests
    import pygame
except Exception:  # pragma: no cover - pygame may be missing
    pygame = None
else:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
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
            self.selected = False

        def toggle(self):
            self.selected = not self.selected

    class DummyCardSprite(DummySprite):
        def __init__(self, pos=(0, 0)):
            super().__init__(pos)
            import tien_len_full

            self.card = tien_len_full.Card("Spades", "3")
else:  # pragma: no cover - pygame missing
    class DummySprite:
        def __init__(self, pos=(0, 0)):
            self.rect = None
            self.selected = False

        def toggle(self):
            self.selected = not self.selected

    class DummyCardSprite(DummySprite):
        def __init__(self, pos=(0, 0)):
            super().__init__(pos)
            self.card = None


if pygame:
    import pygame_gui  # noqa: E402
else:  # pragma: no cover - pygame missing
    pygame_gui = None


def make_view(width=1, height=1, clock=None):
    """Create a ``GameView`` instance with common patches applied."""

    if not pygame or not pygame_gui:
        pytest.skip("pygame not available")

    pygame.init()
    pygame.font.init()
    pygame.display.init()
    pygame_gui.clear_font_cache()
    clk = clock or DummyClock()
    with patch("pygame.display.set_mode", return_value=pygame.Surface((width, height))):
        with patch("pygame_gui.view.get_font", return_value=DummyFont()), patch(
            "pygame_gui.helpers.get_font", return_value=DummyFont()
        ), patch.object(pygame_gui, "load_card_images"), patch(
            "pygame.time.Clock", return_value=clk
        ):
            view = pygame_gui.GameView(width, height)
            # Ensure deterministic turn order for tests
            view.game.current_idx = 0
            view.game.start_idx = 0
    view._draw_frame = lambda *a, **k: None
    return view, clk
