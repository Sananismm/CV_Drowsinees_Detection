# Interface tracking — SG-4 inputs and outputs

Status values are PROPOSED (SG-4 drafted it, not yet confirmed), AGREED (both sides confirmed), CHANGED (an agreed field changed; see the change log). Any change to an SG-5 field needs a row in the change log.

SG-4 owners: Saman Iqbal, Syeda Musfirah Hamid.

## Inputs to SG-4 — `interfaces/sg4_input_v1.schema.json` (V1-PROPOSED)

| Field (v1) | From | Unit / range | SG-4 uses it for | Status | Owner | Date |
|---|---|---|---|---|---|---|
| `frame_id` | SG-1 | int | logging only (never timing) | PROPOSED | SG-1 | 2026-10-27 |
| `timestamp_ms` | SG-1 | int ms, monotonic capture clock | all durations and windows | PROPOSED | SG-1 | 2026-10-27 |
| `face.present` / `face.confidence` | SG-1 | bool / 0–1 | `face_valid`, validity, face-absent time | PROPOSED | SG-1 | 2026-10-27 |
| `eye.closure_prob` | SG-2 | 0 open … 1 closed | PERCLOS P80, closures | PROPOSED. SG-2 draft sends `eye_closure_prob: null` (CNN not calibrated), so SG-4 falls back to state | SG-2 | 2026-10-27 |
| `eye.state` | SG-2 | open / closed / unknown | fallback when prob is null | PROPOSED. SG-2 draft: `eye_state` OPEN/CLOSED/UNKNOWN (mapped in `adapters.py`) | SG-2 | 2026-10-27 |
| `eye.confidence` | SG-2 | 0–1 | eye validity | PROPOSED. SG-2 draft has `eye_valid` (bool) instead, mapped to 1.0/invalid | SG-2 | 2026-10-27 |
| `eye.ear` | SG-2 | float | reference / future baseline | PROPOSED. SG-2 draft: `ear`, `left_ear`, `right_ear` | SG-2 | 2026-10-27 |
| SG-2 `timestamp` | SG-2 | seconds (float) | converted to `timestamp_ms` in `adapters.py` | SG-2 draft received | SG-2 | 2026-10-27 |
| SG-2 `closure_duration_sec`, `closure_event`, `is_blink`, `quality` | SG-2 | — | not used. SG-4 computes events from timestamps; kept for cross-checking | SG-2 draft received | SG-2 | 2026-10-27 |
| `mouth.yawn_prob` / `mouth.confidence` | SG-3 | 0–1 | yawn events | PROPOSED, waiting for SG-3 | SG-3 | 2026-10-27 |
| `mouth.mar` | SG-3 | float | reference only | PROPOSED | SG-3 | 2026-10-27 |
| `head.pitch_deg` / `head.confidence` | SG-3 | degrees, **negative = head down** | nods, head-down time, head drop | PROPOSED, sign convention needs SG-3 confirmation | SG-3 | 2026-10-27 |
| `head.yaw_deg`, `head.roll_deg` | SG-3 | degrees | reference only | PROPOSED | SG-3 | 2026-10-27 |

Interim rule while there is no SG-1 face record: when SG-2 says `eye_valid: true`, SG-4 infers `face.present = true` (`adapters.merge_upstream`). This goes away once SG-1 provides face presence.

## Outputs from SG-4 to SG-5 — `interfaces/sg4_output_v1_1.schema.json`

| Field | Unit / range | Window | Status | Owner | Date |
|---|---|---|---|---|---|
| `time_s` | float s, increasing | — | AGREED (SG-5 request) | SG-4 | 2026-10-27 |
| `perclos` | 0–1 | 60 s (SG-4 decision) | AGREED (SG-5 request); window decided by SG-4 | SG-4 | 2026-10-27 |
| `face_valid` | 0/1 | current frame | AGREED (SG-5 request) | SG-4 | 2026-10-27 |
| `long_blinks` | int, closures ≥ 0.5 s | 30 s | AGREED (SG-5 request) | SG-4 | 2026-10-27 |
| `yawn_count` | int, events | 60 s | AGREED (SG-5 request) | SG-4 | 2026-10-27 |
| `eye_closure_s` | float s, live, unsmoothed | live | AGREED (SG-5 request) | SG-4 | 2026-10-27 |
| `nod_count` | int, events | 60 s | PROPOSED (extra offered to SG-5) | SG-4 | 2026-10-27 |
| `validity_score`, `calibrating`, `blink_rate_bpm`, `mean_blink_ms`, `slow_blinks`, `longest_closure_s`, `head_down_s`, `face_absent_s`, `perclos_vs_baseline`, `trend` | see schema | 60 s / 30 s | PROPOSED (extras; SG-5 may ignore them) | SG-4 | 2026-10-27 |

Written confirmation from SG-5 is pending. SG-4 does not block on it: SG-5's request table is the contract (see `module_4/docs/SG5_INTERFACE.md`).

## Decisions SG-4 made and published (no SG-5 reply needed)

| # | Decision | Why |
|---|---|---|
| D1 | `perclos` window = 60 s | SG-5 did not state one; 60 s is the standard PERCLOS window. One config line (`perclos_window_s`) changes it. |
| D2 | Face lost → `face_valid = 0`, `eye_closure_s = 0.0`; counts keep their window values | Looking away must never trigger SG-5's micro-sleep override. A head drop that loses the face is reported through `nod_count`. |
| D3 | SG-5 fields are computed from the first frame; calibration affects only `perclos_vs_baseline` and `trend` | SG-5 never has to handle a calibration state. |
| D4 | `long_blinks` counts a closure the moment it reaches 0.5 s, by detection time | No lag for SG-5 (max 0.12 s in the 10-seed evaluation). |
| D5 | No data → a vector is still sent (`face_valid 0`, `validity_score 0`, counts 0, `eye_closure_s 0.0`) | SG-5 always receives a well-formed vector. |

## SG-5 change log (SG-4 output v1 → v1.1)

| Date | Before (v1) | Now (v1.1) | Reason |
|---|---|---|---|
| 2026-10-27 | `perclos` 0–100 % | `perclos` 0–1 | SG-5 expects 0–1 |
| 2026-10-27 | `validity_score` only | `face_valid` (0/1, current frame) added; `validity_score` kept as an extra | SG-5 expects a per-frame flag |
| 2026-10-27 | `long_blinks` = blinks > 400 ms | renamed to `slow_blinks` (> 400 and < 500 ms) | name clash with SG-5's `long_blinks` |
| 2026-10-27 | `microsleep_count` (≥ 0.5 s, 60 s) | `long_blinks` (≥ 0.5 s, **30 s**) | SG-5 name and window |
| 2026-10-27 | `yawn_rate` (yawn frames/min) | `yawn_count` (yawn events in 60 s) | SG-5 needs events, not frames |
| 2026-10-27 | — | `eye_closure_s` added | SG-5 Method C micro-sleep override |
| 2026-10-27 | — | `time_s` added | SG-5 smoothing and timers |
| 2026-10-27 | — | `nod_count` offered as an extra | covers SG-4's "face lost / head drop" limitation |

## How the match is proven

- `module_4/tests/test_sg5_contract.py`: exact field set, types and ranges on every output of every mock scenario. It also checks that the golden files are current.
- `interfaces/mocks/sg5_expected/*.jsonl`: golden SG-4 output for SG-5.
- `python module_4/tools/check_sg5_compat.py <file.jsonl>`: PASS/FAIL per field, standard library only.
