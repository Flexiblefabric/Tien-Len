import types
from unittest.mock import MagicMock, patch

import sound


def _stub_pygame(mock_sound):
    mixer = types.SimpleNamespace(Sound=mock_sound)
    return types.SimpleNamespace(mixer=mixer)


def test_load_success(tmp_path):
    wav = tmp_path / "a.wav"
    wav.write_text("data")
    mock_instance = MagicMock()
    with patch.object(sound, "pygame", _stub_pygame(MagicMock(return_value=mock_instance))):
        with patch("sound.Path.is_file", return_value=True):
            sound._ENABLED = True
            sound._SOUNDS.clear()
            assert sound.load("hit", wav)
            assert sound._SOUNDS["hit"] is mock_instance


def test_load_disabled_or_missing(tmp_path):
    wav = tmp_path / "a.wav"
    wav.write_text("data")
    mock_cls = MagicMock()
    # Disabled
    with patch.object(sound, "pygame", _stub_pygame(mock_cls)):
        with patch("sound.Path.is_file", return_value=True):
            sound._ENABLED = False
            sound._SOUNDS.clear()
            assert not sound.load("foo", wav)
            mock_cls.assert_not_called()
            assert "foo" not in sound._SOUNDS
    # Missing file
    with patch.object(sound, "pygame", _stub_pygame(mock_cls)):
        with patch("sound.Path.is_file", return_value=False):
            sound._ENABLED = True
            sound._SOUNDS.clear()
            assert not sound.load("bar", wav)
            mock_cls.assert_not_called()
            assert "bar" not in sound._SOUNDS


def test_play_noop_when_disabled_or_unknown():
    mock_sound = MagicMock()
    sound._SOUNDS.clear()
    sound._SOUNDS["shoot"] = mock_sound

    # Disabled
    sound._ENABLED = False
    sound.play("shoot")
    mock_sound.play.assert_not_called()

    # Unknown name
    sound._ENABLED = True
    mock_sound.play.reset_mock()
    sound.play("missing")
    mock_sound.play.assert_not_called()


def test_play_handles_errors():
    mock_sound = MagicMock()
    mock_sound.play.side_effect = Exception("boom")
    sound._SOUNDS.clear()
    sound._SOUNDS["explode"] = mock_sound
    sound._ENABLED = True
    sound.play("explode")  # should not raise
    mock_sound.play.assert_called_once()
