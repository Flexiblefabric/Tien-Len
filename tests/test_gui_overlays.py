import logging
from unittest.mock import MagicMock, patch

import pygame
import pytest

import tienlen
import tienlen_gui
from conftest import DummyCardSprite, DummyFont, make_view
from tienlen import sound

pytest.importorskip("PIL")
pytest.importorskip("pygame")

pytestmark = pytest.mark.gui


def test_on_resize_rebuilds_sprites():
    pygame.init()
    pygame.font.init()
    pygame.display.init()
    surf_small = pygame.Surface((300, 200))
    surf_large = pygame.Surface((650, 400))
    set_mode = MagicMock(side_effect=[surf_small, surf_large])
    with patch("pygame.display.set_mode", set_mode):
        with (
            patch("tienlen_gui.view.get_font", return_value=DummyFont()),
            patch("tienlen_gui.helpers.get_font", return_value=DummyFont()),
        ):
            with (
                patch.object(tienlen_gui, "load_card_images") as load_images,
                patch.object(
                    tienlen_gui,
                    "get_card_image",
                    side_effect=lambda c, w: pygame.Surface((w, 1)),
                ),
            ):
                view = tienlen_gui.GameView(300, 200)
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
    pygame.init()
    pygame.font.init()
    pygame.display.init()
    surf = pygame.Surface((300, 200))
    set_mode = MagicMock(return_value=surf)
    with patch("pygame.display.set_mode", set_mode):
        with (
            patch("tienlen_gui.view.get_font", return_value=DummyFont()),
            patch("tienlen_gui.helpers.get_font", return_value=DummyFont()),
        ):
            with (
                patch.object(tienlen_gui, "load_card_images") as load_images,
                patch.object(
                    tienlen_gui,
                    "get_card_image",
                    side_effect=lambda c, w: pygame.Surface((w, 1)),
                ),
            ):
                with patch("pygame.display.toggle_fullscreen"):
                    view = tienlen_gui.GameView(300, 200)
                    load_images.reset_mock()
                    set_mode.reset_mock()

                    view.toggle_fullscreen()
                    set_mode.assert_called_with((300, 200), pygame.FULLSCREEN | pygame.DOUBLEBUF)
                    load_images.assert_called_with(view.card_width)
                    fs_width = view.card_width

                    view.toggle_fullscreen()
                    set_mode.assert_called_with((300, 200), pygame.RESIZABLE | pygame.DOUBLEBUF)
                    assert load_images.call_args_list[-1][0][0] == view.card_width
                    assert view.card_width == fs_width  # width unchanged for same size
    pygame.quit()


def test_action_buttons_created_and_clickable():
    view, _ = make_view()
    texts = [b.text for b in view.action_buttons]
    assert texts == ["Play", "Pass", "Hint", "Undo"]

    btn = view.action_buttons[0]
    btn.callback = MagicMock()
    view.state = tienlen_gui.GameState.PLAYING
    view.handle_mouse(btn.rect.center)
    btn.callback.assert_called_once()


def test_hint_button_selects_cards():
    view, _ = make_view()
    hint_cards = [view.game.players[0].hand[0]]
    with patch.object(view.game, "hint", return_value=hint_cards):
        hint_btn = next(b for b in view.action_buttons if b.text == "Hint")
        view.state = tienlen_gui.GameState.PLAYING
        view.handle_mouse(hint_btn.rect.center)
    assert all(sp.card in hint_cards for sp in view.selected)


def test_undo_button_disabled_when_no_snapshot():
    view, _ = make_view()
    undo = next(b for b in view.action_buttons if b.text == "Undo")
    undo.callback = MagicMock()
    view.state = tienlen_gui.GameState.PLAYING
    view.game.snapshots = ["s1"]
    view.handle_mouse(undo.rect.center)
    undo.callback.assert_not_called()
    view.game.snapshots.append("s2")
    view.handle_mouse(undo.rect.center)
    undo.callback.assert_called_once()


def test_undo_button_triggers_game_undo_last():
    view, _ = make_view()
    undo_btn = next(b for b in view.action_buttons if b.text == "Undo")
    view.state = tienlen_gui.GameState.PLAYING
    view.game.snapshots.append("s2")
    with (
        patch.object(view.game, "undo_last", return_value=True) as undo_mock,
        patch.object(view, "_highlight_turn"),
        patch.object(view, "_animate_avatar_blink"),
    ):
        view.handle_mouse(undo_btn.rect.center)
        undo_mock.assert_called_once()
    pygame.quit()


def test_on_resize_calls_create_action_buttons():
    view, _ = make_view()
    with patch.object(view, "_create_action_buttons") as create:
        view.on_resize(100, 100)
        create.assert_called_once()


def test_on_resize_clamps_score_pos():
    view, _ = make_view()
    with (
        patch("pygame.display.set_mode", return_value=pygame.Surface((1, 1))),
        patch.object(tienlen_gui, "load_card_images"),
        patch.object(view, "update_hand_sprites"),
        patch.object(view, "_create_action_buttons"),
        patch.object(view, "_position_score_button"),
        patch.object(view, "_position_settings_button"),
        patch.object(view, "_clamp_score_pos") as clamp,
    ):
        view.on_resize(100, 100)
    clamp.assert_called_once()


