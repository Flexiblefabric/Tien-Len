import os
import math
from unittest.mock import patch, MagicMock
from pathlib import Path
import pytest
import pygame
import pygame_gui
import tien_len_full
from conftest import make_view, DummyFont, DummySprite, DummyCardSprite

pytest.importorskip("PIL")
pytest.importorskip("pygame")

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")


def test_card_sprite_draw_shadow_blits():
    pygame.init()
    pygame.font.init()
    pygame.display.init()
    with patch("pygame_gui.helpers.get_font", return_value=DummyFont()), patch(
        "pygame_gui.view.get_font", return_value=DummyFont()
    ):
        with patch.object(
            pygame_gui,
            "get_card_image",
            return_value=pygame.Surface((1, 1), pygame.SRCALPHA),
        ):
            sprite = pygame_gui.CardSprite(tien_len_full.Card("Spades", "3"), (0, 0), 1)
    surf = MagicMock()
    sprite.draw_shadow(surf)
    assert surf.blit.call_count > 0
    pygame.quit()


def test_button_draw_uses_nine_patch():
    pygame.init()
    pygame.font.init()
    pygame.display.init()
    rect = pygame.Rect(0, 0, 10, 10)
    surf = pygame.Surface((20, 20))
    btn = pygame_gui.overlays.Button(
        "Play",
        rect,
        lambda: None,
        DummyFont(),
        **{
            "idle_image": pygame.Surface((5, 5)),
            "hover_image": pygame.Surface((5, 5)),
            "pressed_image": pygame.Surface((5, 5)),
        },
    )
    with patch.object(pygame_gui.overlays, "draw_nine_patch") as nine, patch(
        "pygame.draw.rect"
    ) as rect_draw:
        btn.draw(surf)
    nine.assert_called_once()
    rect_draw.assert_not_called()
    pygame.quit()


def test_card_sprite_draw_shadow_uses_default_constants():
    pygame.init()
    pygame.font.init()
    pygame.display.init()
    with patch("pygame_gui.helpers.get_font", return_value=DummyFont()), patch(
        "pygame_gui.view.get_font", return_value=DummyFont()
    ):
        with patch.object(
            pygame_gui,
            "get_card_image",
            return_value=pygame.Surface((1, 1), pygame.SRCALPHA),
        ):
            sprite = pygame_gui.CardSprite(tien_len_full.Card("Spades", "3"), (0, 0), 1)
    from pygame_gui import helpers as h
    h._SHADOW_CACHE.clear()
    base = MagicMock()
    shadow = MagicMock()
    base.copy.return_value = shadow
    h._SHADOW_CACHE[sprite.image.get_size()] = base
    surf = MagicMock()
    sprite.draw_shadow(surf)
    shadow.set_alpha.assert_called_once_with(h.SHADOW_ALPHA)
    expected = (h.SHADOW_BLUR * 2 + 1) ** 2
    assert surf.blit.call_count == expected
    first = surf.blit.call_args_list[0].args[1]
    dx = first.x - sprite.rect.x
    dy = first.y - sprite.rect.y
    assert dx == h.SHADOW_OFFSET[0] - h.SHADOW_BLUR
    assert dy == h.SHADOW_OFFSET[1] - h.SHADOW_BLUR
    pygame.quit()


def test_draw_shadow_cache_cleared_on_size_change():
    pygame.init()
    pygame.font.init()
    pygame.display.init()
    from pygame_gui import helpers as h

    h._SHADOW_CACHE.clear()
    h._SHADOW_SIZE = None

    with patch("pygame_gui.helpers.get_font", return_value=DummyFont()), patch(
        "pygame_gui.view.get_font", return_value=DummyFont()
    ):
        with patch.object(
            pygame_gui,
            "get_card_image",
            return_value=pygame.Surface((2, 3), pygame.SRCALPHA),
        ):
            sprite = pygame_gui.CardSprite(tien_len_full.Card("Spades", "3"), (0, 0), 2)

    surf = pygame.Surface((10, 10))
    sprite.draw_shadow(surf)
    size = sprite.image.get_size()
    assert size in h._SHADOW_CACHE

    # Prepare fake base images for load_card_images
    h._BASE_IMAGES.clear()
    h._BASE_IMAGES["dummy"] = pygame.Surface((10, 14))
    with patch.object(Path, "glob", return_value=[]):
        pygame_gui.load_card_images(5)

    assert not h._SHADOW_CACHE
    pygame.quit()


def test_draw_surface_shadow_blits():
    pygame.init()
    pygame.font.init()
    pygame.display.init()
    target = MagicMock()
    img = pygame.Surface((1, 1), pygame.SRCALPHA)
    rect = img.get_rect()
    pygame_gui.draw_surface_shadow(target, img, rect)
    assert target.blit.call_count > 0
    pygame.quit()


