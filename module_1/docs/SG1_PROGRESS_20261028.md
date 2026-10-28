# SG-1 progress record

Status recorded: 28 October 2026. Scope: driver face and landmark detection in `module_1`, on branch `sg1`.

Subgroup owners: Muhammad Bilal Maqbool (470990, `b1L4L00`) and Sharjeel Hanif (455543, `MuhammadSharjeelHanif`). Ownership identifies responsibility for the task; commit attribution remains the repository's recorded authorship.

## Recorded repository milestones

| Recorded date | Evidence | Recorded author | Result |
|---|---|---|---|
| 7 Oct 2026 | [ea33abc](https://github.com/Sananismm/CV_Drowsinees_Detection/commit/ea33abc57a9ec6eda05bb4ba517994bc05872eff) | Muhammad Bilal Maqbool | Week 5 detector experiment |
| 7 Oct 2026 | [67ab7e4](https://github.com/Sananismm/CV_Drowsinees_Detection/commit/67ab7e4) | Muhammad Bilal Maqbool | Annotated SG-1 input/output example |
| 7 Oct 2026 | [7bd6bd1](https://github.com/Sananismm/CV_Drowsinees_Detection/commit/7bd6bd143eea6b834be8bb41384928deefe32f85), [2c9a505](https://github.com/Sananismm/CV_Drowsinees_Detection/commit/2c9a505795d25afcbb012a265d8903ad15f9f719) | Muhammad Sharjeel Hanif | Subgroup names and README updates |
| 21 Oct 2026 | [250bd52](https://github.com/Sananismm/CV_Drowsinees_Detection/commit/250bd52) | Muhammad Sharjeel Hanif | Landmark interface hardening, schema/fixture and verification work |
| 21 Oct 2026 | [fc2e023](https://github.com/Sananismm/CV_Drowsinees_Detection/commit/fc2e023), [f946306](https://github.com/Sananismm/CV_Drowsinees_Detection/commit/f946306) | Muhammad Sharjeel Hanif | Shared-branch workflow documentation |
| 27 Oct 2026 | [8ae431d](https://github.com/Sananismm/CV_Drowsinees_Detection/commit/8ae431d) | Muhammad Bilal Maqbool | Box-evaluation validation and full-video aggregation |
| 27 Oct 2026 | [e9b076f](https://github.com/Sananismm/CV_Drowsinees_Detection/commit/e9b076f) | Muhammad Bilal Maqbool | Midterm video evidence and demonstration documentation |
| 27 Oct 2026 | [400661c](https://github.com/Sananismm/CV_Drowsinees_Detection/commit/400661c) | Muhammad Bilal Maqbool | Live/saved-video preview and VS Code demonstration workspace |
| 27 Oct 2026 | [1b5b4b7](https://github.com/Sananismm/CV_Drowsinees_Detection/commit/1b5b4b791e37c8e75b7e3b58ee8529daffb5f951) | Muhammad Sharjeel Hanif | Driver samples added to the SG-1 branch |

These are existing commit records. This progress update records the current state and does not backdate new work.

## Completed implementation and experiment work

- MediaPipe video inference returns an original-frame face region, 478 normalized x/y landmarks and explicit `OK` / `NO_FACE` output.
- The draft `sg1.v1` interface, machine-readable schema, positive/no-face fixtures, setup verification and tests exist. This establishes implementation, not downstream acceptance.
- Three configurations have been compared on the same five downloaded videos: 2,932 frames per configuration. The full rerun and output verification are documented in [MIDTERM_REAL_VIDEO_RESULTS.md](MIDTERM_REAL_VIDEO_RESULTS.md).
- The 192 px / 0.50 configuration remains the provisional desktop primary. The measured 256 px / 0.50 option remains an available configuration fallback.
- Runnable webcam and saved-video previews, VS Code setup, repeatable benchmark commands and demonstration instructions exist. A previous camera smoke test read frames but returned no faces; it does not establish a successful person-present webcam demonstration.
- Midterm algorithm explanations and an eight-slide presentation have been prepared locally, including both presenters, actual outputs, results and limitations. Rehearsal is still to be completed by the presenters.

## Full-video configuration comparison, 27 October

| MediaPipe setting | Face-return records | Mean / p95 path latency | Desktop throughput |
|---|---:|---:|---:|
| 256 px / 0.50 | 2,931 / 2,932 | 7.963 / 8.512 ms | 77.251 FPS |
| 256 px / 0.35 | 2,931 / 2,932 | 7.956 / 8.483 ms | 78.274 FPS |
| 192 px / 0.50 | 2,931 / 2,932 | 6.189 / 6.681 ms | 90.791 FPS |

The runner includes detector setup/teardown, decoding, validation and result writing in throughput. Drawing and encoding are excluded. Threshold changes affect detection, face presence and tracking together. These are desktop measurements; coverage measures availability, not landmark accuracy or driver identity.

## Independent backup experiment, 28 October

OpenCV DNN SSD ResNet-10 plus dlib's 68-point regression-tree landmark predictor has been implemented and run locally. It has an explicit 68-point topology and a separate `sg1.dlib68.v1` schema. It does not invent 478 points or reuse MediaPipe indices. Publication of the runnable backup package and a downstream topology handoff remain review tasks.

| Method | Face-return records | Mean / p95 process latency | Application-loop FPS |
|---|---:|---:|---:|
| MediaPipe 192 px / 0.50 | 2,931 / 2,932 | 8.013 / 9.338 ms | 83.600 |
| OpenCV DNN + dlib 68 | 2,929 / 2,932 | 35.393 / 39.419 ms | 25.089 |

Both methods processed the same complete five videos sequentially. A common outer `process()` timer measures latency. Loop FPS includes capture open/decode, validation and JSONL writing, excluding model load and drawing. OpenCV threads were fixed at one; MediaPipe manages its own inference threads. Compare within this table because the October 27 runner has different timing boundaries.

CSV evidence: [aggregate comparison](../results/fallback_20261028/aggregate_comparison.csv), [per-clip comparison](../results/fallback_20261028/per_clip_comparison.csv), [input manifest](../results/fallback_20261028/input_manifest.csv).

## Preliminary failure review

| Controlled condition | MediaPipe 192 face returned | DNN + dlib face returned |
|---|---:|---:|
| Five original frames | 5 / 5 | 5 / 5 |
| Brightness multiplied by 0.10 | 0 / 5 | 0 / 5 |
| Gaussian blur, 101 by 101 | 1 / 5 | 1 / 5 |
| Face-region blackout | 0 / 5 | 0 / 5 |

One frame per clip was used, with a new detector per condition. These are small artificial cold-start tests; they do not measure tracking recovery or landmark accuracy. See [stress summary](../results/fallback_20261028/stress_summary.csv) and [per-case records](../results/fallback_20261028/stress_cases.csv).

In natural video, DNN returned `NO_FACE` at frames 218–219 of `P10427801_na`, where inspection shows a visible face tilted upward with an open mouth. This establishes a visible-face miss but does not isolate the causal pose/expression factor. Both methods returned `NO_FACE` on the actual black final frame of `P1043079_na`.

## Remaining work and blockers

| Work | State | Completion evidence needed |
|---|---|---|
| Independent review of reference boxes | Ready | Human reviewer and corrected/accepted labels. The existing 20 boxes are AI-assisted and unreviewed. |
| Landmark-point quality, no-face negatives and broader conditions | Ready | Ground-truth point/negative labels and results across pose, glasses, lighting and natural occlusions. |
| SG-2 / SG-3 interface acceptance | Blocked | Consumer-run fixtures, agreed indices/topology and recorded acceptance. |
| 68-point backup handoff | In review | Published runnable code, consumer adaptation and accepted topology mapping. |
| Person-present webcam demonstration and presenter rehearsal | Ready | Successful rehearsal by the presenters. |

No target-device performance, validated landmark accuracy, passenger-safe driver selection or completed downstream integration is claimed.
