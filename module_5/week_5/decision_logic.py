"""SG-5 Week 5: fuse SG-4 temporal evidence and choose an alert action."""

import json
import math
from pathlib import Path

from week4_baseline import DecisionEngine as Week4Engine


CONFIG_PATH = Path(__file__).parent / "configs.json"
STATES = {"ALERT": "NONE", "CAUTION": "VISUAL", "DROWSY": "AUDIO_VISUAL", "UNKNOWN": "NONE"}


def load_configs():
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def make_engine(config_name):
    config = load_configs()[config_name]
    if config["engine"] == "week4":
        # Week 4 settings live in the preserved code. Do not silently retune them.
        return Week4Engine()
    return DecisionEngine(config)


def validate_input(cues):
    """Check the V1 fields, types and ranges before using any values."""
    if not isinstance(cues, dict):
        raise ValueError("input must be a JSON object")
    fields = {
        "schema_version", "session_id", "driver_track_id", "timestamp_ms",
        "window_ms", "temporal_confidence", "eye", "yawn", "fatigue",
    }
    if set(cues) != fields:
        raise ValueError("input fields do not match temporal-cues.v1")
    if cues["schema_version"] != "sg5.temporal-cues.v1":
        raise ValueError("unsupported input schema_version")
    for field in ("session_id", "driver_track_id"):
        if not isinstance(cues[field], str) or not cues[field]:
            raise ValueError(f"{field} must be a nonempty string")

    def number(value, name, minimum=0, maximum=None, integer=False):
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError(f"{name} must be a finite number")
        if integer and type(value) is not int:
            raise ValueError(f"{name} must be an integer")
        if value < minimum or (maximum is not None and value > maximum):
            raise ValueError(f"{name} is outside its permitted range")

    number(cues["timestamp_ms"], "timestamp_ms", integer=True)
    number(cues["window_ms"], "window_ms", minimum=1000, integer=True)
    number(cues["temporal_confidence"], "temporal_confidence", maximum=1)
    required = {
        "eye": {"perclos", "longest_closure_ms", "blink_rate_per_min", "confidence"},
        "yawn": {"count", "total_duration_ms", "confidence"},
        "fatigue": {"persistence", "confidence"},
    }
    for group, names in required.items():
        values = cues[group]
        if not isinstance(values, dict) or set(values) != names:
            raise ValueError(f"{group} fields do not match temporal-cues.v1")
        for name in names:
            maximum = 1 if name in ("confidence", "perclos", "persistence") else None
            integer = name in ("longest_closure_ms", "count", "total_duration_ms")
            number(values[name], f"{group}.{name}", maximum=maximum, integer=integer)
    for group, field in (("eye", "longest_closure_ms"), ("yawn", "total_duration_ms")):
        if cues[group][field] > cues["window_ms"]:
            raise ValueError(f"{group}.{field} exceeds the observation window")


class DecisionEngine:
    def __init__(self, config):
        self.config = config
        weights = [config[k] for k in ("eye_weight", "yawn_weight", "persistence_weight")]
        if any(w < 0 for w in weights) or not math.isclose(sum(weights), 1.0):
            raise ValueError("weights must be nonnegative and sum to 1")
        if not 0 <= config["release_threshold"] < config["caution_threshold"] < config["drowsy_threshold"] <= 1:
            raise ValueError("thresholds must satisfy release < caution < drowsy")
        if not 0 <= config["min_confidence"] <= 1:
            raise ValueError("min_confidence must lie between 0 and 1")
        if any(config[k] < 0 for k in ("drowsy_entry_ms", "release_ms")) or config["max_update_gap_ms"] <= 0:
            raise ValueError("invalid timer configuration")
        self.context = None
        self.last_timestamp = None
        self.reset()

    def reset(self):
        self.state = "ALERT"
        self.high_since = None
        self.low_since = None

    def decide(self, cues):
        validate_input(cues)
        timestamp = cues["timestamp_ms"]
        context = (cues["session_id"], cues["driver_track_id"])
        if context != self.context:
            self.reset()
            self.last_timestamp = None
        if self.last_timestamp is not None:
            if timestamp <= self.last_timestamp:
                raise ValueError("timestamps must increase for the same driver/session")
            if timestamp - self.last_timestamp > self.config["max_update_gap_ms"]:
                self.reset()  # A gap is not evidence that high/low risk persisted.
        self.context = context
        self.last_timestamp = timestamp

        confidence = min(
            cues["temporal_confidence"], cues["eye"]["confidence"],
            cues["yawn"]["confidence"], cues["fatigue"]["confidence"],
        )
        if confidence < self.config["min_confidence"]:
            self.reset()
            self.state = "UNKNOWN"
            return self.result(cues, 0.0, confidence, [], "input confidence below threshold")

        eye_risk = max(cues["eye"]["perclos"], min(cues["eye"]["longest_closure_ms"] / 3000, 1))
        # Normalize counts and duration to a one-minute rate. At a 60s window
        # this is exactly the Week 4 formula.
        window_scale = 60000 / cues["window_ms"]
        yawn_risk = min(
            (cues["yawn"]["count"] * window_scale / 3
             + cues["yawn"]["total_duration_ms"] * window_scale / 9000) / 2, 1,
        )
        persistence = cues["fatigue"]["persistence"]
        risk = (
            self.config["eye_weight"] * eye_risk
            + self.config["yawn_weight"] * yawn_risk
            + self.config["persistence_weight"] * persistence
        )
        self.update_state(risk, timestamp)
        evidence = [f"eye_risk={eye_risk:.3f}", f"yawn_risk={yawn_risk:.3f}", f"fatigue_persistence={persistence:.3f}"]
        return self.result(cues, risk, confidence, evidence, "weighted fusion with entry/release timers")

    def update_state(self, risk, timestamp):
        if risk >= self.config["drowsy_threshold"]:
            self.low_since = None
            if self.high_since is None:
                self.high_since = timestamp
            if self.state == "DROWSY" or timestamp - self.high_since >= self.config["drowsy_entry_ms"]:
                self.state = "DROWSY"
            else:
                self.state = "CAUTION"  # Visual warning while confirming high risk.
            return

        self.high_since = None
        if self.state in ("DROWSY", "CAUTION"):
            if risk < self.config["release_threshold"]:
                if self.low_since is None:
                    self.low_since = timestamp
                if timestamp - self.low_since >= self.config["release_ms"]:
                    self.state = "ALERT"
                    self.low_since = None
            else:
                self.low_since = None
            return

        self.state = "CAUTION" if risk >= self.config["caution_threshold"] else "ALERT"

    def result(self, cues, risk, confidence, evidence, reason):
        return {
            "schema_version": "sg5.decision.v1",
            "session_id": cues["session_id"],
            "driver_track_id": cues["driver_track_id"],
            "timestamp_ms": cues["timestamp_ms"],
            "state": self.state,
            "risk_score": round(risk, 3),
            "confidence": round(confidence, 3),
            "alert_action": STATES[self.state],
            "evidence": evidence,
            "reason": reason,
        }
