"""Headless SG5 decision logic and a conservative SG6 compatibility adapter.

This is a deployment proposal, not a claim that the team has approved a new V1
interface. The unchanged legacy SG6 payload is available through
``to_legacy_sg6`` only while observations are usable. SG6 must inspect the richer
status, or catch adapter failures, rather than treat missing evidence as NORMAL.

Times are seconds on the producer's capture clock. ``tick`` must use that same
clock; mixing capture-relative time with wall-clock or monotonic host time is
not supported. All imports are from the Python standard library.
"""

from collections.abc import Mapping
from dataclasses import dataclass
import math
from numbers import Real
from types import MappingProxyType


STATES = ("NORMAL", "WARNING", "DROWSY")
SCHEMA_VERSION = "sg5.sg6.v2"


def _number(value, name, minimum=0.0, maximum=None):
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite number")
    value = float(value)
    if not math.isfinite(value) or value < minimum:
        raise ValueError(f"{name} must be finite and >= {minimum}")
    if maximum is not None and value > maximum:
        raise ValueError(f"{name} must be <= {maximum}")
    return value


def _flag(value, name):
    if isinstance(value, bool):
        return value
    if isinstance(value, Real) and value in (0, 1):
        return bool(value)
    raise ValueError(f"{name} must be true/false or 0/1")


