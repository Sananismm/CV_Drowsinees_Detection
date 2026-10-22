"""Create fixed, labelled SG-4 inputs for Week 5 decision experiments.

These are simulated scenarios, not recorded driving data. Labels describe the
scripted scenario and are stored outside the frozen V1 input message.
"""

import json
from pathlib import Path


DATA_PATH = Path(__file__).parent / "data" / "mock_temporal_inputs.jsonl"

NORMAL = (0.08, 220, 0, 0, 0.04)
WARNING = (0.38, 1100, 1, 3000, 0.45)
STRONG = (0.52, 2800, 3, 7500, 0.84)
WEAK = (0.80, 2400, 0, 0, 0.75)
RECOVERY_BAND = (0.40, 900, 0, 0, 0.35)


def input_message(scenario, second, values, confidence=0.92):
    perclos, closure, yawns, yawn_duration, persistence = values
    return {
        "schema_version": "sg5.temporal-cues.v1",
        "session_id": f"mock-{scenario}",
        "driver_track_id": "driver-01",
        "timestamp_ms": second * 1000,
        "window_ms": 60000,
        "temporal_confidence": confidence,
        "eye": {"perclos": perclos, "longest_closure_ms": closure, "blink_rate_per_min": 15.0, "confidence": confidence},
        "yawn": {"count": yawns, "total_duration_ms": yawn_duration, "confidence": confidence},
        "fatigue": {"persistence": persistence, "confidence": confidence},
    }


def build_rows():
    rows = []

    def add(scenario, phases):
        second = 0
        for duration, label, values, confidence in phases:
            for _ in range(duration):
                rows.append({
                    "scenario": scenario,
                    "label": label,
                    "input": input_message(scenario, second, values, confidence),
                })
                second += 1

    add("progression", [
        (6, "ALERT", NORMAL, 0.92), (6, "CAUTION", WARNING, 0.92),
        (14, "DROWSY", STRONG, 0.92), (14, "ALERT", NORMAL, 0.92),
    ])
    add("normal_driving", [(40, "ALERT", NORMAL, 0.92)])
    # Measurement spike without an actual drowsiness episode.
    add("false_spike", [
        (10, "ALERT", NORMAL, 0.92), (1, "ALERT", STRONG, 0.92),
        (19, "ALERT", NORMAL, 0.92),
    ])
    jitter_phases = [(8, "ALERT", NORMAL, 0.92)]
    for perclos in (0.92, 0.96, 0.92, 0.96, 0.92, 0.96, 0.92, 0.96):
        # Scores straddle 0.65, but the scripted driver is only tired.
        jitter_phases.append((1, "CAUTION", (perclos, 1000, 0, 0, 0.70), 0.92))
    jitter_phases.append((14, "ALERT", NORMAL, 0.92))
    add("threshold_jitter", jitter_phases)
    add("weak_drowsiness", [
        (8, "ALERT", NORMAL, 0.92), (15, "DROWSY", WEAK, 0.92),
        (12, "ALERT", NORMAL, 0.92),
    ])
    # An intentionally short true episode exposes the entry-delay trade-off.
    add("short_true_episode", [
        (10, "ALERT", NORMAL, 0.92), (1, "DROWSY", STRONG, 0.92),
        (19, "ALERT", NORMAL, 0.92),
    ])
    add("visibility_loss", [
        (8, "ALERT", NORMAL, 0.92), (10, "DROWSY", STRONG, 0.20),
        (12, "ALERT", NORMAL, 0.92),
    ])
    add("recovery_band", [
        (8, "ALERT", NORMAL, 0.92), (10, "DROWSY", STRONG, 0.92),
        (8, "CAUTION", RECOVERY_BAND, 0.92), (14, "ALERT", NORMAL, 0.92),
    ])
    add("late_strong_evidence", [
        (8, "ALERT", NORMAL, 0.92), (3, "DROWSY", WEAK, 0.92),
        (12, "DROWSY", STRONG, 0.92), (12, "ALERT", NORMAL, 0.92),
    ])
    return rows


if __name__ == "__main__":
    rows = build_rows()
    DATA_PATH.parent.mkdir(exist_ok=True)
    DATA_PATH.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
    )
    print(f"Created {len(rows)} mock messages in {DATA_PATH}")
