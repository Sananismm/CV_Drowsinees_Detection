# Manual Face-Box Annotation Protocol - SG-1

**Reference-box provenance:** The 20 boxes were estimated by an AI assistant from visual inspection of sampled frames. No independent human review is recorded.
**Purpose:** Create a small provisional reference set for exploratory face-box agreement.

## What was labeled

One primary, visible driver's face per frame was enclosed in an axis-aligned rectangle. The rectangle covers the visible face from forehead/temples to chin/jaw; it excludes the neck, shoulders, and the rest of the body. Coordinates are pixel coordinates in the original 1920x1080 image, with `x1,y1` at the top-left and `x2,y2` at the bottom-right. A box file has columns `frame_idx,x1,y1,x2,y2`.

Four approximately evenly spaced frames were selected from each of the five clips (20 frames total). The assistant estimated the boxes from unannotated source-frame contact sheets rather than detector overlays for those frames. Exact frame indices and boxes are in the five CSV files under `results/downloaded_samples/ground_truth/`. These are AI-assisted reference estimates, not independently reviewed human ground truth.

## How scores are calculated

For each labeled frame, the predicted face box is compared with the provisional reference box using intersection over union (IoU). A prediction counts as a match when IoU is at least 0.50. A below-threshold overlap is reported by the evaluator as one IoU-mismatch false positive and one IoU-mismatch false negative for that frame. Precision, recall, and F1 are computed relative to these reference estimates. The scores describe agreement with provisional face boxes on this sample; they are not independently validated detection accuracy and do not evaluate facial landmarks, yawning, or drowsiness classification.

## Limitations

Twenty frames are a small exploratory set, not a representative benchmark. All 20 references contain a face, so this set cannot measure false-alarm performance on no-face negatives. The clips are mostly nighttime driving and do not systematically cover profile poses, occlusion, eyewear, varied lighting, or multiple faces. A different annotator or box-tightness convention may shift IoU around the 0.50 threshold. Have a person independently review the reference boxes, document any corrections, and expand the labels before making an accuracy claim.
