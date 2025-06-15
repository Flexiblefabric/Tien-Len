import sys
import os
import pygame
from tien_len_full import Game, RANKS, SUITS

# Basic constants for card layout
CARD_WIDTH = 60
CARD_HEIGHT = 90
CARD_GAP = 10
SCREEN_SIZE = (800, 600)
FELT_GREEN = (0, 128, 0)

def load_card_images():
    """Return a {(suit, rank): Surface} mapping for all 52 cards."""

    rank_map = {'J': 'jack', 'Q': 'queen', 'K': 'king', 'A': 'ace', '2': '2'}
    for r in '3 4 5 6 7 8 9 10 J Q K A 2'.split():
        rank_map.setdefault(r, r)

    suit_map = {
        'Spades': 'spades',
        'Hearts': 'hearts',
        'Diamonds': 'diamonds',
        'Clubs': 'clubs',
    }

    images = {}
    for suit, suit_name in suit_map.items():
        for rank in RANKS:
            filename = f"{rank_map[rank]}_of_{suit_name}.png"
            path = os.path.join('assets', filename)
            images[(suit, rank)] = pygame.image.load(path).convert_alpha()
    return images


def draw_hand(screen, font, hand):
    """Draw the first five cards of ``hand`` at the bottom of ``screen``."""
    for i, card in enumerate(hand[:5]):
        x = 50 + i * (CARD_WIDTH + CARD_GAP)
        y = SCREEN_SIZE[1] - CARD_HEIGHT - 40
        rect = pygame.Rect(x, y, CARD_WIDTH, CARD_HEIGHT)
        pygame.draw.rect(screen, (255, 255, 255), rect)
        text = font.render(str(card), True, (0, 0, 0))
        screen.blit(text, (rect.x + 5, rect.y + 5))


def main():
    pygame.init()
    screen = pygame.display.set_mode(SCREEN_SIZE)
    pygame.display.set_caption("Tiến Lên - Pygame Prototype")
    clock = pygame.time.Clock()

    font = pygame.font.SysFont(None, 24)

    game = Game()
    game.setup()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        screen.fill(FELT_GREEN)
        draw_hand(screen, font, game.players[0].hand)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
