from unittest.mock import MagicMock, patch
import sys

sys.modules.setdefault('pygame', MagicMock())

import gui


def make_gui_stub(root):
    g = gui.GameGUI.__new__(gui.GameGUI)
    g.root = root
    # Provide cget so set_high_contrast can read the default background
    g.root.cget = MagicMock(return_value="white")
    g._default_bg = "white"
    g.card_font = MagicMock()
    g.update_display = MagicMock()
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


def test_show_rules_creates_modal():
    root = MagicMock()
    gui_obj = make_gui_stub(root)
    win = MagicMock()
    with patch('gui.tk.Toplevel', return_value=win) as mock_top, \
         patch('gui.tk.Label') as mock_label, \
         patch('gui.tk.Button') as mock_button:
        gui_obj.show_rules()
        mock_top.assert_called_with(gui_obj.root)
        win.title.assert_called_with('Game Rules')
        win.transient.assert_called_with(gui_obj.root)
        win.grab_set.assert_called_once()
        mock_label.assert_called()
        mock_button.assert_called()


def test_show_menu_overlay():
    root = MagicMock()
    gui_obj = make_gui_stub(root)
    overlay = MagicMock()
    box = MagicMock()
    with patch('gui.tk.Frame', side_effect=[overlay, box]) as mock_frame, \
         patch('gui.tk.Label') as mock_label, \
         patch('gui.tk.Button') as mock_button:
        gui_obj.show_menu()
        mock_frame.assert_any_call(gui_obj.root, bg='#00000080')
        overlay.place.assert_called_with(relx=0, rely=0, relwidth=1, relheight=1)
        assert mock_button.call_count >= 4

