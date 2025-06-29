import pytest

pytest.importorskip("PIL")
pytest.importorskip("pygame")

import os
from unittest.mock import patch, MagicMock

# Use dummy video driver so no window is opened
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pygame_gui
import tien_len_full
import sound


class DummyFont:
    def render(self, *args, **kwargs):
        return pygame.Surface((1, 1))

    def get_linesize(self):
        return 1


class DummyClock:
    def __init__(self):
        self.count = 0

    def tick(self, *args, **kwargs):
        self.count += 1


def make_view():
    pygame.display.init()
    clock = DummyClock()
    with patch("pygame.display.set_mode", return_value=pygame.Surface((1, 1))):
        with patch("pygame.font.SysFont", return_value=DummyFont()):
            with patch.object(pygame_gui, "load_card_images"):
                with patch("pygame.time.Clock", return_value=clock):
                    view = pygame_gui.GameView(1, 1)
    view._draw_frame = lambda: None
    return view, clock


def test_update_hand_sprites():
    pygame.display.init()
    with patch("pygame.display.set_mode", return_value=pygame.Surface((1, 1))):
        with patch("pygame.font.SysFont", return_value=DummyFont()):
            with patch.object(pygame_gui, "load_card_images"):
                view = pygame_gui.GameView(1, 1)
                view.update_hand_sprites()
                assert len(view.hand_sprites) == len(view.game.players[0].hand)
    pygame.quit()


class DummySprite(pygame.sprite.Sprite):
    """Minimal sprite used for input tests."""

    def __init__(self, pos=(0, 0)):
        super().__init__()
        self.image = pygame.Surface((1, 1))
        self.rect = self.image.get_rect(center=pos)
        self.selected = False

    def toggle(self):
        self.selected = not self.selected


class DummyCardSprite(DummySprite):
    def __init__(self, pos=(0, 0)):
        super().__init__(pos)
        self.card = tien_len_full.Card("Spades", "3")


def test_handle_key_shortcuts():
    view, _ = make_view()
    view.state = pygame_gui.GameState.PLAYING

    with patch.object(view, "play_selected") as play:
        view.handle_key(pygame.K_RETURN)
        play.assert_called_once()

    with patch.object(view, "pass_turn") as pass_turn:
        view.handle_key(pygame.K_SPACE)
        pass_turn.assert_called_once()

    with patch.object(view, "show_menu") as show_menu:
        view.handle_key(pygame.K_m)
        show_menu.assert_called_once()

    with patch.object(view, "show_settings") as show_settings:
        view.handle_key(pygame.K_o)
        show_settings.assert_called_once()
    pygame.quit()


def test_handle_mouse_select_and_overlay():
    view, _ = make_view()
    sprite = DummySprite()
    center = sprite.rect.center
    view.hand_sprites = pygame.sprite.OrderedUpdates(sprite)
    view.selected = []
    view.state = pygame_gui.GameState.PLAYING
    view.action_buttons = []

    view.handle_mouse(center)
    assert sprite.selected is True
    assert sprite in view.selected

    view.handle_mouse(center)
    assert sprite.selected is False
    assert sprite not in view.selected

    view.state = pygame_gui.GameState.MENU
    overlay = MagicMock()
    view.overlay = overlay
    view.handle_mouse((5, 5))
    event = overlay.handle_event.call_args[0][0]
    assert event.pos == (5, 5)
    pygame.quit()


def test_handle_mouse_selects_rightmost_sprite():
    view, _ = make_view()
    left = DummySprite((5, 5))
    right = DummySprite((5, 5))
    view.hand_sprites = pygame.sprite.OrderedUpdates(left, right)
    view.selected = []
    view.state = pygame_gui.GameState.PLAYING
    view.action_buttons = []
    with patch.object(view, "update_play_button_state"), patch.object(
        view, "_highlight_turn"
    ):
        view.handle_mouse((5, 5))
    assert right.selected is True
    assert right in view.selected
    assert left.selected is False
    pygame.quit()