def _session(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("session_id must be a nonempty string")
    return value


@dataclass(frozen=True)
class Config:
    """Immutable rules; scores are engineering evidence, not probabilities."""

    config_id: str = "midterm_c_v2"
    method: str = "C"
    weights: tuple = (0.45, 0.20, 0.20, 0.15)
    warn_score: float = 0.20
    drowsy_score: float = 0.50
    enter_warn: float = 0.20
    exit_warn: float = 0.14
    enter_drowsy: float = 0.65
    exit_drowsy: float = 0.53
    smoothing_s: float = 2.0
    confirm_s: float = 1.0
    release_s: float = 3.0
    microsleep_s: float = 1.5
    max_gap_s: float = 0.5
    min_quality: float = 0.55
    a_drowsy_perclos: float = 0.22
    a_drowsy_closure_s: float = 1.5
    a_warn_perclos: float = 0.10
    a_warn_yawns: int = 2
    a_warn_long_blinks: int = 3

    def __post_init__(self):
        _session(self.config_id)
        if self.method not in ("A", "B", "C"):
            raise ValueError("method must be A, B or C")
        if not isinstance(self.weights, tuple) or len(self.weights) != 4:
            raise ValueError("weights must be an immutable four-number tuple")
        weights = [_number(w, "weight") for w in self.weights]
        if sum(weights) <= 0:
            raise ValueError("at least one weight must be positive")
        for name in ("warn_score", "drowsy_score", "enter_warn", "exit_warn",
                     "enter_drowsy", "exit_drowsy", "min_quality",
                     "a_drowsy_perclos", "a_warn_perclos"):
            _number(getattr(self, name), name, maximum=1.0)
        if not self.exit_warn <= self.enter_warn <= self.exit_drowsy <= self.enter_drowsy:
            raise ValueError("C entry and exit thresholds must be ordered")
        if self.warn_score > self.drowsy_score:
            raise ValueError("B warning threshold must not exceed its drowsy threshold")
        if self.a_warn_perclos > self.a_drowsy_perclos:
            raise ValueError("A warning threshold must not exceed its drowsy threshold")
        for name in ("smoothing_s", "microsleep_s", "max_gap_s", "a_drowsy_closure_s"):
            if _number(getattr(self, name), name) <= 0:
                raise ValueError(f"{name} must be positive")
        for name in ("confirm_s", "release_s", "a_warn_yawns", "a_warn_long_blinks"):
            _number(getattr(self, name), name)
        for name in ("a_warn_yawns", "a_warn_long_blinks"):
            if not float(getattr(self, name)).is_integer():
                raise ValueError(f"{name} must be an integer")


# These preserve the Week 5 weights and thresholds, not its timestamp/quality
# bugs. The original frozen implementation remains the experiment reference.
CONFIGURATIONS = MappingProxyType({
    "threshold_a": Config(config_id="midterm_a_v2", method="A"),
    "weighted_b": Config(config_id="midterm_b_v2", method="B"),
    "stable_c": Config(),
})


def _observation(row, session_id):
    if not isinstance(row, Mapping):
        raise ValueError("observation must be a mapping")
    required = ("time_s", "face_valid", "perclos", "eye_closure_s", "long_blinks", "yawn_count")
    missing = [name for name in required if name not in row]
    if missing:
        raise ValueError("missing fields: " + ", ".join(missing))
    values = {
        "time_s": _number(row["time_s"], "time_s"),
        "face_valid": _flag(row["face_valid"], "face_valid"),
        "eye_valid": _flag(row.get("eye_valid", True), "eye_valid"),
        "perclos": _number(row["perclos"], "perclos", maximum=1.0),
        "eye_closure_s": _number(row["eye_closure_s"], "eye_closure_s"),
        "validity_score": _number(row.get("validity_score", 1.0), "validity_score", maximum=1.0),
        "session_id": _session(row.get("session_id", session_id)),
    }
    for name in ("long_blinks", "yawn_count"):
        value = _number(row[name], name)
        if not value.is_integer():
            raise ValueError(f"{name} must be an integer count")
        values[name] = int(value)
    return values


def drowsiness_score(row, config=None):
    """Normalize SG4 fractions, durations and counts before weighting them."""
    config = config or CONFIGURATIONS["stable_c"]
    limits = (("perclos", 0.05, 0.30), ("eye_closure_s", 0.40, 2.00),
              ("long_blinks", 1.0, 6.0), ("yawn_count", 0.0, 3.0))
    contributions = [weight * min(1.0, max(0.0, (row[name] - low) / (high - low)))
                     for (name, low, high), weight in zip(limits, config.weights)]
    return sum(contributions) / sum(config.weights)


class DecisionEngine:
    """One stateful engine per driver/session; reuse it for successive SG4 rows.

    A different row session_id explicitly starts a new session and clears all
    state, so its capture clock may restart. reset() retains the current session
    name unless another is supplied. Extra SG4 diagnostics and test-only labels
    are ignored. Six-field legacy rows assume full observation quality when
    face_valid is true; this is availability, never a learned confidence.
    """

    def __init__(self, config=None, session_id="default"):
        self.config = config or CONFIGURATIONS["stable_c"]
        if not isinstance(self.config, Config):
            raise TypeError("config must be a Config instance")
        self.session_id = _session(session_id)
        self.reset()

    def reset(self, session_id=None):
        if session_id is not None:
            self.session_id = _session(session_id)
        self._level = 0
        self._last_observation_s = None
        self._last_clock_s = None
        self._raw = self._reported_smooth = self._quality = 0.0
        self._status = "INSUFFICIENT_EVIDENCE"
        self._reason = "no observations received"
        self._clear_evidence()

    def _clear_evidence(self):
        self._smooth = None
        self._last_valid_s = None
        self._pending_target = self._pending_since = None
        self._down_since = {}

    def _output(self, time_s, old_level):
        usable = self._status == "OK"
        return {
            "schema_version": SCHEMA_VERSION,
            "time_s": time_s,
            "session_id": self.session_id,
            "driver_state": STATES[self._level],
            "alert": usable and self._level > 0,
            "alert_level": self._level if usable else 0,
            "score": self._raw,
            "smoothed_score": self._reported_smooth,
            "quality": self._quality,
            "status": self._status,
            "reason": self._reason,
            "transition": self._level != old_level,
            "alert_event": usable and self._level > old_level,
            "config_id": self.config.config_id,
        }

    def step(self, row):
        r = _observation(row, self.session_id)
        new_session = r["session_id"] != self.session_id
        t = r["time_s"]
        if not new_session:
            if self._last_observation_s is not None and t <= self._last_observation_s:
                raise ValueError("observation timestamps must strictly increase")
            if self._last_clock_s is not None and t < self._last_clock_s:
                raise ValueError("observation timestamp precedes the last capture-clock tick")
        else:
            self.reset(r["session_id"])
        old_level = self._level
        gap = self._last_observation_s is not None and t - self._last_observation_s > self.config.max_gap_s
        if gap:
            self._clear_evidence()
        self._last_observation_s = self._last_clock_s = t
        self._quality = r["validity_score"] if r["face_valid"] and r["eye_valid"] else 0.0
        if not r["face_valid"] or not r["eye_valid"] or self._quality < self.config.min_quality:
            self._clear_evidence()
            self._status = "INSUFFICIENT_EVIDENCE"
            self._reason = "unusable face, eye or observation quality; previous state is untrusted"
            return self._output(t, old_level)

        self._status = "OK"
        self._raw = drowsiness_score(r, self.config)
        dt = t - self._last_valid_s if self._last_valid_s is not None else 0.0
        if self._smooth is None or self.config.method != "C":
            self._smooth = self._raw
        else:
            alpha = -math.expm1(-dt / self.config.smoothing_s)
            self._smooth += alpha * (self._raw - self._smooth)
        self._reported_smooth = self._smooth
        self._last_valid_s = t
        if self.config.method == "A":
            p = self.config
            self._level = (2 if r["perclos"] >= p.a_drowsy_perclos or r["eye_closure_s"] >= p.a_drowsy_closure_s
                           else 1 if r["perclos"] >= p.a_warn_perclos or r["yawn_count"] >= p.a_warn_yawns
                           or r["long_blinks"] >= p.a_warn_long_blinks else 0)
            self._reason = "threshold reference"
        elif self.config.method == "B":
            self._level = 2 if self._raw >= self.config.drowsy_score else 1 if self._raw >= self.config.warn_score else 0
            self._reason = "weighted-score reference"
        elif r["eye_closure_s"] >= self.config.microsleep_s:
            self._level = 2
            self._pending_target = self._pending_since = None
            self._down_since.clear()
            self._reason = "prolonged eye-closure override"
        else:
            self._advance(t)
        if gap:
            self._reason += "; evidence restarted after input gap"
        return self._output(t, old_level)

    def _advance(self, t):
        p, score = self.config, self._smooth
        up = 2 if score >= p.enter_drowsy else 1 if score >= p.enter_warn else 0
        if up > self._level:
            self._down_since.clear()
            if self._pending_target != up:
                self._pending_target, self._pending_since = up, t
            if t - self._pending_since >= p.confirm_s:
                self._level = up
                self._pending_target = self._pending_since = None
                self._reason = "sustained higher-risk evidence confirmed"
            else:
                self._reason = "confirming higher-risk evidence"
            return
        self._pending_target = self._pending_since = None
        # Track each lower boundary independently. A brief dip cannot inherit
        # time previously spent below a different (less demanding) boundary.
        for target in range(self._level):
            threshold = p.exit_warn if target == 0 else p.exit_drowsy
            if score < threshold:
                self._down_since.setdefault(target, t)
            else:
                self._down_since.pop(target, None)
        ready = [target for target, since in self._down_since.items() if t - since >= p.release_s]
        if ready:
            self._level = min(ready)
            self._down_since = {target: since for target, since in self._down_since.items() if target < self._level}
            self._reason = "sustained lower-risk evidence confirmed"
        else:
            self._reason = "holding state during recovery" if self._down_since else "evidence supports current state"

    def tick(self, now_s):
        """Check producer silence without pretending a fresh observation arrived."""
        t = _number(now_s, "now_s")
        if self._last_clock_s is not None and t < self._last_clock_s:
            raise ValueError("capture-clock ticks must not go backwards")
        old_level = self._level
        self._last_clock_s = t
        if self._last_observation_s is None or t - self._last_observation_s > self.config.max_gap_s:
            self._clear_evidence()
            self._quality = 0.0
            self._status = "STALE"
            self._reason = "upstream input is stale; previous state is untrusted"
        return self._output(t, old_level)


def to_legacy_sg6(decision):
    """Return exactly SG6's existing three fields, only for usable decisions.

    confidence is observation quality, not probability of drowsiness. Legacy
    consumers cannot represent stale/missing evidence, so those decisions must
    go through the status-aware v2 consumer or its explicit error path instead.
    """
    if not isinstance(decision, Mapping) or decision.get("status") != "OK":
        raise ValueError("legacy SG6 payload cannot express insufficient or stale evidence")
    if decision.get("schema_version") != SCHEMA_VERSION or decision.get("driver_state") not in STATES:
        raise ValueError("not an SG5 v2 decision")
    quality = _number(decision.get("quality"), "quality", maximum=1.0)
    return {"driver_state": decision["driver_state"], "alert": decision["driver_state"] != "NORMAL", "confidence": quality}
