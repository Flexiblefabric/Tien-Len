import pygame
import pytest

import tienlen_gui
from conftest import make_view

pytest.importorskip("pygame")
pytestmark = pytest.mark.gui


def test_human_hand_uses_fan_layout_for_small_counts():
    view, _ = make_view(300, 200)
    # shrink the human player's hand to a few cards
    view.game.players[0].hand = view.game.players[0].hand[:3]
    view.update_hand_sprites()
    sprites = view.hand_sprites.sprites()
    ys = [s.rect.centery for s in sprites]
    base_y = view._player_pos(0)[1]
    # outer cards should align with base_y while center card is above
    assert ys[0] == base_y
    assert ys[-1] == base_y
    assert min(ys) < base_y
    pygame.quit()
