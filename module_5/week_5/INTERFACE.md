# SG5 V1 interface

These are copies of the existing local Lab 4 schemas, not a newly agreed team-wide contract. SG-4 and SG-6 need to confirm that their implementations use these fields. The experiment changes internal decision behaviour without changing input or output fields.

## SG4 to SG5

Format: one Python dictionary or UTF-8 JSON object per update. Schema: `interfaces/sg5_temporal_cues_v1.schema.json`.

```json
{
  "schema_version": "sg5.temporal-cues.v1",
  "session_id": "demo-session",
  "driver_track_id": "driver-01",
  "timestamp_ms": 12000,
  "window_ms": 60000,
  "temporal_confidence": 0.92,
  "eye": {
    "perclos": 0.52,
    "longest_closure_ms": 2800,
    "blink_rate_per_min": 15.0,
    "confidence": 0.92
  },
  "yawn": {
    "count": 3,
    "total_duration_ms": 7500,
    "confidence": 0.92
  },
  "fatigue": {
    "persistence": 0.84,
    "confidence": 0.92
  }
}
```

- Time is integer milliseconds since the session started, increasing for a given driver/session.
- `window_ms` is the observation-window length. In the experiment it is always 60000 ms.
- PERCLOS is a fraction in [0,1], not a percentage in [0,100]. SG-4 must agree on how it defines eye closure and handles unobservable frames.
- `fatigue.persistence` is a fraction of usable observations with fatigue evidence, not a second drowsiness classifier label. Its exact derivation needs SG-4 agreement.
- `blink_rate_per_min` is preserved for compatibility but is not used in this baseline's fusion score.
- Confidences are quality indicators in [0,1], not validated probabilities. SG-5 uses the minimum of all four supplied confidences.
- The stream should update roughly once per second. A gap over 2500 ms resets candidate timers; missing messages do not prove continuous evidence. The caller must detect a completely stopped stream, since an engine receives no call when no data arrives.
- A new driver/session resets candidate state so one driver's history is not transferred to another.

The Week 5 validator checks required/extraneous fields, numeric types, finite values and ranges. It also checks that closure/yawn durations fit within the observation window. Bad-format input raises `ValueError`; the integration caller should log that error and treat the sample as unavailable. Valid low-confidence input returns UNKNOWN rather than an exception.

## SG5 to SG6

Schema: `interfaces/sg5_decision_output_v1.schema.json`.

```json
{
  "schema_version": "sg5.decision.v1",
  "session_id": "demo-session",
  "driver_track_id": "driver-01",
  "timestamp_ms": 14000,
  "state": "DROWSY",
  "risk_score": 0.911,
  "confidence": 0.92,
  "alert_action": "AUDIO_VISUAL",
  "evidence": [
    "eye_risk=0.933",
    "yawn_risk=0.917",
    "fatigue_persistence=0.840"
  ],
  "reason": "weighted fusion with entry/release timers"
}
```

| State | Meaning | Action |
| --- | --- | --- |
| ALERT | Awake/normal | NONE |
| CAUTION | Warning, including the high-risk confirmation period | VISUAL |
| DROWSY | Sound alert confirmed, or held during recovery | AUDIO_VISUAL |
| UNKNOWN | Insufficient confidence | NONE; log unavailable observation |

UNKNOWN currently reports risk_score 0.0 as the V1 fallback. This must not be interpreted as evidence that the driver is awake. Use the state together with the score.

SG-6 executes the requested warning and event logging. It should manage buzzer repetition rather than restarting a sound every time the same DROWSY message arrives.

Keep one engine alive for the entire driver stream:

```python
from decision_logic import make_engine

engine = make_engine("week5_stable")

# Each time a temporal message arrives from SG-4:
decision = engine.decide(temporal_message)
# SG-6 receives decision and implements decision["alert_action"].
```

Creating a new engine on every update erases the timers and prevents the two-second confirmation from completing.

## Experiment wrapper

The fixture adds labels outside the V1 message:

```json
{
  "scenario": "progression",
  "label": "DROWSY",
  "input": {"schema_version": "sg5.temporal-cues.v1", "...": "the complete message above"}
}
```

The abbreviated input above only illustrates the wrapper. The committed JSONL file contains complete valid messages. `engine.decide(row["input"])` receives no label. `compare.py` uses the separate label afterwards to count errors and delay.