def test_update_play_button_state_enables_button_on_valid_selection():
    view, _ = make_view()
    card_sprite = DummyCardSprite()
    view.selected = [card_sprite]
    btn = view.action_buttons[0]
    with patch.object(view.game, "is_valid", return_value=(True, "")) as mock:
        view.update_play_button_state()
    mock.assert_called_once_with(
        view.game.players[view.game.current_idx],
        [card_sprite.card],
        view.game.current_combo,
    )
    assert btn.enabled is True


def test_update_play_button_state_disables_when_invalid():
    view, _ = make_view()
    card_sprite = DummyCardSprite()
    view.selected = [card_sprite]
    btn = view.action_buttons[0]
    with patch.object(view.game, "is_valid", return_value=(False, "bad")):
        view.update_play_button_state()
    assert btn.enabled is False


def test_handle_mouse_calls_update_play_button_state():
    view, _ = make_view()
    sprite = DummyCardSprite((5, 5))
    view.hand_sprites = pygame.sprite.OrderedUpdates(sprite)
    view.selected = []
    view.state = pygame_gui.GameState.PLAYING
    view.action_buttons = []
    with patch.object(view, "update_play_button_state") as upd, patch.object(
        view, "_highlight_turn"
    ):
        view.handle_mouse(sprite.rect.center)
        upd.assert_called()


def test_update_hand_sprites_calls_update_play_button_state():
    view, _ = make_view()
    with patch.object(view, "update_play_button_state") as upd:
        view.update_hand_sprites()
        upd.assert_called_once()


def test_card_sprite_draw_shadow_blits():
    pygame.display.init()
    with patch("pygame.font.SysFont", return_value=DummyFont()):
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


def test_draw_players_uses_draw_shadow():
    view, _ = make_view()
    with patch("pygame.font.SysFont", return_value=DummyFont()):
        with patch.object(
            pygame_gui,
            "get_card_image",
            return_value=pygame.Surface((1, 1), pygame.SRCALPHA),
        ):
            sprite = pygame_gui.CardSprite(tien_len_full.Card("Spades", "3"), (0, 0), 1)
    view.hand_sprites = pygame.sprite.OrderedUpdates(sprite)
    with patch.object(sprite, "draw_shadow") as ds:
        view.draw_players()
        ds.assert_called()
    pygame.quit()


def test_draw_players_labels_use_padding():
    view, _ = make_view()
    view.hand_sprites = pygame.sprite.OrderedUpdates()
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


def test_animate_sprites_moves_to_destination():
    view, clock = make_view()
    sprite = DummySprite()
    with patch("pygame.event.pump"), patch("pygame.display.flip"):
        view._animate_sprites([sprite], (10, 15), frames=3)
    assert sprite.rect.center == (10, 15)
    assert clock.count == 3
    pygame.quit()


def test_animate_back_moves_to_destination():
    view, clock = make_view()
    view.screen = MagicMock()
    rect = pygame.Rect(0, 0, 1, 1)
    img = MagicMock()
    img.get_rect.return_value = rect
    with patch.object(pygame_gui, "get_card_back", return_value=img):
        with patch("pygame.event.pump"), patch("pygame.display.flip"):
            view._animate_back((0, 0), (10, 5), frames=4)
    assert rect.center == (10, 5)
    assert clock.count == 10
    pygame.quit()


def test_animate_flip_moves_to_destination():
    view, clock = make_view()
    view.screen = MagicMock()
    sprite = DummyCardSprite()
    with patch.object(
        pygame_gui, "get_card_back", return_value=pygame.Surface((1, 1))
    ), patch("pygame.event.pump"), patch("pygame.display.flip"):
        view._animate_flip([sprite], (10, 5), frames=4)
    assert sprite.rect.center == (10, 5)
    assert clock.count == 10
    pygame.quit()


