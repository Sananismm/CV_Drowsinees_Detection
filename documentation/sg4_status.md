# SG-4 status

Updated 2026-10-27. Status key: GREEN = on track, AMBER = at risk, RED = blocking integration.

| Area | Status | Notes |
|---|---|---|
| Core engine (sync, buffer, events, baseline, 10 Hz output) | GREEN | 54 tests pass. Works on 5 mock scenarios. |
| SG-5 output contract v1.1 | GREEN | Golden files plus checker in place. SG-5 written confirmation pending (not blocking). |
| SG-2 eye input | AMBER | Draft format received and supported in `adapters.py`. `eye_closure_prob` is null, so PERCLOS uses the hard state. Waiting for a probability or the threshold, and for confidence. |
| SG-3 yawn / head-pose input | AMBER | No format yet. Pitch sign convention unconfirmed. Mocks are used meanwhile. |
| SG-1 face presence and clock | AMBER | No face record yet. Face presence is inferred from SG-2 `eye_valid`. |
| Evaluation on real video | AMBER | Scripts ready (`eval_clip.py`); no annotated clips yet. |
| Jetson benchmark | AMBER | Script ready; waiting for Jetson access from SG-6. |

## Blockers

1. Waiting for SG-2: calibrated `eye_closure_prob`, or their closed threshold, plus a per-frame eye confidence.
2. Waiting for SG-3: output field names and head-pitch sign convention.
3. Waiting for SG-5: written confirmation of the v1.1 windows (non-blocking).
4. Waiting for SG-6: Jetson Orin Nano access to run `benchmark.py`.
