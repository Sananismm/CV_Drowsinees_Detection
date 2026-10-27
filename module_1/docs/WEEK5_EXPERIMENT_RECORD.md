# Week 5 Experiment Record - SG-1

**Student:** Muhammad Bilal Maqbool (470990)
**Project:** Driver Drowsiness Monitoring
**Task:** Compare face/landmark detector configurations.

## Question

How do input resolution and detector acceptance thresholds affect face coverage, labeled box detection precision/recall, landmark availability, latency and processing speed on the same driver-facing clips?

## Baseline and alternatives

Use the configs in `configs/experiment.json`. Keep clip, frame sampling, lighting/pose content and evaluation labels identical across runs. The baseline is `baseline`; the alternatives are `lower_threshold` and `lower_resolution`.

## Results

Ran all three configurations on the same five driver-facing sample videos found in Downloads (`P10427801_na`, `P1043061_na`, `P1043079_na`, `P1043080_na`, `P1043128_na`). All are 1920x1080 at 25 FPS. Each full video was processed (2,932 frames total; approximately 117.3 seconds of footage). The tracked combined table is `results/downloaded_samples/aggregate_comparison.csv` and the qualitative check image is `results/downloaded_samples/qualitative_review.png`. The original per-frame prediction streams and detailed per-clip metric JSON files were local run artifacts and are not included in the repository; regenerate them from the videos and reference CSVs when needed.

Coverage means frames where the detector emitted a face and landmarks; it is not precision/recall and does not verify that the returned face is the driver. The one frame with no returned face (frame 576 in `P1043079_na`) is entirely black at the end of the clip. The same frame was missed under all three settings. An AI assistant visually estimated four reference boxes per clip (20 frames total); see `results/downloaded_samples/ground_truth/` and `docs/MANUAL_ANNOTATION_PROTOCOL.md`. No independent human review of these reference boxes is documented. They support exploratory box agreement only, not independently validated accuracy. Landmark coordinate accuracy is not measured.

### Automated smoke test (not a driver evaluation)

Before the driver-facing samples were located, the complete pipeline was smoke-tested on a generated 20-frame, 320x240 black video to check model loading, video decoding, prediction serialization, failure logging, CSV/metadata generation, and annotated-video writing. As expected for a clip with no face, each configuration found 0/20 faces and reported 0% coverage. The original `results/smoke_no_face/` artifacts were local-only and are not tracked in the repository. These recorded desktop timings are smoke-test timings only and must not be used to compare driver-face performance.

| Configuration | Smoke-test faces | Smoke-test mean latency (ms) | Smoke-test end-to-end FPS |
|---|---:|---:|---:|
| Baseline | 0/20 | 1.536 | 452.760 |
| Lower threshold | 0/20 | 1.406 | 512.722 |
| Lower resolution | 0/20 | 1.304 | 544.412 |

### Driver-facing sample comparison

| Configuration | Faces / frames | Coverage | Mean inference (ms) | p95 inference (ms) | Combined end-to-end FPS |
|---|---:|---:|---:|---:|---:|
| Baseline (256 px / 0.50) | 2,931 / 2,932 | 99.966% | 8.249 | 8.861 | 77.081 |
| Lower threshold (256 px / 0.35) | 2,931 / 2,932 | 99.966% | 8.132 | 8.682 | 78.362 |
| Lower resolution (192 px / 0.50) | 2,931 / 2,932 | 99.966% | 6.274 | 6.746 | 92.193 |

### Provisional face-box agreement

| Configuration | Annotated frames | TP | IoU-mismatch FP | IoU-mismatch FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Baseline | 20 | 17 | 3 | 3 | 0.85 | 0.85 | 0.85 |
| Lower threshold | 20 | 17 | 3 | 3 | 0.85 | 0.85 | 0.85 |
| Lower resolution | 20 | 17 | 3 | 3 | 0.85 | 0.85 | 0.85 |

Evaluation uses one provisional AI-assisted driver-face reference box per labeled frame and an IoU threshold of 0.50. The three FP/FN counts are paired below-threshold overlaps between a prediction and its reference box, not three unrelated hallucinated faces and three separate absent detections. Neither a below-threshold match nor the reported 0.85 scores establish validated detector accuracy without independent reference review. The pooled summary is tracked in `results/downloaded_samples/manual_box_metrics_summary.csv`; per-clip `box_metrics_<config>.json` files were local-only and must be regenerated if unavailable. All 20 references contain a face, so they do not measure performance on no-face negatives.

## Interpretation and Week 6 recommendation

Preliminary recommendation from these five samples and 20 provisional reference boxes: use **192 px / 0.50** as the Week 6 speed candidate. It retained the same observed coverage and provisional box-agreement metrics on this small set while increasing combined desktop throughput by about 19.6% versus the 256 px baseline. Lowering thresholds to 0.35 did not improve observed coverage or box agreement. This is not a final accuracy choice: the clips are a small, mostly night-driving sample, the reference boxes are not independently reviewed, and reported FPS is from this desktop, not the target embedded board. Validate profile views, occlusion, glasses, daytime/lighting changes and the actual target hardware before freezing the setting.

Remaining evaluation work: have a human independently review the existing references, then expand labels to cover more clips/frames, no-face negatives and challenging conditions; run the same evaluation on the group's agreed common clips and target hardware; compare against the actual Week 4 baseline if it differs from this MediaPipe configuration.

- Which setting improved reference-box recall? **None on this 20-frame provisional set; all were 0.85.**
- Which setting was fastest? **192 px was fastest in this desktop run. A returned face was not independently checked on every frame, so coverage alone cannot establish that no visible driver face was missed.**
- Were landmarks stable/available on every detected face? **Landmarks were emitted on all detected frames; coordinate accuracy/stability still needs labeled or broader temporal review.**
- Which failures are model limits, and which are input/lighting/pose issues? **The only recorded `NO_FACE` frame was a fully black end frame. Three provisional box comparisons had IoU below 0.50, but the references need independent review before attributing those mismatches to the model.**
- Week 6 candidate: **192 px / 0.50, provisional pending broader-condition and target-hardware validation.**

Do not report face coverage as precision/recall. Do not report desktop FPS as Jetson FPS. Add Jetson observations after running on the actual target.
