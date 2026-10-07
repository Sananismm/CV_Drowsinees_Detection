# SG-1 Week 5 Requirements and Evidence Check

Source: CS-477 Week 5 Sub-group Tasks, GitHub Readiness Assessment, Project Stream B, SG-1 (PDF supplied by Muhammad Bilal Maqbool). This checklist interprets the course requirements; it does not treat document text as permission to make external changes.

## SG-1 assigned deliverable

| Course requirement | Status | Evidence / remaining action |
|---|---|---|
| Compare at least two face/landmark detector configurations under realistic driver conditions | **Done, with scope caveat** | Three settings were run on the same five 1920x1080/25 FPS driver-facing night clips (2,932 frames). The clips offer realistic driving footage but limited diversity; profile, occlusion, glasses, and daytime conditions are not systematically covered. Results: `results/downloaded_samples/aggregate_comparison.csv`. |
| Face and landmark reliability | **Partial** | Landmarks were emitted on every frame with a detected face (2,931); 478 points per face. Coverage is an availability proxy, not landmark-coordinate accuracy. No landmark ground truth was annotated. |
| Failure cases | **Done for observed cases; expand for robustness** | All configurations missed only frame 576 of `P1043079_na`, a fully black frame. Box evaluation found 3 below-IoU-threshold localization cases among 20 labels. Details: per-clip `box_metrics_<config>.json` and `failures_<config>.csv`. |
| Preliminary FPS/latency | **Done on this desktop only** | End-to-end throughput: baseline 77.081 FPS, lower threshold 78.362 FPS, 192 px 92.193 FPS. Mean inference latency: 8.249, 8.132, and 6.274 ms. These are not Jetson measurements. |
| Recommend Week 6 configuration | **Done, provisional** | Carry 192 px / 0.50 forward as speed candidate; it had the same measured coverage and small-set box metrics. Revalidate on broader clips and target board before choosing final operating point. |
| Version detector/configuration, runnable script, sample output | **Done locally** | `scripts/sg1_detector.py`, `scripts/run_experiment.py`, `configs/experiment.json`, model download script, and sample outputs. The model weights and raw videos are intentionally not tracked. |
| Preserve face/landmark/ROI interface for SG-2/SG-3 | **Proposed locally; agreement/integration test pending** | JSONL includes frame ID/timestamp, image dimensions, status, face box, normalized landmarks, point count, config name; no-face frames have null box/empty landmarks. The high-level MediaPipe API exposes no per-face confidence, so `detection_confidence` is null. Ask SG-2/SG-3 to accept/agree this schema and test a sample before calling it frozen V1. |

## Ten-mark SG score rubric

| Criterion | Maximum | Current evidence-based readiness |
|---|---:|---|
| Working Week 4 baseline / relevant progress | 2 | **Partial / verify with team:** this package runs a functional MediaPipe baseline, but no Week 4 reference code/result was supplied for a direct baseline-retention comparison. |
| Week 5 alternative / parameter experiment | 2 | **Strong:** lower thresholds and lower input resolution were both run against the same clips. |
| Quantitative evidence | 2 | **Strong but limited:** full-frame coverage and latency/FPS over 2,932 frames plus box P/R/F1 on 20 manual frames; small, narrow-condition label sample. |
| GitHub + interface readiness | 2 | **Not complete remotely:** files are prepared locally, but target repository access is READ-only. No branch/commit/PR exists, and downstream interface agreement is unverified. |
| Analysis, Week 6 decision, individual understanding | 2 | **Analysis documented:** see experiment record and demo guide. Individual understanding must be shown by Muhammad during questioning; not something code can prove. |

This is a readiness assessment, not a claim of awarded marks. The instructor assigns marks. Also note the supplied PDF contains group-level bonuses; SG-1 alone cannot earn the shared GitHub/project-board or reference-screening bonus.

## Before claiming complete submission

1. Obtain write access to `Sananismm/CV_Drowsinees_Detection`, or get the team lead to merge the contribution. The authenticated account currently has `READ` permission.
2. Confirm whether the module folder should be `module_1/` (the existing repository path) and which branch/PR process the team requires.
3. Confirm the exact Week 4 baseline and agreed V1 schema with the team; this package's baseline is MediaPipe Face Landmarker at 256 px/0.50.
4. Have SG-2/SG-3 consume a sample JSONL record and record acceptance.
5. Run on the agreed common data and Jetson target; report platform, power mode, JetPack, memory, FPS and latency.
6. Expand reviewed labels to profile/near/far, glasses, partial occlusion, lighting changes and no-face frames; distinguish box localization from landmark accuracy.