def test_highlight_turn_draws_at_player_position():
    view, clock = make_view()
    view.screen = MagicMock()
    view.screen.get_size.return_value = (100, 100)
    overlay_surface = MagicMock()
    with patch("pygame.Surface", return_value=overlay_surface), patch(
        "pygame.event.pump"
    ), patch("pygame.display.flip"), patch("pygame.draw.circle"), patch.object(
        view, "_player_pos", return_value=(50, 100)
    ) as pos:
        view._highlight_turn(0, frames=2)
    pos.assert_called_with(0)
    topleft = (50 - 70, 100 - 30)
    view.screen.blit.assert_called_with(overlay_surface, topleft)
    assert clock.count == 2
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
        view._animate_sprites([sprite], (0, 0), frames=10)
        assert clock.count == 5
    pygame.quit()


def test_animate_back_speed():
    view, clock = make_view()
    with patch.object(pygame_gui, "get_card_back", return_value=pygame.Surface((1, 1))):
        with patch("pygame.event.pump"), patch("pygame.display.flip"):
            view.animation_speed = 0.5
            view._animate_back((0, 0), (1, 1), frames=10)
            assert clock.count == 32
    pygame.quit()


def test_highlight_turn_speed():
    view, clock = make_view()
    with patch("pygame.event.pump"), patch("pygame.display.flip"):
        view.animation_speed = 2.0
        view._highlight_turn(0, frames=10)
        assert clock.count == 5
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


def test_on_resize_rebuilds_sprites():
    pygame.display.init()
    surf_small = pygame.Surface((300, 200))
    surf_large = pygame.Surface((650, 400))
    set_mode = MagicMock(side_effect=[surf_small, surf_large])
    with patch("pygame.display.set_mode", set_mode):
        with patch("pygame.font.SysFont", return_value=DummyFont()):
            with patch.object(
                pygame_gui, "load_card_images"
            ) as load_images, patch.object(
                pygame_gui,
                "get_card_image",
                side_effect=lambda c, w: pygame.Surface((w, 1)),
            ):
                view = pygame_gui.GameView(300, 200)
                view.update_hand_sprites()
                start_width = view.card_width
                first = next(iter(view.hand_sprites))
                assert first.rect.width >= start_width

                view.on_resize(650, 400)
                new_width = view.card_width
                assert new_width != start_width
                first = next(iter(view.hand_sprites))
                assert first.rect.width >= new_width
                load_images.assert_called_with(new_width)
    pygame.quit()


def test_toggle_fullscreen_sets_flags_and_rescales():
    pygame.display.init()
    surf = pygame.Surface((300, 200))
    set_mode = MagicMock(return_value=surf)
    with patch("pygame.display.set_mode", set_mode):
        with patch("pygame.font.SysFont", return_value=DummyFont()):
            with patch.object(
                pygame_gui, "load_card_images"
            ) as load_images, patch.object(
                pygame_gui,
                "get_card_image",
                side_effect=lambda c, w: pygame.Surface((w, 1)),
            ):
                with patch("pygame.display.toggle_fullscreen"):
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


def test_action_buttons_created_and_clickable():
    view, _ = make_view()
    texts = [b.text for b in view.action_buttons]
    assert texts == ["Play", "Pass", "Undo"]

    btn = view.action_buttons[0]
    btn.callback = MagicMock()
    view.state = pygame_gui.GameState.PLAYING
    view.handle_mouse(btn.rect.center)
    btn.callback.assert_called_once()


def test_undo_button_disabled_when_no_snapshot():
    view, _ = make_view()
    undo = next(b for b in view.action_buttons if b.text == "Undo")
    undo.callback = MagicMock()
    view.state = pygame_gui.GameState.PLAYING
    view.game.snapshots = ["s1"]
    view.handle_mouse(undo.rect.center)
    undo.callback.assert_not_called()
    view.game.snapshots.append("s2")
    view.handle_mouse(undo.rect.center)
    undo.callback.assert_called_once()


def test_undo_button_triggers_game_undo_last():
    view, _ = make_view()
    undo_btn = next(b for b in view.action_buttons if b.text == "Undo")
    view.state = pygame_gui.GameState.PLAYING
    view.game.snapshots.append("s2")
    with patch.object(
        view.game, "undo_last", return_value=True
    ) as undo_mock, patch.object(view, "_highlight_turn"):
        view.handle_mouse(undo_btn.rect.center)
        undo_mock.assert_called_once()
    pygame.quit()


