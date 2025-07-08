from __future__ import annotations

from typing import Callable

from .easing import EASING_FUNCTIONS, linear


class Tween:
    """Simple tween for numeric values."""

    def __init__(self, start: float, end: float, duration: float,
                 ease: str | Callable[[float], float] | None = None):
        self.start = start
        self.end = end
        self.duration = max(duration, 1e-8)
        if isinstance(ease, str):
            if ease not in EASING_FUNCTIONS:
                raise KeyError(f"Unknown easing '{ease}'")
            self.ease = EASING_FUNCTIONS[ease]
        else:
            self.ease = ease or linear
        self.elapsed = 0.0

    def update(self, dt: float) -> float:
        """Advance by ``dt`` seconds and return the current interpolated value."""
        self.elapsed = min(self.elapsed + dt, self.duration)
        progress = self.elapsed / self.duration
        eased = self.ease(progress)
        return self.start + (self.end - self.start) * eased

    @property
    def finished(self) -> bool:
        """Return ``True`` when the tween has reached its end value."""
        return self.elapsed + 1e-9 >= self.duration


class Timeline:
    """Chain multiple ``Tween`` objects and callbacks sequentially."""

    def __init__(self) -> None:
        self._steps: list = []
        self._current = None

    def add(self, tween: Tween, setter: Callable[[float], None] | None = None) -> "Timeline":
        """Append ``tween`` to the queue applying ``setter`` on each update."""
        self._steps.append((tween, setter))
        return self

    def wait(self, duration: float) -> "Timeline":
        """Pause for ``duration`` seconds."""
        self._steps.append((Tween(0.0, 1.0, duration), None))
        return self

    def then(self, step) -> "Timeline":
        """Execute ``step`` after previous entries finish."""
        self._steps.append(step)
        return self

    # Internal update -------------------------------------------------
    def _advance(self, dt: float) -> float:
        if isinstance(self._current, tuple):
            tw, setter = self._current
            before = tw.elapsed
            value = tw.update(dt)
            if setter:
                setter(value)
            return tw.elapsed - before
        elif hasattr(self._current, "send"):
            try:
                self._current.send(dt)
            except StopIteration:
                self._current = None
            return dt
        return dt

    def update(self, dt: float) -> None:
        """Advance the timeline by ``dt`` seconds."""
        while dt > 0 or (dt == 0 and self._current is None and self._steps):
            if self._current is None:
                if not self._steps:
                    break
                step = self._steps.pop(0)
                if isinstance(step, tuple) or hasattr(step, "send"):
                    self._current = step
                    if hasattr(step, "send"):
                        try:
                            next(step)
                        except StopIteration:
                            self._current = None
                            continue
                elif isinstance(step, Tween):
                    self._current = (step, None)
                else:
                    step()
                    continue
            consumed = self._advance(dt)
            if isinstance(self._current, tuple) and self._current[0].finished:
                self._current = None
            dt -= consumed

    @property
    def active(self) -> bool:
        return self._current is not None or bool(self._steps)

    # Generator wrapper -----------------------------------------------
    def play(self):
        """Return a generator that updates the timeline each frame."""

        def gen():
            dt = yield
            while self.active:
                self.update(dt)
                dt = yield
            yield

        return gen()
