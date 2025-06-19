import pytest
pytest.importorskip("PIL")
pytest.importorskip("pygame")

from unittest.mock import MagicMock, patch
import json
import sys
import gui
from tien_len_full import Game, Card

sys.modules.setdefault('pygame', MagicMock())
gui.pygame = sys.modules['pygame']


def make_gui_stub(root):
    g = gui.GameGUI.__new__(gui.GameGUI)
    g.root = root
    # Provide cget so set_high_contrast can read the default background
    g.root.cget = MagicMock(return_value="white")
    g._default_bg = "white"
    g.card_font = MagicMock()
    g.undo_btn = MagicMock()
    g.update_display = MagicMock()
    g.base_images = {}
    g.scaled_images = {}
    g.opponent_views = []
    return g


def test_set_high_contrast_toggle():
    root = MagicMock()
    gui_obj = make_gui_stub(root)
    default_font = MagicMock()
    with patch('gui.tkfont.nametofont', return_value=default_font):
        gui_obj.set_high_contrast(True)
        assert gui_obj.high_contrast is True
        default_font.configure.assert_called_with(size=12)
        gui_obj.card_font.configure.assert_called_with(size=16)
        root.tk_setPalette.assert_called_with(background="black", foreground="white",
                                             activeBackground="#333", activeForeground="white")
        gui_obj.update_display.assert_called_once()

        root.reset_mock()
        default_font.configure.reset_mock()
        gui_obj.card_font.configure.reset_mock()
        gui_obj.update_display.reset_mock()

        gui_obj.set_high_contrast(False)
        assert gui_obj.high_contrast is False
        default_font.configure.assert_called_with(size=10)
        gui_obj.card_font.configure.assert_called_with(size=12)
        root.tk_setPalette.assert_called_with(background="white")
        gui_obj.update_display.assert_called_once()

        # Empty default background should fall back to constant
        root.reset_mock()
        default_font.configure.reset_mock()
        gui_obj.card_font.configure.reset_mock()
        gui_obj.update_display.reset_mock()

        gui_obj._default_bg = ""
        gui_obj.set_high_contrast(False)
        assert gui_obj.high_contrast is False
        default_font.configure.assert_called_with(size=10)
        gui_obj.card_font.configure.assert_called_with(size=12)
        root.tk_setPalette.assert_called_with(background=gui.DEFAULT_BG_FALLBACK)
        gui_obj.update_display.assert_called_once()


def test_show_rules_creates_modal():
    root = MagicMock()
    gui_obj = make_gui_stub(root)
    win = MagicMock()
    with patch('gui.tk.Toplevel', return_value=win) as mock_top, \
         patch('gui.tk.Frame') as mock_frame, \
         patch('gui.tk.Label'), \
         patch('gui.tk.Button') as mock_button:
        gui_obj.show_rules()
        mock_top.assert_called_with(gui_obj.root)
        win.title.assert_called_with('Game Tutorial')
        win.transient.assert_called_with(gui_obj.root)
        win.grab_set.assert_called_once()
        assert mock_frame.call_count >= 1
        assert mock_button.call_count >= 3


def test_show_menu_overlay():
    root = MagicMock()
    gui_obj = make_gui_stub(root)
    overlay = MagicMock()
    box = MagicMock()
    with patch('gui.tk.Frame', side_effect=[overlay, box]) as mock_frame, \
         patch('gui.tk.Label'), \
         patch('gui.tk.Button') as mock_button:
        gui_obj.show_menu()
        mock_frame.assert_any_call(gui_obj.root, bg='#000000')
        overlay.place.assert_called_with(relx=0, rely=0, relwidth=1, relheight=1)
        assert mock_button.call_count >= 4


def test_menu_includes_tutorial_button():
    root = MagicMock()
    gui_obj = make_gui_stub(root)
    overlay = MagicMock()
    box = MagicMock()
    with patch('gui.tk.Frame', side_effect=[overlay, box]), \
         patch('gui.tk.Label'), \
         patch('gui.tk.Button') as mock_button:
        gui_obj.show_menu()
        texts = [kwargs.get('text', '') for _, kwargs in mock_button.call_args_list]
        assert 'Start Tutorial' in texts