def test_apply_options_updates_game_and_audio():
    view, _ = make_view()
    p0 = view.game.players[0]
    view.table_color_name = "navy"
    view.player_name = "Alice"
    view.sort_mode = "suit"
    view.ai_level = "Hard"
    view.ai_personality = "aggressive"
    view.ai_lookahead = True
    view.ai_depth = 2
    view.fx_volume = 0.7
    view.music_volume = 0.5
    view.sound_enabled = True
    view.music_enabled = False
    with (
        patch.object(sound, "set_volume") as sv,
        patch.object(view.game, "set_ai_level") as sal,
        patch.object(view.game, "set_personality") as sp,
        patch.object(tienlen_gui, "_mixer_ready", return_value=True),
        patch.object(view, "update_hand_sprites"),
        patch("pygame.mixer.music.set_volume") as mv,
        patch("pygame.mixer.music.pause") as pause,
        patch("pygame.mixer.music.unpause") as unpause,
    ):
        view.apply_options()
    assert view.table_color == tienlen_gui.TABLE_THEMES["navy"]
    assert p0.name == "Alice"
    sal.assert_called_with("Hard")
    sp.assert_called_with("aggressive")
    assert view.game.ai_lookahead is True
    assert view.game.ai_depth == 2
    sv.assert_called_with(0.7)
    mv.assert_called_with(0.5)
    pause.assert_called_once()
    unpause.assert_not_called()


def test_toggle_fullscreen_flag_toggles():
    with patch("pygame.display.set_mode", return_value=pygame.Surface((1, 1))):
        with (
            patch("tienlen_gui.view.get_font", return_value=DummyFont()),
            patch("tienlen_gui.helpers.get_font", return_value=DummyFont()),
        ):
            with patch.object(tienlen_gui, "load_card_images"):
                with patch("pygame.display.toggle_fullscreen"):
                    view = tienlen_gui.GameView(100, 100)
                    start = view.fullscreen
                    view.toggle_fullscreen()
                    assert view.fullscreen != start
                    view.toggle_fullscreen()
                    assert view.fullscreen == start


def test_on_resize_updates_screen_size():
    view, _ = make_view()
    with (
        patch("pygame.display.set_mode", return_value=pygame.Surface((1, 1))) as sm,
        patch.object(tienlen_gui, "load_card_images"),
        patch.object(view, "update_hand_sprites") as uh,
        patch.object(view, "_create_action_buttons") as cab,
    ):
        view.on_resize(300, 200)
    sm.assert_called_with((300, 200), pygame.RESIZABLE | pygame.DOUBLEBUF)
    uh.assert_called_once()
    cab.assert_called_once()


