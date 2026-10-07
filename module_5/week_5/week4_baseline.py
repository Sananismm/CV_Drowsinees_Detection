"""Baseline V1 drowsiness decision and alert logic for SG-5.

This deterministic baseline deliberately has no external dependencies. It consumes
the frozen SG-4 temporal-cues.v1 contract and produces the SG-5 decision.v1
contract, so SG-6 can integrate it on a Jetson before final model tuning.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


MIN_CONFIDENCE = 0.55
CAUTION_THRESHOLD = 0.35
DROWSY_THRESHOLD = 0.65
RELEASE_THRESHOLD = 0.25
RELEASE_DWELL_MS = 5_000


@dataclass
class DecisionEngine:
    """Stateful V1 fusion baseline with conservative alert release hysteresis."""

    previous_state: str = "ALERT"
    low_risk_since_ms: int | None = None

    def decide(self, cues: dict[str, Any]) -> dict[str, Any]:
        """Return a V1 decision. Invalid/low-confidence inputs never raise an alert."""
        self._check_required_fields(cues)
        confidence = self._combined_confidence(cues)
        if confidence < MIN_CONFIDENCE:
            return self._result(cues, "UNKNOWN", 0.0, confidence, "NONE", [], "input confidence below 0.55")

        eye_risk = max(cues["eye"]["perclos"], min(cues["eye"]["longest_closure_ms"] / 3000.0, 1.0))
        yawn_risk = min((cues["yawn"]["count"] / 3.0 + cues["yawn"]["total_duration_ms"] / 9000.0) / 2.0, 1.0)
        persistence_risk = cues["fatigue"]["persistence"]
        risk = round(0.55 * eye_risk + 0.25 * yawn_risk + 0.20 * persistence_risk, 3)
        evidence = self._evidence(cues, eye_risk, yawn_risk, persistence_risk)
        desired_state = self._desired_state(risk)
        state = self._apply_hysteresis(desired_state, risk, cues["timestamp_ms"])
        action = {"ALERT": "NONE", "CAUTION": "VISUAL", "DROWSY": "AUDIO_VISUAL"}[state]
        return self._result(cues, state, risk, confidence, action, evidence, "weighted temporal-cue fusion")

    @staticmethod
    def _check_required_fields(cues: dict[str, Any]) -> None:
        if cues.get("schema_version") != "sg5.temporal-cues.v1":
            raise ValueError("expected schema_version 'sg5.temporal-cues.v1'")
        for key in ("session_id", "driver_track_id", "timestamp_ms", "temporal_confidence", "eye", "yawn", "fatigue"):
            if key not in cues:
                raise ValueError(f"missing required field: {key}")

    @staticmethod
    def _combined_confidence(cues: dict[str, Any]) -> float:
        return round(min(cues["temporal_confidence"], cues["eye"]["confidence"], cues["yawn"]["confidence"], cues["fatigue"]["confidence"]), 3)

    @staticmethod
    def _evidence(cues: dict[str, Any], eye_risk: float, yawn_risk: float, persistence_risk: float) -> list[str]:
        evidence: list[str] = []
        if eye_risk >= CAUTION_THRESHOLD:
            evidence.append(f"eye_risk={eye_risk:.2f}")
        if yawn_risk >= CAUTION_THRESHOLD:
            evidence.append(f"yawn_risk={yawn_risk:.2f}")
        if persistence_risk >= CAUTION_THRESHOLD:
            evidence.append(f"fatigue_persistence={persistence_risk:.2f}")
        return evidence or ["no elevated temporal cue"]

    @staticmethod
    def _desired_state(risk: float) -> str:
        if risk >= DROWSY_THRESHOLD:
            return "DROWSY"
        if risk >= CAUTION_THRESHOLD:
            return "CAUTION"
        return "ALERT"

    def _apply_hysteresis(self, desired_state: str, risk: float, timestamp_ms: int) -> str:
        # Escalation is immediate; a high-risk alert must not wait for a second cycle.
        if desired_state in ("CAUTION", "DROWSY"):
            self.previous_state = desired_state
            self.low_risk_since_ms = None
            return desired_state

        # De-escalation requires sustained low risk, preventing alert chatter.
        if self.previous_state != "ALERT" and risk < RELEASE_THRESHOLD:
            if self.low_risk_since_ms is None:
                self.low_risk_since_ms = timestamp_ms
                return self.previous_state
            if timestamp_ms - self.low_risk_since_ms < RELEASE_DWELL_MS:
                return self.previous_state

        self.previous_state = "ALERT"
        self.low_risk_since_ms = None
        return "ALERT"

    @staticmethod
    def _result(cues: dict[str, Any], state: str, risk_score: float, confidence: float, action: str, evidence: list[str], reason: str) -> dict[str, Any]:
        return {
            "schema_version": "sg5.decision.v1",
            "session_id": cues["session_id"],
            "driver_track_id": cues["driver_track_id"],
            "timestamp_ms": cues["timestamp_ms"],
            "state": state,
            "risk_score": risk_score,
            "confidence": confidence,
            "alert_action": action,
            "evidence": evidence,
            "reason": reason,
        }
