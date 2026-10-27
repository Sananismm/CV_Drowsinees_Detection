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
