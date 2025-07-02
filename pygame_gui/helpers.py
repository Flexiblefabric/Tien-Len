"""Minimal Pygame interface for the Tiến Lên card game."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple, List, Callable, Optional
from enum import Enum, auto
import json
import logging
import math
import types

import pygame

from tien_len_full import Game, Card, detect_combo, Player
import sound

LOG_FILE = "tien_len_game.log"

logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def _mixer_ready() -> bool:
    """Return True if pygame's mixer is initialised."""
    return bool(pygame.mixer.get_init())


TABLE_THEMES = {
    "darkgreen": (0, 100, 0),
    "saddlebrown": (139, 69, 19),
    "navy": (0, 0, 128),
    "darkred": (139, 0, 0),
}

# Color used for card glows by player index
PLAYER_COLORS = [
    (255, 255, 255),  # Human - white glow
    (255, 100, 100),  # AI Left - red glow
    (100, 100, 255),  # AI Top - blue glow
    (100, 255, 100),  # AI Right - green glow
]

USER_DIR = Path.home() / ".tien_len"
OPTIONS_FILE = USER_DIR / "options.json"
SAVE_FILE = USER_DIR / "saved_game.json"

# Default distance between cards in a player's hand
HAND_SPACING = 20
# Horizontal margin used when centring hands on screen
HORIZONTAL_MARGIN = 20
# Extra padding used when positioning player labels
LABEL_PAD = 10
# Button dimensions and layout spacing
BUTTON_HEIGHT = 40
ZONE_GUTTER = 10
AVATAR_DIR = Path(__file__).with_name("assets") / "avatars"
AVATAR_SIZE = 40

# Helper for positioning card sequences


def calc_start_and_overlap(
    screen_width: int,
    count: int,
    card_width: int,
    min_overlap: int,
    max_overlap: int,
) -> tuple[int, int]:
    """Return `(start_x, overlap)` centred within `screen_width`.

    `overlap` is clamped to the given range and represents how much consecutive
    cards cover one another."""
    if count <= 0:
        return screen_width // 2 - card_width // 2, 0
    min_spacing = card_width - max_overlap
    max_spacing = card_width - min_overlap
    if count > 1:
        fit_spacing = (screen_width - card_width) / (count - 1)
    else:
        fit_spacing = card_width
    spacing = max(min_spacing, min(fit_spacing, max_spacing))
    total_w = card_width + (count - 1) * spacing
    start_x = screen_width // 2 - int(total_w // 2)
    overlap = card_width - spacing
    return int(start_x), int(overlap)


def calc_hand_layout(screen_width: int, card_width: int, count: int) -> tuple[int, int]:
    """Return ``(start_x, spacing)`` for a horizontal hand."""

    start_rel, overlap = calc_start_and_overlap(
        screen_width - 2 * HORIZONTAL_MARGIN,
        count,
        card_width,
        25,
        card_width - 5,
    )
    spacing = card_width - overlap
    return start_rel + HORIZONTAL_MARGIN, spacing


# ---------------------------------------------------------------------------
# Helpers for loading and caching card images
# ---------------------------------------------------------------------------

_CARD_CACHE: Dict[Tuple[str, int], pygame.Surface] = {}
_BASE_IMAGES: Dict[str, pygame.Surface] = {}


def list_card_back_colors() -> List[str]:
    """Return available card back color names."""
    backs_dir = Path(__file__).with_name("assets") / "card_backs"
    colors: List[str] = []
    for img in backs_dir.glob("*.png"):
        stem = img.stem
        if stem == "card_back":
            colors.append("blue")
        elif stem.startswith("card_back_"):
            colors.append(stem.replace("card_back_", ""))
    return sorted(colors)


def list_table_textures() -> List[str]:
    """Return available table texture names."""
    tex_dir = Path(__file__).with_name("assets") / "tables"
    return sorted(p.stem for p in tex_dir.glob("*.png"))


def list_music_tracks() -> List[str]:
    """Return available music track filenames."""
    mdir = Path(__file__).with_name("assets") / "music"
    return sorted(p.name for p in mdir.glob("*.mp3"))


class GameState(Enum):
    """Simple enum representing the game's current state."""

    MENU = auto()
    PLAYING = auto()
    SETTINGS = auto()
    GAME_OVER = auto()


def _image_key(card: Card) -> str:
    rank_map = {"J": "jack", "Q": "queen", "K": "king", "A": "ace"}
    rank = rank_map.get(card.rank, card.rank.lower())
    suit = card.suit.lower()
    return f"{rank}_of_{suit}"


