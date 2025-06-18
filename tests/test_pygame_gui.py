import os
from unittest.mock import patch, MagicMock

# Use dummy video driver so no window is opened
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

import pygame
import pygame_gui


class DummyFont:
    def render(self, *args, **kwargs):
        return pygame.Surface((1, 1))


class DummyClock:
    def __init__(self):
        self.count = 0

    def tick(self, *args, **kwargs):
        self.count += 1


def make_view():
    pygame.display.init()
    clock = DummyClock()
    with patch('pygame.display.set_mode', return_value=pygame.Surface((1, 1))):
        with patch('pygame.font.SysFont', return_value=DummyFont()):
            with patch.object(pygame_gui, 'load_card_images'):
                with patch('pygame.time.Clock', return_value=clock):
                    view = pygame_gui.GameView(1, 1)
    view._draw_frame = lambda: None
    return view, clock


def test_update_hand_sprites():
    pygame.display.init()
    with patch('pygame.display.set_mode', return_value=pygame.Surface((1, 1))):
        with patch('pygame.font.SysFont', return_value=DummyFont()):
            with patch.object(pygame_gui, 'load_card_images'):
                view = pygame_gui.GameView(1, 1)
                view.update_hand_sprites()
                assert len(view.hand_sprites) == len(view.game.players[0].hand)
    pygame.quit()


def test_animate_sprites_speed():
    view, clock = make_view()
    sprite = pygame.sprite.Sprite()
    sprite.image = pygame.Surface((1, 1))
    sprite.rect = sprite.image.get_rect()
    with patch('pygame.event.pump'), patch('pygame.display.flip'):
        view.animation_speed = 2.0
        view._animate_sprites([sprite], (0, 0), frames=10)
        assert clock.count == 5
    pygame.quit()


def test_animate_back_speed():
    view, clock = make_view()
    with patch.object(pygame_gui, 'get_card_back', return_value=pygame.Surface((1, 1))):
        with patch('pygame.event.pump'), patch('pygame.display.flip'):
            view.animation_speed = 0.5
            view._animate_back((0, 0), (1, 1), frames=10)
            assert clock.count == 20
    pygame.quit()


def test_highlight_turn_speed():
    view, clock = make_view()
    with patch('pygame.event.pump'), patch('pygame.display.flip'):
        view.animation_speed = 2.0
        view._highlight_turn(0, frames=10)
        assert clock.count == 5
    pygame.quit()


def test_state_transitions():
    view, _ = make_view()
    assert view.state == pygame_gui.GameState.MENU
    with patch.object(view, 'ai_turns'):
        view.close_overlay()
    assert view.state == pygame_gui.GameState.PLAYING

    view.show_settings()
    assert view.state == pygame_gui.GameState.SETTINGS
    with patch.object(view, 'ai_turns'):
        view.handle_key(pygame.K_ESCAPE)
    assert view.state == pygame_gui.GameState.PLAYING

    view.show_game_over('P1')
    assert view.state == pygame_gui.GameState.GAME_OVER
    with patch.object(view, 'ai_turns') as mock:
        view.handle_key(pygame.K_ESCAPE)
        mock.assert_not_called()
    assert view.state == pygame_gui.GameState.GAME_OVER
    pygame.quit()


def test_on_resize_rebuilds_sprites():
    pygame.display.init()
    surf_small = pygame.Surface((300, 200))
    surf_large = pygame.Surface((650, 400))
    set_mode = MagicMock(side_effect=[surf_small, surf_large])
    with patch('pygame.display.set_mode', set_mode):
        with patch('pygame.font.SysFont', return_value=DummyFont()):
            with patch.object(pygame_gui, 'load_card_images') as load_images, \
                 patch.object(pygame_gui, 'get_card_image', side_effect=lambda c, w: pygame.Surface((w, 1))):
                view = pygame_gui.GameView(300, 200)
                view.update_hand_sprites()
                start_width = view.card_width
                first = next(iter(view.hand_sprites))
                assert first.rect.width == start_width

                view.on_resize(650, 400)
                new_width = view.card_width
                assert new_width != start_width
                first = next(iter(view.hand_sprites))
                assert first.rect.width == new_width
                load_images.assert_called_with(new_width)
    pygame.quit()


def test_toggle_fullscreen_sets_flags_and_rescales():
    pygame.display.init()
    surf = pygame.Surface((300, 200))
    set_mode = MagicMock(return_value=surf)
    with patch('pygame.display.set_mode', set_mode):
        with patch('pygame.font.SysFont', return_value=DummyFont()):
            with patch.object(pygame_gui, 'load_card_images') as load_images, \
                 patch.object(pygame_gui, 'get_card_image', side_effect=lambda c, w: pygame.Surface((w, 1))):
                with patch('pygame.display.toggle_fullscreen'):
                    view = pygame_gui.GameView(300, 200)
                    load_images.reset_mock()
                    set_mode.reset_mock()

                    view.toggle_fullscreen()
                    set_mode.assert_called_with((300, 200), pygame.FULLSCREEN)
                    load_images.assert_called_with(view.card_width)
                    fs_width = view.card_width

                    view.toggle_fullscreen()
                    set_mode.assert_called_with((300, 200), pygame.RESIZABLE)
                    assert load_images.call_args_list[-1][0][0] == view.card_width
                    assert view.card_width == fs_width  # width unchanged for same size
    pygame.quit()
