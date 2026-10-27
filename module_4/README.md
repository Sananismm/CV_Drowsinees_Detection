# SG-4 — Temporal Behaviour Analysis

CS-477 Driver Drowsiness Monitoring, group G1-D2. Owners: Saman Iqbal, Syeda Musfirah Hamid.

SG-4 turns per-frame cues (eye closure, yawn, head pitch, about 30 FPS) into **persistent temporal indicators** such as PERCLOS, microsleeps, yawn and nod events, and trend. It publishes them to SG-5 as one flat JSON vector **every 100 ms (10 Hz)**.

```
Camera → SG-1 face/landmarks → SG-2 eye/blink ┐
                              → SG-3 yawn/pose ┴→ SG-4 temporal (this) → SG-5 decision → alert
                                                   (CPU thread on the Jetson Orin Nano, SG-6)
```

**Status:** working on mock and stand-in input. SG-2 and SG-3 have not delivered final outputs yet. SG-2's draft eye output is already supported through [`src/sg4/adapters.py`](src/sg4/adapters.py). See [`documentation/sg4_status.md`](../documentation/sg4_status.md).

## Dependencies

- Core (Jetson and PC): Python **3.8+**, `numpy`, `pyyaml`, `jsonschema` ([requirements.txt](requirements.txt)). Pure Python plus NumPy, with no GPU, PyTorch or TensorFlow.
- Dev tools: `pytest`, `matplotlib`, `opencv-python`, `mediapipe` ([requirements-dev.txt](requirements-dev.txt)). The last two are needed only for the stand-in extractor.

```bash
# Linux / macOS / Jetson
python3 -m venv .venv && source .venv/bin/activate
pip install -r module_4/requirements-dev.txt        # Jetson: pip install -r module_4/requirements.txt

# Windows (PowerShell)
py -3 -m venv .venv; .venv\Scripts\Activate.ps1
pip install -r module_4\requirements-dev.txt
```

## I/O interface

| Direction | Schema | Status |
|---|---|---|
| Input (SG-1/2/3 → SG-4), one JSON record per frame | [`interfaces/sg4_input_v1.schema.json`](../interfaces/sg4_input_v1.schema.json) | V1-PROPOSED |
| Output (SG-4 → SG-5), 10 Hz | [`interfaces/sg4_output_v1_1.schema.json`](../interfaces/sg4_output_v1_1.schema.json) | Agreed with SG-5 (written confirmation pending) |

The adapter also accepts **SG-2's native eye record** (`eye_state`, `eye_valid`, `timestamp` in seconds, `eye_closure_prob` = null). When `eye_closure_prob` is null, the state is mapped as `CLOSED` → 1.0, `OPEN` → 0.0 and `UNKNOWN` → invalid.

**Fields SG-5 consumes (names, units and windows exactly as SG-5 requested):**

| Field | Type | Meaning | Window |
|---|---|---|---|
| `time_s` | float | SG-1 capture time of the latest frame, in seconds, increasing | — |
| `perclos` | float 0–1 | Share of **valid** time with eyes ≥ 80% closed (P80). Not a percentage | 60 s |
| `face_valid` | 0/1 | Current frame has a face with confidence ≥ 0.5 | current frame |
| `long_blinks` | int | Closures ≥ 0.5 s (microsleeps), counted when the closure reaches 0.5 s | 30 s |
| `yawn_count` | int | Debounced yawn **events**; repeats < 1 s apart are merged | 60 s |
| `eye_closure_s` | float | Length of the ongoing closure, unsmoothed; 0.0 when eyes are open or the face is lost | live |
| `nod_count` (extra) | int | Nods and head drops, including a head drop that loses the face | 60 s |

The extras are `validity_score`, `calibrating`, `blink_rate_bpm`, `mean_blink_ms`, `slow_blinks` (> 400 ms and < 500 ms), `longest_closure_s`, `head_down_s`, `face_absent_s`, `perclos_vs_baseline` and `trend`. All thresholds and windows live in [`config/sg4_v1.yaml`](config/sg4_v1.yaml).

## How it works