def test_draw_surface_shadow_uses_default_constants():
    pygame.init()
    pygame.font.init()
    pygame.display.init()
    target = MagicMock()
    img = pygame.Surface((2, 2), pygame.SRCALPHA)
    rect = img.get_rect()
    shadow = MagicMock()
    with patch("pygame.Surface", return_value=shadow):
        pygame_gui.draw_surface_shadow(target, img, rect)
    from pygame_gui import helpers as h
    shadow.set_alpha.assert_called_once_with(h.SHADOW_ALPHA)
    expected = (h.SHADOW_BLUR * 2 + 1) ** 2
    assert target.blit.call_count == expected
    first = target.blit.call_args_list[0].args[1]
    dx = first.x - rect.x
    dy = first.y - rect.y
    assert dx == h.SHADOW_OFFSET[0] - h.SHADOW_BLUR
    assert dy == h.SHADOW_OFFSET[1] - h.SHADOW_BLUR
    pygame.quit()


def test_draw_glow_blits():
    pygame.init()
    pygame.font.init()
    pygame.display.init()
    target = MagicMock()
    rect = pygame.Rect(0, 0, 2, 2)
    pygame_gui.draw_glow(target, rect, (255, 0, 0), radius=1, alpha=10)
    assert target.blit.call_count > 0
    pygame.quit()


def test_draw_glow_uses_cache(monkeypatch):
    pygame.init()
    pygame.font.init()
    pygame.display.init()
    from pygame_gui import helpers as h

    h._GLOW_CACHE.clear()

    calls = 0
    orig_surface = pygame.Surface

    def fake_surface(*args, **kwargs):
        nonlocal calls
        calls += 1
        return orig_surface(*args, **kwargs)

    monkeypatch.setattr(pygame, "Surface", fake_surface)

    target = pygame.Surface((10, 10))
    rect = pygame.Rect(0, 0, 2, 2)
    pygame_gui.draw_glow(target, rect, (1, 2, 3), radius=1, alpha=10)
    first = calls
    pygame_gui.draw_glow(target, rect, (1, 2, 3), radius=1, alpha=10)
    assert calls == first

    key = (rect.size, (1, 2, 3), 1, 10)
    assert key in h._GLOW_CACHE
    pygame.quit()


def test_draw_players_uses_draw_shadow():
    view, _ = make_view()
    with patch("pygame_gui.helpers.get_font", return_value=DummyFont()), patch(
        "pygame_gui.view.get_font", return_value=DummyFont()
    ):
        with patch.object(
            pygame_gui,
            "get_card_image",
            return_value=pygame.Surface((1, 1), pygame.SRCALPHA),
        ):
            sprite = pygame_gui.CardSprite(tien_len_full.Card("Spades", "3"), (0, 0), 1)
    view.hand_sprites = pygame.sprite.RenderUpdates(sprite)
    with patch.object(sprite, "draw_shadow") as ds:
        view.draw_players()
        ds.assert_called()
    pygame.quit()


def test_draw_players_labels_use_padding():
    view, _ = make_view()
    view.hand_sprites = pygame.sprite.RenderUpdates()
    view.ai_sprites = []
    view.screen = MagicMock()
    view.screen.get_size.return_value = (200, 200)

    positions = {
        0: (100, 150),
        1: (100, 50),
        2: (50, 100),
        3: (150, 100),
    }

    def player_pos(idx):
        return positions[idx]

    with patch.object(view, "_player_pos", side_effect=player_pos):
        view.draw_players()

    calls = view.screen.blit.call_args_list
    assert len(calls) == 4

    card_w = view.card_width
    card_h = int(card_w * 1.4)
    spacing = min(40, card_w)
    pad_v = card_h // 2 + spacing // 2 + pygame_gui.LABEL_PAD
    pad_h = card_h // 2 + spacing // 2 + pygame_gui.LABEL_PAD

    assert calls[0].args[1].midbottom == (100, 150 - pad_v)
    assert calls[1].args[1].midtop == (100, 50 + pad_v)
    assert calls[2].args[1].midleft == (50 + pad_h, 100)
    assert calls[3].args[1].midright == (150 - pad_h, 100)


def test_player_zone_rect_returns_union():
    view, _ = make_view()
    view.hand_sprites = pygame.sprite.RenderUpdates()
    view.ai_sprites = [pygame.sprite.RenderUpdates() for _ in range(3)]
    rects = [pygame.Rect(1, 2, 4, 5), pygame.Rect(4, 10, 2, 3)]
    sprites = [DummySprite() for _ in rects]
    for sp, r in zip(sprites, rects):
        sp.rect = r
    view.hand_sprites.add(*sprites)
    zone = view._player_zone_rect(0)
    assert zone.topleft == (1, 2)
    assert zone.bottomright == (6, 13)


