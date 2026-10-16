"""Chess-clock helpers with monotonic timing and per-move increment."""

from __future__ import annotations

import math
import time
from collections.abc import Callable


class ClockExpired(Exception):
    """Raised when a player's clock reaches zero while entering a move."""

    def __init__(self, color: bool):
        self.color = color
        super().__init__("White ran out of time." if color else "Black ran out of time.")


def color_name(color: bool) -> str:
    return "White" if color else "Black"


def format_clock(seconds: float) -> str:
    """Format remaining time as M:SS or H:MM:SS."""
    whole_seconds = max(0, math.ceil(seconds))
    hours, remainder = divmod(whole_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


class ChessClock:
    """Two-sided chess clock. Call start once when a turn begins."""

    def __init__(self, base_seconds: float, increment_seconds: float = 0, *, now: Callable[[], float] = time.monotonic) -> None:
        if base_seconds <= 0:
            raise ValueError("base_seconds must be greater than zero")
        if increment_seconds < 0:
            raise ValueError("increment_seconds cannot be negative")
        self.base_seconds = float(base_seconds)
        self.increment_seconds = float(increment_seconds)
        self._remaining = {True: float(base_seconds), False: float(base_seconds)}
        self._now = now
        self._running_color: bool | None = None
        self._started_at: float | None = None

    @property
    def running_color(self) -> bool | None:
        return self._running_color

    def start(self, color: bool) -> None:
        """Start a side's clock; repeated calls for the same side are harmless."""
        if self._running_color == color:
            return
        if self._running_color is not None:
            raise RuntimeError("Cannot start one clock while the other is running")
        if self._remaining[color] <= 0:
            raise ClockExpired(color)
        self._running_color = color
        self._started_at = self._now()

    def remaining(self, color: bool) -> float:
        """Return a live, non-negative time value for a side."""
        value = self._remaining[color]
        if self._running_color == color and self._started_at is not None:
            value -= self._now() - self._started_at
        return max(0.0, value)

    def is_flagged(self, color: bool) -> bool:
        return self.remaining(color) <= 0

    def finish_move(self, color: bool) -> bool:
        """Stop a turn and add increment. Return False if the side flagged."""
        if self._running_color != color or self._started_at is None:
            raise RuntimeError("The selected side's clock is not running")
        value = self.remaining(color)
        self._remaining[color] = value
        self._running_color = None
        self._started_at = None
        if value <= 0:
            return False
        self._remaining[color] += self.increment_seconds
        return True

    def stop(self) -> None:
        """Freeze the active clock, for example when leaving a game."""
        if self._running_color is not None and self._started_at is not None:
            color = self._running_color
            self._remaining[color] = self.remaining(color)
        self._running_color = None
        self._started_at = None