1. **Sync and validate** ([sync.py](src/sg4/sync.py)). Duplicate and out-of-order timestamps are dropped and counted, and gaps over 200 ms are logged. Each frame gets per-cue validity: no face, low confidence or a null cue makes that cue **invalid**. An invalid cue is never treated as "closed", so looking away is never counted as sleep.
2. **Ring buffer** ([ring_buffer.py](src/sg4/ring_buffer.py)). This is a fixed NumPy array. Each frame stores the milliseconds it contributes, for example "valid and closed for 33 ms". Each window (60 s for PERCLOS, validity and blink rate) keeps a running sum: add the new frame, subtract frames that left the window. This is **O(1) per frame**, and integer sums never drift.
   **PERCLOS = closed-and-valid ms ÷ valid ms.**
3. **Event state machines** ([events.py](src/sg4/events.py)).
   - Eyes: hysteresis. A closure starts at `closure_prob ≥ 0.8` and ends at `≤ 0.5`, so flicker around 0.8 does not create fake blinks. Duration comes from timestamps. 70–400 ms is a blink, 400–500 ms a slow blink, and ≥ 500 ms a long blink (microsleep). A long blink is counted the moment it reaches 500 ms. If the eye becomes invalid, the closure ends and `eye_closure_s` drops to 0.
   - Yawns and nods: hysteresis, plus a minimum duration (yawn 1.5 s, which filters out talking; nod 300 ms), plus merging of repeats < 1 s apart.
   - Head drops: if the face is lost within 300 ms of the head pitching down past −10°, the event counts as a nod.
4. **Baseline and trend** ([baseline.py](src/sg4/baseline.py)). The first 60 s set the driver's own PERCLOS. After that, `perclos_vs_baseline = perclos / baseline` (with a floor of 0.02). `trend` comes from the least-squares slope of PERCLOS over the last 30 s: ≥ +0.05/min is worsening.
5. **Output** ([engine.py](src/sg4/engine.py) → [sg5_output.py](src/sg4/sg5_output.py)). `TemporalEngine.push(record)` returns a vector every 100 ms of capture time. `to_sg5()` is the **only** place SG-5 field names are written. SG-5 fields are valid from the first frame; calibration affects only the extras.

**Backup approaches** ([baselines_alt.py](src/sg4/baselines_alt.py)) emit the same v1.1 vector, so the ablation is like-for-like:
- (1) naive consecutive-closed-frame counter: single-frame classification, no validity handling, no hysteresis, frame counts instead of timestamps;
- (2) EMA PERCLOS: a moving average instead of an exact window, with no calibration.

## How to run

Run these from the team repo root.

```bash
pytest module_4/tests -q                                           # 54 tests, incl. SG-5 contract
python module_4/tools/mock_stream.py --all                         # regenerate the 5 mock scenarios (+ ground truth)
python module_4/tools/run_sg4.py --input interfaces/mocks/drowsy.jsonl --output out.jsonl --plot out.png
python module_4/tools/check_sg5_compat.py out.jsonl                # PASS/FAIL per SG-5 field (stdlib only)
python evaluation/sg4/evaluate.py --plots                            # metrics + ablation -> module_4/results/
python evaluation/sg4/evaluate.py --seeds 10                         # 10-seed robustness sweep
python module_4/tools/benchmark.py --csv module_4/results/benchmark_pc.csv
python module_4/tools/standin_extractor.py --camera 0 --live       # live demo (stand-in cues, dev PC)
```

Other options:
- `run_sg4.py --approach naive|ema` runs a backup approach.
- `run_sg4.py` also accepts SG-2 native JSONL directly.

**Jetson (CPU only, no GPU needed):**

```bash
pip3 install -r module_4/requirements.txt
python3 module_4/tools/benchmark.py --frames 30000 --csv module_4/results/benchmark_jetson.csv
pytest module_4/tests -q
```

## Test data

- `interfaces/mocks/*.jsonl` holds 5 seeded 90 s scenarios at 30 FPS, each with `*.gt.json` ground truth: `alert`, `drowsy`, `yawns_nods`, `face_lost` and `noisy`. The noisy scenario adds dropped frames, jitter, out-of-order and duplicate frames, talking and spikes.
- `interfaces/mocks/sg5_expected/*.jsonl` holds the golden SG-4 output for each scenario, for SG-5 to develop against.
- `interfaces/examples/` holds valid and invalid input records, SG-2 native records, and output examples: alert, microsleep, face lost and calibrating.
- Real video: see [`datasets/sg4_manifest.md`](../datasets/sg4_manifest.md) (NTHU-DDD, YawDD, team clips). No data is committed.