def test_on_resize_repositions_layout():
    pygame.init()
    pygame.font.init()
    pygame.display.init()
    surf_small = pygame.Surface((300, 200))
    surf_large = pygame.Surface((600, 400))
    set_mode = MagicMock(side_effect=[surf_small, surf_large])
    with patch("pygame.display.set_mode", set_mode):
        with (
            patch("tienlen_gui.view.get_font", return_value=DummyFont()),
            patch("tienlen_gui.helpers.get_font", return_value=DummyFont()),
        ):
            with (
                patch.object(tienlen_gui, "load_card_images"),
                patch.object(
                    tienlen_gui,
                    "get_card_image",
                    side_effect=lambda c, w: pygame.Surface((w, 1)),
                ),
            ):
                view = tienlen_gui.GameView(300, 200)
                pos_small = view._player_pos(0)
                btn_small_x = [b.rect.x for b in view.action_buttons]
                btn_small_y = [b.rect.y for b in view.action_buttons]
                settings_small = view.settings_button.rect.topright

                view.on_resize(600, 400)

                pos_large = view._player_pos(0)
                btn_large_x = [b.rect.x for b in view.action_buttons]
                btn_large_y = [b.rect.y for b in view.action_buttons]
                settings_large = view.settings_button.rect.topright
                hand_center = view.hand_sprites.sprites()[0].rect.centery

                card_w = view.card_width
                card_h = int(card_w * 1.4)
                margin = min(60, max(40, int(card_w * 0.75)))
                expected_pos = (600 // 2, 400 - margin - card_h // 2)
                spacing = max(10, card_w // 2)
                total = 120 * 4 + spacing * 3
                start_x = 600 // 2 - total // 2
                expected_y = view.button_y
                setting_margin = min(60, max(40, card_w // 3))
                expected_settings = (600 - setting_margin, setting_margin)

    pygame.quit()
    assert pos_large == expected_pos
    assert btn_large_x[0] == start_x
    assert btn_large_y[0] == expected_y
    assert hand_center == pos_large[1]
    assert settings_large == expected_settings
    assert pos_small != pos_large
    assert btn_small_x[0] != btn_large_x[0]
    assert btn_small_y[0] != btn_large_y[0]
    assert settings_small != settings_large


def test_resize_keeps_sprites_within_margins():
    pygame.init()
    pygame.font.init()
    pygame.display.init()
    surf_small = pygame.Surface((300, 200))
    surf_large = pygame.Surface((600, 600))
    set_mode = MagicMock(side_effect=[surf_small, surf_large])
    with patch("pygame.display.set_mode", set_mode):
        with (
            patch("tienlen_gui.view.get_font", return_value=DummyFont()),
            patch("tienlen_gui.helpers.get_font", return_value=DummyFont()),
        ):
            with (
                patch.object(tienlen_gui, "load_card_images"),
                patch.object(
                    tienlen_gui,
                    "get_card_image",
                    side_effect=lambda c, w: pygame.Surface((w, int(w * 1.4))),
                ),
                patch.object(
                    tienlen_gui,
                    "get_card_back",
                    side_effect=lambda name, w=1: pygame.Surface((w, int(w * 1.4))),
                ),
            ):
                view = tienlen_gui.GameView(300, 200)
                view.on_resize(600, 600)

                w, h = view.screen.get_size()
                card_w = view.card_width
                margin_h = tienlen_gui.horizontal_margin(card_w)
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


def test_vertical_spacing_changes_on_resize():
    pygame.init()
    pygame.font.init()
    pygame.display.init()
    surf_small = pygame.Surface((300, 200))
    surf_large = pygame.Surface((600, 600))
    set_mode = MagicMock(side_effect=[surf_small, surf_large])
    with patch("pygame.display.set_mode", set_mode):
        with (
            patch("tienlen_gui.view.get_font", return_value=DummyFont()),
            patch("tienlen_gui.helpers.get_font", return_value=DummyFont()),
        ):
            with (
                patch.object(tienlen_gui, "load_card_images"),
                patch.object(
                    tienlen_gui,
                    "get_card_image",
                    side_effect=lambda c, w: pygame.Surface((w, int(w * 1.4))),
                ),
                patch.object(
                    tienlen_gui,
                    "get_card_back",
                    side_effect=lambda name, w=1: pygame.Surface((w, int(w * 1.4))),
                ),
            ):
                view = tienlen_gui.GameView(300, 200)
                left_small = view.ai_sprites[1].sprites()
                spacing_small = left_small[1].rect.centery - left_small[0].rect.centery

                view.on_resize(600, 600)

                left_large = view.ai_sprites[1].sprites()
                spacing_large = left_large[1].rect.centery - left_large[0].rect.centery

    pygame.quit()
    assert spacing_large != spacing_small


def test_overlay_instances_created():
    view, _ = make_view()
    with patch("pygame.display.update"), patch("pygame.event.pump"):
        view.show_menu()
        assert isinstance(view.overlay, tienlen_gui.MainMenuOverlay)
        view.show_in_game_menu()
        assert isinstance(view.overlay, tienlen_gui.InGameMenuOverlay)
        view.show_settings()
        assert isinstance(view.overlay, tienlen_gui.SettingsOverlay)
        view.show_game_settings()
        assert isinstance(view.overlay, tienlen_gui.GameSettingsOverlay)
        view.show_graphics()
        assert isinstance(view.overlay, tienlen_gui.GraphicsOverlay)
        view.show_audio()
        assert isinstance(view.overlay, tienlen_gui.AudioOverlay)
        view.show_ai_setup()
        assert isinstance(view.overlay, tienlen_gui.AiSetupOverlay)
        tienlen_gui.GameView.show_rules(view)
        assert isinstance(view.overlay, tienlen_gui.RulesOverlay)
        view.show_how_to_play()
        assert isinstance(view.overlay, tienlen_gui.HowToPlayOverlay)
        view.show_tutorial()
        assert isinstance(view.overlay, tienlen_gui.TutorialOverlay)
        view.show_game_over("P1")
        assert isinstance(view.overlay, tienlen_gui.GameOverOverlay)
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
    with (
        patch.object(view.screen, "blit") as blit,
        patch("pygame.display.update") as flip,
        patch("pygame.Surface", return_value=overlay_surface),
        patch.object(view.score_button, "draw"),
        patch("tienlen_gui.view.draw_nine_patch"),
    ):
        tienlen_gui.GameView._draw_frame(view)
    blit.assert_any_call(overlay_surface, (0, 0))
    flip.assert_called_once()
    pygame.quit()


def test_play_selected_triggers_flip():
    view, _ = make_view()
    sprite = DummyCardSprite()
    view.selected = [sprite]
    view.hand_sprites = pygame.sprite.LayeredUpdates(sprite)
    dest = view._pile_center()
    with (
        patch.object(view.game, "is_valid", return_value=(True, "")),
        patch.object(view.game, "process_play", return_value=False),
        patch.object(view.game, "next_turn"),
        patch.object(view, "_highlight_turn"),
        patch.object(view, "_animate_avatar_blink"),
        patch.object(view, "ai_turns"),
        patch.object(view, "update_hand_sprites"),
        patch.object(view, "_animate_flip") as flip,
        patch.object(sound, "play"),
    ):
        view.play_selected()
    flip.assert_called_once_with([sprite], dest)
    pygame.quit()


def test_play_selected_triggers_glow():
    view, _ = make_view()
    sprite = DummyCardSprite()
    view.selected = [sprite]
    view.hand_sprites = pygame.sprite.LayeredUpdates(sprite)
    with (
        patch.object(view.game, "is_valid", return_value=(True, "")),
        patch.object(view.game, "process_play", return_value=False),
        patch.object(view.game, "next_turn"),
        patch.object(view, "_highlight_turn"),
        patch.object(view, "_animate_avatar_blink"),
        patch.object(view, "ai_turns"),
        patch.object(view, "update_hand_sprites"),
        patch.object(view, "_animate_flip", return_value="flip"),
        patch.object(view, "_animate_glow", return_value="glow") as glow,
        patch.object(view, "_start_animation") as start,
        patch.object(sound, "play"),
    ):
        view.play_selected()
    glow.assert_called_once_with([sprite], tienlen_gui.PLAYER_COLORS[0])
    assert "glow" in [c.args[0] for c in start.call_args_list]
    pygame.quit()


def test_play_selected_triggers_bomb_reveal():
    view, _ = make_view()
    sprite = DummyCardSprite()
    view.selected = [sprite]
    view.hand_sprites = pygame.sprite.LayeredUpdates(sprite)
    with (
        patch.object(view.game, "is_valid", return_value=(True, "")),
        patch.object(view.game, "process_play", return_value=False),
        patch.object(view.game, "next_turn"),
        patch.object(view, "_highlight_turn"),
        patch.object(view, "_animate_avatar_blink"),
        patch.object(view, "ai_turns"),
        patch.object(view, "update_hand_sprites"),
        patch.object(view, "_animate_flip", return_value="flip"),
        patch.object(view, "_animate_glow", return_value="glow"),
        patch.object(view, "_bomb_reveal", return_value="boom") as reveal,
        patch.object(view, "_start_animation") as start,
        patch.object(sound, "play"),
        patch("tienlen_gui.view.detect_combo", return_value="bomb"),
    ):
        view.play_selected()
    reveal.assert_called_once_with()
    assert "boom" in [c.args[0] for c in start.call_args_list]
    pygame.quit()


def test_ai_turns_triggers_pass_animation():
    view, _ = make_view()
    view.game.current_idx = 1
    with (
        patch.object(view.game, "ai_play", return_value=[]),
        patch.object(view.game, "is_valid", return_value=(True, "")),
        patch.object(view.game, "process_pass") as proc,
        patch.object(view.game, "next_turn"),
        patch.object(view, "_highlight_turn"),
        patch.object(view, "_animate_avatar_blink"),
        patch.object(view, "update_hand_sprites"),
        patch.object(view, "_animate_pass_text", return_value="pass") as anim,
        patch.object(view, "_start_animation") as start,
        patch.object(sound, "play"),
    ):
        view.ai_turns()
    proc.assert_called_once_with(view.game.players[1])
    anim.assert_called_once_with(1)
    assert "pass" in [c.args[0] for c in start.call_args_list]


def test_play_selected_shakes_on_invalid():
    view, _ = make_view()
    sprite = DummyCardSprite()
    view.selected = [sprite]
    view.hand_sprites = pygame.sprite.LayeredUpdates(sprite)
    with (
        patch.object(view.game, "is_valid", return_value=(False, "bad")),
        patch.object(view, "_animate_shake", return_value="gen") as shake,
        patch.object(view, "_start_animation") as start,
    ):
        view.play_selected()
    shake.assert_called_once_with([sprite])
    start.assert_called_once_with("gen")


def test_pass_turn_shakes_on_invalid():
    view, _ = make_view()
    with (
        patch.object(view.game, "handle_pass", return_value=False),
        patch.object(view, "_animate_shake", return_value="gen") as shake,
        patch.object(view, "_start_animation") as start,
        patch.object(sound, "play"),
        patch.object(view, "_highlight_turn"),
        patch.object(view, "_animate_avatar_blink"),
        patch.object(view, "ai_turns"),
    ):
        view.pass_turn()
    shake.assert_called_once_with(list(view.selected))
    assert start.call_args_list[0].args[0] == "gen"


def test_pass_turn_triggers_pass_animation():
    view, _ = make_view()
    with (
        patch.object(view.game, "handle_pass", return_value=False),
        patch.object(view, "_animate_shake", return_value="shake"),
        patch.object(view, "_animate_pass_text", return_value="pass") as anim,
        patch.object(view, "_start_animation") as start,
        patch.object(sound, "play"),
        patch.object(view, "_highlight_turn"),
        patch.object(view, "_animate_avatar_blink"),
        patch.object(view, "ai_turns"),
    ):
        view.pass_turn()
    anim.assert_called_once_with(view.game.current_idx)
    assert "pass" in [c.args[0] for c in start.call_args_list]


def test_undo_move_triggers_return_animation():
    view, _ = make_view()
    player = view.game.players[0]
    card = tienlen.Card("Spades", "3")
    view.game.pile.append((player, [card]))
    view.game.snapshots.append(view.game.to_json())

    def undo():
        view.game.pile.pop()
        return True

    with (
        patch.object(view.game, "undo_last", side_effect=undo) as undo_last,
        patch.object(view, "_animate_return", return_value="gen") as ret,
        patch.object(view, "_start_animation") as start,
        patch.object(view, "update_hand_sprites"),
        patch.object(view, "_highlight_turn"),
        patch.object(view, "_animate_avatar_blink"),
    ):
        view.undo_move()
    undo_last.assert_called_once()
    ret.assert_called_once_with(0, 1)
    start.assert_any_call("gen")
    pygame.quit()


def test_ai_turns_triggers_glow_on_play():
    view, _ = make_view()
    view.game.current_idx = 1
    card = tienlen.Card("Spades", "3")
    with (
        patch.object(view.game, "ai_play", return_value=[card]),
        patch.object(view.game, "is_valid", return_value=(True, "")),
        patch.object(view.game, "process_play", return_value=False),
        patch.object(view.game, "next_turn"),
        patch.object(view, "_highlight_turn"),
        patch.object(view, "_animate_avatar_blink"),
        patch.object(view, "update_hand_sprites"),
        patch.object(view, "_animate_back", return_value="back"),
        patch.object(view, "_animate_glow", return_value="glow") as glow,
        patch.object(view, "_start_animation") as _,
        patch.object(sound, "play"),
        patch.object(tienlen_gui, "get_card_image", return_value=pygame.Surface((1, 1))),
    ):
        view.ai_turns()
    glow.assert_called_once()
    assert glow.call_args.args[1] == tienlen_gui.PLAYER_COLORS[1]
    pygame.quit()


def test_ai_turns_triggers_bomb_reveal():
    view, _ = make_view()
    view.game.current_idx = 1
    card = tienlen.Card("Spades", "3")
    with (
        patch.object(view.game, "ai_play", return_value=[card]),
        patch.object(view.game, "is_valid", return_value=(True, "")),
        patch.object(view.game, "process_play", return_value=False),
        patch.object(view.game, "next_turn"),
        patch.object(view, "_highlight_turn"),
        patch.object(view, "_animate_avatar_blink"),
        patch.object(view, "update_hand_sprites"),
        patch.object(view, "_animate_back", return_value="back"),
        patch.object(view, "_animate_glow", return_value="glow"),
        patch.object(view, "_bomb_reveal", return_value="boom") as reveal,
        patch.object(view, "_start_animation") as start,
        patch.object(sound, "play"),
        patch.object(tienlen_gui, "get_card_image", return_value=pygame.Surface((1, 1))),
        patch("tienlen_gui.view.detect_combo", return_value="bomb"),
    ):
        view.ai_turns()
    reveal.assert_called_once_with()
    assert "boom" in [c.args[0] for c in start.call_args_list]
    pygame.quit()


def test_draw_score_overlay_positions_panel():
    with patch("random.sample", return_value=tienlen.AI_NAMES[:3]):
        view, _ = make_view()
    view.screen = MagicMock()
    view.score_pos = (15, 20)
    view.score_visible = True
    view.screen.get_size.return_value = (300, 200)
    surf = pygame.Surface((200, 20))
    with patch("pygame.Surface", return_value=surf), patch.object(view.score_button, "draw"):
        view.draw_score_overlay()
    view.screen.blit.assert_called_with(surf, view.score_pos)
    pygame.quit()


class RecordingFont(DummyFont):
    def __init__(self):
        self.calls = []

    def render(self, text, aa, color):
        self.calls.append((text, color))
        return pygame.Surface((1, 1))


def test_draw_scoreboard_midtop_and_line_count():
    view, _ = make_view()
    view.screen = MagicMock()
    view.screen.get_size.return_value = (200, 100)
    font = RecordingFont()
    with patch("tienlen_gui.view.get_font", return_value=font):
        view.draw_scoreboard()
    surf, rect = view.screen.blit.call_args[0]
    assert rect.midtop == (100, 5)
    assert len(font.calls) == len(view.game.players)
    pygame.quit()


def test_draw_game_log_highlights_latest():
    view, _ = make_view()
    view.screen = MagicMock()
    view.screen.get_size.return_value = (200, 100)
    view.scoreboard_rect = pygame.Rect(90, 5, 20, 10)
    view.game.history = [(0, f"line{i}") for i in range(5)]
    font = RecordingFont()
    with patch("tienlen_gui.view.get_font", return_value=font):
        view.draw_game_log()
    surf, rect = view.screen.blit.call_args[0]
    assert rect.topleft == (
        view.scoreboard_rect.right + tienlen_gui.LABEL_PAD,
        view.scoreboard_rect.top,
    )
    assert len(font.calls) == 4
    assert font.calls[-1][1] == (255, 255, 0)
    pygame.quit()


def test_toggle_score_panel_changes_visibility():
    view, _ = make_view()
    start = view.score_visible
    view.toggle_score()
    assert view.score_visible != start


def test_show_game_over_updates_win_counts():
    with patch("random.sample", return_value=tienlen.AI_NAMES[:3]):
        view, _ = make_view()
    with patch.object(sound, "play"), patch("pygame.display.update"):
        view.show_game_over("Player")
    assert view.win_counts["Player"] == 1
    pygame.quit()


def test_restart_game_resets_scores():
    with patch("random.sample", return_value=tienlen.AI_NAMES[:3]):
        view, _ = make_view()
    view.win_counts["Player"] = 2
    with patch("random.sample", return_value=tienlen.AI_NAMES[1:4]), patch.object(view, "close_overlay"):
        view.restart_game()
    for p in view.game.players:
        assert view.win_counts[p.name] == 0
    pygame.quit()


def test_restart_game_triggers_deal_animation():
    with patch("random.sample", return_value=tienlen.AI_NAMES[:3]):
        view, _ = make_view()
    with (
        patch.object(view, "close_overlay"),
        patch("random.sample", return_value=tienlen.AI_NAMES[1:4]),
        patch.object(view, "_animate_deal", return_value="gen") as deal,
        patch.object(view, "_start_animation") as start,
    ):
        view.restart_game()
    start.assert_any_call("gen")
    deal.assert_called_once()
    pygame.quit()


def test_current_trick_reset_on_restart_and_new_round():
    view, _ = make_view()
    view.current_trick.append(("P1", pygame.Surface((1, 1))))
    with patch.object(view, "close_overlay"):
        view.restart_game()
    assert view.current_trick == []

    view.current_trick.append(("P1", pygame.Surface((1, 1))))
    with (
        patch.object(view, "_animate_fade_out", return_value="gen") as _,
        patch.object(view, "_animate_trick_clear", return_value="clear") as _,
        patch.object(view, "_start_animation") as start,
    ):
        view.game.reset_pile()
    start_calls = [c.args[0] for c in start.call_args_list]
    assert "gen" in start_calls
    assert "clear" in start_calls
    assert view.current_trick == []
    pygame.quit()


def test_restart_game_clears_current_trick_immediately():
    view, _ = make_view()
    view.current_trick.append(("P1", pygame.Surface((1, 1))))
    with patch.object(view, "close_overlay"):
        view.restart_game()
    assert view.current_trick == []
    pygame.quit()


def test_reset_current_trick_starts_animation():
    view, _ = make_view()
    view.current_trick.append(("P1", pygame.Surface((1, 1))))
    with (
        patch.object(view, "_animate_trick_clear", return_value="clear") as clear,
        patch.object(view, "_start_animation") as start,
    ):
        view.reset_current_trick()
    clear.assert_called_once_with()
    start.assert_any_call("clear")
    assert view.current_trick == []
    pygame.quit()


def test_draw_players_displays_trick_linearly():
    view, _ = make_view()
    view.hand_sprites = pygame.sprite.LayeredUpdates()
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
    start_rel, overlap = tienlen_gui.calc_start_and_overlap(200, len(view.current_trick), card_w, 25, card_w - 5)
    spacing = card_w - overlap
    start = start_rel + card_w // 2
    expected = {surf1: (start, 50), surf2: (start + spacing, 50)}
    for call in calls:
        surf, rect = call.args
        assert rect.center == expected[surf]
    pygame.quit()


def test_draw_center_pile_uses_shadow_helper():
    view, _ = make_view()
    img = pygame.Surface((10, 20))
    view.current_trick = [("P1", img)]
    view.screen = MagicMock()
    view.screen.get_size.return_value = (100, 100)
    view.pile_y = 40
    view.game.pile.append((view.game.players[0], []))
    with patch.object(tienlen_gui.view, "draw_surface_shadow") as shadow:
        view.draw_center_pile()
        shadow.assert_called_once()
    pygame.quit()


def test_calc_hand_layout_wraps_start_and_spacing():
    width = 200
    card_w = 50
    count = 3
    start, spacing = tienlen_gui.calc_hand_layout(width, card_w, count)
    margin = tienlen_gui.horizontal_margin(card_w)
    start_rel, overlap = tienlen_gui.calc_start_and_overlap(
        width - 2 * margin,
        count,
        card_w,
        25,
        card_w - 5,
    )
    assert start == start_rel + margin
    assert spacing == card_w - overlap


@pytest.mark.parametrize(
    "cls, args",
    [
        (tienlen_gui.ProfileOverlay, ()),
        (tienlen_gui.MainMenuOverlay, ()),
        (tienlen_gui.InGameMenuOverlay, ()),
        (tienlen_gui.SettingsOverlay, ()),
        (tienlen_gui.GameSettingsOverlay, ()),
        (tienlen_gui.GraphicsOverlay, ()),
        (tienlen_gui.AudioOverlay, ()),
        (tienlen_gui.AiSetupOverlay, ()),
        (tienlen_gui.RulesOverlay, (lambda: None,)),
        (tienlen_gui.HowToPlayOverlay, (lambda: None,)),
        (tienlen_gui.TutorialOverlay, (lambda: None,)),
        (tienlen_gui.SavePromptOverlay, (lambda: None, "Quit")),
    ],
)
def test_overlay_keyboard_navigation(cls, args):
    view, _ = make_view()
    overlay = cls(view, *args) if args else cls(view)

    assert overlay.focus_idx == 0

    overlay.handle_event(pygame.event.Event(pygame.MOUSEMOTION, {"pos": overlay.buttons[-1].rect.center}))
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
    overlay = tienlen_gui.InGameMenuOverlay(view)
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


def test_game_settings_overlay_ai_setup_toggle():
    view, _ = make_view()
    overlay = tienlen_gui.GameSettingsOverlay(view)
    texts = [b.text for b in overlay.buttons]
    assert "AI Setup" not in texts
    view.use_global_ai_settings = False
    overlay = tienlen_gui.GameSettingsOverlay(view)
    texts = [b.text for b in overlay.buttons]
    assert "AI Setup" in texts
    pygame.quit()


def test_settings_button_opens_in_game_menu():
    view, _ = make_view()
    with patch.object(view, "_save_options"), patch.object(view, "ai_turns"), patch("pygame.display.update"):
        view.close_overlay()
    view.settings_button.callback = MagicMock()
    view.handle_mouse(view.settings_button.rect.center)
    view.settings_button.callback.assert_called_once()
    pygame.quit()


def test_how_to_play_overlay_escape_returns_menu():
    view, _ = make_view()
    with patch.object(view, "show_menu") as show_menu, patch("pygame.display.update"):
        view.show_how_to_play(from_menu=True)
        view.overlay.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE}))
        show_menu.assert_called_once()
    pygame.quit()


def test_tutorial_overlay_escape_returns_settings():
    view, _ = make_view()
    with patch.object(view, "show_settings") as show_settings, patch("pygame.display.update"):
        view.show_tutorial(from_menu=False)
        view.overlay.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE}))
        show_settings.assert_called_once()
    pygame.quit()


