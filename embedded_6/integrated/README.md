# Integrated SG1–SG6 prototype

This snapshot was taken from remote `main` commit `a5570c4` on 2026-10-28. It preserves SG1's MediaPipe Face Landmarker and output contract, SG2's selected EAR method, SG5's SG3 causal yawn adapter (derived from SG3 commit `e3661b7`), SG4's temporal engine/configuration, and SG5's decision engine and SG4 bridge. SG6's `../Integration/run_integrated.py` supplies camera/video acquisition, orchestration and a Tk display. Subgroup algorithms remain attributable to their respective owners. No original branch was merged or modified.

The SG3 adapter uses mouth geometry and 0.50/0.45 thresholds with 1.5 seconds of observed opening. This is an experimental yawn candidate, not a medically validated determination. SG4 counts sustained yawn events, and SG5 consumes that count with eye and temporal data. SG1 provides no calibrated face confidence; SG4's availability bridge passes hard observations without presenting them as probabilities. Head nod is unavailable. SG4 and SG3 owner acceptance of these adapters remains pending. Missing face/eyes displays insufficient evidence. Rapid consecutive measurements more than 200 ms apart are censored by the inherited gap policy; low performance can prevent sustained events being confirmed.

## Run

From the repository root:

```bash
embedded_6/.venv-integrated/bin/python embedded_6/Integration/run_integrated.py
```

Press q or Escape to exit. For terminal-only output add `--headless`; `--frames 150` stops after 150 frames. To process a local video instead, use `--video /path/to/video.mp4 --headless`. The app does not save frames or video. It displays face presence, eye state, yawn state, mouth aspect ratio, SG5 decision/status, and processing FPS. A mouth opening must persist to be confirmed; talking or other expressions can trigger it. Yawn count is an input to SG5, not an automatic DROWSY decision.

The isolated environment was approved separately. Its dependencies are MediaPipe 0.10.18, NumPy 1.26.4, OpenCV contrib 4.10.0.84 and PyYAML, plus transitive dependencies. `../models/face_landmarker.task` is the official SG1 model, verified against SHA-256 `64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff`. Both the environment and model are ignored by Git. Installation/model retrieval require network; operation does not.

## Verification

```bash
embedded_6/.venv-integrated/bin/python -m unittest discover -s embedded_6/integrated/tests -v
```

These are synthetic landmark/contract tests, not live accuracy evidence. See the terminal output from actual video/camera tests for runtime observations. This is a research prototype, not a safety-certified driver monitoring system.

To provision a new isolated environment (network needed), from the repository root:

```bash
python3 -m venv --system-site-packages embedded_6/.venv-integrated
embedded_6/.venv-integrated/bin/python -m pip install -r embedded_6/integrated/requirements.txt
```

Obtain the SG1 Face Landmarker model from [the official MediaPipe model](https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task), place it at `embedded_6/models/face_landmarker.task`, and verify the hash above. Python Tkinter must be available for the graphical mode. No camera data or private recording should be committed.

On 2026-10-28, the real SG1 model and integrated code processed 120 frames from the repository's `driver_sample_01.mp4` on the Jetson in a scratch environment: face and eye outputs were observed, and reported throughput was about 14 FPS by the end. A 10-frame graphical video smoke run also exited successfully. That clip did not establish yawn accuracy; the confirmed-yawn and prolonged-closure tests above use synthetic landmarks. Live camera, real-yawn accuracy, continuous capture interruptions and physical alert hardware still require verification.
