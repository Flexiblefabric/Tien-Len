import math
import pytest

from pygame_gui.tween import Tween
from pygame_gui.easing import EASING_FUNCTIONS


def test_tween_named_ease():
    tw = Tween(0, 1, 1, ease="ease-out-cubic")
    assert math.isclose(tw.update(0.5), EASING_FUNCTIONS["ease-out-cubic"](0.5))


def test_tween_callable_ease():
    tw = Tween(0, 1, 1, ease=lambda t: t * t)
    assert math.isclose(tw.update(1.0), 1.0)


def test_unknown_ease_raises():
    with pytest.raises(KeyError):
        Tween(0, 1, 1, ease="nope")