def test_on_resize_calls_create_action_buttons():
    view, _ = make_view()
    with patch.object(view, "_create_action_buttons") as create:
        view.on_resize(100, 100)
        create.assert_called_once()


def test_apply_options_updates_game_and_audio():
    view, _ = make_view()
    p0 = view.game.players[0]
    view.table_color_name = "navy"
    view.player_name = "Alice"
    view.sort_mode = "suit"
    view.ai_level = "Hard"
    view.ai_personality = "aggressive"
    view.ai_lookahead = True
    view.fx_volume = 0.7
    view.music_volume = 0.5
    view.sound_enabled = True
    view.music_enabled = False
    with patch.object(sound, "set_volume") as sv, patch.object(
        view.game, "set_ai_level"
    ) as sal, patch.object(view.game, "set_personality") as sp, patch.object(
        pygame_gui, "_mixer_ready", return_value=True
    ), patch.object(
        view, "update_hand_sprites"
    ), patch(
        "pygame.mixer.music.set_volume"
    ) as mv, patch(
        "pygame.mixer.music.pause"
    ) as pause, patch(
        "pygame.mixer.music.unpause"
    ) as unpause:
        view.apply_options()
    assert view.table_color == pygame_gui.TABLE_THEMES["navy"]
    assert p0.name == "Alice"
    sal.assert_called_with("Hard")
    sp.assert_called_with("aggressive")
    assert view.game.ai_lookahead is True
    sv.assert_called_with(0.7)
    mv.assert_called_with(0.5)
    pause.assert_called_once()
    unpause.assert_not_called()


def test_toggle_fullscreen_flag_toggles():
    with patch("pygame.display.set_mode", return_value=pygame.Surface((1, 1))):
        with patch("pygame.font.SysFont", return_value=DummyFont()):
            with patch.object(pygame_gui, "load_card_images"):
                with patch("pygame.display.toggle_fullscreen"):
                    view = pygame_gui.GameView(100, 100)
                    start = view.fullscreen
                    view.toggle_fullscreen()
                    assert view.fullscreen != start
                    view.toggle_fullscreen()
                    assert view.fullscreen == start


def test_on_resize_updates_screen_size():
    view, _ = make_view()
    with patch(
        "pygame.display.set_mode", return_value=pygame.Surface((1, 1))
    ) as sm, patch.object(pygame_gui, "load_card_images"), patch.object(
        view, "update_hand_sprites"
    ) as uh, patch.object(
        view, "_create_action_buttons"
    ) as cab:
        view.on_resize(300, 200)
    sm.assert_called_with((300, 200), pygame.RESIZABLE)
    uh.assert_called_once()
    cab.assert_called_once()


