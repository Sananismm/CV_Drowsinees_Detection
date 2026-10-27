# SG-1 Test Plan

## Test levels

1. Static checks.
2. Unit tests.
3. Interface tests.
4. Video experiments.
5. Robustness tests.
6. Jetson tests.

## Static checks

- [x] Every Python file compiles.
- [x] Required imports succeed.
- [x] `pip check` reports no conflicts.
- [x] JSON configuration parses.
- [x] Markdown links resolve.

## Unit tests

- [x] Resize preserves aspect ratio.
- [x] Small frames are not enlarged.
- [x] Timestamp is forced to increase.
- [x] Face box is clamped to image bounds.
- [x] `NO_FACE` has a null box.
- [x] `NO_FACE` has an empty landmark list.
- [x] Landmark count matches list length.
- [x] IoU is 1 for identical boxes.
- [x] IoU is 0 for disjoint boxes.
- [x] Empty ground truth is handled.

## Interface tests

- [x] Positive fixture passes schema validation.
- [x] No-face fixture passes schema validation.
- [x] Missing field fails validation.
- [x] Wrong schema version fails validation.
- [x] Wrong topology fails validation.
- [x] Truncated landmarks fail consumer validation.
- [ ] SG-2 accepts a real SG-1 record.
- [ ] SG-3 accepts a real SG-1 record.
- [ ] SG-6 loads both standard fixtures.

## Video experiment tests

- [x] All configurations use the same video.
- [x] All configurations use the same frames.
- [x] Every processed frame creates one output record.
- [x] Failure CSV matches `NO_FACE` records.
- [x] Metadata records package versions.
- [x] Annotated video dimensions match the source.
- [x] Output FPS accounts for frame stride.
- [x] Aggregate values can be regenerated.

## Robustness set

- [ ] Frontal driver.
- [ ] Left head turn.
- [ ] Right head turn.
- [ ] Head up.
- [ ] Head down.
- [ ] Glasses.
- [ ] Partial face occlusion.
- [ ] Low light.
- [ ] Bright light.
- [ ] Strong shadow.
- [ ] Motion blur.
- [ ] Driver near camera.
- [ ] Driver far from camera.
- [ ] Empty seat.
- [x] Fully black frame.
- [ ] More than one visible person.

## Metrics

- Face coverage.
- Precision.
- Recall.
- F1.
- IoU distribution.
- Landmark availability.
- Landmark temporal stability.
- Mean latency.
- P95 latency.
- End-to-end FPS.
- Failure count by condition.

## Jetson tests

- [ ] Model loads on the target image.
- [ ] Camera input opens.
- [ ] Saved-video input opens.
- [ ] Mean and P95 latency are recorded.
- [ ] FPS is recorded.
- [ ] CPU/GPU use is recorded.
- [ ] Memory use is recorded.
- [ ] Power mode is recorded.
- [ ] Thermal throttling is checked.
- [ ] 192 px and 256 px are compared.

## Midterm acceptance

- [x] Clean environment setup succeeds locally.
- [x] Model hash matches.
- [x] Generated saved-video demonstration succeeds.
- [x] Face and landmarks are rendered in annotated output.
- [x] Machine-readable output is generated and validated.
- [x] No-face behavior is generated and validated.
- [x] Comparison evidence is generated and verified.
- [x] Interface contract, schema and fixtures exist.
- [ ] At least one downstream contract test passes.

## Evidence policy

Record commands and results.
Keep the input identity clear.
Keep raw private footage out of Git.
Do not replace execution evidence with screenshots alone.

Checked items describe the 2026-10-21 local Windows run.
They do not imply downstream acceptance, approved-video coverage or Jetson execution.