def test_on_resize_calls_overlay_resize():
    view, _ = make_view()
    overlay = MagicMock()
    view.overlay = overlay
    with (
        patch("pygame.display.set_mode", return_value=pygame.Surface((1, 1))),
        patch.object(tienlen_gui, "load_card_images"),
        patch.object(view, "update_hand_sprites"),
        patch.object(view, "_create_action_buttons"),
        patch.object(view, "_position_settings_button"),
    ):
        view.on_resize(100, 100)
    overlay.resize.assert_called_once()


def test_on_resize_recreates_font():
    pygame.init()
    pygame.font.init()
    pygame.display.init()
    sizes = []

    def fake_font(*args):
        size = args[-1]
        sizes.append(size)
        return DummyFont()

    with patch("pygame.display.set_mode", return_value=pygame.Surface((1, 1))):
        with (
            patch("tienlen_gui.view.get_font", side_effect=fake_font),
            patch("tienlen_gui.helpers.get_font", side_effect=fake_font),
        ):
            with patch.object(tienlen_gui, "load_card_images"):
                view = tienlen_gui.GameView(100, 100)
                first = sizes[-1]
                sizes.clear()
                with (
                    patch.object(view, "update_hand_sprites"),
                    patch.object(view, "_create_action_buttons"),
                    patch.object(view, "_position_score_button"),
                    patch.object(view, "_position_settings_button"),
                ):
                    view.on_resize(300, 300)
                second = sizes[-1]
    pygame.quit()
    assert first != second