def test_on_resize_repositions_layout():
    pygame.display.init()
    surf_small = pygame.Surface((300, 200))
    surf_large = pygame.Surface((600, 400))
    set_mode = MagicMock(side_effect=[surf_small, surf_large])
    with patch("pygame.display.set_mode", set_mode):
        with patch("pygame.font.SysFont", return_value=DummyFont()):
            with patch.object(pygame_gui, "load_card_images"), patch.object(
                pygame_gui,
                "get_card_image",
                side_effect=lambda c, w: pygame.Surface((w, 1)),
            ):
                view = pygame_gui.GameView(300, 200)
                pos_small = view._player_pos(0)
                btn_small_x = [b.rect.x for b in view.action_buttons]
                btn_small_y = [b.rect.y for b in view.action_buttons]
                settings_small = view.settings_button.rect.topright

                view.on_resize(600, 400)

                pos_large = view._player_pos(0)
                btn_large_x = [b.rect.x for b in view.action_buttons]
                btn_large_y = [b.rect.y for b in view.action_buttons]
                settings_large = view.settings_button.rect.topright

                card_w = view.card_width
                card_h = int(card_w * 1.4)
                margin = min(60, max(40, int(card_w * 0.75)))
                expected_pos = (600 // 2, 400 - margin - card_h // 2)
                spacing = max(10, card_w // 2)
                total = 120 * 3 + spacing * 2
                start_x = 600 // 2 - total // 2
                expected_y = view.button_y
                setting_margin = min(60, max(40, card_w // 3))
                expected_settings = (600 - setting_margin, setting_margin)

    pygame.quit()
    assert pos_large == expected_pos
    assert btn_large_x[0] == start_x
    assert btn_large_y[0] == expected_y
    assert settings_large == expected_settings
    assert pos_small != pos_large
    assert btn_small_x[0] != btn_large_x[0]
    assert btn_small_y[0] != btn_large_y[0]
    assert settings_small != settings_large


def test_resize_keeps_sprites_within_margins():
    pygame.display.init()
    surf_small = pygame.Surface((300, 200))
    surf_large = pygame.Surface((600, 600))
    set_mode = MagicMock(side_effect=[surf_small, surf_large])
    with patch("pygame.display.set_mode", set_mode):
        with patch("pygame.font.SysFont", return_value=DummyFont()):
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
                card_w = view.card_width
                margin_h = pygame_gui.HORIZONTAL_MARGIN
                margin_v = min(60, max(40, int(card_w * 0.75)))

                hand = view.hand_sprites.sprites()
                assert hand[0].rect.left >= margin_h
                assert hand[-1].rect.right <= w - margin_h

                top_group = view.ai_sprites[0].sprites()
                assert top_group[0].rect.left >= margin_h
                assert top_group[-1].rect.right <= w - margin_h

                left_group = view.ai_sprites[1].sprites()
                assert min(sp.rect.top for sp in left_group) >= margin_v
                assert max(sp.rect.bottom for sp in left_group) <= h - margin_v

                right_group = view.ai_sprites[2].sprites()
                assert min(sp.rect.top for sp in right_group) >= margin_v
                assert max(sp.rect.bottom for sp in right_group) <= h - margin_v

    pygame.quit()


def test_overlay_instances_created():
    view, _ = make_view()
    with patch("pygame.display.flip"), patch("pygame.event.pump"):
        view.show_menu()
        assert isinstance(view.overlay, pygame_gui.MainMenuOverlay)
        view.show_in_game_menu()
        assert isinstance(view.overlay, pygame_gui.InGameMenuOverlay)
        view.show_settings()
        assert isinstance(view.overlay, pygame_gui.SettingsOverlay)
        view.show_game_settings()
        assert isinstance(view.overlay, pygame_gui.GameSettingsOverlay)
        view.show_graphics()
        assert isinstance(view.overlay, pygame_gui.GraphicsOverlay)
        view.show_audio()
        assert isinstance(view.overlay, pygame_gui.AudioOverlay)
        pygame_gui.GameView.show_rules(view)
        assert isinstance(view.overlay, pygame_gui.RulesOverlay)
        view.show_how_to_play()
        assert isinstance(view.overlay, pygame_gui.HowToPlayOverlay)
        view.show_tutorial()
        assert isinstance(view.overlay, pygame_gui.TutorialOverlay)
        view.show_game_over("P1")
        assert isinstance(view.overlay, pygame_gui.GameOverOverlay)
        with patch.object(view, "_save_options"), patch.object(view, "ai_turns"):
            view.close_overlay()
    assert view.overlay is None


def test_overlay_transitions_called():
    view, _ = make_view()
    with patch.object(view, "_transition_overlay") as trans:
        view.show_settings()
        view.show_menu()
    assert trans.call_count == 2


def test_draw_frame_with_overlay():
    view, _ = make_view()
    # restore original method
    view.draw_players = MagicMock()
    view.overlay = MagicMock()
    view.screen = MagicMock()
    view.screen.get_size.return_value = (100, 100)
    overlay_surface = MagicMock()
    with patch.object(view.screen, "blit") as blit, patch(
        "pygame.display.flip"
    ) as flip, patch("pygame.Surface", return_value=overlay_surface), patch.object(
        view.score_button, "draw"
    ):
        pygame_gui.GameView._draw_frame(view)
    blit.assert_any_call(overlay_surface, (0, 0))
    flip.assert_called_once()
    pygame.quit()


def test_play_selected_triggers_flip():
    view, _ = make_view()
    sprite = DummyCardSprite()
    view.selected = [sprite]
    view.hand_sprites = pygame.sprite.OrderedUpdates(sprite)
    dest = view._pile_center()
    with (
        patch.object(view.game, "is_valid", return_value=(True, "")),
        patch.object(view.game, "process_play", return_value=False),
        patch.object(view.game, "next_turn"),
        patch.object(view, "_highlight_turn"),
        patch.object(view, "ai_turns"),
        patch.object(view, "update_hand_sprites"),
        patch.object(view, "_animate_flip") as flip,
        patch.object(sound, "play"),
    ):
        view.play_selected()
    flip.assert_called_once_with([sprite], dest)
    pygame.quit()


def test_draw_score_overlay_positions_panel():
    with patch("random.sample", return_value=tien_len_full.AI_NAMES[:3]):
        view, _ = make_view()
    view.screen = MagicMock()
    view.score_pos = (15, 20)
    view.score_visible = True
    view.screen.get_size.return_value = (300, 200)
    surf = pygame.Surface((200, 20))
    with patch("pygame.Surface", return_value=surf), patch.object(
        view.score_button, "draw"
    ):
        view.draw_score_overlay()
    view.screen.blit.assert_called_with(surf, view.score_pos)
    pygame.quit()


def test_toggle_score_panel_changes_visibility():
    view, _ = make_view()
    start = view.score_visible
    view.toggle_score()
    assert view.score_visible != start


def test_show_game_over_updates_win_counts():
    with patch("random.sample", return_value=tien_len_full.AI_NAMES[:3]):
        view, _ = make_view()
    with patch.object(sound, "play"), patch("pygame.display.flip"):
        view.show_game_over("Player")
    assert view.win_counts["Player"] == 1
    pygame.quit()


def test_restart_game_preserves_scores():
    with patch("random.sample", return_value=tien_len_full.AI_NAMES[:3]):
        view, _ = make_view()
    view.win_counts["Player"] = 2
    with patch("random.sample", return_value=tien_len_full.AI_NAMES[1:4]), patch.object(
        view, "close_overlay"
    ):
        view.restart_game()
    assert view.win_counts["Player"] == 2
    for p in view.game.players:
        assert p.name in view.win_counts
    pygame.quit()


def test_current_trick_reset_on_restart_and_new_round():
    view, _ = make_view()
    view.current_trick.append(("P1", pygame.Surface((1, 1))))
    with patch.object(view, "close_overlay"):
        view.restart_game()
    assert view.current_trick == []

    view.current_trick.append(("P1", pygame.Surface((1, 1))))
    view.game.reset_pile()
    assert view.current_trick == []
    pygame.quit()


def test_restart_game_clears_current_trick_immediately():
    view, _ = make_view()
    view.current_trick.append(("P1", pygame.Surface((1, 1))))
    with patch.object(view, "close_overlay"):
        view.restart_game()
    assert view.current_trick == []
    pygame.quit()


def test_draw_players_displays_trick_linearly():
    view, _ = make_view()
    view.hand_sprites = pygame.sprite.OrderedUpdates()
    view.ai_sprites = []
    surf1 = pygame.Surface((10, 20))
    surf2 = pygame.Surface((10, 20))
    view.current_trick = [("A", surf1), ("B", surf2)]
    view.screen = MagicMock()
    view.screen.get_size.return_value = (200, 200)
    view.pile_y = 50
    view.draw_center_pile()
    calls = [c for c in view.screen.blit.call_args_list if c.args[0] in (surf1, surf2)]
    card_w = view.card_width
    start_rel, overlap = pygame_gui.calc_start_and_overlap(
        200, len(view.current_trick), card_w, 25, card_w - 5
    )
    spacing = card_w - overlap
    start = start_rel + card_w // 2
    expected = {surf1: (start, 50), surf2: (start + spacing, 50)}
    for call in calls:
        surf, rect = call.args
        assert rect.center == expected[surf]
    pygame.quit()


def test_calc_hand_layout_wraps_start_and_spacing():
    width = 200
    card_w = 50
    count = 3
    start, spacing = pygame_gui.calc_hand_layout(width, card_w, count)
    start_rel, overlap = pygame_gui.calc_start_and_overlap(
        width - 2 * pygame_gui.HORIZONTAL_MARGIN,
        count,
        card_w,
        25,
        card_w - 5,
    )
    assert start == start_rel + pygame_gui.HORIZONTAL_MARGIN
    assert spacing == card_w - overlap


@pytest.mark.parametrize(
    "cls, args",
    [
        (pygame_gui.MainMenuOverlay, ()),
        (pygame_gui.InGameMenuOverlay, ()),
        (pygame_gui.SettingsOverlay, ()),
        (pygame_gui.GameSettingsOverlay, ()),
        (pygame_gui.GraphicsOverlay, ()),
        (pygame_gui.AudioOverlay, ()),
        (pygame_gui.RulesOverlay, (lambda: None,)),
        (pygame_gui.HowToPlayOverlay, (lambda: None,)),
        (pygame_gui.TutorialOverlay, (lambda: None,)),
        (pygame_gui.SavePromptOverlay, (lambda: None, "Quit")),
    ],
)
def test_overlay_keyboard_navigation(cls, args):
    view, _ = make_view()
    overlay = cls(view, *args) if args else cls(view)

    assert overlay.focus_idx == 0

    overlay.handle_event(
        pygame.event.Event(pygame.MOUSEMOTION, {"pos": overlay.buttons[-1].rect.center})
    )
    assert overlay.focus_idx == len(overlay.buttons) - 1

    overlay.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_UP}))
    assert overlay.focus_idx == (len(overlay.buttons) - 2) % len(overlay.buttons)

    overlay.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_DOWN}))
    assert overlay.focus_idx == len(overlay.buttons) - 1

    overlay.focus_idx = len(overlay.buttons) - 1
    btn = overlay.buttons[overlay.focus_idx]
    btn.callback = MagicMock()
    overlay.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN}))
    btn.callback.assert_called_once()

    overlay.back_callback = MagicMock()
    overlay.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE}))
    overlay.back_callback.assert_called_once()
    pygame.quit()



