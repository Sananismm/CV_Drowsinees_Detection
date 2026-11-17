# SG6 executable code and run commands

Run all commands from the repository root. Basic verification, the detector demo
and the benchmark use Python 3.10/3.11 with `code/requirements.txt`. The YuNet ONNX
file is already in `embedded_6/models/`. Haar's XML comes with the OpenCV wheel.

## 1. Isolated setup

Linux / Jetson (do not install into the system Python):

```bash
python3 -m venv .venv-sg6
.venv-sg6/bin/python -m pip install -r embedded_6/midterm/code/requirements.txt
.venv-sg6/bin/python embedded_6/midterm/code/verify.py
```

Windows PowerShell:

```powershell
python -m venv .venv-sg6
.\.venv-sg6\Scripts\python.exe -m pip install -r embedded_6/midterm/code/requirements.txt
.\.venv-sg6\Scripts\python.exe embedded_6/midterm/code/verify.py
```

On Jetson, wheel availability and this newly pinned environment must be checked
on ARM64. The historical benchmark used a different environment (OpenCV 4.14.0).
The checked-in verification JSON identifies the environment actually tested.
No CUDA build or acceleration is assumed. A failed package install is a blocker,
not a completed setup; save the install log rather than silently changing versions.

## 2. Live detector demo

Replace `python` below with the isolated environment's executable. The GUI uses
Python Tkinter; Linux may require the distribution's `python3-tk` package. Use
`--headless` without a desktop. Stop with q/Escape in the window, or Ctrl+C.

```bash
python embedded_6/midterm/code/run_demo.py --help
python embedded_6/midterm/code/run_demo.py --detector yunet --camera 0 --frames 150 --save-metrics
python embedded_6/midterm/code/run_demo.py --detector haar --camera 0 --frames 150 --save-metrics
python embedded_6/midterm/code/run_demo.py --detector yunet --headless --duration 30 --save-metrics
```

`--backend auto` selects V4L2 on Linux and OpenCV's default on Windows. Windows
also supports `--backend dshow` or `--backend msmf`. The current revision's live
camera and GUI behavior still need physical validation. JSON metrics go to ignored
`embedded_6/evidence/`. They include timestamp, host/architecture, Python/OpenCV,
model hash, detector settings, resolution, frame/read counts, mean/median detector
time and processing FPS. Images and videos are not recorded.

## 3. Paired detector benchmark

Privately prepare 150 consented `.jpg`, `.jpeg` or `.png` frames of the same
resolution. Both detectors receive the same decoded frames in sorted filename
order. The benchmark performs five warm-ups per detector per repeat and three
repeats, alternating detector order between repeats.

```bash
python embedded_6/midterm/code/benchmark.py --frames-dir /path/to/private/frames --frames 150 --warmup 5 --repeats 3
```

Windows uses a quoted local folder instead of `/path/to/private/frames`.
The default output is ignored `embedded_6/evidence/post_midterm_benchmark.json`.
It records per-frame detector time/count, mean/median/p95, detector-only FPS,
input hashes, model hashes, environment and parameters. Decode/capture/display
and downstream modules are excluded. Ground-truth accuracy, power and temperature
are not measured. Review metrics before copying selected evidence into Git.

The older `python embedded_6/Integration/benchmark_detectors.py` remains available
for the original private `evidence/benchmark_frames/frame_*.jpg` dataset. That
dataset is absent here. Missing images are not replaced with fabricated results.

## 4. Optional complete software pipeline

Follow [integrated/README.md](../integrated/README.md) in a **separate environment**
using `embedded_6/integrated/requirements.txt`. It pins NumPy 1.26.4,
opencv-contrib-python 4.10.0.84, MediaPipe 0.10.18 and PyYAML. Do not install
opencv-python and opencv-contrib-python in the same environment.

The separate SG1 `face_landmarker.task` model is not bundled. The existing
integration guide gives the download source and pinned SHA-256. The launcher
rejects missing or mismatched models. Its historical snapshot is optional;
camera-free integration tests do not need MediaPipe or that model.

```bash
python embedded_6/Integration/run_integrated.py --video /path/to/private/demo.mp4 --headless --frames 120
python embedded_6/Integration/run_integrated.py --camera 0 --headless --frames 150
```

It uses the pinned SG3-derived adapter, displays experimental decisions and
does not actuate GPIO. On Linux a GUI requires DISPLAY/WAYLAND. This full-pipeline
launcher is retained from the October SG6 snapshot, unlike the updated detector
launcher. Prefer `--headless` for portable verification.

## 5. Refresh verification evidence deliberately

```bash
python embedded_6/midterm/code/verify.py --output-dir embedded_6/midterm/evidence
```

This overwrites the recorded verification JSON and four text logs with the current
host's results. The default without this option writes to the ignored private
evidence folder instead. Do not describe PC verification as Jetson evidence.

## 6. Collect fresh target platform evidence

The existing SG5 handoff provides a diagnostic collector. Run it in the provisioned
target environment; strict success requires the actual target and scoped stack
checks, plus physical camera acquisition:

```bash
python embedded_6/sg5_handoff/check_platform.py --camera 0 --frames 30 --output embedded_6/evidence/platform_jetson.json --strict
```

See [the handoff guide](../sg5_handoff/README.md). A saved video is a fallback test,
not physical-camera evidence. Review its diagnostics before sharing. No strict
target success or physical alert verification has been recorded in this package.
