# SG-4 experiments log

Every number here comes from a committed script:
- `evaluation/sg4/evaluate.py` → `module_4/results/metrics.md` (the 5 committed mocks)
- `evaluation/sg4/evaluate.py --seeds 10` → `results/metrics_10seeds.md` (seeds 100–109 × 5 scenarios, 75 min)
- `tools/benchmark.py` → `results/benchmark_pc.csv`

**Caveat that applies to everything below.** The mock generator and the engine share the same event definitions (P80, 500 ms and so on). Near-perfect primary scores therefore show that the implementation is correct and robust to stream defects (drops, jitter, reordering, face loss). They are **not** real-world accuracy. Real-video evaluation is listed under next steps.

The *proxy alert rule* used to count false alerts is ours, for ablation only: `eye_closure_s ≥ 1.0 or perclos ≥ 0.15 or long_blinks ≥ 3`. A false alert is an alert onset with no ground-truth alert within ±1 s. SG-5 owns the real decision.

---

## E1. Exact sliding-window PERCLOS vs EMA PERCLOS

- **Tried:** the primary engine computes PERCLOS from O(1) running sums over an exact 60 s window. The alternative (`EmaPerclosEngine`) uses an exponential moving average of the closed flag over valid time (τ = 30 s), with no calibration.
- **Measured:** mean / worst PERCLOS error in points, on outputs with a full 60 s window.

  | | committed mocks | 10 seeds |
  |---|---|---|
  | Primary (window) | 0.12 / 0.32 | 0.11 / 0.65 |
  | EMA | 1.05 / 3.59 | 0.96 / 3.88 |

- **Learned:** both meet the < 5 pt target. EMA lags when PERCLOS changes (worst on `drowsy` and `noisy`, where PERCLOS rises) and does not match the standard window definition SG-5 asked for. The exact window costs the same O(1) per update.
- **Decision:** keep the exact 60 s window. EMA stays as a documented alternative.

## E2. Temporal engine vs naive single-frame counter (ablation)

- **Tried:** `NaiveFrameCounter`. Each frame is classified on its own, and a frame without a visible eye counts as "closed". It counts 15 consecutive closed frames (= 0.5 s at a nominal 30 FPS) and uses frame-count windows, with no hysteresis, validity handling or debounce.
- **Measured (`results/metrics_10seeds.md`, totals):**

  | | Primary | Naive |
  |---|---|---|
  | PERCLOS error mean / worst (pts) | 0.11 / 0.65 | 2.34 / 13.38 |
  | Microsleep precision | 96% (120/125) | 74% (120/163) |
  | False alerts per hour (proxy rule) | 0 | 27 |

  On the committed `face_lost` mock, the naive approach has a PERCLOS error of 9.42 mean and 12.85 worst. It reports 3 microsleeps that never happened (precision 0/3) and an `eye_closure_s` error of 152 ms on average. On `yawns_nods`, its yawn-count error is 3.12, because talking is counted and merged yawns are double-counted. Primary scores 0.00 on both.
- **Learned:** almost all of the naive approach's errors come from **validity**, not from eye-state accuracy. When the driver looks away, a frame classifier "sees" closed eyes, and `eye_closure_s` climbs past 1 s (see `results/ablation_face_lost.png`). That would fire SG-5's micro-sleep override. Debounce and a minimum duration matter for yawns.
- **Decision:** the primary approach is the temporal state machine with explicit validity. The naive counter is kept as the single-frame ablation baseline.

## E3. Counting long blinks at 500 ms vs at reopen

- **Tried:** counting a microsleep when the ongoing closure reaches `long_blink_ms`, rather than when the eye reopens.
- **Measured:** the lag from a ground-truth microsleep ending to `eye_closure_s` returning to 0 is at most 0.08 s on the committed mocks and 0.12 s over 10 seeds (target ≤ 1 s). `long_blinks` rises 0.5 s after the closure starts, which unit tests check (`test_long_blink_0p7s_counts_and_live_closure_rises_then_resets`).
- **Decision:** keep counting at the 500 ms crossing.

