# SG-1 Midterm Presentation Guide

## What to show

1. Open the SG-1 README and state the input: a video frame and timestamp.
2. Run an approved driver video using [MIDTERM_DEMO.md](MIDTERM_DEMO.md), then show an annotated output with the face ROI and landmarks. The five downloaded clips were run locally on 2026-10-27; confirm permission for the clip you choose to present.
3. Show a generated `OK` JSONL record and the real black-frame [`NO_FACE` record](../results/midterm_real_20261027/example_no_face.json); point to frame ID, timestamp, face box, normalized landmarks, and status.
4. Show the full-video [comparison table](../results/midterm_real_20261027/aggregate_comparison.csv) and [primary/backup decision](MIDTERM_METHOD_DECISION.md).
5. State the known limitations, then show the draft [interface contract](INTERFACE_CONTRACT.md), schema and fixtures.

## A 90-second explanation

“SG-1 receives each driver-camera frame and timestamp. OpenCV reads and resizes the frame, and a pretrained MediaPipe Face Landmarker returns one face mesh. Our code uses the landmarks to build a face rectangle and returns normalized landmark points, frame identity, time and status. SG-2 and SG-3 can use these geometry records for eye and mouth analysis; SG-1 itself does not decide drowsiness.

“We compared three configurations on the same five saved clips. All three returned a face on 2,931 of 2,932 frames; the only NO_FACE frame was black. On this desktop, 192 pixels at 0.50 thresholds processed 90.8 frames per second versus 77.3 for the 256-pixel baseline, so 192 pixels is our provisional primary configuration. The 256-pixel baseline is a tested backup configuration using the same model, not an independent backup model.

“Against 20 AI-assisted face-box estimates that a person has not independently reviewed, all three settings had 0.85 precision, recall and F1 at IoU 0.50. Those are provisional box-agreement scores, not proven landmark or overall accuracy. We still need independent label review, more varied conditions, and downstream agreement on the interface.”

Use the recorded numbers only for the tested desktop run. Both SG-1 members should explain their own actual contribution accurately and be able to answer questions about the shared module.

## Likely questions

- **Did we train MediaPipe?** No. We use a pretrained model bundle and wrote the surrounding frame processing, interface, configuration comparison, evaluation and demonstration code.
- **What changes between configurations?** The input frame's long-side size or the detection, presence and tracking thresholds. These are three configurations of the same model, not three separately trained models. The 0.35 experiment changes all three thresholds together.
- **What is the threshold?** A minimum acceptance cutoff used by the task. It is not the per-face observed confidence; the interface returns `null` for that field.
- **Why normalize coordinates?** Landmark x/y values are fractions of image width/height, making them reusable across frame sizes. Our code maps the face ROI back to original-frame pixels.
- **What is coverage?** The fraction of frames where a face mesh was returned. It does not establish that the selected face is always the driver or that landmarks are accurate.
- **What is IoU?** The intersection area of the predicted and reference boxes divided by their union area. At 0.50 or higher, the evaluator counts a match. The reference boxes are provisional AI-assisted estimates awaiting human review.
- **Why are there three FP and three FN?** Three predicted boxes overlapped their provisional references by less than 0.50; each such pair is counted once as FP and once as FN. The three cases are not proven model failures without reference review.
- **What is the failure example?** One entirely black frame returned `NO_FACE`. Additional pose, occlusion, no-face and landmark-accuracy tests are needed.
- **What happens to missing faces?** SG-1 writes `NO_FACE`, a null rectangle and an empty landmark list. Downstream modules should treat that frame as invalid or unknown, not as evidence of eye closure or yawning.
