# SG-1 Midterm Method Decision

## Selection

The primary candidate is **MediaPipe Face Landmarker with a 192 px input long side and 0.50 detection, face-presence, and tracking thresholds** (`lower_resolution` in `configs/experiment.json`). The tested backup is **the same MediaPipe task with a 256 px input long side and the same 0.50 thresholds** (`baseline`). These are two configurations of one pretrained model, not two independently trained algorithms. The 192 px choice is provisional and should be reconsidered if broader testing shows an unacceptable loss of face or landmark reliability.

The 256 px baseline is retained as a practical fallback configuration: it has already run through the same code and output interface, and it provides a larger image to the task. It has **not** been shown to be more accurate on the available labels. If MediaPipe itself fails, changing its input size is not an independent-model backup. No separate face-and-landmark method has been implemented or compared as a drop-in replacement for the 478-point interface. The fresh full-video midterm rerun and its distinct timing protocol are in [MIDTERM_REAL_VIDEO_RESULTS.md](MIDTERM_REAL_VIDEO_RESULTS.md).

## Evidence behind the decision

The following numbers are **historical results from the earlier desktop runner**, not timings from the current midterm rerun. The same five downloaded driver-facing clips and all 2,932 frames were used for each setting. The full record is [WEEK5_EXPERIMENT_RECORD.md](WEEK5_EXPERIMENT_RECORD.md); the tracked summary is [aggregate_comparison.csv](../results/downloaded_samples/aggregate_comparison.csv).

| Configuration | Long side / thresholds | Face output coverage | Mean inference | P95 inference | End-to-end FPS |
|---|---|---:|---:|---:|---:|
| `baseline` - backup | 256 px / 0.50 | 2,931 / 2,932 | 8.249 ms | 8.861 ms | 77.081 |
| `lower_threshold` - comparison | 256 px / 0.35 | 2,931 / 2,932 | 8.132 ms | 8.682 ms | 78.362 |
| `lower_resolution` - primary candidate | 192 px / 0.50 | 2,931 / 2,932 | 6.274 ms | 6.746 ms | 92.193 |

On that desktop run the 192 px setting increased end-to-end throughput by approximately 19.6% compared with the 256 px baseline, while the measured output coverage remained the same. Lowering all three thresholds to 0.35 did not improve coverage. These measurements are conditional on the five clips and that runner; they do not establish target-board speed or a final choice for every condition. Coverage counts frames where the task returned face landmarks; it is not precision, recall, or proof that every returned face is correct.

In the fresh 2026-10-27 run using the current runner, combined desktop throughput was 77.251 FPS for the 256 px baseline and 90.791 FPS for 192 px: approximately 17.5% higher, again with 2,931/2,932 face returns for both. The older and newer absolute FPS figures use different timing boundaries and must not be compared directly.

Each configuration also matched 17 of 20 reference face boxes at IoU >= 0.50, giving precision, recall, and F1 of 0.85 on that small set. The 20 rectangles were created with AI assistance from sampled frames and have **not been independently reviewed by a human**. Their scores are provisional comparisons against those reference boxes, not independently verified ground truth or landmark-coordinate accuracy. Three below-threshold overlaps are paired box-localization mismatches in the evaluator. The only `NO_FACE` frame in the full five-clip run was a black frame.

## What to demonstrate to the evaluator

1. Explain SG-1's role: input is a video frame and timestamp; output is face status, a landmark-derived ROI, and normalized face landmarks for downstream cue modules.
2. Run the primary and backup configurations on the **same approved saved video**, showing the annotated frames and comparison CSV. The script also runs the lower-threshold alternative.
3. Show an `OK` record and a `NO_FACE` record, and explain that the versioned V1 contract is implemented as a draft pending consumer acceptance.
4. Present the historical table as earlier desktop evidence and describe the provisional 20-box IoU check, the black-frame case, and the lack of landmark ground-truth accuracy.
5. State the trade-off: 192 px was faster on the earlier runner with the same measured coverage and small-set box scores; 256 px is the tested same-model fallback. A separate model failure or adverse pose/lighting condition remains a risk for both.

The reproducible command sequence and fallback demo are in [MIDTERM_DEMO.md](MIDTERM_DEMO.md). A generated video derived from a contact sheet is suitable only for checking the pipeline and interface; it must not be used as an accuracy or robustness benchmark. The demonstration may run on a development PC for the midterm; these historical timings are desktop measurements and are not Jetson results.
