# SG6 midterm demo guide

Run from `~/CV_Drowsinees_Detection`. This is a YuNet face detection demonstration, not a drowsiness decision system. No frames are saved by the new demo.

## Before the examiner

1. Boot the Jetson and connect the USB camera. Check `ls -l /dev/video*`. The audit found no camera; the live run must be verified after connection.
2. Confirm the model is present: `ls -l embedded_6/models/face_detection_yunet_2023mar.onnx`.
3. Check the isolated environment: `~/sg6-yunet-env/bin/python -c 'import cv2,numpy; print(cv2.__version__,numpy.__version__)'`.
4. Run `python3 -m unittest discover -s embedded_6/Integration -p test_midterm_demo.py -v`.
5. With a local display, run `~/sg6-yunet-env/bin/python embedded_6/Integration/run_midterm_demo.py`. Press q or Escape to exit. For SSH without display use `~/sg6-yunet-env/bin/python embedded_6/Integration/run_midterm_demo.py --headless --frames 150`; Ctrl-C also exits. Select another camera with `--camera 1` if needed.

The display uses Python Tkinter (the installed OpenCV has no GUI support) and shows boxes and five keypoints, frame count, face count, inference latency and cumulative processing FPS. Headless prints measurements approximately once a second and on the last frame. Show a face, then move out of view; `faces=0` indicates no detection, not a drowsiness judgement. Measurements come from actual processed frames. Processing FPS covers the loop through inference (and previous display work), not downstream analysis. A read error exits with a nonzero status and releases the camera.

## Recovery

- Camera open error: reconnect, inspect `/dev/video*` and permissions, select the correct `--camera` index, close other camera applications. Do not claim live results if unavailable.
- No display: use `--headless`; no boxes are visible in that mode.
- Missing OpenCV/FaceDetectorYN: use the exact isolated interpreter above. Missing model: restore the tracked model through an approved repository procedure; no internet is needed when present.
- Poor detection: check light, camera framing and focus. No-face handling is expected; never infer driver alertness from it.

## What to say in 5–7 minutes

1. (1 min) Explain SG6 integrates the embedded platform and detector, not the other subgroups' algorithms.
2. (1 min) Show Jetson, environment, camera and command.
3. (2 min) Demonstrate face box/keypoints, no-face state, timing, headless mode and clean exit, if camera is working.
4. (1 min) Compare Haar with YuNet using benchmark table in BENCHMARK_RESULTS.md and latest rerun below. Explain inference-only coverage.
5. (1–2 min) Explain proposed camera → SG1 landmarks → SG2 eyes and SG3 cues → SG4 temporal indicators → SG5 decision/alerts. Identify the unverified interfaces and hardware, and show MIDTERM_TASKS.md.

## Benchmark and questions

On 2026-10-28, 150 private recorded frames gave Haar 40.74 ms / 24.55 inference FPS and YuNet 25.02 ms / 39.96 inference FPS; both reported a face in all frames. Earlier reported 31.65 / 17.89 ms are historical, with different run conditions. Coverage is not labelled accuracy; timings exclude capture and the rest of the pipeline. The limited same-frame dataset does not establish robustness.

**Is this drowsiness detection?** No; this demo detects faces. The end-to-end pipeline and alerts have not been verified.

**Can YuNet calculate EAR?** No; its five keypoints do not provide the six detailed points per eye required by SG2.

**Are all modules integrated?** No. Reference SG2→SG4 and SG5 logic passed controlled synthetic tests. Newer handoffs need joint validation and hardware execution.

**What happens when the face disappears?** This demo displays zero faces. Downstream lost-face and stale-data policies must be agreed and tested; no alert decision is produced here.

**What is FPS?** The on-screen figure measures this demonstration's processing loop, not the full drowsiness system. Detector benchmark FPS excludes camera capture.

## Updated SG6 detector demo (2026-10-28)

From the repository root, use the isolated interpreter. These commands select the detector at startup; no interactive switching is implemented:

```bash
~/sg6-yunet-env/bin/python embedded_6/Integration/run_midterm_demo.py --detector yunet
~/sg6-yunet-env/bin/python embedded_6/Integration/run_midterm_demo.py --detector haar
~/sg6-yunet-env/bin/python embedded_6/Integration/run_midterm_demo.py --detector yunet --headless --duration 60 --save-metrics
~/sg6-yunet-env/bin/python embedded_6/Integration/run_midterm_demo.py --help
```

Use `--camera 1` for another device, `--frames` for a frame limit, and `--output-dir` for an alternative metrics directory. Default JSON output is in ignored `embedded_6/evidence/`; the program never saves frames. For an indefinite run latency samples are retained in memory to calculate the exact median. GUI uses Tk, supports q/Escape, and requires a working display. Confidence and five points are YuNet-only; Haar has neither. Actual resolution comes from frames, and processing FPS includes acquisition and loop work. Inference latency includes Haar grayscale conversion or YuNet input-size setup; coverage is not accuracy. Failed reads are counted; camera-driver dropped frames are unknown, not assumed to be zero.

The 2026-10-28 rerun of 150 identical 640×480 private images measured Haar 40.32 ms / 24.80 inference FPS and YuNet 24.23 ms / 41.27 inference FPS, both 150/150 face coverage. Five warm-up calls per detector; CPU default; image decoding and camera capture excluded. See the ignored `evidence/detector_benchmark.json` for configuration. The set is unlabelled and limited. A camera test in this session failed because no `/dev/video0` was visible; neither real-time camera performance nor this revision's GUI has been demonstrated.

Synthetic current-snapshot SG1 contract, SG2, SG4 and SG5 tests:

```bash
embedded_6/.venv-integrated/bin/python -m unittest discover -s embedded_6/integrated/tests -v
```

The integration snapshot and its video-based optional mode are described in `integrated/README.md`. It uses a separate environment and a MediaPipe landmark model, not YuNet's five points. The SG3/SG4/SG5 adapters remain experimental and require subgroup acceptance. Synthetic results do not establish live accuracy.
