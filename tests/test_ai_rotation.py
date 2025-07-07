import pygame
import pygame_gui
from unittest.mock import patch, MagicMock
from conftest import DummyFont
import pytest

pytest.importorskip("pygame")


def test_card_back_rotation_calls_pygame_rotate():
    pygame.init()
    pygame.font.init()
    pygame.display.init()
    surf = pygame.Surface((300, 200))
    with patch("pygame.display.set_mode", return_value=surf):
        with patch("pygame_gui.view.get_font", return_value=DummyFont()), patch(
            "pygame_gui.helpers.get_font", return_value=DummyFont()
        ), patch.object(pygame_gui, "load_card_images"), patch.object(
            pygame_gui,
            "get_card_image",
            side_effect=lambda c, w: pygame.Surface((w, int(w * 1.4))),
        ), patch.object(
            pygame_gui,
            "get_card_back",
            side_effect=lambda name, w=1: pygame.Surface((w, int(w * 1.4))),
        ):
            view = pygame_gui.GameView(300, 200)

    with patch(
        "pygame.transform.rotate", side_effect=lambda s, a: s
    ) as rotate, patch.object(
        pygame_gui,
        "get_card_back",
        side_effect=lambda name, w=1: pygame.Surface((w, int(w * 1.4))),
    ):
        view.update_hand_sprites()
    angles = [call.args[1] for call in rotate.call_args_list]
    assert 90 in angles
    assert -90 in angles
    pygame.quit()


def test_rotated_ai_sprites_stay_within_bounds_on_resize():
    pygame.init()
    pygame.font.init()
    pygame.display.init()
    surf_small = pygame.Surface((300, 200))
    surf_large = pygame.Surface((600, 600))
    set_mode = MagicMock(side_effect=[surf_small, surf_large])
    with patch("pygame.display.set_mode", set_mode):
        with patch("pygame_gui.view.get_font", return_value=DummyFont()), patch(
            "pygame_gui.helpers.get_font", return_value=DummyFont()
        ):
            with patch.object(pygame_gui, "load_card_images"), patch.object(
                pygame_gui,
                "get_card_image",
                side_effect=lambda c, w: pygame.Surface((w, int(w * 1.4))),
            ), patch.object(
                pygame_gui,
                "get_card_back",
                side_effect=lambda name, w=1: pygame.Surface((w, int(w * 1.4))),
            ):
                view = pygame_gui.GameView(300, 200)
                view.on_resize(600, 600)

                w, h = view.screen.get_size()
                left_group = view.ai_sprites[1].sprites()
                right_group = view.ai_sprites[2].sprites()

                assert all(sp.rect.left >= 0 for sp in left_group)
                assert all(sp.rect.right <= w for sp in left_group)
                assert all(sp.rect.top >= 0 for sp in left_group)
                assert all(sp.rect.bottom <= h for sp in left_group)

                assert all(sp.rect.left >= 0 for sp in right_group)
                assert all(sp.rect.right <= w for sp in right_group)
                assert all(sp.rect.top >= 0 for sp in right_group)
                assert all(sp.rect.bottom <= h for sp in right_group)
    pygame.quit()