def load_card_images(width: int = 80) -> None:
    """Load all card images scaled to ``width`` pixels."""
    assets = Path(__file__).with_name("assets")
    for img in assets.glob("*_of_*.png"):
        key = img.stem
        base = pygame.image.load(str(img)).convert_alpha()
        _BASE_IMAGES[key] = base
    backs = assets / "card_backs"
    for img in backs.glob("*.png"):
        _BASE_IMAGES[img.stem] = pygame.image.load(str(img)).convert_alpha()
    for key, base in _BASE_IMAGES.items():
        ratio = width / base.get_width()
        _CARD_CACHE[(key, width)] = pygame.transform.smoothscale(
            base, (width, int(base.get_height() * ratio))
        )


def get_card_back(name: str = "card_back", width: int = 80) -> Optional[pygame.Surface]:
    if name not in _BASE_IMAGES:
        return None
    key = (name, width)
    if key not in _CARD_CACHE:
        base = _BASE_IMAGES[name]
        ratio = width / base.get_width()
        _CARD_CACHE[key] = pygame.transform.smoothscale(
            base, (width, int(base.get_height() * ratio))
        )
    return _CARD_CACHE[key]


def get_card_image(card: Card, width: int) -> pygame.Surface:
    key = _image_key(card)
    if (key, width) not in _CARD_CACHE:
        base = _BASE_IMAGES.get(key)
        if base is None:
            return None
        ratio = width / base.get_width()
        _CARD_CACHE[(key, width)] = pygame.transform.smoothscale(
            base, (width, int(base.get_height() * ratio))
        )
    return _CARD_CACHE[(key, width)]


# ---------------------------------------------------------------------------
# Sprite classes
# ---------------------------------------------------------------------------


class CardSprite(pygame.sprite.Sprite):
    def __init__(self, card: Card, pos: Tuple[int, int], width: int = 80) -> None:
        super().__init__()
        img = get_card_image(card, width)
        if img is None:
            # Render a text fallback
            font = pygame.font.SysFont(None, 20)
            img = font.render(str(card), True, (0, 0, 0), (255, 255, 255))

        border = 2
        w, h = img.get_size()
        surf = pygame.Surface((w + border * 2, h + border * 2), pygame.SRCALPHA)
        rect = surf.get_rect()
        pygame.draw.rect(surf, (220, 220, 220), rect, border_radius=5)
        pygame.draw.rect(surf, (0, 0, 0), rect, width=1, border_radius=5)
        surf.blit(img, (border, border))

        self.image = surf
        self.rect = self.image.get_rect(topleft=pos)
        self.card = card
        self.selected = False

    def toggle(self) -> None:
        self.selected = not self.selected
        offset = -10 if self.selected else 10
        self.rect.move_ip(0, offset)

    def draw_shadow(
        self,
        surface: pygame.Surface,
        offset: Tuple[int, int] = (5, 5),
        blur: int = 2,
        alpha: int = 80,
    ) -> None:
        """Draw a simple blurred shadow beneath the card."""
        shadow = pygame.Surface(self.image.get_size(), pygame.SRCALPHA)
        shadow.fill((0, 0, 0))
        shadow.set_alpha(alpha)
        for dx in range(-blur, blur + 1):
            for dy in range(-blur, blur + 1):
                rect = self.rect.move(offset[0] + dx, offset[1] + dy)
                surface.blit(shadow, rect)


def draw_glow(
    surface: pygame.Surface,
    rect: pygame.Rect,
    color: Tuple[int, int, int],
    radius: int = 8,
    alpha: int = 100,
) -> None:
    """Draw a subtle glow effect behind a rect."""
    glow = pygame.Surface(
        (rect.width + radius * 2, rect.height + radius * 2), pygame.SRCALPHA
    )
    for dx in range(-radius, radius + 1):
        for dy in range(-radius, radius + 1):
            dist = dx * dx + dy * dy
            if dist <= radius * radius:
                glow_x = rect.x - radius + dx
                glow_y = rect.y - radius + dy
                glow.fill((*color, alpha // (1 + dist)), special_flags=pygame.BLEND_RGBA_ADD)
                surface.blit(glow, (glow_x, glow_y))


class CardBackSprite(pygame.sprite.Sprite):
    def __init__(
        self,
        pos: Tuple[int, int],
        width: int = 80,
        name: str = "card_back",
        rotation: int = 0,
    ) -> None:
        super().__init__()
        img = get_card_back(name, width)
        if img is None:
            font = pygame.font.SysFont(None, 20)
            img = font.render("[]", True, (0, 0, 0), (255, 255, 255))
        if rotation:
            img = pygame.transform.rotate(img, rotation)
        self.image = img
        self.rect = self.image.get_rect(topleft=pos)


# ---------------------------------------------------------------------------
# Simple button and overlay helpers
# ---------------------------------------------------------------------------