def test_show_hint_calls_game_and_displays():
    root = MagicMock()
    gui_obj = make_gui_stub(root)
    gui_obj.game = MagicMock()
    gui_obj.game.current_combo = None
    gui_obj.game.hint.return_value = ['A', 'B']
    with patch('gui.messagebox.showinfo') as mock_info:
        gui_obj.show_hint()
        gui_obj.game.hint.assert_called_with(gui_obj.game.current_combo)
        mock_info.assert_called_once()


def test_update_display_disables_hint_for_ai_turn():
    root = MagicMock()
    gui_obj = make_gui_stub(root)
    gui_obj.update_display = gui.GameGUI.update_display.__get__(gui_obj)
    gui_obj.table_view = MagicMock()
    gui_obj.hand_view = MagicMock()
    gui_obj.info_var = MagicMock()
    gui_obj.turn_label = MagicMock()
    gui_obj.turn_var = MagicMock()
    gui_obj.play_btn = MagicMock()
    gui_obj.pass_btn = MagicMock()
    gui_obj.hint_btn = MagicMock()
    gui_obj.update_sidebar = MagicMock()
    human = MagicMock(is_human=True, name='Human')
    ai = MagicMock(is_human=False, name='AI')
    gui_obj.game = MagicMock()
    gui_obj.game.players = [human, ai]
    gui_obj.game.current_idx = 1  # AI's turn
    gui_obj.game.current_combo = None
    gui_obj.selected = set()
    gui_obj.game.is_valid.return_value = (True, '')

    gui_obj.update_display()
    gui_obj.hint_btn.config.assert_called_with(state=gui.tk.DISABLED)


def test_show_game_over_displays_rankings():
    root = MagicMock()
    gui_obj = make_gui_stub(root)
    gui_obj.game = MagicMock()
    gui_obj.game.get_rankings.return_value = [('Alice', 0), ('Bob', 3)]

    overlay = MagicMock()
    box = MagicMock()
    btn_frame = MagicMock()
    with patch('gui.tk.Frame', side_effect=[overlay, box, btn_frame]) as mock_frame, \
         patch('gui.tk.Label') as mock_label, \
         patch('gui.tk.Button') as mock_button, \
         patch('gui.sound.play'), \
         patch.object(gui.GameGUI, '_sparkle'):
        gui_obj.show_game_over('Alice')

        mock_frame.assert_any_call(gui_obj.root, bg='#000000')
        overlay.place.assert_called_with(relx=0, rely=0, relwidth=1, relheight=1)
        gui_obj.game.get_rankings.assert_called_once()

        texts = [kwargs.get('text', '') for _, kwargs in mock_label.call_args_list]
        assert any('Alice' in t and 'Bob' in t for t in texts)
        assert mock_button.call_count >= 2


def test_update_display_sets_undo_state():
    root = MagicMock()
    gui_obj = make_gui_stub(root)
    gui_obj.update_display = gui.GameGUI.update_display.__get__(gui_obj)
    gui_obj.table_view = MagicMock()
    gui_obj.hand_view = MagicMock()
    gui_obj.info_var = MagicMock()
    gui_obj.turn_label = MagicMock()
    gui_obj.turn_var = MagicMock()
    gui_obj.play_btn = MagicMock()
    gui_obj.pass_btn = MagicMock()
    gui_obj.hint_btn = MagicMock()
    gui_obj.update_sidebar = MagicMock()
    player = MagicMock(is_human=True, name='Player')
    gui_obj.game = MagicMock()
    gui_obj.game.players = [player]
    gui_obj.game.current_idx = 0
    gui_obj.game.current_combo = None
    gui_obj.game.is_valid.return_value = (True, '')
    gui_obj.selected = set()

    gui_obj.game.snapshots = ['s1']
    gui_obj.update_display()
    gui_obj.undo_btn.config.assert_called_with(state=gui.tk.DISABLED)

    gui_obj.game.snapshots.append('s2')
    gui_obj.update_display()
    gui_obj.undo_btn.config.assert_called_with(state=gui.tk.NORMAL)


