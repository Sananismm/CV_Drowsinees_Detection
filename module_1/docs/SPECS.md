# SG-1 Technical Specifications

## Module identity

| Item | Value |
|---|---|
| Project | Driver Drowsiness Monitoring |
| Module | SG-1 Face and Landmark Detection |
| Owners | Muhammad Sharjeel Hanif, Muhammad Bilal Maqbool |
| Shared SG-1 branch | `sg1/w5-face-landmark` (historical name; reused for current SG-1 progress) |
| Input | One BGR video frame |
| Output | Face status, face box, normalized landmarks and timing data |
| Downstream modules | SG-2 Eye/Blink Analysis and SG-3 Yawn/Facial Cues |

## Verified development environment

Verified on 2026-10-21.

| Component | Version |
|---|---:|
| Python | 3.12.14 |
| MediaPipe | 0.10.35 |
| OpenCV contrib | 4.11.0.86 |
| NumPy | 1.26.4 |
| Platform tested in this setup | Windows x86-64 |

Use `requirements-lock.txt` to reproduce this exact environment.
Use `requirements.txt` when a compatible version range is preferred.
Use `requirements-dev.txt` to run schema and automated tests.

## Model resource

| Item | Value |
|---|---|
| Model | MediaPipe Face Landmarker float16 task bundle |
| Local path | `models/face_landmarker.task` |
| Download script | `scripts/download_model.py` |
| Download source | Google MediaPipe model storage |
| File size | 3,758,596 bytes |
| SHA-256 | `64184E229B263107BC2B804C6625DB1341FF2BB731874B0BCC2FE6544E0BC9FF` |
| Git policy | Ignored. Download locally. |

The download script verifies the exact SHA-256.
It downloads to a temporary `.part` file and replaces the target only after verification.

## Configuration resource

File: `configs/experiment.json`

| Name | Long side | Detection threshold | Presence threshold | Tracking threshold |
|---|---:|---:|---:|---:|
| `baseline` | 256 px | 0.50 | 0.50 | 0.50 |
| `lower_threshold` | 256 px | 0.35 | 0.35 | 0.35 |
| `lower_resolution` | 192 px | 0.50 | 0.50 | 0.50 |

The current provisional candidate is `lower_resolution`.
This choice is based on desktop results.
It is not yet validated on Jetson.

## Code file specifications

### `scripts/sg1_detector.py`

Purpose:

- Load the Face Landmarker model.
- Resize each input frame.
- detect one face.
- return one face mesh.
- build a face box from landmark bounds.
- return a stable dictionary.

Main types:

- `DetectorConfig`
- `SG1FaceLandmarkDetector`

Primary method:

```text
process(frame_bgr, frame_id, timestamp_ms) -> dictionary
```

Required input:

- OpenCV BGR image.
- Integer frame ID.
- Integer timestamp in milliseconds.

Possible status values:

- `OK`
- `NO_FACE`

Known limits:

- One face only.
- No observed face-confidence score.
- No explicit eye or mouth ROI.
- No face alignment.
- Landmarks can move outside the normal image range near boundaries.

### `scripts/run_experiment.py`

Purpose:

- Read a video.
- Run each configured detector setting.
- write JSONL predictions.
- write failure CSV files.
- write comparison metrics.
- optionally write annotated videos.

Required resource:

- A readable video.
- The downloaded model.
- `configs/experiment.json`.

Generated files:

- `predictions_<config>.jsonl`
- `failures_<config>.csv`
- `comparison.csv`
- `run_metadata.json`
- optional `annotated_<config>.mp4`

### `scripts/evaluate_boxes.py`

Purpose:

- Compare predicted face boxes with manual boxes.
- use IoU matching.
- report TP, FP, FN, precision, recall and F1.

Inputs:

- Prediction JSONL.
- Label CSV.
- IoU threshold.

Limit:

- It evaluates one primary face per frame.
- It does not evaluate landmark accuracy.

### `scripts/capture_video.py`

Purpose:

- Capture an approved driver-facing video.
- save it for repeatable experiments.

Important rule:

- Obtain consent.
- Do not commit private video.

### `scripts/download_model.py`

Purpose:

- Download the official Face Landmarker task bundle.
- Verify the expected SHA-256.
- Avoid leaving an unverified final model file.

### `scripts/sg1_contract.py`

Purpose:

- Validate SG-1 V1 records without a runtime schema dependency.
- Reject incompatible records.
- Convert valid records to proposed SG-2 and SG-3 input packets.

### `scripts/verify_setup.py`

Purpose:

- Check package versions, configuration and model integrity.
- Optionally run a black-frame model smoke test.

### `scripts/verify_experiment.py`

Purpose:

- Validate every prediction record.
- Confirm identical frame selection across configurations.
- Recompute output and failure counts.
- Check annotated video dimensions, frame count and FPS.

## Data specifications

### Video input

- Recommended format: MP4.
- Color format after OpenCV decode: BGR.
- Timestamp source: frame index and video FPS.
- Driver face count: one primary driver.

### Manual face-box labels

CSV columns:

```text
frame_idx,x1,y1,x2,y2
```

Coordinates use original-frame pixels.
An empty box means no visible driver face.

## Output specification

The canonical proposal is defined in `INTERFACE_CONTRACT.md`.
The current implementation returns JSON-compatible dictionaries.
JSONL is used for saved experiments.

## Repository policy

Ignored resources:

- `.venv/`
- model binaries;
- raw videos;
- local labels;
- generated prediction streams;
- generated annotated videos.

Tracked evidence:

- source code;
- configuration;
- documentation;
- approved aggregate metrics;
- approved small label files;
- approved qualitative examples.
