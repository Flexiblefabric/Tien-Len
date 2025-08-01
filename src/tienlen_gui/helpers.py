"""Minimal Pygame interface for the Tiến Lên card game."""

from __future__ import annotations

from pathlib import Path
import sys
from importlib.resources import files
from typing import Dict, Tuple, List, Optional
from collections import OrderedDict
from enum import Enum, auto

import pygame

from tienlen import Card

# Path to the installed assets directory
ASSETS_DIR = files(__package__).joinpath("assets")
# Path to the bundled TTF font shipped with the package
FONT_FILE = ASSETS_DIR / "fonts" / "DejaVuSans.ttf"

# Reuse the game's logger defined in ``tien_len_full`` so all components
# write to the same rotating log file.


def _mixer_ready() -> bool:
    """Return True if pygame's mixer is initialised."""
    return bool(pygame.mixer.get_init())


# Cache for pygame Font objects keyed by size
_FONT_CACHE: Dict[int, pygame.font.Font] = {}


def get_font(size: int) -> pygame.font.Font:
    """Return a cached ``pygame.font.Font`` for ``size``."""
    # Reinitialise the font module if it was quit to avoid returning
    # invalid ``Font`` objects from the cache.
    if not pygame.font.get_init():
        pygame.font.init()
        _FONT_CACHE.clear()

    if size not in _FONT_CACHE:
        # Use bundled font when available to ensure consistent appearance
        if FONT_FILE.is_file():
            try:
                _FONT_CACHE[size] = pygame.font.Font(str(FONT_FILE), size)
            except Exception:  # pragma: no cover - fall back if font load fails
                _FONT_CACHE[size] = pygame.font.SysFont(None, size)
        else:
            _FONT_CACHE[size] = pygame.font.SysFont(None, size)
    return _FONT_CACHE[size]


def clear_font_cache() -> None:
    """Clear any cached fonts."""
    _FONT_CACHE.clear()


def get_scaled_surface(image: pygame.Surface, size: Tuple[int, int]) -> pygame.Surface:
    """Return ``image`` scaled to ``size`` using an LRU cache."""
    key = (id(image), size)
    surf = _SCALE_CACHE.get(key)
    if surf is None:
        surf = pygame.transform.smoothscale(image, size)
        _SCALE_CACHE[key] = surf
        _SCALE_CACHE.move_to_end(key)
        if len(_SCALE_CACHE) > _SCALE_CACHE_SIZE:
            _SCALE_CACHE.popitem(last=False)
    else:
        _SCALE_CACHE.move_to_end(key)
    return surf


def clear_scale_cache() -> None:
    """Clear the scaled surface cache."""
    _SCALE_CACHE.clear()


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
# Vertical margin below the human player's hand
BOTTOM_MARGIN = 20

# ---------------------------------------------------------------------------
# Margin helpers
# ---------------------------------------------------------------------------


def horizontal_margin(card_width: int) -> int:
    """Return a horizontal margin size based on ``card_width``."""
    return min(40, max(20, int(card_width * 0.5)))


def bottom_margin(card_width: int) -> int:
    """Return the bottom margin below the player's hand."""
    return min(40, max(20, int(card_width * 0.5)))


# Extra padding used when positioning player labels
LABEL_PAD = 10
# Button dimensions and layout spacing
BUTTON_HEIGHT = 40
ZONE_GUTTER = 10
AVATAR_DIR = ASSETS_DIR / "avatars"
AVATAR_SIZE = 40
# Background colour for player hand zones
ZONE_BG = (0, 0, 0, 100)
# Glow color for the active player's zone
ZONE_HIGHLIGHT = (255, 255, 0)

# Shadow drawing defaults
SHADOW_OFFSET = (5, 5)
SHADOW_BLUR = 2
SHADOW_ALPHA = 80

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

    margin = horizontal_margin(card_width)
    start_rel, overlap = calc_start_and_overlap(
        screen_width - 2 * margin,
        count,
        card_width,
        25,
        card_width - 5,
    )
    spacing = card_width - overlap
    return start_rel + margin, spacing


