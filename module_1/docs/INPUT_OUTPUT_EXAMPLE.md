# SG-1 Visual Input/Output Example

The image at `../results/downloaded_samples/qualitative_review.png` is a contact sheet of five driver-facing sample frames with the automated SG-1 predictions drawn over each input frame.

- **Input:** a single frame decoded from a sample driver-facing video.
- **Model output:** 478 MediaPipe Face Landmarker points (yellow) and a green face ROI rectangle computed from the minimum/maximum landmark coordinates.
- **What the image demonstrates:** the detector's visual output and the relationship between the face ROI and facial landmark mesh.
- **What it does not demonstrate:** drowsiness classification, eye/yawn results, temporal analysis, alert logic, or ground-truth accuracy by itself.

The contact sheet is a qualitative example. Quantitative evidence is separate: the configuration comparison is in `../results/downloaded_samples/aggregate_comparison.csv`; manual box scores are in `../results/downloaded_samples/manual_box_metrics_summary.csv` and use the CSV labels in `../results/downloaded_samples/ground_truth/`.

To regenerate annotated output locally from an approved source video, run from `module_1/`:

```powershell
python scripts\run_experiment.py `
  --input "C:\path\to\approved_driver_video.mp4" `
  --output-dir results\demo `
  --max-frames 100 `
  --save-video
```

This writes one annotated MP4 per configuration and a comparison table. It does not upload the input video. The repository is public and the included contact sheet shows visible faces; confirm that publishing those sample frames is allowed by the source dataset/team before wider redistribution.
