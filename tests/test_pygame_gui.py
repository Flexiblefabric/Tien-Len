import os
from unittest.mock import patch

# Use dummy video driver so no window is opened
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

import pygame
import pygame_gui


class DummyFont:
    def render(self, *args, **kwargs):
        return pygame.Surface((1, 1))


def test_update_hand_sprites():
    pygame.display.init()
    with patch('pygame.display.set_mode', return_value=pygame.Surface((1, 1))):
        with patch('pygame.font.SysFont', return_value=DummyFont()):
            with patch.object(pygame_gui, 'load_card_images'):
                view = pygame_gui.GameView(1, 1)
                view.update_hand_sprites()
                assert len(view.hand_sprites) == len(view.game.players[0].hand)
    pygame.quit()
