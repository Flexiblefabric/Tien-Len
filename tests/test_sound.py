import types
from unittest.mock import MagicMock, patch

from tienlen import sound


def _stub_pygame(mock_sound):
    mixer = types.SimpleNamespace(Sound=mock_sound)
    return types.SimpleNamespace(mixer=mixer)


def test_load_success(tmp_path):
    wav = tmp_path / "a.wav"
    wav.write_text("data")
    mock_instance = MagicMock()
    with patch.object(sound, "pygame", _stub_pygame(MagicMock(return_value=mock_instance))):
        with patch("sound.Path.is_file", return_value=True):
            sound.set_enabled(True)
            sound._SOUNDS.clear()
            assert sound.load("hit", wav)
            assert sound._SOUNDS["hit"] is mock_instance


def test_load_respects_current_volume(tmp_path):
    wav = tmp_path / "a.wav"
    wav.write_text("data")
    snd = MagicMock()
    with patch.object(sound, "pygame", _stub_pygame(MagicMock(return_value=snd))):
        with patch("sound.Path.is_file", return_value=True):
            sound.set_enabled(True)
            sound.set_volume(0.25)
            sound._SOUNDS.clear()
            assert sound.load("hit", wav)
            snd.set_volume.assert_called_with(0.25)


def test_set_enabled_toggles_flag():
    sound.set_enabled(True)
    assert sound._ENABLED is True
    sound.set_enabled(False)
    assert sound._ENABLED is False


def test_load_disabled_or_missing(tmp_path):
    wav = tmp_path / "a.wav"
    wav.write_text("data")
    mock_cls = MagicMock()
    # Disabled
    with patch.object(sound, "pygame", _stub_pygame(mock_cls)):
        with patch("sound.Path.is_file", return_value=True):
            sound.set_enabled(False)
            sound._SOUNDS.clear()
            assert not sound.load("foo", wav)
            mock_cls.assert_not_called()
            assert "foo" not in sound._SOUNDS
    # Missing file
    with patch.object(sound, "pygame", _stub_pygame(mock_cls)):
        with patch("sound.Path.is_file", return_value=False):
            sound.set_enabled(True)
            sound._SOUNDS.clear()
            assert not sound.load("bar", wav)
            mock_cls.assert_not_called()
            assert "bar" not in sound._SOUNDS


def test_play_noop_when_disabled_or_unknown():
    mock_sound = MagicMock()
    sound._SOUNDS.clear()
    sound._SOUNDS["shoot"] = mock_sound

    # Disabled
    sound.set_enabled(False)
    sound.play("shoot")
    mock_sound.play.assert_not_called()

    # Unknown name
    sound.set_enabled(True)
    mock_sound.play.reset_mock()
    sound.play("missing")
    mock_sound.play.assert_not_called()


def test_play_handles_errors():
    mock_sound = MagicMock()
    mock_sound.play.side_effect = Exception("boom")
    sound._SOUNDS.clear()
    sound._SOUNDS["explode"] = mock_sound
    sound.set_enabled(True)
    sound.play("explode")  # should not raise
    mock_sound.play.assert_called_once()


def test_load_handles_sound_error(tmp_path):
    wav = tmp_path / "err.wav"
    wav.write_text("data")
    mock_cls = MagicMock(side_effect=Exception("boom"))
    with patch.object(sound, "pygame", _stub_pygame(mock_cls)):
        with patch("sound.Path.is_file", return_value=True):
            sound.set_enabled(True)
            sound._SOUNDS.clear()
            assert not sound.load("bad", wav)
            assert "bad" not in sound._SOUNDS
