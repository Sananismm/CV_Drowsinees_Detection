"""The ONLY place SG-5 field names are written (contract sg4.output.v1.1).

SG-5's request is followed literally: names, units (perclos 0-1, face_valid
0/1) and windows. Change a field here only together with an entry in
documentation/interface_tracking.md and the output schema.
"""
from typing import Any, Dict

from .indicators import IndicatorState
from .schema import OUTPUT_SCHEMA_ID

# Fields SG-5 consumes (contract) and SG-4 extras, in output order.
SG5_FIELDS = ("time_s", "perclos", "face_valid", "long_blinks", "yawn_count", "eye_closure_s")
EXTRA_FIELDS = ("nod_count", "validity_score", "calibrating", "blink_rate_bpm", "mean_blink_ms",
                "slow_blinks", "longest_closure_s", "head_down_s", "face_absent_s",
                "perclos_vs_baseline", "trend")


def _unit(x: float) -> float:
    return round(min(1.0, max(0.0, float(x))), 4)


def to_sg5(s: IndicatorState) -> Dict[str, Any]:
    """IndicatorState -> flat sg4.output.v1.1 dict (JSON-serialisable)."""
    return {
        "schema": OUTPUT_SCHEMA_ID,
        # --- SG-5 contract ---
        "time_s": round(float(s.time_s), 3),
        "perclos": _unit(s.perclos),
        "face_valid": 1 if s.face_valid else 0,
        "long_blinks": int(s.long_blinks),
        "yawn_count": int(s.yawn_count),
        "eye_closure_s": round(max(0.0, float(s.eye_closure_s)), 3),
        # --- extras (SG-5 may ignore) ---
        "nod_count": int(s.nod_count),
        "validity_score": _unit(s.validity_score),
        "calibrating": bool(s.calibrating),
        "blink_rate_bpm": round(float(s.blink_rate_bpm), 2),
        "mean_blink_ms": int(round(s.mean_blink_ms)),
        "slow_blinks": int(s.slow_blinks),
        "longest_closure_s": round(float(s.longest_closure_s), 3),
        "head_down_s": round(float(s.head_down_s), 3),
        "face_absent_s": round(float(s.face_absent_s), 3),
        "perclos_vs_baseline": None if s.perclos_vs_baseline is None else round(float(s.perclos_vs_baseline), 3),
        "trend": s.trend,
    }
