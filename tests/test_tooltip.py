from unittest.mock import MagicMock, patch
import tooltip


def test_show_creates_window_and_hide_destroys():
    widget = MagicMock()
    widget.winfo_rootx.return_value = 10
    widget.winfo_rooty.return_value = 20
    widget.winfo_height.return_value = 5

    win = MagicMock()
    with patch('tooltip.tk.Toplevel', return_value=win) as mock_top, \
         patch('tooltip.tk.Label'):
        tip = tooltip.ToolTip(widget, 'info')
        tip.show()

        expected_x = 10 + 20
        expected_y = 20 + 5 + 10
        mock_top.assert_called_with(widget)
        win.wm_overrideredirect.assert_called_with(True)
        win.wm_geometry.assert_called_with(f"+{expected_x}+{expected_y}")
        assert tip.tip is win

        tip.hide()
        win.destroy.assert_called_once()
        assert tip.tip is None