def calc_fan_layout(
    screen_width: int,
    card_width: int,
    count: int,
    base_y: int,
    amplitude: int | None = None,
    angle_range: float = 30,
) -> list[tuple[int, int, float]]:
    """Return ``[(x, y, angle), ...]`` for a fanned hand.

    ``amplitude`` controls the height of the arc and defaults to ``card_width``.
    ``angle_range`` specifies the total rotation spread in degrees.
    """

    if amplitude is None:
        amplitude = card_width

    start_x, spacing = calc_hand_layout(screen_width, card_width, count)
    if count > 1:
        mid = (count - 1) / 2
        step = angle_range / (count - 1)
    else:
        mid = 0
        step = 0

    layout = []
    for i in range(count):
        x = start_x + i * spacing
        if count > 1:
            rel = (i - mid) / mid
            y = base_y - int(amplitude * (1 - rel * rel))
        else:
            y = base_y - amplitude
        angle = (i - mid) * step
        layout.append((int(x), int(y), angle))
    return layout


# ---------------------------------------------------------------------------
# Helpers for loading and caching card images
# ---------------------------------------------------------------------------

_CARD_CACHE: Dict[Tuple[str, int], pygame.Surface] = {}
_BASE_IMAGES: Dict[str, pygame.Surface] = {}
# Cache for card shadow surfaces keyed by (width, height)
_SHADOW_CACHE: Dict[Tuple[int, int], pygame.Surface] = {}
# Track the size currently used to build cached shadows
_SHADOW_SIZE: Tuple[int, int] | None = None
# Cache for glow surfaces keyed by (size, color, radius, alpha)
_GLOW_CACHE: Dict[
    Tuple[Tuple[int, int], Tuple[int, int, int], int, int], pygame.Surface
] = {}
# Cache for nine-patch button images
_NINE_PATCH_CACHE: Dict[str, pygame.Surface] = {}

# Cache for scaled surfaces keyed by (image_id, size)
_SCALE_CACHE: OrderedDict[Tuple[int, Tuple[int, int]], pygame.Surface] = OrderedDict()
_SCALE_CACHE_SIZE = 64


def list_card_back_colors() -> List[str]:
    """Return available card back color names."""
    backs_dir = ASSETS_DIR / "card_backs"
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
    tex_dir = ASSETS_DIR / "tables"
    return sorted(p.stem for p in tex_dir.glob("*.png"))


def list_music_tracks() -> List[str]:
    """Return available music track filenames."""
    mdir = ASSETS_DIR / "music"
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


def load_nine_patch(name: str) -> pygame.Surface:
    """Return a nine-patch image from ``assets/buttons``."""
    if name not in _NINE_PATCH_CACHE:
        path = ASSETS_DIR / "buttons" / f"{name}.png"
        img = pygame.image.load(str(path))
        if pygame.display.get_surface():
            img = img.convert_alpha()
        _NINE_PATCH_CACHE[name] = img
    return _NINE_PATCH_CACHE[name]


def load_button_images(prefix: str, alt: bool = False) -> Dict[str, pygame.Surface]:
    """Load idle/hover/pressed images for a button prefix."""
    suffix = "_alt" if alt else ""
    return {
        "idle_image": load_nine_patch(f"{prefix}_idle{suffix}"),
        "hover_image": load_nine_patch(f"{prefix}_hover{suffix}"),
        "pressed_image": load_nine_patch(f"{prefix}_pressed{suffix}"),
    }