def test_gui_initializes_opponent_views():
    root = MagicMock()
    root.cget = MagicMock(return_value="white")
    with patch('gui.tk.Menu'), \
         patch('gui.tk.Frame'), \
         patch('gui.tk.Label'), \
         patch('gui.tk.Button'), \
         patch('gui.tk.Scale'), \
         patch('gui.tk.StringVar'), \
         patch('gui.tk.DoubleVar'), \
         patch('gui.tkfont.Font'), \
         patch.object(gui.GameGUI, 'load_images'), \
         patch.object(gui.GameGUI, 'show_menu'), \
         patch.object(gui.GameGUI, 'update_display'), \
         patch('gui.TableView'), \
         patch('gui.HandView'), \
         patch('gui.OpponentView') as mock_opp, \
         patch('gui.Game') as MockGame:
        game = MagicMock()
        game.setup = MagicMock()
        players = [MagicMock(is_human=True, name='P', hand=[])]
        players += [MagicMock(is_human=False, name=f'A{i}', hand=[]) for i in range(1,4)]
        game.players = players
        game.scores = {p.name: 0 for p in players}
        MockGame.return_value = game
        gui_obj = gui.GameGUI(root)
        assert mock_opp.call_count == 3
        assert hasattr(gui_obj, 'left_opponent')
        assert hasattr(gui_obj, 'top_opponent')
        assert hasattr(gui_obj, 'right_opponent')



def test_play_selected_updates_hand_and_refreshes():
    root = MagicMock()
    gui_obj = make_gui_stub(root)
    gui_obj.update_display = gui.GameGUI.update_display.__get__(gui_obj)
    gui_obj.table_view = MagicMock()
    gui_obj.hand_view = MagicMock()
    gui_obj.hand_view.selected = set()
    gui_obj.hand_view.refresh = MagicMock()
    gui_obj.info_var = MagicMock()
    gui_obj.turn_label = MagicMock()
    gui_obj.turn_var = MagicMock()
    gui_obj.play_btn = MagicMock()
    gui_obj.pass_btn = MagicMock()
    gui_obj.hint_btn = MagicMock()
    gui_obj.history_var = MagicMock()
    gui_obj.ranking_var = MagicMock()
    gui_obj.score_var = MagicMock()
    gui_obj.update_sidebar = MagicMock()

    game = Game()
    player = game.players[0]
    player.hand = [Card('Spades', '3'), Card('Hearts', '4')]
    game.current_idx = 0
    game.current_combo = None
    game.is_valid = MagicMock(return_value=(True, ''))
    game.snapshots = [game.to_json()]
    gui_obj.game = game

    gui_obj.selected = {player.hand[0]}

    with patch.object(gui_obj, 'animate_play'), \
         patch('gui.sound.play'):
        gui_obj.play_selected()

    assert len(player.hand) == 1
    gui_obj.hand_view.refresh.assert_called_once()


def test_load_options_and_save_options(tmp_path):
    path = tmp_path / "opts.json"
    path.write_text('{"ai_level": "Hard"}')
    root = MagicMock()
    gui_obj = make_gui_stub(root)
    gui_obj.OPTIONS_FILE = path
    opts = gui_obj.load_options()
    assert opts["ai_level"] == "Hard"

    gui_obj.animation_speed = 1.5
    gui_obj.table_cloth_color = "navy"
    gui_obj.card_back_name = "card_back"
    gui_obj.sort_mode = "suit"
    gui_obj.player_name = "Bob"
    gui_obj.ai_level = "Easy"
    gui_obj.ai_personality = "defensive"
    gui_obj.ai_lookahead = True
    gui_obj.save_options()
    saved = json.loads(path.read_text())
    assert saved["animation_speed"] == 1.5
    assert saved["ai_personality"] == "defensive"


def test_resize_bg_updates_image():
    root = MagicMock()
    gui_obj = make_gui_stub(root)
    gui_obj._bg_base = MagicMock()
    gui_obj._bg_label = MagicMock()
    resized = MagicMock()
    gui_obj._bg_base.resize.return_value = resized
    with patch('gui.ImageTk.PhotoImage', return_value='img') as photo:
        gui_obj._resize_bg(MagicMock(width=10, height=20))
    gui_obj._bg_base.resize.assert_called_with((10, 20), gui.Image.LANCZOS)
    gui_obj._bg_label.config.assert_called_with(image='img')
    assert gui_obj._bg_label.image == 'img'


def test_show_menu_sets_overlay_active():
    root = MagicMock()
    gui_obj = make_gui_stub(root)
    overlay = MagicMock()
    box = MagicMock()
    with patch('gui.tk.Frame', side_effect=[overlay, box]):
        with patch('gui.tk.Label'), patch('gui.tk.Button'):
            gui_obj.show_menu()
    assert gui_obj.overlay_active is True
    assert gui_obj.menu_overlay is overlay
    overlay.place.assert_called_once()
