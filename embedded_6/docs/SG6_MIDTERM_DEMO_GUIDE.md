# SG6 Midterm Demonstration Guide

> **Repository availability:** This report describes a Jetson worktree snapshot. The revised demo, its tests, and `embedded_6/integrated/` were local and uncommitted at the time of publication and are not present on `main`; commands that use those files require that local snapshot. Do not assume a fresh `main` checkout can run them.

Evidence reviewed 28 October 2026. The primary demonstration detects faces only. It does not calculate EAR or drowsiness. Run commands from a Jetson terminal on the host, not a sandbox that masks /dev/video*.

## Before the examiner

- Power the Jetson correctly, connect the USB webcam, and verify `ls -l /dev/video*`. The USB camera was enumerated but this session could not open the host device from its sandbox.
- Close applications using the camera; ensure the current user can access the chosen device. Check `id` and device permissions/ACLs. Try another index only if it is a capture endpoint.
- Confirm `~/sg6-yunet-env/bin/python -c 'import cv2,numpy; print(cv2.__version__, numpy.__version__)'` and `ls -l embedded_6/models/face_detection_yunet_2023mar.onnx` after changing to the repository. A working graphical display and Tk are needed for windows.
- Pre-run the tests and run each detector with and without a face. Keep private frames and metrics out of Git. Have the benchmark table ready as a fallback.

## Commands

```bash
cd ~/CV_Drowsinees_Detection
source ~/sg6-yunet-env/bin/activate
python embedded_6/Integration/run_midterm_demo.py --detector yunet
# Quit with q or Escape. To run Haar, use:
python embedded_6/Integration/run_midterm_demo.py --detector haar
# Headless; use --camera 1 if the actual capture device is video1:
python embedded_6/Integration/run_midterm_demo.py --detector yunet --headless --duration 60 --save-metrics
# Benchmark (requires the private 150 frame_*.jpg files):
python embedded_6/Integration/benchmark_detectors.py
# Demo tests:
python -m unittest discover -s embedded_6/Integration -p test_midterm_demo.py -v
# Synthetic integration tests, separate environment:
embedded_6/.venv-integrated/bin/python -m unittest discover -s embedded_6/integrated/tests -v
python3 embedded_6/Integration/validate_interfaces.py
```

The activation is optional if commands use `~/sg6-yunet-env/bin/python` explicitly. The graphical display shows boxes, and YuNet adds five points and scores. Headless output should show detector, actual size, frame number, face count, status, confidence when available, latency and cumulative processing FPS. A no-face frame is expected to show NO FACE. Metrics go to ignored embedded_6/evidence/ unless --output-dir is specified. Check the exit status and JSON; zero frames and exit_status 1 is an error, not a successful test.

## Troubleshooting

| Symptom | Action |
|---|---|
| Camera cannot open | Verify device nodes, permissions and competing processes on the host; try `--camera 1` only when appropriate. Sandbox device masking can prevent access even when USB enumeration succeeds. |
| `cv2.data` missing | Use the isolated interpreter: system OpenCV 4.5.4 reproduced this error in the Haar tests. |
| No GUI or cannot connect display | Use --headless or open a local graphical session with Tk. |
| YuNet model missing | Restore the tracked model from the repository's model source; do not substitute unknown weights. |
| Benchmark finds fewer than 150 frames | Obtain the original private dataset; do not create or publish substitute images and do not claim a rerun. |
| Low or no detections | Check framing and light, then state that coverage is not accuracy. |
| Import error in integration tests | Use the separately prepared integrated environment; see [setup](SG6_SETUP_AND_REPRODUCIBILITY.md). |

## Five-to-seven-minute sequence

1. (1 min) Describe SG6, hardware and the difference between live face detection and the separate experimental pipeline.
2. (2 min) Show YuNet live if verified; demonstrate face/no-face, keypoints, latency, FPS and clean exit. Switch to Haar by restarting with its option.
3. (1 min) Show saved private metrics and distinguish end-to-end processing from timed detector calls.
4. (1 min) Explain the identical-frame comparison: 40.32 vs 24.23 ms; both 150/150 coverage, not labelled accuracy.
5. (1–2 min) Run synthetic integration tests and explain SG1→SG2/SG3→SG4→SG5, missing evidence and remaining live validation.

## Examiner questions

- **Is this a drowsiness detector?** The primary demo is face detection only. The separate integrated pipeline is experimental and is not a validated live alert system.
- **Why YuNet?** Faster on this particular recorded comparison and provides five keypoints; it is not proven more accurate on this dataset.
- **What happens without a face?** The detector reports NO FACE; downstream synthetic tests check insufficient evidence.
- **What is FPS?** Demo processing FPS includes acquisition and loop work; benchmark inference FPS excludes capture and decoding.
- **Can the five points produce EAR?** No; SG2 requires detailed points around each eye.

See [viva preparation](SG6_VIVA_PREPARATION.md) for additional questions and [technical report](SG6_MIDTERM_TECHNICAL_REPORT.md) for evidence limitations.