def test_overlay_font_changes_after_resize():
    pygame.init()
    pygame.font.init()
    pygame.display.init()
    sizes = []

    def fake_font(*args):
        size = args[-1]
        sizes.append(size)
        return DummyFont()

    surf = pygame.Surface((100, 100))
    with patch("pygame.display.set_mode", return_value=surf):
        with (
            patch("tienlen_gui.view.get_font", side_effect=fake_font),
            patch("tienlen_gui.helpers.get_font", side_effect=fake_font),
        ):
            with patch.object(tienlen_gui, "load_card_images"):
                view = tienlen_gui.GameView(100, 100)
                overlay = tienlen_gui.SavePromptOverlay(view, lambda: None, "Quit")
                overlay.draw(surf)
                before = sizes[-1]
                sizes.clear()
                with (
                    patch.object(view, "update_hand_sprites"),
                    patch.object(view, "_create_action_buttons"),
                    patch.object(view, "_position_score_button"),
                    patch.object(view, "_position_settings_button"),
                ):
                    view.on_resize(300, 300)
                overlay.draw(surf)
                after = sizes[-1]
    pygame.quit()
    assert before != after


@pytest.mark.parametrize(
    "show_fn, args",
    [
        ("show_menu", ()),
        ("show_in_game_menu", ()),
        ("show_settings", ()),
        ("show_game_settings", ()),
        ("show_graphics", ()),
        ("show_audio", ()),
        ("show_ai_setup", ()),
        ("show_how_to_play", ()),
        ("show_tutorial", ()),
    ],
)
def test_overlay_buttons_reposition_after_resize(show_fn, args):
    pygame.init()
    pygame.font.init()
    pygame.display.init()
    surf_small = pygame.Surface((300, 200))
    surf_large = pygame.Surface((600, 400))
    set_mode = MagicMock(side_effect=[surf_small, surf_large])
    with patch("pygame.display.set_mode", set_mode):
        with (
            patch("tienlen_gui.view.get_font", return_value=DummyFont()),
            patch("tienlen_gui.helpers.get_font", return_value=DummyFont()),
        ):
            with (
                patch.object(tienlen_gui, "load_card_images"),
                patch.object(
                    tienlen_gui,
                    "get_card_image",
                    side_effect=lambda c, w: pygame.Surface((w, 1)),
                ),
                patch("pygame.display.update"),
            ):
                view = tienlen_gui.GameView(300, 200)
                getattr(view, show_fn)(*args)
                before = [b.rect.topleft for b in view.overlay.buttons]

                view.on_resize(600, 400)

                after = [b.rect.topleft for b in view.overlay.buttons]

    pygame.quit()
    assert before != after