def test_in_game_menu_buttons():
    view, _ = make_view()
    overlay = pygame_gui.InGameMenuOverlay(view)
    texts = [b.text for b in overlay.buttons]
    cbs = [b.callback for b in overlay.buttons]
    assert texts == [
        "Resume Game",
        "Save Game",
        "Load Game",
        "Game Settings",
        "Return to Main Menu",
        "Quit Game",
    ]
    assert cbs == [
        view.close_overlay,
        view.save_game,
        view.load_game,
        view.show_settings,
        view.confirm_return_to_menu,
        view.confirm_quit,
    ]
    pygame.quit()


def test_settings_button_opens_in_game_menu():
    view, _ = make_view()
    with patch.object(view, "_save_options"), patch.object(view, "ai_turns"), patch(
        "pygame.display.flip"
    ):
        view.close_overlay()
    view.settings_button.callback = MagicMock()
    view.handle_mouse(view.settings_button.rect.center)
    view.settings_button.callback.assert_called_once()
    pygame.quit()


def test_how_to_play_overlay_escape_returns_menu():
    view, _ = make_view()
    with patch.object(view, "show_menu") as show_menu, patch("pygame.display.flip"):
        view.show_how_to_play(from_menu=True)
        view.overlay.handle_event(
            pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE})
        )
        show_menu.assert_called_once()
    pygame.quit()


