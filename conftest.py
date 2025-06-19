import os
import sys

# Add repository root to Python path for tests
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Ensure Pygame can initialise a dummy display if available
try:  # Pygame is optional for some tests
    import pygame

    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.display.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((1, 1))
except Exception:
    pass
