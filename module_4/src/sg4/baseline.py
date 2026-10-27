"""Per-driver calibration (first calibration_s of a drive) and short-term trend."""
from collections import deque
from typing import Optional

import numpy as np

from .config import Config

STABLE, WORSENING, IMPROVING = "stable", "worsening", "improving"


class Baseline:
    """Freezes the driver's PERCLOS and blink rate at the end of calibration."""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.start_ms: Optional[int] = None
        self.perclos: Optional[float] = None
        self.blink_rate_bpm: Optional[float] = None

    def calibrating(self, now_ms: int) -> bool:
        if self.start_ms is None:
            return True
        return now_ms - self.start_ms < self.cfg.calibration_s * 1000

    def update(self, now_ms: int, perclos: float, blink_rate_bpm: float) -> None:
        """Call once per output. The values at the end of calibration become the baseline."""
        if self.start_ms is None:
            self.start_ms = now_ms
        if self.perclos is None and not self.calibrating(now_ms):
            self.perclos, self.blink_rate_bpm = perclos, blink_rate_bpm

    def relative_perclos(self, perclos: float) -> Optional[float]:
        """perclos / baseline (1.0 = same as when the drive started). None while calibrating."""
        if self.perclos is None:
            return None
        return perclos / max(self.perclos, self.cfg.baseline_perclos_floor)


def slope_per_min(t_s, y) -> float:
    """Least-squares slope of y over time, in units per minute (0.0 if < 2 points)."""
    t = np.asarray(t_s, dtype=float)
    if t.size < 2 or np.ptp(t) <= 0:
        return 0.0
    y = np.asarray(y, dtype=float)
    tc = t - t.mean()
    return float(np.dot(tc, y - y.mean()) / np.dot(tc, tc)) * 60.0


class Trend:
    """PERCLOS slope over the last trend_window_s of outputs -> stable / worsening / improving."""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.t = deque()
        self.y = deque()

    def update(self, time_s: float, perclos: float) -> None:
        self.t.append(time_s)
        self.y.append(perclos)
        while self.t and self.t[0] < time_s - self.cfg.trend_window_s:
            self.t.popleft()
            self.y.popleft()

    def label(self) -> str:
        s = slope_per_min(self.t, self.y)
        if s >= self.cfg.trend_worsening_per_min:
            return WORSENING
        if s <= -self.cfg.trend_worsening_per_min:
            return IMPROVING
        return STABLE
