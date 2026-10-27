# SG-1 to SG-3 AI Integration Handoff

## Audience and scope

This file is technical context for an AI coding agent working on SG-3 Yawn/Facial-Cue Analysis.
Use it only when a human asks you to integrate SG-3 with SG-1.
Do not commit, push, change the shared contract or declare acceptance without human authorization.

## Integration objective

Replace SG-3's synthetic-only Mouth Aspect Ratio (MAR) input with mouth landmarks produced by SG-1.
Produce a valid frame-level mouth cue while preserving frame identity and invalid-face behavior.
Do not run a second face detector.

## Source of truth

Read these files before editing SG-3:

1. `module_1/docs/INTERFACE_CONTRACT.md`
2. `interfaces/sg1_v1.schema.json`
3. `interfaces/examples/sg1_v1_ok.json`
4. `interfaces/examples/sg1_v1_no_face.json`
5. `module_1/scripts/sg1_contract.py`
6. `module_3/SG-3 Facial Cues.py`
7. `module_3/README.md` from the SG-3 branch

Contract status: implemented by SG-1, but not frozen until SG-2, SG-3 and SG-6 accept it.

## Current SG-3 mismatch

The current SG-3 program generates a synthetic MAR time series.
It does not calculate MAR from real facial landmarks.
Its sample `confidence: 0.92` is fabricated example data, not a calibrated model score.

Do not carry the synthetic metrics into a real-video accuracy claim.
Do not emit numeric confidence unless SG-3 defines and validates its meaning.

## Mouth-index decision required

SG-3 must explicitly approve its mouth landmark indices before V1 is frozen.

A minimal candidate for MediaPipe Face Landmarker is:

```text
left mouth corner:  61
right mouth corner: 291
upper inner lip:    13
lower inner lip:    14
```

A minimal candidate MAR is:

```text
MAR = distance(upper_inner_lip, lower_inner_lip)
      / distance(left_mouth_corner, right_mouth_corner)
```

This is a candidate, not an accepted team decision.
If SG-3 selects a six-point or eight-point MAR definition, record the exact indices, point order and equation before implementation.

## Preparing the SG-3 packet

After SG-3 approves the indices, the integration layer calls:

```python
to_sg3_input(sg1_record, mouth_indices=[61, 291, 13, 14])
```

The adapter returns the points in the same order requested by SG-3.
It also returns:

- `frame_id`
- `timestamp_sec`
- `image_width`
- `image_height`
- `face_valid`
- `mouth_valid`
- `landmark_format`
- `coordinate_system`
- `mouth_landmark_indices`
- `mouth_points_xy_normalized`

## Required geometry rule

Convert normalized coordinates to pixels before calculating MAR:

```python
pixel_x = normalized_x * packet["image_width"]
pixel_y = normalized_y * packet["image_height"]
```

Do not calculate MAR directly from normalized coordinates on a non-square frame.
Do not reuse SG-3's synthetic MAR thresholds without measuring the real landmark-based MAR distribution.

## Required SG-3 implementation

Separate geometry from temporal state.
Add functions with behavior equivalent to:

```text
calculate_mar_from_points(points, image_width, image_height) -> float or null
process_sg1_mouth_packet(packet, state, config) -> SG-3 output dictionary
```

Required steps:

1. Preserve `frame_id`.
2. Preserve `timestamp_sec`.
3. Validate positive image dimensions.
4. Require both `face_valid` and `mouth_valid`.
5. Require the exact approved index list and point count.
6. Convert normalized points to pixels.
7. Reject zero mouth width.
8. Calculate real MAR.
9. Apply the selected threshold.
10. Update persistence only on valid frames.
11. Return invalid output when the face or mouth is invalid.

Recommended output shape for team review:

```json
{
  "frame_id": 0,
  "timestamp_sec": 0.0,
  "valid": true,
  "mouth_aspect_ratio": 0.24,
  "mar_threshold": 0.5,
  "yawn_cue_detected": false,
  "consecutive_yawn_frames": 0,
  "confidence": null,
  "processing_time_ms": 0.12
}
```

The displayed threshold is only a placeholder until SG-3 recalibrates it using real SG-1 landmarks.

## Invalid-input behavior

For an SG-1 `NO_FACE` record, SG-3 must return behavior equivalent to:

```json
{
  "frame_id": 1,
  "timestamp_sec": 0.04,
  "valid": false,
  "mouth_aspect_ratio": null,
  "mar_threshold": 0.5,
  "yawn_cue_detected": false,
  "consecutive_yawn_frames": 0,
  "confidence": null,
  "processing_time_ms": 0.0
}
```

Missing landmarks are not evidence that the driver is not yawning.
Downstream code must inspect `valid` before using the cue.
An invalid frame must not extend a yawn event.

## Production connection

The integrated flow is:

```text
SG-1 full record
    -> validate_sg1_record(record)
    -> to_sg3_input(record, approved_mouth_indices)
    -> SG-3 process_sg1_mouth_packet(packet, state, config)
    -> SG-3 output for SG-4
```

Keep `simulate_driver_facial_cues()` only as a controlled unit-test or parameter-study helper.
Do not use it as the production input path.

## Required tests

- Positive SG-1 fixture produces a finite MAR.
- No-face fixture produces `valid: false` and `mouth_aspect_ratio: null`.
- Wrong point count becomes invalid.
- Wrong index order is rejected.
- Zero mouth width becomes invalid without division by zero.
- Missing dimensions become invalid.
- Frame ID and timestamp remain unchanged.
- Invalid input resets or pauses persistence according to the accepted rule.
- Short speech-like openings do not satisfy the selected persistence rule.
- Real-landmark thresholds are evaluated separately from synthetic thresholds.

Run SG-1 checks first:

```powershell
module_1\.venv\Scripts\python.exe -m unittest module_1.tests.test_contract -v
module_1\.venv\Scripts\python.exe module_1\scripts\validate_output.py interfaces\examples\sg1_v1_ok.json
module_1\.venv\Scripts\python.exe module_1\scripts\validate_output.py interfaces\examples\sg1_v1_no_face.json
```

## Completion evidence

Integration is complete only when SG-3 records:

- tested SG-1 commit SHA;
- accepted mouth indices and MAR equation;
- selected real-landmark threshold and supporting evidence;
- positive fixture result;
- no-face fixture result;
- SG-3 output example;
- reviewer name;
- unresolved limitations.
