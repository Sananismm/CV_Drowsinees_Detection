"""Load SG-4 thresholds and windows from config/sg4_v1.yaml.

The YAML file is the single source of truth: Config has no defaults, so a
missing key fails loudly instead of silently using a hard-coded value.
"""
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "sg4_v1.yaml"


@dataclass(frozen=True)
class Config:
    output_rate_hz: float

    face_conf_min: float
    eye_conf_min: float
    mouth_conf_min: float
    head_conf_min: float
    gap_ms: int
    max_frame_dt_ms: int

    buffer_capacity: int

    p80_threshold: float
    close_on: float
    close_off: float
    min_blink_ms: int
    slow_blink_ms: int
    long_blink_ms: int

    yawn_on: float
    yawn_off: float
    min_yawn_ms: int
    yawn_merge_gap_ms: int

    nod_on_deg: float
    nod_off_deg: float
    min_nod_ms: int
    nod_merge_gap_ms: int
    nod_face_loss_ms: int

    perclos_window_s: float
    long_blink_window_s: float
    yawn_window_s: float
    nod_window_s: float
    blink_window_s: float
    validity_window_s: float
    min_valid_for_rate_s: float

    calibration_s: float
    baseline_perclos_floor: float
    trend_window_s: float
    trend_worsening_per_min: float

    @property
    def output_period_ms(self) -> int:
        return int(round(1000.0 / self.output_rate_hz))


def load_config(path: Optional[Path] = None, overrides: Optional[Dict[str, Any]] = None) -> Config:
    """Read the YAML config; `overrides` replaces individual keys (used by tests and sweeps)."""
    with open(path or DEFAULT_CONFIG_PATH, "r") as f:
        raw = yaml.safe_load(f)
    if overrides:
        raw.update(overrides)
    names = {f.name for f in fields(Config)}
    unknown = set(raw) - names
    if unknown:
        raise ValueError("Unknown config keys: %s" % sorted(unknown))
    missing = names - set(raw)
    if missing:
        raise ValueError("Missing config keys: %s" % sorted(missing))
    return Config(**raw)