def test_draw_players_highlights_active_zone():
    view, _ = make_view()
    view.screen = MagicMock()
    view.screen.get_size.return_value = (100, 100)
    view.hand_sprites = pygame.sprite.RenderUpdates()
    view.ai_sprites = [pygame.sprite.RenderUpdates() for _ in range(3)]
    zone = pygame.Rect(0, 0, 10, 10)
    with patch.object(view, "_player_zone_rect", return_value=zone), patch.object(
        pygame_gui.view, "draw_glow"
    ) as glow:
        view.game.current_idx = 2
        view.draw_players()
    assert glow.call_count == 1
    glow.assert_called_with(view.screen, zone, pygame_gui.ZONE_HIGHLIGHT)


def test_animate_sprites_moves_to_destination():
    view, clock = make_view()
    sprite = DummySprite()
    gen = view._animate_sprites([sprite], (10, 15), duration=3 / 60)
    next(gen)
    steps = 0
    while True:
        try:
            gen.send(1 / 60)
            steps += 1
        except StopIteration:
            break
    assert sprite.rect.center == (10, 15)
    expected = math.ceil((3 / 60) / view.animation_speed / (1 / 60))
    assert steps == expected
    pygame.quit()


def test_animate_back_moves_to_destination():
    view, clock = make_view()
    view.screen = MagicMock()
    img = pygame.Surface((1, 1))
    with patch.object(pygame_gui.animations, "get_card_back", return_value=img):
        with patch("pygame.event.pump"), patch("pygame.display.flip"):
            gen = view._animate_back((0, 0), (10, 5), duration=4 / 60)
            next(gen)
            steps = 0
            while True:
                try:
                    gen.send(1 / 60)
                    steps += 1
                except StopIteration:
                    break
    rect = view.screen.blit.call_args_list[-1].args[1]
    assert rect.center == (10, 5)
    move_steps = math.ceil((4 / 60) / view.animation_speed / (1 / 60))
    bounce_steps = math.ceil((0.1) / view.animation_speed / (1 / 60))
    assert steps == move_steps + bounce_steps + 2
    pygame.quit()


def test_animate_flip_moves_to_destination():
    view, clock = make_view()
    view.screen = MagicMock()
    sprite = DummyCardSprite()
    with patch.object(
        pygame_gui, "get_card_back", return_value=pygame.Surface((1, 1))
    ), patch("pygame.event.pump"), patch("pygame.display.flip"):
        gen = view._animate_flip([sprite], (10, 5), duration=4 / 60)
        next(gen)
        steps = 0
        while True:
            try:
                gen.send(1 / 60)
                steps += 1
            except StopIteration:
                break
    assert sprite.rect.center == (10, 5)
    move_steps = math.ceil((4 / 60) / view.animation_speed / (1 / 60))
    bounce_steps = math.ceil((0.1) / view.animation_speed / (1 / 60))
    assert steps == move_steps + bounce_steps + 2
    pygame.quit()


def test_animate_glow_draws_glow():
    view, _ = make_view()
    view.screen = MagicMock()
    sprite = DummyCardSprite()
    with patch.object(pygame_gui.animations, "draw_glow") as glow, patch(
        "pygame.event.pump"
    ), patch("pygame.display.flip"):
        gen = view._animate_glow([sprite], (1, 2, 3), duration=2 / 60)
        next(gen)
        gen.send(1 / 60)
        try:
            gen.send(1 / 60)
        except StopIteration:
            pass
    assert glow.call_count >= 1
    pygame.quit()


def test_bomb_reveal_draws_flash():
    view, _ = make_view()
    view.screen = MagicMock()
    with patch("pygame.event.pump"), patch("pygame.display.flip"):
        gen = view._bomb_reveal(duration=2 / 60)
        next(gen)
        gen.send(1 / 60)
        try:
            gen.send(1 / 60)
        except StopIteration:
            pass
    assert view.screen.blit.call_count >= 1
    pygame.quit()


def test_highlight_turn_draws_at_player_position():
    view, clock = make_view()
    view.screen = MagicMock()
    view.screen.get_size.return_value = (100, 100)
    overlay_surface = MagicMock()
    with patch("pygame.Surface", return_value=overlay_surface) as surf_mock, patch(
        "pygame.event.pump"
    ), patch("pygame.display.flip"), patch("pygame.draw.circle"), patch.object(
        view, "_player_pos", return_value=(50, 100)
    ) as pos:
        gen = view._highlight_turn(0, duration=2 / 60)
        next(gen)
        gen.send(1 / 60)
        try:
            gen.send(1 / 60)
        except StopIteration:
            pass
    pos.assert_called_with(0)
    topleft = (50 - 70, 100 - 30)
    view.screen.blit.assert_called_with(overlay_surface, topleft)
    assert surf_mock.call_count == 1
    assert overlay_surface.fill.call_count == 2
    pygame.quit()