## Current performance

These numbers come from the [`results/`](results/) files: `metrics.md`, `metrics_10seeds.md` and `benchmark_pc.csv`.

> **Synthetic data only.** The mocks are generated with the same event definitions as the engine. These numbers show that the implementation is correct and robust to stream defects; they do **not** show real-world accuracy, which needs annotated video.

| Metric | Target | Primary (5 mocks) | Primary (10 seeds × 5) | Naive baseline (10 seeds) |
|---|---|---|---|---|
| PERCLOS error, mean / worst (pts) | < 5 | 0.12 / 0.32 | 0.11 / 0.65 | 2.34 / 13.38 |
| Microsleep recall | ≥ 90% | 100% (12/12) | 100% (120/120) | 100% (120/120) |
| Microsleep precision | — | 100% (12/12) | 96% (120/125) | 74% (120/163) |
| Blink-rate error (bpm) | < 2 | 0.01 | 0.08 | n/a |
| Lag after microsleep ends (max) | ≤ 1 s | 0.08 s | 0.12 s | 0.13 s |
| False alerts/h (proxy SG-5 rule) | lower is better | 0 | 0 | 27 |
| Update time, mean / p95 / max (PC: Apple arm64, Py 3.9) | < 2 ms | 0.026 / 0.060 / 0.172 ms | | |
| Engine memory (tracemalloc peak) / process RSS | < 50 MB | 0.43 MB / 41.4 MB | | |
| Update time on the Jetson Orin Nano | < 2 ms | **not measured yet**: run the Jetson command above | | |

The ablation figure is [`results/ablation_face_lost.png`](results/ablation_face_lost.png). When the driver looks away, the naive counter's `eye_closure_s` climbs past 1 s, which would fire SG-5's micro-sleep override. SG-4 reports `face_valid = 0` and `eye_closure_s = 0.0`.

## Known limitations

- The numbers above are from synthetic data. Real-video evaluation (NTHU-DDD, YawDD, team clips) is still to do.
- SG-2 currently sends a hard OPEN/CLOSED state and no probability. P80 PERCLOS then equals "share of time SG-2 says closed", so its accuracy depends on SG-2's closed threshold.
- Slow blinks of about 475 ms can measure ≥ 500 ms at 30 FPS because of frame quantization. These caused all 5 false microsleeps in the 10-seed run.
- If the face is lost mid-closure, the closure's true length is unknown. It is not counted as a microsleep unless it had already reached 0.5 s.
- Looking down at a phone just before the face is lost counts as a nod (head-drop heuristic).
- PERCLOS in the first seconds of a drive rests on little valid time and is noisy. SG-5 can use `validity_score` and `calibrating`.

More detail, and the failure cases (glasses, lighting, talking vs yawning, dropped frames), are in [`documentation/sg4_experiments.md`](../documentation/sg4_experiments.md).

## Next steps (to Integration Gate 1, Lab 8)

1. Get the SG-2 eye and SG-3 yawn/pose field confirmations, and update `adapters.py` only.
2. Run `benchmark.py` on the Jetson and add `results/benchmark_jetson.csv`.
3. Annotate at least 3 team clips and 2 NTHU-DDD clips, then run `eval_clip.py`.
4. Integration test with SG-5 using `check_sg5_compat.py` on live output, then tag `sg4-gate1`.

## Layout

```
module_4/
  config/sg4_v1.yaml        all thresholds and windows
  src/sg4/                  core (numpy only): adapters, sync, ring_buffer, events, indicators,
                            baseline, engine, sg5_output, baselines_alt, schema, config, paths
  tools/                    mock_stream, run_sg4, check_sg5_compat, benchmark, plot_mock,
                            make_examples, standin_extractor (test harness)
  tests/                    pytest suite
  results/                  metrics, benchmark CSV, plots (small files only)
(SG-4's team-level files live at the repo root: interfaces/, evaluation/sg4/, documentation/, datasets/)
```
