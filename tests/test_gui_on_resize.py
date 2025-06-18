import gui
from unittest.mock import MagicMock
import pytest
from tests.test_gui_features import make_gui_stub


def test_on_resize_busy_flag_prevents_recursion():
    root = MagicMock()
    gui_obj = make_gui_stub(root)
    gui_obj.card_font.__getitem__.return_value = 12
    gui_obj.card_font.configure = MagicMock()

    gui_obj.on_resize = gui.GameGUI.on_resize.__get__(gui_obj)
    event = MagicMock(width=400)

    call_count = 0

    def patched_update():
        nonlocal call_count
        call_count += 1
        gui_obj.on_resize(event)

    gui_obj.update_display = patched_update

    try:
        gui_obj.on_resize(event)
    except RecursionError:
        pytest.fail("RecursionError raised")

    assert call_count == 1