def test_state_methods_update_state():
    view, _ = make_view()
    assert view.state == pygame_gui.GameState.MENU
    with patch("pygame.display.flip"):
        with patch.object(view, "ai_turns"):
            view.close_overlay()
        assert view.state == pygame_gui.GameState.PLAYING
        view.show_in_game_menu()
        assert view.state == pygame_gui.GameState.SETTINGS
        view.show_settings()
        assert view.state == pygame_gui.GameState.SETTINGS
        view.show_menu()
        assert view.state == pygame_gui.GameState.MENU
        view.show_game_over("X")
        assert view.state == pygame_gui.GameState.GAME_OVER
    pygame.quit()


def test_animate_sprites_speed():
    view, clock = make_view()
    sprite = pygame.sprite.Sprite()
    sprite.image = pygame.Surface((1, 1))
    sprite.rect = sprite.image.get_rect()
    with patch("pygame.event.pump"), patch("pygame.display.flip"):
        view.animation_speed = 2.0
        gen = view._animate_sprites([sprite], (0, 0), duration=10 / 60)
        next(gen)
        steps = 0
        while True:
            try:
                gen.send(1 / 60)
                steps += 1
            except StopIteration:
                break
        expected = math.ceil((10 / 60) / view.animation_speed / (1 / 60))
        assert steps == expected
    pygame.quit()


def test_animate_back_speed():
    view, clock = make_view()
    with patch.object(pygame_gui, "get_card_back", return_value=pygame.Surface((1, 1))):
        with patch("pygame.event.pump"), patch("pygame.display.flip"):
            view.animation_speed = 0.5
            gen = view._animate_back((0, 0), (1, 1), duration=10 / 60)
            next(gen)
            steps = 0
            while True:
                try:
                    gen.send(1 / 60)
                    steps += 1
                except StopIteration:
                    break
            move_steps = math.ceil((10 / 60) / view.animation_speed / (1 / 60))
            bounce_steps = math.ceil((0.1) / view.animation_speed / (1 / 60))
            assert steps == move_steps + bounce_steps + 2
    pygame.quit()


def test_highlight_turn_speed():
    view, clock = make_view()
    with patch("pygame.event.pump"), patch("pygame.display.flip"):
        view.animation_speed = 2.0
        gen = view._highlight_turn(0, duration=10 / 60)
        next(gen)
        steps = 0
        while True:
            try:
                gen.send(1 / 60)
                steps += 1
            except StopIteration:
                break
        expected = math.ceil((10 / 60) / view.animation_speed / (1 / 60))
        assert steps == expected
    pygame.quit()


def test_animate_deal_moves_cards():
    view, _ = make_view()
    deck = view._pile_center()
    groups = [view.hand_sprites.sprites()] + [g.sprites() for g in view.ai_sprites]
    dests = [[sp.rect.center for sp in grp] for grp in groups]
    gen = view._animate_deal(duration=1 / 60, delay=0)
    next(gen)
    for grp in groups:
        for sp in grp:
            assert sp.rect.center == deck
    steps = 0
    while True:
        try:
            gen.send(1 / 60)
            steps += 1
        except StopIteration:
            break
    for grp, pos in zip(groups, dests):
        for sp, dest in zip(grp, pos):
            assert sp.rect.center == dest
    total = sum(len(g) for g in groups)
    expected = total * math.ceil((1 / 60) / view.animation_speed / (1 / 60))
    assert steps == expected
    pygame.quit()


def test_state_transitions():
    view, _ = make_view()
    assert view.state == pygame_gui.GameState.MENU
    with patch.object(view, "ai_turns"):
        view.close_overlay()
    assert view.state == pygame_gui.GameState.PLAYING

    view.show_settings()
    assert view.state == pygame_gui.GameState.SETTINGS
    with patch.object(view, "ai_turns"):
        view.handle_key(pygame.K_ESCAPE)
    assert view.state == pygame_gui.GameState.PLAYING

    view.show_game_over("P1")
    assert view.state == pygame_gui.GameState.GAME_OVER
    with patch.object(view, "ai_turns") as mock:
        view.handle_key(pygame.K_ESCAPE)
        mock.assert_not_called()
    assert view.state == pygame_gui.GameState.GAME_OVER
    pygame.quit()
