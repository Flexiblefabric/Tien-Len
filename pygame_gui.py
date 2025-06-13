import sys
import pygame
from tien_len_full import Game

# Basic constants for card layout
CARD_WIDTH = 60
CARD_HEIGHT = 90
CARD_GAP = 10
SCREEN_SIZE = (800, 600)
FELT_GREEN = (0, 128, 0)


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
