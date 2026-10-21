# SG-1 Midterm Demonstration

## What this demo proves

- The model and dependencies load.
- A video can be processed end to end.
- Every processed frame produces a valid SG-1 V1 record.
- `OK` and `NO_FACE` paths work.
- Three configurations can be compared on identical frames.
- SG-1 output can be converted to the proposed SG-2 eye packet.

It does not prove Jetson performance, landmark accuracy or downstream team acceptance.

## One-time setup

Run from `module_1`:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe scripts\download_model.py
.\.venv\Scripts\python.exe scripts\verify_setup.py --smoke-model
```

## Reproducible local fallback demo

The fallback video is built from the tracked qualitative contact sheet. It is only for setup and interface demonstration. It must not be used for an accuracy claim.

```powershell
.\.venv\Scripts\python.exe scripts\build_tracked_demo_video.py
.\.venv\Scripts\python.exe scripts\run_experiment.py `
  --input data\videos\sg1_tracked_demo.mp4 `
  --output-dir results\midterm_demo `
  --save-video
.\.venv\Scripts\python.exe scripts\verify_experiment.py results\midterm_demo
```

## Approved-video demo

Use an approved driver-facing video when available:

```powershell
.\.venv\Scripts\python.exe scripts\run_experiment.py `
  --input data\videos\approved_driver.mp4 `
  --output-dir results\approved_driver `
  --save-video
.\.venv\Scripts\python.exe scripts\verify_experiment.py results\approved_driver
```

Do not commit private footage, per-frame predictions or annotated videos.

## Quality checks

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts\validate_output.py ..\interfaces\examples\sg1_v1_ok.json
.\.venv\Scripts\python.exe scripts\validate_output.py ..\interfaces\examples\sg1_v1_no_face.json
```

## Presentation order

1. State SG-1 input and output.
2. Show `INTERFACE_CONTRACT.md` and the JSON Schema.
3. Run `verify_setup.py --smoke-model`.
4. Play one annotated output video.
5. Open one `OK` record and one `NO_FACE` record.
6. Show `comparison.csv`.
7. Run the tests.
8. State limitations without weakening them.

## Current fallback evidence

Run date: 2026-10-21.

| Configuration | Face coverage | Mean inference | P95 inference | End-to-end FPS |
|---|---:|---:|---:|---:|
| Baseline, 256 px / 0.50 | 16.4% | 11.3 ms | 23.0 ms | 64.5 |
| Lower threshold, 256 px / 0.35 | 52.7% | 15.8 ms | 22.9 ms | 47.5 |
| Lower resolution, 192 px / 0.50 | 28.2% | 17.6 ms | 25.4 ms | 45.0 |

These numbers come from a generated 110-frame interface-demo video. They are evidence that the comparison pipeline works. They are not a detector benchmark and do not replace the earlier Week 5 real-video results.

## Before entering the evaluation

- [ ] Replace the fallback with an approved raw driver clip if available.
- [ ] Run the experiment verifier on that clip.
- [ ] Ask SG-2 and SG-3 to run the fixtures.
- [ ] Record their acceptance or objections.
- [ ] Rehearse within the allotted time.
- [x] Keep a copy of the model and fallback video locally in case the network is unavailable.
