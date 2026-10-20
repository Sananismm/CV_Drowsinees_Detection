# SG-1 Demo and Explanation (Muhammad Bilal Maqbool)

## Short live demonstration (about 3 minutes)

The checked local demo ran all three settings on the first 100 frames of `P10427801_na.mp4` and wrote annotated videos plus a comparison table under `results/demo/` in the full working package. It completed successfully. The 100-frame demo reported 100% face coverage for all three settings, with end-to-end throughput of 45.4, 47.0 and 49.6 FPS respectively. These are short-demo timings; use the full five-clip aggregate table for the experiment result. The GitHub-ready export intentionally omits video-derived demo outputs to avoid publishing driver footage; reproduce the demo locally with the command below and an approved video.

From this folder in PowerShell, repeat it with any approved video:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts\download_model.py
python scripts\run_experiment.py `
  --input "C:\path\to\approved_driver_video.mp4" `
  --output-dir results\demo `
  --max-frames 100 `
  --save-video
```

Show `results/demo/annotated_baseline.mp4` for the face rectangle and landmark overlay, then `results/demo/comparison.csv` to show the same clip was tested under three settings. Open `results/demo/predictions_baseline.jsonl` to show the machine-readable SG-1 output. Do not present the 100-frame demo as the full accuracy test or the desktop FPS as Jetson performance.

## How to explain the processing

1. **Input:** OpenCV decodes a video into frames and keeps each frame index and time.
2. **Resize:** The code scales each frame to a chosen maximum side (256 px or 192 px) while preserving aspect ratio. Lower resolution reduces model work, usually improving speed but potentially losing small face detail.
3. **Face and landmarks:** MediaPipe's pretrained Face Landmarker returns one face's mesh landmarks (478 points in these runs). This is not a drowsiness classifier; it only estimates face geometry.
4. **ROI and interface:** The code encloses the landmark coordinates in a face rectangle and maps landmarks to normalized `[0,1]` image coordinates. It writes one JSONL row per frame, including timestamp and status. Downstream eye/yawn groups can use this synchronized face/landmark result, subject to their agreement on the schema.
5. **Variants:** The baseline uses 256 px and 0.50 acceptance thresholds. One alternative lowers thresholds to 0.35; the other keeps 0.50 but reduces input size to 192 px. Same model and clips keep the comparison controlled.
6. **Evaluation:** Face coverage tells how often a face/mesh was returned; it is not accuracy. For accuracy, 20 manually boxed frames were compared to model boxes with IoU (intersection-over-union) at least 0.50. We did not annotate landmark points, so landmark coordinate accuracy is not measured.
7. **Decision:** On the available clips, 192 px retained the measured coverage and 20-frame box scores while improving end-to-end desktop speed by about 19.6% over baseline. Therefore it is the Week 6 speed candidate, not a final safety or accuracy decision.

## Suggested spoken summary

“My SG-1 module takes each driver-camera frame and returns a face region and facial landmarks for the later eye and mouth-analysis modules. I tested the same MediaPipe model with a baseline setting, a lower confidence threshold, and a lower input resolution on five videos. Across 2,932 frames, the detector returned a face on 2,931; the missed frame was entirely black. On 20 manually labeled frames, each setting scored 0.85 precision, recall, and F1 at IoU 0.50, so the sample is too small to claim general accuracy. The 192-pixel setting was about 19.6% faster on my desktop with the same observed results, so I recommend it as a Week 6 candidate. I still need broader pose/lighting tests, interface acceptance from SG-2/SG-3, and Jetson measurements.”

## Likely questions

- **What is normalization?** We map x/y landmark positions to fractions of the image width/height so downstream code can use positions consistently across different image sizes.
- **Why compare confidence thresholds?** A lower threshold may accept weaker detections and improve recall, but can also add false detections. It did not improve results in this sample.
- **What is IoU?** Intersection area divided by union area for the predicted and manual rectangles; 1 means perfect overlap and 0 means no overlap. We count a match at 0.50 or above.
- **Why not say this detects drowsiness?** SG-1 only supplies face/landmark geometry. SG-2/SG-3 derive eye/yawn cues; temporal analysis and decision modules must combine evidence before an alert.
- **Is it real-time on Jetson?** Not established. These timing results came from this desktop; the team's target board must be measured separately.
