# SG6 Face Detector Benchmark

## Test Platform
- Device: NVIDIA Jetson Orin Nano
- OS: Ubuntu 22.04 / Jetson Linux R36.4.3
- Python: 3.10
- OpenCV: 4.14.0 (isolated virtual environment)
- Input: 150 recorded webcam frames, 640x480

## Results

| Metric | Haar Cascade | YuNet |
|---|---:|---:|
| Frames processed | 150 | 150 |
| Frames with faces | 150 | 150 |
| Face coverage | 100% | 100% |
| Mean inference latency | 31.65 ms | 17.89 ms |
| Inference-only FPS | 31.59 | 55.91 |

## Interpretation

YuNet achieved approximately 1.77x the inference throughput
of Haar Cascade on the same recorded frames.

Both detectors reported at least one face in every frame.

Face coverage is not equivalent to precision, recall, or
ground-truth detection accuracy.

The benchmark excludes camera acquisition, image decoding,
and downstream landmark/eye-state processing.

## Decision

YuNet is selected as the current SG6 face-detection candidate,
subject to further testing under varied lighting and poses.

YuNet's five keypoints are insufficient to calculate SG2 EAR.
A separate detailed facial-landmark model is still required.

## Reproducibility

Run inside sg6-yunet-env:

python embedded_6/Integration/benchmark_detectors.py

The benchmark dataset contains identifiable camera frames.
These frames must remain private and must not be committed.

## Re-run on 2026-10-28

The existing 150 private frames were rerun on this Jetson with OpenCV 4.14.0: Haar 150/150 frames, 40.74 ms mean and 24.55 inference FPS; YuNet 150/150, 25.02 ms and 39.96 inference FPS. These are separate observed timings, not a guarantee; operating conditions can affect them. The same limitations above apply. The machine reported Jetson Linux R36.4.7 at this audit. The images and generated JSON are ignored and remain local.

## Additional rerun on 2026-10-28

Same 150 private frames, 640×480, five warm-up calls per detector, OpenCV 4.14.0 default CPU: Haar 40.32 ms mean (24.80 inference FPS), YuNet 24.23 ms (41.27 inference FPS); both covered 150/150 frames. Timings include Haar grayscale conversion or YuNet input-size setup, exclude image decoding and capture. Configuration is recorded in ignored `evidence/detector_benchmark.json`. This is not a labelled accuracy study or live processing FPS.
