"""Event state machines: eye closures (blink / slow blink / long blink) and
debounced segment events (yawns, nods). All durations come from timestamps.
"""
from collections import deque
from dataclasses import dataclass
from typing import List, Optional

from .config import Config

# Closure kinds
NOISE = "noise"              # shorter than min_blink_ms
BLINK = "blink"              # min_blink_ms <= d <= slow_blink_ms
SLOW = "slow_blink"          # slow_blink_ms < d < long_blink_ms
LONG = "long_blink"          # d >= long_blink_ms (= microsleep)
INTERRUPTED = "interrupted"  # eye became invalid before long_blink_ms: true length unknown


@dataclass
class Closure:
    start_ms: int
    end_ms: int
    kind: str
    long_reported: bool = False   # True if already counted as a long blink while ongoing

    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms


def classify_closure(duration_ms: int, cfg: Config) -> str:
    if duration_ms >= cfg.long_blink_ms:
        return LONG
    if duration_ms > cfg.slow_blink_ms:
        return SLOW
    if duration_ms >= cfg.min_blink_ms:
        return BLINK
    return NOISE


class ClosureTracker:
    """Hysteresis open/closed state machine on closure_prob.

    Closed when closure_prob >= close_on, reopened when <= close_off. A long
    blink is reported the moment the ongoing closure reaches long_blink_ms
    (so SG-5 sees it with no lag); blinks are classified when the eye reopens.
    An invalid eye ends the closure: eye_closure_s must drop to 0 on face loss.
    """

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.closed = False
        self.start_ms = 0
        self.last_valid_ms = 0
        self.long_reported = False

    def live_ms(self, now_ms: int) -> int:
        """Length of the ongoing closure (0 when open or invalid)."""
        return now_ms - self.start_ms if self.closed else 0

    def update(self, t_ms: int, eye_valid: bool, closure_prob: float):
        """Return (long_blink_started_now, finished_closure_or_None)."""
        cfg = self.cfg
        if not eye_valid:
            if not self.closed:
                return False, None
            self.closed = False
            end = self.last_valid_ms
            kind = LONG if self.long_reported else INTERRUPTED
            return False, Closure(self.start_ms, end, kind, self.long_reported)
        self.last_valid_ms = t_ms
        if not self.closed:
            if closure_prob >= cfg.close_on:
                self.closed, self.start_ms, self.long_reported = True, t_ms, False
            return False, None
        if closure_prob <= cfg.close_off:
            self.closed = False
            d = t_ms - self.start_ms
            return False, Closure(self.start_ms, t_ms, classify_closure(d, cfg), self.long_reported)
        if not self.long_reported and t_ms - self.start_ms >= cfg.long_blink_ms:
            self.long_reported = True
            return True, None
        return False, None


class SegmentTracker:
    """Hysteresis + minimum duration + merge for yawns and nods.

    `level` is oriented so that higher = more active (yawn_prob, or -pitch for
    nods). A segment starts at level >= on and ends at level < off. It is counted
    once, as soon as it has lasted min_ms. A new segment starting less than
    merge_gap_ms after the previous one ended continues that event (no new count).
    `force_on` keeps / starts the segment while the cue is invalid (head drop
    that loses the face).
    """

    def __init__(self, on: float, off: float, min_ms: int, merge_gap_ms: int):
        self.on, self.off = on, off
        self.min_ms, self.merge_gap_ms = min_ms, merge_gap_ms
        self.active = False
        self.seg_start = 0
        self.counted = False
        self.last_end: Optional[int] = None
        self.last_start = 0
        self.last_counted = False

    def update(self, t_ms: int, valid: bool, level: float, force_on: bool = False) -> bool:
        """Advance one frame; return True when a new event is counted at this frame."""
        if valid:
            is_on = level > self.off if self.active else level >= self.on
        else:
            is_on = force_on
        if is_on and not self.active:
            self.active = True
            if self.last_end is not None and t_ms - self.last_end < self.merge_gap_ms:
                self.seg_start, self.counted = self.last_start, self.last_counted
            else:
                self.seg_start, self.counted = t_ms, False
        elif not is_on and self.active:
            self.active = False
            self.last_end, self.last_start, self.last_counted = t_ms, self.seg_start, self.counted
            return False
        if self.active and not self.counted and t_ms - self.seg_start >= self.min_ms:
            self.counted = True
            return True
        return False


class EventWindow:
    """Events (time, value) in a sliding time window; amortised O(1) count/sum."""

    def __init__(self, length_ms: int):
        self.length_ms = int(length_ms)
        self.items = deque()
        self.total = 0.0

    def add(self, t_ms: int, value: float = 1.0) -> None:
        self.items.append((t_ms, value))
        self.total += value

    def prune(self, now_ms: int) -> None:
        cutoff = now_ms - self.length_ms
        items = self.items
        while items and items[0][0] <= cutoff:
            self.total -= items.popleft()[1]
        if not items:
            self.total = 0.0               # reset float drift whenever the window empties

    def count(self) -> int:
        return len(self.items)

    def mean(self) -> float:
        return self.total / len(self.items) if self.items else 0.0

    def max(self) -> float:
        return max(v for _, v in self.items) if self.items else 0.0

    def values(self) -> List[float]:
        return [v for _, v in self.items]
