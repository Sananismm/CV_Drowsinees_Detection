# SG-4 midterm demo (about 5 minutes)

Run from the team repo root with the venv active.

| min | Command | What to point out |
|---|---|---|
| 0:00 | `pytest module_4/tests -q` | 54 tests pass, including the SG-5 contract and the required cases (0.7 s closure, 0.45 s slow blink, yawn = 1 event, face lost mid-closure, 30 s expiry, empty input). |
| 0:45 | `python module_4/tools/run_sg4.py --input interfaces/mocks/drowsy.jsonl --output /tmp/drowsy_out.jsonl --plot /tmp/drowsy.png` | 900 vectors at 10 Hz, 0 schema errors. Open the plot: `long_blinks` steps up and `eye_closure_s` ramps during each microsleep. |
| 1:30 | `sed -n '745,760p' /tmp/drowsy_out.jsonl` | Live microsleep (ground truth 74.0–75.8 s): `eye_closure_s` rises 0.4 → 1.7 s, then 0.0 at 75.8 s (reopen); `long_blinks` steps 3 → 4 at 74.5 s, when the closure reaches 0.5 s. |
| 2:00 | `python module_4/tools/run_sg4.py --input interfaces/mocks/noisy.jsonl --output /tmp/noisy_out.jsonl` | Duplicates, out-of-order frames and gaps are dropped and counted (printed stats). Output still valid. |
| 2:30 | `python module_4/tools/check_sg5_compat.py /tmp/noisy_out.jsonl` | PASS per SG-5 field. This is what SG-5 runs at Gate 1. |
| 3:00 | `python evaluation/sg4/evaluate.py --plots` + open `module_4/results/ablation_face_lost.png` | Primary vs EMA vs naive. Looking away: naive `eye_closure_s` > 1 s (false micro-sleep) vs SG-4 0.0. |
| 4:00 | `python module_4/tools/benchmark.py` | about 0.03 ms per update vs the 2 ms target; 0.4 MB of engine allocations. Same command on the Jetson. |
| 4:30 | (optional) `python module_4/tools/standin_extractor.py --camera 0 --live` | Live overlay. Say clearly: stand-in cues, not SG-2/SG-3 work. |

## Likely examiner questions

1. **Why not decide per frame?** A single closed frame is a blink; the same closure held for 0.5 s is a microsleep. The ablation shows a per-frame counter raises false alerts from 0 to 27 per hour (proxy rule, 10 seeds), mostly from look-aways counted as closed eyes (`results/metrics_10seeds.md`).
2. **How is PERCLOS O(1)?** Each frame stores the milliseconds it was valid and closed. Each window keeps running sums: add the new frame, subtract frames whose timestamp left the window. Every frame is added once and removed once (`ring_buffer.py`).
3. **What if the face is lost?** That frame is invalid. It is excluded from PERCLOS's denominator, any ongoing closure ends, and `eye_closure_s = 0.0`. `face_valid = 0` tells SG-5. A head drop that loses the face is still reported via `nod_count` (`engine._head_drop_lost_face`).
4. **Why hysteresis (0.8 / 0.5)?** A closure-prob signal hovering around 0.8 would otherwise split one closure into several fake blinks (`test_hysteresis_ignores_flicker_around_threshold`).
5. **Why timestamps and not frame counts?** FPS varies and frames drop. Durations from SG-1's clock stay correct; the noisy mock (3% drops, jitter) still gives a 0.19-pt PERCLOS error.
6. **Your backup approach?** The naive frame counter (implemented, ablation) and EMA PERCLOS (implemented: 1.05 vs 0.12 pts error). A learned HMM/GRU is documented only: no labelled data yet, and it adds a runtime to the NumPy-only core (`sg4_experiments.md` E6).
7. **How do you know SG-5 can use your output?** We followed SG-5's table literally. A contract test runs on every change, there are golden files for SG-5, and a stdlib-only checker prints PASS/FAIL per field.
8. **Limitations?** The scores are from synthetic data generated with the same definitions. Slow blinks near 500 ms can flip to microsleeps at 30 FPS (all 5 false positives in the sweep). SG-2 currently sends hard states only. The Jetson numbers are not measured yet.

---

# PR proposal

**Title:** `sg4: temporal engine v1.1 aligned with SG-5, mocks, evaluation and ablation`

**Body:**

> ## What
> - SG-4 core (NumPy only, Py 3.8+): sync and validity, O(1) ring-buffer PERCLOS, hysteresis event machines (blink, slow, long, yawn, nod), baseline and trend, a 10 Hz `TemporalEngine`.
> - SG-5 v1.1 output built only in `sg5_output.to_sg5`; JSON schemas; golden files `interfaces/mocks/sg5_expected/`; `check_sg5_compat.py`.
> - `adapters.py` accepts our v1 input and SG-2's draft eye record.
> - Seeded mock generator with ground truth (5 scenarios); evaluation, backup approaches (naive, EMA) and ablation; benchmark; stand-in MediaPipe extractor (test harness).
> - Docs: README, interface tracking, experiments log, status, meeting notes.
>
> ## Why
> Midterm Stage 1: a working module on mock input with a frozen V1 contract, primary vs backup evidence, and reproducible results. SG-5's request table is followed literally, so SG-5 can integrate without waiting for us.
>
> ## Evidence
> `pytest module_4/tests -q` → 54 passed. `results/metrics.md` and `results/metrics_10seeds.md`: PERCLOS error 0.11 pts, microsleep recall 100%, lag ≤ 0.12 s. The naive ablation gives 27 false alerts/h vs 0. `results/benchmark_pc.csv`: 0.026 ms per update.
>
> ## Not done
> Jetson benchmark; real-video evaluation; SG-3 format.
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)

After merge: `git tag -a sg4-v1-midterm -m "SG-4 midterm Stage 1" && git push origin sg4-v1-midterm`.
