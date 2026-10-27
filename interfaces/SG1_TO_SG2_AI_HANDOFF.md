# SG-1 to SG-2 AI Integration Handoff

## Audience and scope

This file is technical context for an AI coding agent working on SG-2 Eye/Blink Analysis.
Use it only when a human asks you to integrate SG-2 with SG-1.
Do not commit, push, change the shared contract or declare acceptance without human authorization.

## Integration objective

Consume one SG-1 result for each frame.
Calculate left-eye, right-eye and average Eye Aspect Ratio (EAR).
Return `OPEN`, `CLOSED` or `UNKNOWN` without running another face detector.

## Source of truth

Read these files before editing SG-2:

1. `module_1/docs/INTERFACE_CONTRACT.md`
2. `interfaces/sg1_v1.schema.json`
3. `interfaces/examples/sg1_v1_ok.json`
4. `interfaces/examples/sg1_v1_no_face.json`
5. `interfaces/examples/sg1_to_sg2_v1_ok.json`
6. `interfaces/examples/sg1_to_sg2_v1_no_face.json`
7. `module_1/scripts/sg1_contract.py`
8. `module_2/eye_analysis.py` from the SG-2 branch

Contract status: implemented by SG-1, but not frozen until SG-2, SG-3 and SG-6 accept it.

## Current SG-2 mismatch

The current SG-2 function `calculate_ear()` expects a complete MediaPipe landmark list.
Each item must have `.x` and `.y` attributes.

The SG-1 adapter packet instead supplies these arrays:

```text
left_eye_points_xy_normalized:  six [x,y] lists
right_eye_points_xy_normalized: six [x,y] lists
```

Do not pass these arrays into the old function unchanged.
Do not reconstruct fake landmark objects.
Add a function that accepts the selected `[x,y]` lists directly.

## Agreed proposed eye order

Left eye:

```text
[33, 160, 158, 133, 153, 144]
```

Right eye:

```text
[362, 385, 387, 263, 373, 380]
```

The six points are ordered as `P1` through `P6` for:

```text
EAR = (distance(P2,P6) + distance(P3,P5))
      / (2 * distance(P1,P4))
```

These indices match the current SG-2 branch.
SG-2 must still record explicit acceptance before V1 is frozen.

## Required geometry rule

SG-1 coordinates are normalized against the full image.
Convert them to pixels before calculating EAR:

```python
pixel_x = normalized_x * packet["image_width"]
pixel_y = normalized_y * packet["image_height"]
```

Do not calculate EAR directly from normalized coordinates on a non-square frame.
Different horizontal and vertical scales would distort the ratio.

## Required SG-2 implementation

Add a public function with behavior equivalent to:

```text
process_sg1_eye_packet(packet, threshold=0.15) -> SG-2 output dictionary
```

Required steps:

1. Preserve `frame_id`.
2. Preserve `timestamp_sec`.
3. Validate positive `image_width` and `image_height`.
4. Require both `face_valid` and `eyes_valid`.
5. Require exactly six points for each eye.
6. Convert the selected points to pixels.
7. Calculate left and right EAR.
8. Calculate their average.
9. Use the current preliminary threshold `0.15` unless SG-2 changes it with evidence.
10. Return `UNKNOWN`, `ear: null` and `valid: false` when input is invalid.

The SG-2 output must preserve at least:

```json
{
  "frame_id": 0,
  "timestamp_sec": 0.0,
  "eye_state": "OPEN",
  "ear": 0.2855,
  "ear_threshold": 0.15,
  "valid": true,
  "closure_event": null
}
```

The numeric EAR above is illustrative.
Tests should calculate it from the fixture rather than hard-code it as a contract value.

## Invalid-input behavior

For `sg1_to_sg2_v1_no_face.json`, return:

```json
{
  "frame_id": 1,
  "timestamp_sec": 0.04,
  "eye_state": "UNKNOWN",
  "ear": null,
  "ear_threshold": 0.15,
  "valid": false,
  "closure_event": null
}
```

Missing landmarks are not closed eyes.
An invalid frame must not start or extend an eye-closure event.

## Production connection

The integration layer should perform this flow:

```text
SG-1 full record
    -> validate_sg1_record(record)
    -> to_sg2_input(record)
    -> SG-2 process_sg1_eye_packet(packet)
    -> SG-2 output for SG-4
```

SG-2 should consume the adapter packet.
It should not import MediaPipe or rerun face detection in the integrated path.

## Required tests

- Positive fixture produces finite left, right and average EAR.
- Current positive fixture produces `valid: true`.
- No-face fixture produces `UNKNOWN`, `ear: null`, `valid: false`.
- Wrong point count is rejected or becomes invalid.
- Zero horizontal eye width becomes invalid without division by zero.
- Missing dimensions become invalid.
- Frame ID and timestamp remain unchanged.
- No-face input resets or pauses closure state as agreed with SG-4.

Run SG-1 checks first:

```powershell
module_1\.venv\Scripts\python.exe -m unittest module_1.tests.test_contract -v
module_1\.venv\Scripts\python.exe module_1\scripts\validate_output.py interfaces\examples\sg1_v1_ok.json
module_1\.venv\Scripts\python.exe module_1\scripts\validate_output.py interfaces\examples\sg1_v1_no_face.json
```

## Completion evidence

Integration is complete only when SG-2 records:

- tested SG-1 commit SHA;
- accepted eye indices;
- positive fixture test result;
- no-face fixture test result;
- SG-2 output example;
- reviewer name;
- unresolved limitations.
