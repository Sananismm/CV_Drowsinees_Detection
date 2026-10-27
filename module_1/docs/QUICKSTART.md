# SG-1 Quick Start

Run all commands from `module_1/`.

## 1. Create the environment

```powershell
python -m venv .venv
```

If `python` is not a real installation, install Python 3.12 first.
Do not use the Microsoft Store alias as the project runtime.

## 2. Install the verified packages

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
```

Use `requirements.txt` only when exact locked versions are unavailable.

## 3. Download and verify the model

```powershell
.\.venv\Scripts\python.exe scripts\download_model.py
```

Verify its hash:

```powershell
(Get-FileHash -Algorithm SHA256 models\face_landmarker.task).Hash
```

Expected SHA-256:

```text
64184E229B263107BC2B804C6625DB1341FF2BB731874B0BCC2FE6544E0BC9FF
```

## 4. Check the environment

```powershell
.\.venv\Scripts\python.exe -c "import cv2, mediapipe, numpy; print(cv2.__version__, mediapipe.__version__, numpy.__version__)"
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts\verify_setup.py --smoke-model
```

Expected verified versions:

```text
OpenCV 4.11.0
MediaPipe 0.10.35
NumPy 1.26.4
```

## 5. Prepare an approved video

Place it under:

```text
data/videos/
```

The directory is ignored by Git.
Do not commit private footage.

To record a short clip:

```powershell
.\.venv\Scripts\python.exe scripts\capture_video.py --camera 0 --duration 30 --output data\videos\driver_sample.mp4
```

## 6. Run the experiment

```powershell
.\.venv\Scripts\python.exe scripts\run_experiment.py --input data\videos\driver_sample.mp4 --save-video
```

Outputs appear under:

```text
results/driver_sample/
```

## 7. Inspect the result

Check:

- `comparison.csv`
- `predictions_baseline.jsonl`
- `failures_baseline.csv`
- `annotated_baseline.mp4`
- `run_metadata.json`

## 8. Run box evaluation

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_boxes.py `
  --predictions results\driver_sample\predictions_baseline.jsonl `
  --labels data\labels\driver_sample_boxes.csv
```

## 9. Before presenting

- Run the full command once.
- Keep the model downloaded.
- Keep an approved video available.
- Keep generated output available.
- Keep a prerecorded fallback.
- Do not install packages during the presentation.

For the exact fallback and approved-video evaluation sequence, use [`MIDTERM_DEMO.md`](MIDTERM_DEMO.md).