## E4. Frame quantization at the 500 ms boundary (failure case found)

- **Measured:** all 5 primary false-positive microsleeps in the 10-seed run were ground-truth slow blinks of 476–477 ms. At 30 FPS, the first open frame can arrive up to 33 ms after the true reopening, plus the hysteresis delay. We found this by inspecting the engine event log.
- **Learned:** around 500 ms, a single frame decides the class. This is inherent to 30 FPS input.
- **Decision:** keep 500 ms, because it is SG-5's definition. Revisit once there is real data. A one-frame tolerance would be a config change (`long_blink_ms`) and needs SG-5's agreement.

## E5. Runtime cost (PC; Jetson pending)

- **Measured** (`tools/benchmark.py`, 12,000 frames of the noisy stream, Apple arm64, Python 3.9.6, NumPy 2.0.2): mean 0.026 ms, p95 0.060 ms and max 0.172 ms per update. Frames that also build the 10 Hz vector take 0.053 ms on average. Engine allocation peak (tracemalloc) is 0.43 MB; process max RSS is 41.4 MB, which includes the interpreter, NumPy and the 12,000 test records held in memory.
- **Decision:** the same script runs unchanged on the Jetson (numpy and pyyaml only). The Jetson numbers are not measured yet: `python3 module_4/tools/benchmark.py --frames 30000 --csv module_4/results/benchmark_jetson.csv`.

## E6. Learned temporal model (documented only, not implemented)

An HMM or a small 1D-CNN/GRU over the 60 s window could learn blink and microsleep patterns directly from `closure_prob`. We did not implement one, for three reasons:
- it needs labelled sequences we don't have yet (hundreds of annotated microsleeps);
- it is harder to explain and to tie to SG-5's fixed definitions (≥ 0.5 s, 30 s window);
- a GRU per 100 ms on the Jetson CPU is feasible (a few thousand parameters is under 1 ms) but adds a PyTorch/ONNX runtime to a core that is currently NumPy-only.

We will reconsider after real-video evaluation, if the rule-based engine's errors are dominated by noisy cue signals rather than definitions.

---

## Known limitations and failure cases

| Case | What happens | Mitigation / status |
|---|---|---|
| **Face lost during a head drop** | The closure's true length is unknown. It counts as a microsleep only if it had already reached 0.5 s. A head drop is counted as a nod if the face is lost within 300 ms of pitch ≤ −10°. | `nod_count` gives SG-5 the head-drop cue. A heuristic; it needs real head-drop clips. |
| **Looking down at a phone** | Same signature as a head drop, so it counts as a nod. | Known false positive. Yaw and duration could separate the two later. |
| **Glasses / glare** | SG-2 should mark the eye invalid. PERCLOS then rests on less valid time, and `validity_score` drops. | SG-5 can down-weight via `validity_score`. Not tested on real glasses yet. |
| **Lighting (night, IR)** | This is an upstream accuracy issue. SG-4 only sees its effect through confidence and validity. | Team clips in low light are planned. |
| **Talking vs yawning** | Mouth openings < 1.5 s are ignored, and repeats < 1 s apart are merged. Long laughs or singing could still pass as yawns. | Verified on mock talking bursts (yawn error 0.00). YawDD has talking clips for a real test. |
| **Dropped frames / gaps** | The time credited per frame is capped at 200 ms, so unobserved time is neither "closed" nor "valid". Durations come from timestamps. | Verified on the `noisy` mock (~3% drops plus two 300 ms bursts; PERCLOS error 0.19 mean). |
| **Hard OPEN/CLOSED from SG-2 (no probability)** | P80 becomes "share of time SG-2 says closed". Accuracy depends on SG-2's internal threshold. | Asked SG-2 for a calibrated probability or the EAR threshold they use. |
| **Start of drive** | PERCLOS over a few seconds of valid time is noisy (one blink early on reads as about 0.06). | SG-5 sees `calibrating: true` and `validity_score`. |
| **Synthetic evaluation only** | The scores are optimistic (see the caveat at the top). | NTHU-DDD, YawDD and team clips through `eval_clip.py`. |