def test_options_persist_across_sessions(tmp_path):
    opt = tmp_path / "opts.json"
    with patch.object(tienlen_gui, "OPTIONS_FILE", opt):
        view, _ = make_view()
        view.card_color = "blue"
        view.colorblind_mode = True
        view.fx_volume = 0.5
        view.music_volume = 0.25
        view.rule_flip_suit_rank = True
        view.rule_no_2s = False
        view.rule_bomb_override = False
        view.rule_chain_cutting = True
        view.rule_bomb_hierarchy = False
        view.fullscreen = True
        view.score_visible = False
        view.score_pos = (30, 40)
        view.win_counts["Player"] = 3
        view.fps_limit = 30
        view._save_options()
        # create new view that loads from same options file
        new_view, _ = make_view()
    assert new_view.card_color == "blue"
    assert new_view.colorblind_mode is True
    assert new_view.fx_volume == 0.5
    assert new_view.music_volume == 0.25
    assert new_view.rule_flip_suit_rank is True
    assert new_view.rule_no_2s is False
    assert new_view.rule_bomb_override is False
    assert new_view.rule_chain_cutting is True
    assert new_view.rule_bomb_hierarchy is False
    assert new_view.fullscreen is True
    assert new_view.score_visible is False
    assert new_view.score_pos == (30, 40)
    assert new_view.win_counts["Player"] == 3
    assert new_view.fps_limit == 30


