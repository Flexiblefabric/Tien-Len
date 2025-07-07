import math
from pygame_gui.tween import Tween, Timeline


def test_timeline_wait_then_updates():
    called = []
    tl = Timeline()
    tl.wait(0.1).then(lambda: called.append(True))
    tl.update(0.05)
    assert not called
    tl.update(0.05)
    assert called == [True]


def test_timeline_add_tween_updates_value():
    values = []
    tw = Tween(0, 1, 0.1)
    tl = Timeline().add(tw, lambda v: values.append(v))
    tl.update(0.05)
    tl.update(0.05)
    assert math.isclose(values[-1], 1.0)