def draw_nine_patch(surface: pygame.Surface, img: pygame.Surface, rect: pygame.Rect) -> None:
    """Draw ``img`` scaled to ``rect`` using a nine-patch split."""
    w, h = img.get_size()
    corner = w // 4
    center_w = w - corner * 2
    center_h = h - corner * 2

    dw, dh = rect.size
    c_w = int(corner * dw / w)
    c_h = int(corner * dh / h)

    pieces = {
        "tl": pygame.Rect(0, 0, corner, corner),
        "top": pygame.Rect(corner, 0, center_w, corner),
        "tr": pygame.Rect(corner + center_w, 0, corner, corner),
        "left": pygame.Rect(0, corner, corner, center_h),
        "mid": pygame.Rect(corner, corner, center_w, center_h),
        "right": pygame.Rect(corner + center_w, corner, corner, center_h),
        "bl": pygame.Rect(0, corner + center_h, corner, corner),
        "bottom": pygame.Rect(corner, corner + center_h, center_w, corner),
        "br": pygame.Rect(corner + center_w, corner + center_h, corner, corner),
    }

    dests = {
        "tl": pygame.Rect(rect.left, rect.top, c_w, c_h),
        "top": pygame.Rect(rect.left + c_w, rect.top, dw - 2 * c_w, c_h),
        "tr": pygame.Rect(rect.right - c_w, rect.top, c_w, c_h),
        "left": pygame.Rect(rect.left, rect.top + c_h, c_w, dh - 2 * c_h),
        "mid": pygame.Rect(rect.left + c_w, rect.top + c_h, dw - 2 * c_w, dh - 2 * c_h),
        "right": pygame.Rect(rect.right - c_w, rect.top + c_h, c_w, dh - 2 * c_h),
        "bl": pygame.Rect(rect.left, rect.bottom - c_h, c_w, c_h),
        "bottom": pygame.Rect(rect.left + c_w, rect.bottom - c_h, dw - 2 * c_w, c_h),
        "br": pygame.Rect(rect.right - c_w, rect.bottom - c_h, c_w, c_h),
    }

    for key, srect in pieces.items():
        drect = dests[key]
        part = img.subsurface(srect)
        if part.get_size() != drect.size:
            part = pygame.transform.smoothscale(part, drect.size)
        surface.blit(part, drect)


def draw_tiled(surface: pygame.Surface, tile: pygame.Surface, rect: pygame.Rect) -> None:
    """Tile ``tile`` across ``rect`` on ``surface``."""
    tw, th = tile.get_size()
    for x in range(rect.left, rect.right, tw):
        for y in range(rect.top, rect.bottom, th):
            surface.blit(tile, (x, y))


def load_card_images(width: int = 80) -> None:
    """Load all card images scaled to ``width`` pixels."""
    cards = ASSETS_DIR / "cards"
    for img in cards.glob("*_of_*.png"):
        key = img.stem
        base = pygame.image.load(str(img)).convert_alpha()
        _BASE_IMAGES[key] = base
    backs = ASSETS_DIR / "card_backs"
    for img in backs.glob("*.png"):
        _BASE_IMAGES[img.stem] = pygame.image.load(str(img)).convert_alpha()
    for key, base in _BASE_IMAGES.items():
        ratio = width / base.get_width()
        _CARD_CACHE[(key, width)] = pygame.transform.smoothscale(
            base, (width, int(base.get_height() * ratio))
        )

    # Rebuild the shadow cache when card sizes change
    global _SHADOW_SIZE
    if _BASE_IMAGES:
        sample = next(iter(_BASE_IMAGES.values()))
        ratio = sample.get_height() / sample.get_width()
        size = (width, int(width * ratio))
        if size != _SHADOW_SIZE:
            _SHADOW_CACHE.clear()
            _SHADOW_SIZE = size


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


def get_card_image(card: Card, width: int) -> Optional[pygame.Surface]:
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
    def __init__(self, card: Card, pos: Tuple[int, int], width: int = 80, rotation: float = 0.0) -> None:
        super().__init__()
        # Import at runtime to allow tests to patch the public helper
        import tienlen_gui

        img = tienlen_gui.get_card_image(card, width)
        if img is None:
            # Render a text fallback
            font = get_font(20)
            img = font.render(str(card), True, (0, 0, 0), (255, 255, 255))

        border = 2
        w, h = img.get_size()
        surf = pygame.Surface((w + border * 2, h + border * 2), pygame.SRCALPHA)
        rect = surf.get_rect()
        pygame.draw.rect(surf, (220, 220, 220), rect, border_radius=5)
        pygame.draw.rect(surf, (0, 0, 0), rect, width=1, border_radius=5)
        surf.blit(img, (border, border))

        self.base_image = surf
        self.angle = rotation
        self.scale = 1.0
        self.image = surf.copy()
        if rotation:
            self.image = pygame.transform.rotate(self.image, rotation)
        self.rect = self.image.get_rect(topleft=pos)
        self.pos = pygame.math.Vector2(self.rect.center)
        self.card = card
        self.selected = False

    def toggle(self) -> None:
        self.selected = not self.selected
        offset = -10 if self.selected else 10
        self.pos.y += offset

    def update(self) -> None:
        self.rect.center = (int(self.pos.x), int(self.pos.y))

    def set_scale(self, scale: float) -> None:
        """Scale the sprite's image about its centre."""
        self.scale = scale
        w, h = self.base_image.get_size()
        img = pygame.transform.smoothscale(
            self.base_image, (int(w * scale), int(h * scale))
        )
        if self.angle:
            img = pygame.transform.rotate(img, self.angle)
        center = self.rect.center
        self.image = img
        self.rect = self.image.get_rect(center=center)
        self.pos.update(self.rect.center)

    def set_angle(self, angle: float) -> None:
        """Rotate the sprite about its centre."""
        self.angle = angle
        self.set_scale(self.scale)

    def set_alpha(self, alpha: int) -> None:
        self.image.set_alpha(alpha)

    def draw_shadow(
        self,
        surface: pygame.Surface,
        offset: Tuple[int, int] = SHADOW_OFFSET,
        blur: int = SHADOW_BLUR,
        alpha: int = SHADOW_ALPHA,
    ) -> None:
        """Draw a simple blurred shadow beneath the card."""
        size = self.image.get_size()
        base = _SHADOW_CACHE.get(size)
        if base is None:
            base = pygame.Surface(size, pygame.SRCALPHA)
            base.fill((0, 0, 0))
            _SHADOW_CACHE[size] = base
        shadow = base.copy()
        shadow.set_alpha(alpha)
        for dx in range(-blur, blur + 1):
            for dy in range(-blur, blur + 1):
                rect = self.rect.move(offset[0] + dx, offset[1] + dy)
                surface.blit(shadow, rect)