def test_per_player_ai_settings_persist(tmp_path):
    opt = tmp_path / "opts.json"
    with patch.object(tienlen_gui, "OPTIONS_FILE", opt):
        with patch("random.sample", return_value=tienlen.AI_NAMES[:3]):
            view, _ = make_view()
        view.use_global_ai_settings = False
        p1 = view.game.players[1].name
        p2 = view.game.players[2].name
        view.game.set_player_ai_level(p1, "Hard")
        view.game.set_player_personality(p2, "aggressive")
        view._save_options()
        with patch("random.sample", return_value=tienlen.AI_NAMES[:3]):
            new_view, _ = make_view()
    assert new_view.use_global_ai_settings is False
    assert new_view.player_ai_levels[p1] == "Hard"
    assert new_view.player_ai_personality[p2] == "aggressive"
    assert new_view.game.players[1].name == p1
    assert new_view.game.players[1].ai_level == "Hard"
    assert new_view.game.players[2].ai_personality == "aggressive"


def test_rules_overlay_toggles_update_state():
    view, _ = make_view()
    with patch("pygame.display.update"):
        tienlen_gui.GameView.show_rules(view)
    overlay = view.overlay
    attrs = [
        "rule_flip_suit_rank",
        "rule_no_2s",
        "rule_bomb_override",
        "rule_chain_cutting",
        "rule_bomb_hierarchy",
    ]
    for btn, attr in zip(overlay.buttons[:-1], attrs):
        start = getattr(view, attr)
        btn.callback()
        assert getattr(view, attr) != start
    pygame.quit()