def test_tutorial_overlay_escape_returns_settings():
    view, _ = make_view()
    with patch.object(view, "show_settings") as show_settings, patch(
        "pygame.display.flip"
    ):
        view.show_tutorial(from_menu=False)
        view.overlay.handle_event(
            pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE})
        )
        show_settings.assert_called_once()
    pygame.quit()


def test_on_resize_calls_overlay_resize():
    view, _ = make_view()
    overlay = MagicMock()
    view.overlay = overlay
    with patch(
        "pygame.display.set_mode", return_value=pygame.Surface((1, 1))
    ), patch.object(pygame_gui, "load_card_images"), patch.object(
        view, "update_hand_sprites"
    ), patch.object(
        view, "_create_action_buttons"
    ), patch.object(
        view, "_position_settings_button"
    ):
        view.on_resize(100, 100)
    overlay.resize.assert_called_once()


@pytest.mark.parametrize(
    "show_fn, args",
    [
        ("show_menu", ()),
        ("show_in_game_menu", ()),
        ("show_settings", ()),
        ("show_game_settings", ()),
        ("show_graphics", ()),
        ("show_audio", ()),
        ("show_how_to_play", ()),
        ("show_tutorial", ()),
    ],
)
def test_overlay_buttons_reposition_after_resize(show_fn, args):
    pygame.display.init()
    surf_small = pygame.Surface((300, 200))
    surf_large = pygame.Surface((600, 400))
    set_mode = MagicMock(side_effect=[surf_small, surf_large])
    with patch("pygame.display.set_mode", set_mode):
        with patch("pygame.font.SysFont", return_value=DummyFont()):
            with patch.object(pygame_gui, "load_card_images"), patch.object(
                pygame_gui,
                "get_card_image",
                side_effect=lambda c, w: pygame.Surface((w, 1)),
            ), patch("pygame.display.flip"):
                view = pygame_gui.GameView(300, 200)
                getattr(view, show_fn)(*args)
                before = [b.rect.topleft for b in view.overlay.buttons]

                view.on_resize(600, 400)

                after = [b.rect.topleft for b in view.overlay.buttons]

    pygame.quit()
    assert before != after


