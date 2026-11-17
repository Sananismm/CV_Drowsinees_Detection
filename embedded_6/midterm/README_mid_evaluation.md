# SG6 midterm evaluation README

**Muhammad Sanan Khan and Muhammad Sami | SG6 | CS-477**

**Version note:** Prepared after the evaluation from the repository's October
technical report, benchmark notes and SG6 source. The exact README shown during
the evaluation has not been confirmed. Replace this reconstruction with that
version if recovered; do not claim it is an unchanged evaluation artifact.

## Objective and architecture

Deploy and integrate the Driver Drowsiness Monitoring System on NVIDIA Jetson
Orin Nano 8 GB, with reproducible camera acquisition, detector comparison, runtime
measurement, and clear interfaces to the other subgroups.

```text
Camera -> SG6 acquisition -> SG1 face/detailed landmarks
                           -> SG2 eye cues + SG3 yawn cues
                           -> SG4 temporal analysis
                           -> SG5 decision -> SG6 display / planned hardware alert

Independent SG6 detector comparison: captured frame -> YuNet OR Haar -> face boxes
```

## Primary algorithm: YuNet through OpenCV FaceDetectorYN

The existing October comparison selected YuNet as the SG6 detector candidate.
It had a lower detector-call mean latency than Haar on the same 150 private
640x480 frames. Configuration: score threshold 0.6, NMS 0.3, top-k 5000, CPU
default. The checked-in ONNX model is `face_detection_yunet_2023mar.onnx`.
YuNet emits boxes, scores and five keypoints. Those points cannot compute SG2's
six-point Eye Aspect Ratio; the full pipeline requires detailed SG1 landmarks.

## Backup algorithm: Haar cascade

OpenCV's `haarcascade_frontalface_default.xml` provides a classical CPU fallback
and baseline when YuNet is unavailable. It uses grayscale images, scaleFactor
1.1, minNeighbors 5 and minSize 40x40. It returns boxes without detailed eye
landmarks. This choice does not claim robustness in arbitrary lighting or poses.

## Recorded detector performance

The latest comparison described in the October report is retained as historical
evidence, with its limitations. Raw private images and JSON are not in this checkout.

| 150 identical private 640x480 frames | Haar | YuNet |
| --- | ---: | ---: |
| Mean detector-call latency | 40.32 ms | 24.23 ms |
| Detector-only throughput | 24.80 FPS | 41.27 FPS |
| Frames with at least one detection | 150/150 | 150/150 |

Platform reported: Jetson Orin Nano, Jetson Linux R36.4.7, OpenCV 4.14.0,
default CPU, five warm-ups. Calls include Haar grayscale conversion or YuNet
input-size setup; capture, decoding, display and downstream modules are excluded.
No independently labelled accuracy, complete-pipeline FPS, or fresh target result
is established. See [all distinct historical runs](latency.md).

## Implementation and reproducibility

- [Run commands and dependencies](RUN_COMMANDS.md).
- [Camera demo entry point](code/run_demo.py), backed by
  [run_midterm_demo.py](../Integration/run_midterm_demo.py).
- [Paired benchmark with per-frame records](code/benchmark.py).
- [Optional pinned integration](../integrated/README.md), using the SG3-derived
  adapter rather than an owner-approved full SG3 live module.
- [Status-aware SG5-to-SG6 software handoff](../sg5_handoff/README.md), preserved
  from main. Requests do not operate physical GPIO.

The seven original demo tests cover detector loading, blank-frame inference,
metrics, missing model, capture failure, cleanup and interruption; an eighth
checks explicit camera-backend selection. The four
synthetic integration tests cover identity/geometry, yawn propagation, sustained
closure and missing-face status. Thirteen existing handoff tests cover decision
validation, status, clocks and hardware requests. Fresh results and test scope are
recorded in [verification.json](evidence/verification.json).

## Remaining work

Verify the current revision on the Jetson with a live camera, display and resource
measurements; obtain subgroup interface acceptance; validate GPIO/buzzer output;
supply demonstration evidence and complete the subgroup email. The original
evaluation video is currently unavailable.

## AI-generated and open-source code

OpenAI Codex assisted with this post-evaluation package and its new utilities.
OpenCV YuNet/Haar and copied subgroup modules are attributed in
[SOURCE_ATTRIBUTION.md](SOURCE_ATTRIBUTION.md). Source restoration preserves
earlier authorship; synthetic tests are not evidence of physical deployment.
