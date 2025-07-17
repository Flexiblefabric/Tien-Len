import hashlib

import pygame
import pytest

from conftest import make_view

pytest.importorskip("pygame")

pytestmark = pytest.mark.gui

BASELINE_MAIN_MENU = "bc83cfecd606f577c01369720e3b64d9"


def _hash_surface(surf: pygame.Surface) -> str:
    return hashlib.md5(pygame.image.tobytes(surf, "RGB")).hexdigest()


def test_main_menu_overlay_snapshot():
    view, _ = make_view(200, 200)
    view.show_menu()
    surf = pygame.Surface((200, 200))
    view.overlay.draw(surf)
    assert _hash_surface(surf) == BASELINE_MAIN_MENU
    pygame.quit()