def test_save_prompt_overlay_buttons():
    view, _ = make_view()
    overlay = tienlen_gui.SavePromptOverlay(view, view.quit_game, "Quit")
    texts = [b.text for b in overlay.buttons]
    assert texts == [
        "Save and Quit",
        "Quit Without Saving",
        "Cancel",
    ]


def test_profile_overlay_select_updates_name():
    view, _ = make_view()
    overlay = tienlen_gui.ProfileOverlay(view)
    with patch.object(view, "show_menu") as sm:
        overlay.select(next(iter(view.win_counts)))
        sm.assert_called_once()
    assert view.player_name in view.win_counts


def test_profile_overlay_new_profile_added():
    view, _ = make_view()
    overlay = tienlen_gui.ProfileOverlay(view)
    existing = set(view.win_counts)
    with patch.object(view, "show_menu"):
        overlay.new_profile()
    assert set(view.win_counts) - existing


def test_handle_score_event_not_draggable():
    view, _ = make_view()
    view.score_visible = True
    # Position the score panel so it does not overlap the toggle button.
    view.score_pos = (50, 10)
    view.draw_score_overlay()
    start_pos = view.score_pos
    with patch.object(view, "_save_options") as save, patch.object(view, "_clamp_score_pos") as clamp:
        down = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (start_pos[0] + 5, start_pos[1] + 5)})
        assert view._handle_score_event(down) is False
        move = pygame.event.Event(pygame.MOUSEMOTION, {"pos": (start_pos[0] + 10, start_pos[1] + 15)})
        assert view._handle_score_event(move) is False
        assert view.score_pos == start_pos
        up = pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": (start_pos[0] + 10, start_pos[1] + 15)})
        assert view._handle_score_event(up) is False
        save.assert_not_called()
        clamp.assert_not_called()
    pygame.quit()


def test_close_overlay_restores_state_and_ai():
    view, _ = make_view()
    view.overlay = MagicMock()
    view.state = tienlen_gui.GameState.SETTINGS
    with patch.object(view, "_save_options") as save, patch.object(view, "ai_turns") as ai:
        view.close_overlay()
    assert view.overlay is None
    assert view.state == tienlen_gui.GameState.PLAYING
    save.assert_called_once()
    ai.assert_called_once()
    pygame.quit()


def test_save_game_warning_on_oserror(tmp_path, caplog):
    view, _ = make_view()
    save_path = tmp_path / "save.json"
    with patch.object(tienlen_gui, "SAVE_FILE", save_path):
        with patch("builtins.open", side_effect=OSError("nope")):
            before = view.game.to_dict()
            with caplog.at_level(logging.WARNING):
                view.save_game()
    assert "Failed to save game" in caplog.text
    assert view.game.to_dict() == before
    pygame.quit()


def test_load_game_warning_on_oserror(tmp_path, caplog):
    view, _ = make_view()
    load_path = tmp_path / "save.json"
    with patch.object(tienlen_gui, "SAVE_FILE", load_path):
        with patch("pathlib.Path.exists", return_value=True), patch("builtins.open", side_effect=OSError("nope")):
            before = view.game.to_dict()
            with caplog.at_level(logging.WARNING):
                view.load_game()
    assert "Failed to load game" in caplog.text
    assert view.game.to_dict() == before
    pygame.quit()