def draw_surface_shadow(
    surface: pygame.Surface,
    image: pygame.Surface,
    rect: pygame.Rect,
    offset: Tuple[int, int] = SHADOW_OFFSET,
    blur: int = SHADOW_BLUR,
    alpha: int = SHADOW_ALPHA,
) -> None:
    """Draw a simple blurred shadow beneath ``image`` at ``rect``."""
    shadow = pygame.Surface(image.get_size(), pygame.SRCALPHA)
    shadow.fill((0, 0, 0))
    shadow.set_alpha(alpha)
    for dx in range(-blur, blur + 1):
        for dy in range(-blur, blur + 1):
            r = rect.move(offset[0] + dx, offset[1] + dy)
            surface.blit(shadow, r)


def draw_glow(
    surface: pygame.Surface,
    rect: pygame.Rect,
    color: Tuple[int, int, int],
    radius: int = 8,
    alpha: int = 100,
) -> None:
    """Draw a subtle glow effect behind ``rect`` using cached surfaces."""
    key = (rect.size, color, radius, alpha)
    glow = _GLOW_CACHE.get(key)
    if glow is None:
        size = (rect.width + radius * 2, rect.height + radius * 2)
        glow = pygame.Surface(size, pygame.SRCALPHA)
        overlay = pygame.Surface(size, pygame.SRCALPHA)
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                dist = dx * dx + dy * dy
                if dist <= radius * radius:
                    overlay.fill((*color, alpha // (1 + dist)))
                    glow.blit(overlay, (dx, dy), special_flags=pygame.BLEND_RGBA_ADD)
        _GLOW_CACHE[key] = glow
    surface.blit(glow, (rect.x - radius, rect.y - radius))


class CardBackSprite(pygame.sprite.Sprite):
    def __init__(
        self,
        pos: Tuple[int, int],
        width: int = 80,
        name: str = "card_back",
        rotation: int = 0,
    ) -> None:
        super().__init__()
        # Import at runtime so tests can patch the function via the package
        import tienlen_gui

        img = tienlen_gui.get_card_back(name, width)
        if img is None:
            font = get_font(20)
            img = font.render("[]", True, (0, 0, 0), (255, 255, 255))
        if rotation:
            img = pygame.transform.rotate(img, rotation)
        self.base_image = img
        self.image = img.copy()
        self.rect = self.image.get_rect(topleft=pos)
        self.scale = 1.0

    def set_scale(self, scale: float) -> None:
        self.scale = scale
        w, h = self.base_image.get_size()
        scaled = pygame.transform.smoothscale(
            self.base_image, (int(w * scale), int(h * scale))
        )
        center = self.rect.center
        self.image = scaled
        self.rect = self.image.get_rect(center=center)

    def set_alpha(self, alpha: int) -> None:
        self.image.set_alpha(alpha)


# ---------------------------------------------------------------------------
# Simple button and overlay helpers
# ---------------------------------------------------------------------------
