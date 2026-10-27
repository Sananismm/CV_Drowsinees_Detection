# SG-4 → SG-5 Interface (v1.1) — matched to SG-5's input request

SG-5 sent the input they expect from SG-4 (see `docs/sg5_input_request.png`). SG-4's output is changed to match it exactly.

## Fields SG-5 requires (send exactly these names, units and windows)

| Field | Type | Meaning | Window |
|---|---|---|---|
| `time_s` | float | SG-1 capture timestamp of the latest frame, in seconds, increasing | — |
| `perclos` | float 0–1 | Share of valid time with eyes ≥ 80% closed (**not %**) | last 60 s |
| `face_valid` | int 0/1 | 1 if the current frame has a face above the confidence threshold | current frame |
| `long_blinks` | int ≥ 0 | Number of eye closures lasting ≥ 0.5 s | last 30 s |
| `yawn_count` | int ≥ 0 | Number of yawn **events** (not frames) | last 60 s |
| `eye_closure_s` | float ≥ 0 | Length of the closure happening right now; 0.0 when eyes open or face lost | live |

## Extra fields (SG-5 may use or ignore)

| Field | Meaning |
|---|---|
| `nod_count` | Nod / head-drop events in last 60 s (covers head drop that loses the face) |
| `validity_score` | Share of valid frames in last 60 s, 0–1 |
| `slow_blinks` | Blinks > 400 ms and < 500 ms in last 60 s |
| `blink_rate_bpm`, `mean_blink_ms`, `longest_closure_s`, `head_down_s`, `face_absent_s` | Supporting indicators |
| `calibrating`, `perclos_vs_baseline`, `trend` | Per-driver baseline info (first 60 s = calibration) |

## Changes from SG-4's earlier output

| Before | Now |
|---|---|
| `perclos` 0–100 % | `perclos` 0–1 |
| `validity_score` only | `face_valid` (0/1) added; `validity_score` kept as extra |
| `microsleep_count` (≥ 0.5 s, 60 s window) | `long_blinks` (≥ 0.5 s, 30 s window) |
| `yawn_rate` (yawn frames per minute) | `yawn_count` (yawn events in 60 s) |
| — | `eye_closure_s` added |
| — | `time_s` added |
| old long blinks > 400 ms | renamed `slow_blinks` |

## Behaviour rules

- Output rate: 10 Hz (every 100 ms).
- Face lost → `face_valid = 0`, `eye_closure_s = 0.0`, counts keep their window values. Looking away never counts as eye closure.
- All SG-5 fields are valid from the first frame. Calibration affects only the extras.
- No data → still send a record with `face_valid = 0`, counts 0, `eye_closure_s = 0.0`, `validity_score = 0`.

## Example record

```json
{"schema":"sg4.output.v1.1","time_s":41.2,"perclos":0.18,"face_valid":1,"long_blinks":2,"yawn_count":1,"eye_closure_s":0.0,"nod_count":0,"validity_score":0.96,"calibrating":false}
```

## How the match is checked

- `module_4/tests/test_sg5_contract.py` checks every output's fields, types and ranges.
- `interfaces/mocks/sg5_expected/*.jsonl` are sample SG-4 outputs SG-5 can test against now.
- `python module_4/tools/check_sg5_compat.py <file.jsonl>` prints PASS/FAIL per field.