def test_options_persist_across_sessions(tmp_path):
    opt = tmp_path / "opts.json"
    with patch.object(pygame_gui, "OPTIONS_FILE", opt):
        view, _ = make_view()
        view.card_color = "blue"
        view.colorblind_mode = True
        view.fx_volume = 0.5
        view.music_volume = 0.25
        view.rule_chat_bomb = True
        view.rule_chain_cutting = True
        view.rule_tu_quy_hierarchy = True
        view.rule_flip_suit_rank = True
        view.rule_no_2s = False
        view.fullscreen = True
        view.score_visible = False
        view.score_pos = (30, 40)
        view._save_options()
        # create new view that loads from same options file
        new_view, _ = make_view()
    assert new_view.card_color == "blue"
    assert new_view.colorblind_mode is True
    assert new_view.fx_volume == 0.5
    assert new_view.music_volume == 0.25
    assert new_view.rule_chat_bomb is True
    assert new_view.rule_chain_cutting is True
    assert new_view.rule_tu_quy_hierarchy is True
    assert new_view.rule_flip_suit_rank is True
    assert new_view.rule_no_2s is False
    assert new_view.fullscreen is True
    assert new_view.score_visible is False
    assert new_view.score_pos == (30, 40)


def test_rules_overlay_toggles_update_state():
    view, _ = make_view()
    with patch("pygame.display.flip"):
        pygame_gui.GameView.show_rules(view)
    overlay = view.overlay
    attrs = [
        "rule_chat_bomb",
        "rule_chain_cutting",
        "rule_tu_quy_hierarchy",
        "rule_flip_suit_rank",
        "rule_no_2s",
    ]
    for btn, attr in zip(overlay.buttons[:-1], attrs):
        start = getattr(view, attr)
        btn.callback()
        assert getattr(view, attr) != start
    pygame.quit()


def test_save_prompt_overlay_buttons():
    view, _ = make_view()
    overlay = pygame_gui.SavePromptOverlay(view, view.quit_game, "Quit")
    texts = [b.text for b in overlay.buttons]
    assert texts == [
        "Save and Quit",
        "Quit Without Saving",
        "Cancel",
    ]
