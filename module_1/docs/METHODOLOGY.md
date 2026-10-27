# SG-1 Methodology

## Goal

Detect the driver's face.
Find facial landmarks.
Send stable geometry to SG-2 and SG-3.

SG-1 does not classify drowsiness.

## Work completed

- Selected MediaPipe Face Landmarker.
- Configured one driver face.
- Added video input.
- Added webcam capture.
- Added frame IDs and timestamps.
- Added normalized landmarks.
- Added a landmark-derived face box.
- Added `OK` and `NO_FACE` outputs.
- Added JSONL output.
- Added failure logging.
- Added annotated video output.
- Added manual box evaluation.
- Tested three configurations.
- Processed five nighttime clips.
- Processed 2,932 frames.
- Labeled 20 frames.
- Recorded desktop latency and FPS.
- Selected 192 px as a provisional speed candidate.
- Created a verified Python environment.
- Downloaded and hashed the model.
- Added schema version and topology fields.
- Added a machine-readable JSON Schema.
- Added positive, no-face and invalid fixtures.
- Added SG-2 and SG-3 adapter helpers.
- Added automated tests.
- Added setup and experiment verification commands.
- Verified a generated fallback video under all three configurations.

## Current experiment

The same clips are used for every configuration.
The same frames are used for every configuration.
The model stays the same.
Only thresholds or input size change.

This controls the comparison.

## Measurements

- Face coverage.
- Frames with landmarks.
- No-face frames.
- Mean inference time.
- P95 inference time.
- End-to-end FPS.
- Face-box IoU.
- Precision.
- Recall.
- F1.

Coverage is not accuracy.
Landmark presence is not landmark accuracy.
Desktop FPS is not Jetson FPS.

## Current result

- All configurations detected 2,931 of 2,932 frames.
- The missed frame was black.
- All configurations scored 0.85 F1 on 20 labeled frames.
- The 192 px configuration was faster on the desktop.
- The label set is too small for a final accuracy claim.

## Work still required

- Freeze the V1 interface with SG-2 and SG-3.
- Connect SG-1 to SG-2.
- Connect SG-1 to SG-3.
- Replace SG-3 synthetic input with real landmarks.
- Update SG-4 validity handling.
- Update SG-6 mock data.
- Test no-face negative frames.
- Run an approved raw-video midterm demo.
- Test profile pose.
- Test glasses.
- Test occlusion.
- Test daytime conditions.
- Test motion blur.
- Increase manual labels.
- Review labels with a second person.
- Measure landmark quality.
- Run on Jetson.
- Measure Jetson FPS and latency.
- Measure memory and compute use.

## Method selection rule

Do not select a method because it is convenient.
Use measured accuracy and speed.
Retest the selected method on Jetson.
Keep a working fallback.

## Midterm evidence

Show real execution.
Show the input.
Show the overlay.
Show one output record.
Show the comparison table.
Show a failure case.
Show the interface contract.
Show one downstream contract test.
State all limits clearly.
