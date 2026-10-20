# Manual Face-Box Annotation Protocol - SG-1

**Annotator:** Muhammad Bilal Maqbool (470990)
**Purpose:** Create a small ground-truth set for evaluating face-box detection.

## What was labeled

One primary, visible driver's face per frame was enclosed in an axis-aligned rectangle. The rectangle covers the visible face from forehead/temples to chin/jaw; it excludes the neck, shoulders, and the rest of the body. Coordinates are pixel coordinates in the original 1920x1080 image, with `x1,y1` at the top-left and `x2,y2` at the bottom-right. A box file has columns `frame_idx,x1,y1,x2,y2`.

Four approximately evenly spaced frames were selected from each of the five clips (20 frames total). These frames were selected and labeled from unannotated source frames, without looking at detector overlays. Exact frame indices and boxes are in the five CSV files under `results/downloaded_samples/ground_truth/`.

## How scores are calculated

For each labeled frame, the predicted face box is compared with the manual box using intersection over union (IoU). A prediction counts as a match when IoU is at least 0.50. A below-threshold overlap is reported by the evaluator as one IoU-mismatch false positive and one IoU-mismatch false negative for that frame. Precision, recall, and F1 are computed from those matches and mismatches. This measures face-box localization on this sample; it does not evaluate facial landmarks, yawning, or drowsiness classification.

## Limitations

Twenty frames are a small exploratory set, not a representative benchmark. The clips are mostly nighttime driving and do not systematically cover profile poses, occlusion, eyewear, varied lighting, or multiple faces. A different annotator or box-tightness convention may shift IoU around the 0.50 threshold. Expand the labels and review annotation consistency before making a general accuracy claim.
