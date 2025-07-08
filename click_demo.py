"""Minimal example demonstrating correct click detection with scaled images."""

import pygame
from tienlen_gui import load_card_images, get_card_image
from tien_len_full import Card

pygame.init()
screen = pygame.display.set_mode((400, 300))
pygame.display.set_caption("Card Click Demo")

# Load card images at default width
load_card_images(80)
# Get a scaled image and its rect after scaling
card_img = get_card_image(Card('spades', 'A'), 80)  # Ace of spades
scaled_img = pygame.transform.smoothscale(card_img, (120, int(card_img.get_height() * 120 / card_img.get_width())))
card_rect = scaled_img.get_rect(topleft=(140, 90))

clock = pygame.time.Clock()

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if card_rect.collidepoint(event.pos):
                print("Card clicked!")
    screen.fill((0, 128, 0))
    screen.blit(scaled_img, card_rect)
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
