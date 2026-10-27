# Meeting — 2026-10-27 — SG-4 / SG-5 output alignment

- **Attendees:** SG-4 (Saman Iqbal, Syeda Musfirah Hamid). SG-5 took part through their written input-request table (`module_4/docs/sg5_input_request.png`). *Fill in any SG-5 members who attended.*
- **Absent:** —

## Decisions
1. SG-4 output becomes v1.1, matching SG-5's request literally. The fields are `time_s`, `perclos` (0–1), `face_valid` (0/1), `long_blinks` (≥ 0.5 s, 30 s), `yawn_count` (events, 60 s) and `eye_closure_s` (live), plus `nod_count` as an extra.
2. SG-4 decides the open details and publishes them: PERCLOS window 60 s; face lost → `face_valid 0` and `eye_closure_s 0.0`; SG-5 fields valid from the first frame.
3. One function (`sg5_output.to_sg5`) writes SG-5 field names. All windows are in `config/sg4_v1.yaml`.
4. SG-5 develops against the golden files in `interfaces/mocks/sg5_expected/` and checks compatibility with `tools/check_sg5_compat.py`.
5. SG-2's draft eye output (`eye_state`, `eye_valid`, `timestamp` in s, `eye_closure_prob: null`) is accepted through `adapters.py`. No core change is needed.

## Interface changes
| Field | From → To | Producer → Consumer | Logged in interface_tracking.md? |
|---|---|---|---|
| perclos | 0–100 % → 0–1 | SG-4 → SG-5 | yes |
| face_valid | — → 0/1 current frame | SG-4 → SG-5 | yes |
| long_blinks | (> 400 ms) → ≥ 0.5 s in 30 s; old one renamed `slow_blinks` | SG-4 → SG-5 | yes |
| yawn_count | yawn_rate (frames/min) → events in 60 s | SG-4 → SG-5 | yes |
| eye_closure_s, time_s | — → added | SG-4 → SG-5 | yes |

## Blockers
| Blocker | Owner | Waiting on | GitHub issue |
|---|---|---|---|
| SG-5 written confirmation of v1.1 windows | SG-4 | SG-5 | # (to create) |
| SG-2 closure probability / confidence | SG-4 | SG-2 | # (to create) |
| SG-3 field names and pitch sign | SG-4 | SG-3 | # (to create) |

## Actions
| Action | Owner | Due |
|---|---|---|
| Send the FYI to SG-5 with the golden files and checker command | SG-4 | |
| Send the field-confirmation request to SG-2 and SG-3 | SG-4 | |
| Run `benchmark.py` on the Jetson | SG-4 with SG-6 | |
