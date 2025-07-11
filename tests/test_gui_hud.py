import os
from unittest.mock import patch
import pytest
import pygame
import tienlen_gui
import tien_len_full
from conftest import make_view

pytest.importorskip("PIL")
pytest.importorskip("pygame")

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")


def test_hud_panel_displays_count_and_last_move():
    view, _ = make_view()
    player = view.game.players[1]
    player.hand = [tien_len_full.Card("Spades", "3"), tien_len_full.Card("Hearts", "4")]
    view.game.history.append((0, f"{player.name} plays something"))
    hud = tienlen_gui.HUDPanel(view, 1)

    with patch.object(view, "_hud_box", return_value=pygame.Surface((1, 1))) as hud_box:
        hud._create_surface()

    lines = hud_box.call_args.args[0]
    assert lines[0] == f"{player.name} ({len(player.hand)})"
    assert lines[1].startswith(player.name)
    pygame.quit()


def test_developer_mode_reveals_ai_hand():
    view, _ = make_view()
    player = view.game.players[1]
    player.hand = [tien_len_full.Card("Spades", "3"), tien_len_full.Card("Diamonds", "4")]
    hud = tienlen_gui.HUDPanel(view, 1)

    with patch.object(view, "_hud_box", return_value=pygame.Surface((1, 1))):
        with patch("tienlen_gui.get_card_image", return_value=pygame.Surface((1, 1))) as get_img:
            view.developer_mode = False
            hud._create_surface()
            assert get_img.call_count == 0
            view.developer_mode = True
            hud._create_surface()
            assert get_img.call_count == len(player.hand)
    pygame.quit()


def test_hud_highlight_switches_on_turn_change():
    view, _ = make_view()
    surf = pygame.Surface((10, 10))
    hud1 = tienlen_gui.HUDPanel(view, 1)
    hud2 = tienlen_gui.HUDPanel(view, 2)

    panel = pygame.Surface((1, 1))
    with (
        patch.object(hud1, "_create_surface", return_value=panel),
        patch.object(hud2, "_create_surface", return_value=panel),
        patch("tienlen_gui.hud.draw_glow") as glow,
    ):
        view.game.current_idx = 1
        hud1.draw(surf)
        hud2.draw(surf)
        assert glow.call_count == 1
        glow.reset_mock()
        view.game.current_idx = 2
        hud1.draw(surf)
        hud2.draw(surf)
        assert glow.call_count == 1
    pygame.quit()
