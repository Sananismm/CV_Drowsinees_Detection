# SG2 to SG4 Output

SG2 sends one `sg2.sg4.v2` cue for each decoded frame, preserving its frame ID and source time. `eye_state` is the final state after temporal filtering. The current method is `EAR_0.15_open2`; CNN inference is disabled in this mode. [Cue adapter](adapters.py) [Settings](final_method.json)

## Cue fields

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | string | Constant `sg2.sg4.v2` |
| `frame_id` | integer | Zero-based decoded input frame index |
| `timestamp` | number | Source time in seconds; retain SG-1 timing and frame synchronization |
| `eye_state` | string | `OPEN`, `CLOSED`, or `UNKNOWN`; authoritative final state |
| `eye_valid` | boolean | True exactly when `eye_state` is OPEN or CLOSED |
| `method` | string | Selected method identifier |
| `ear`, `left_ear`, `right_ear` | number/null | Bilateral EAR diagnostics; null when geometry is invalid |
| `ear_eye_state` | string | Raw EAR classification before temporal OPEN confirmation |
| `cnn` | object | CNN state/crop diagnostics; score values are uncalibrated |
| `quality` | object | Geometry validity, CNN availability/agreement and `cnn_used:false` for selected EAR method |
| `face_confidence` | number/null | Actual upstream SG-1 confidence only; no value is fabricated |
| `eye_closure_prob` | null | Always null; no calibrated closure probability is produced |
| `is_blink` | boolean | One-frame candidate marker for a completed short closure |
| `closure_event` | object/null | Event emitted once at observed event completion |
| `closure_duration_sec` | number/null | Elapsed observed closure duration while active |
| `invalid_reason` | string/null | Reason state could not be produced |

UNKNOWN means `eye_valid:false`; it must not be treated as OPEN or CLOSED. `eye_closure_prob` remains null because EAR is not a calibrated closure probability. `face_confidence` is the observed SG1 value, or null when unavailable. [Validator](adapters.py)

## Closure events

Events contain observed start/end frame IDs, seconds and duration. Reopening completes an uncensored interval; missing input, gaps and end-of-video end incomplete observations. A complete 0.1–0.4-second interval sets `is_blink` once on the completion frame. This marks a predicted candidate, not an independently labelled blink. [Tracker](events.py)

The output uses source seconds and does not invent observations across gaps. EOF-flushed events are saved in `closures.json`, without an extra frame record. [Tracker](events.py) [Video output](demo.py)

## Example

The [example cue](results/live_sg4_example.json) comes from the actual SG1-to-SG2 run. All 590 cues in that run passed the existing validator and were passed through `SG4Bridge` to the team's `TemporalAnalyzer`; SG3 yawn/nod inputs were explicitly disabled. [Run results](results/live_integration_summary.json) [Bridge](adapters.py)

## SG4 compatibility

SG4's native `process_frame` expects numeric `face_confidence` and `eye_closure_prob` values. Passing the current cue directly raises a TypeError on null confidence. Do not replace missing confidence with a configured threshold or rename EAR as a probability to satisfy that method. [SG4 implementation](../module_4/D2-SG4.ipynb) [Compatibility test](tests/test_sg2.py)

The existing `SG4Bridge` maps valid hard states into SG4's internal processed-cue buffer and preserves event flags. It retains the analyzer's vector logic, but this internal-buffer dependency still needs agreement with the SG4 owner. [Bridge](adapters.py)

For native support, SG4 should use explicit eye validity/state when confidence is absent, break runs on UNKNOWN/gaps, and consume the single emitted candidate flag. Its fixed-FPS windows also need to be reconciled with source timing. A fraction of frames classified CLOSED is not a calibrated P80 eyelid-occlusion measure. SG2 does not change the teammate's SG4 source. [Current interface](../module_4/D2-SG4.ipynb) [State mapping](adapters.py)
