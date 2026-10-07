# SG4 — Temporal Behaviour Analysis (Week 5)

**Group D2 · Sub-group SG4 · Driver Drowsiness Detection**
Notebook: [`D2-SG4.ipynb`](../D2-SG4.ipynb)

SG4 converts **per-frame cues** from SG1/SG2/SG3 into **temporal fatigue indicators** over a sliding window, and passes a fixed-schema vector to **SG5** for the alert decision.

```
SG1/2/3 per-frame cues ──► SG4 TemporalAnalyzer (sliding window) ──► temporal vector ──► SG5 decision logic
```

---

## Week 5 Deliverables — Where to Find Them

| Requirement | Evidence | Location |
|---|---|---|
| Frame cues → temporal indicators | `TemporalAnalyzer.process_frame()` + `get_temporal_vector()` | Block 1 |
| Compare ≥ 2 temporal configurations | Config A (10 s) vs Config B (30 s) on same stream | Block 3, [Results](#3-experiment-results) |
| Stability vs detection-delay trade-off | Analysis table | [Trade-off](#4-stability-vs-detection-delay-trade-off) |
| Select Week 6 configuration | 30 s sliding window | [Week 6 Decision](#5-week-6-configuration) |
| Version temporal logic & window parameters | V1 parameters table, Git history | [Parameters](#2-temporal-logic--parameters-v1) |
| Accept standardized / mock cue streams | `generate_mock_stream()` (alert / drowsy / distraction) |  Block 2 |
| Document output schema for SG5 | V1 output contract | [SG5 Schema](#6-output-schema-for-sg5-v1-contract) |

---

## 1. Input Contract (V1) — from SG1/SG2/SG3

One dictionary per frame:

| Field | Type | Source | Description |
|---|---|---|---|
| `timestamp` | float (s) | stream | Frame time |
| `face_confidence` | float 0–1 | SG1 | Face detection confidence |
| `eye_closure_prob` | float 0–1 | SG2 | Probability eyes are closed |
| `is_blink` | bool | SG2 | Blink flag |
| `yawn_prob` | float 0–1 | SG3 | Probability of yawn |
| `head_nod_event` | bool | SG3 | Head nod / drop flag |

```python
{"timestamp": 3.33, "face_confidence": 0.92, "eye_closure_prob": 0.95,
 "is_blink": False, "yawn_prob": 0.10, "head_nod_event": False}
```

---

## 2. Temporal Logic & Parameters (V1)

| Parameter | Value | Purpose |
|---|---|---|
| `window_duration_sec` | 10 / **30** | Sliding window length (experiment variable) |
| `fps` | 30 | Frame rate assumption |
| Face validity threshold | `face_confidence ≥ 0.5` | Invalid frames excluded so looking away ≠ sleep |
| Eye-closed threshold | `eye_closure_prob ≥ 0.8` | PERCLOS P80 standard |
| Yawn threshold | `yawn_prob ≥ 0.7` | Yawn frame flag |
| Microsleep rule | ≥ 0.5 s continuous closure (15 frames) | Separates microsleeps from normal blinks (~0.1–0.4 s) |

**Indicators computed:**
- **PERCLOS** — % of valid frames with eyes ≥ 80% closed
- **Blink rate** — blink flags per minute over the window
- **Microsleep count** — runs of ≥ 15 consecutive closed valid frames
- **Yawn rate** — yawn-flagged frames per minute over the window
- **Nod count** — head-nod flags in window
- **Validity score** — fraction of frames with a valid face

Window implemented as `collections.deque(maxlen = window_sec × fps)` — O(1) append, oldest frames drop automatically.

---

## 3. Experiment Results

**Test stream:** 30 s mock *drowsy* scenario @ 30 fps (900 frames)
- Microsleep 1: frames 100–145 (~1.5 s)
- Microsleep 2: frames 500–560 (~2.0 s)
- Yawn: frames 200–260
- Head nod: frame 570

Both analyzers received the identical stream; vectors read at end of stream.

| Metric | Config A (10 s Window) | Config B (30 s Window) |
|---|---|---|
| Validity Score | 1.0 | 1.0 |
| PERCLOS (%) | 0.0 | 11.89 |
| Microsleep Count | 0 | 2 |
| Yawn Rate (per min) | 0.0 | 122.0 |
| Nod Count | 0 | 1 |

**Interpretation**
- At the read-out point the 10 s window holds only frames 600–899. All injected events occurred before frame 571, so they had already **expired** from the short window → all zeros. This demonstrates the key weakness of short windows: fatigue evidence is forgotten quickly.
- The 30 s window retained all events: 2 microsleeps, 1 nod, PERCLOS 11.89% (107 closed / 900 frames).
- Yawn rate in V1 counts **yawn frames** per minute (61 frames over 30 s → 122.0), not discrete yawn events.

---

## 4. Stability vs Detection-Delay Trade-off

| Aspect | 10 s Window | 30 s Window |
|---|---|---|
| Responsiveness to sudden events | Higher — new events dominate quickly | Lower — diluted by longer history |
| PERCLOS stability | Fluctuates rapidly | Smooth, fewer false-alert spikes |
| Memory of past fatigue | Short — events expire after 10 s | Captures 30 s+ fatigue patterns |
| Detection delay for gradual fatigue | Shorter, but noisier | Longer, but more reliable |
| Microsleep detection | 0.5 s rule — same in both | 0.5 s rule — same in both |

Microsleep detection latency is governed by the 0.5 s persistence rule, not the window length, so SG5 can still react immediately to a microsleep while using the 30 s window for stable PERCLOS trends.

---

## 5. Week 6 Configuration

**Selected baseline: 30-second sliding window @ 30 fps**, with V1 thresholds above.

Reasons: stable PERCLOS, fewer false alerts, retains fatigue evidence long enough for SG5, consistent with the system architecture.

---

## 6. Output Schema for SG5 (V1 Contract)

Returned by `get_temporal_vector()`:

| Field | Type | Range | Description |
|---|---|---|---|
| `validity_score` | float | 0.0–1.0 | Fraction of window frames with valid face |
| `perclos` | float | 0–100 (%) | % valid frames with eyes ≥ 80% closed |
| `blink_rate` | float | ≥ 0 (per min) | Blink flags per minute |
| `microsleep_count` | int | ≥ 0 | Closures ≥ 0.5 s in window |
| `yawn_rate` | float | ≥ 0 (per min) | Yawn-flagged frames per minute |
| `nod_count` | int | ≥ 0 | Head-nod flags in window |

```json
{
  "validity_score": 1.0,
  "perclos": 11.89,
  "blink_rate": 0.0,
  "microsleep_count": 2,
  "yawn_rate": 122.0,
  "nod_count": 1
}
```

**Notes for SG5**
- Returns `None` if no frames received yet.
- If no valid frames, all indicators are 0 with `validity_score = 0.0` — **SG5 must check `validity_score` first** and not treat this as "alert driver".
- Recommended: only act on indicators when `validity_score` is high (e.g. ≥ 0.7).

---

## 7. How to Run

1. Open `D2-SG4.ipynb` in Google Colab / Jupyter.
2. Run Block 1 (TemporalAnalyzer) → Block 2 (mock stream generator) → Block 3 (comparison).
3. Change `scenario` in Block 3 to `"alert"` or `"distraction"` to test other streams.

No external dependencies (Python standard library only).

---

## 8. Known Limitations & Next Steps

- Yawn / nod / blink counted per flagged frame, not per event → planned: rising-edge event counting.
- Window duration assumes fixed fps → planned: compute duration from timestamps.
- Comparison read at a single time point → planned: sample both windows throughout the stream to measure detection delay directly.
- Mock data only → next: integrate real SG1/SG2/SG3 cue output.
