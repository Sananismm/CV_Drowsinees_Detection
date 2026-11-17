"""Indicator formulas and the IndicatorState handed to sg5_output.to_sg5().

Each formula is a small pure function so it can be unit-tested by hand.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class IndicatorState:
    """Everything SG-4 publishes, in SG-4's internal units. to_sg5() formats it."""
    time_s: float
    perclos: float              # 0-1
    face_valid: bool
    long_blinks: int
    yawn_count: int
    eye_closure_s: float
    nod_count: int
    validity_score: float       # 0-1
    calibrating: bool
    blink_rate_bpm: float
    mean_blink_ms: float
    slow_blinks: int
    longest_closure_s: float
    head_down_s: float
    face_absent_s: float
    perclos_vs_baseline: Optional[float]
    trend: Optional[str]


def empty_state(time_s: float = 0.0) -> IndicatorState:
    """No-data vector (CLAUDE.md section 5): face_valid 0, validity 0, counts 0."""
    return IndicatorState(
        time_s=time_s, perclos=0.0, face_valid=False, long_blinks=0, yawn_count=0,
        eye_closure_s=0.0, nod_count=0, validity_score=0.0, calibrating=True,
        blink_rate_bpm=0.0, mean_blink_ms=0.0, slow_blinks=0, longest_closure_s=0.0,
        head_down_s=0.0, face_absent_s=0.0, perclos_vs_baseline=None, trend=None,
    )


def perclos(closed_ms: int, valid_ms: int) -> float:
    """P80 PERCLOS: closed share of VALID time, 0-1. No valid time -> 0.0."""
    if valid_ms <= 0:
        return 0.0
    return min(1.0, max(0.0, closed_ms / float(valid_ms)))


def share(part: int, total: int) -> float:
    """part / total clipped to 0-1 (validity_score)."""
    if total <= 0:
        return 0.0
    return min(1.0, max(0.0, part / float(total)))


def rate_per_min(count: int, valid_ms: int, min_valid_ms: float) -> float:
    """Events per minute of valid observation; 0.0 until min_valid_ms is observed."""
    if valid_ms < max(min_valid_ms, 1):
        return 0.0
    return count * 60000.0 / valid_ms
