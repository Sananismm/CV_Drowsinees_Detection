# SG6 source attribution and AI disclosure

## November assistance

OpenAI Codex assisted with inspection, restoring the existing SG6 source into a
branch based on current main, camera-backend portability and measurement metadata,
the new benchmark/verification entry points and tests, and this documentation.
Muhammad Sanan Khan and Muhammad Sami are the SG6 members supplied by the user;
this is not a claim about individual authorship of historical files. Earlier AI
use was not independently established. The new work requires member review.

## Repository provenance

- Base main: `a6f2e78571c3ae0e36f994a9c0c09de67f9bbda6`.
- Restored SG6 source: branch `sg6` at
  `97573173e8a5ad3acdd753197723e18bfc21b91e`.
  Paths: `Integration/run_midterm_demo.py`, `Integration/test_midterm_demo.py`,
  `Integration/run_integrated.py`, `integrated/`, and `embedded_6/.gitignore`.
- Only the restored detector demo and its tests are subsequently changed for the
  November package; the pinned integrated snapshot retains its October source.
- Main's `sg5_handoff/` and other subgroups' current source are preserved.
- [provenance.json](evidence/provenance.json) records restored-file hashes and
  any local modifications relative to the pinned SG6 branch.
- [Original integration audit](../integrated/BRANCH_AUDIT.md) attributes the
  snapshot's SG1 contract/detector, SG2 eye analysis, SG4 temporal engine, and SG5
  decision/bridge/SG3-derived adapter to the relevant subgroups and revisions.
- [Legacy reference attribution](../reference_modules/README.md) covers the older
  experimental references; those are separate from the selected snapshot.

## External software and models

| Component | Source and use |
| --- | --- |
| OpenCV FaceDetectorYN / YuNet | [OpenCV face detector tutorial](https://docs.opencv.org/4.x/d0/dd4/tutorial_dnn_face.html); detector implementation supplied by OpenCV |
| YuNet ONNX model | [OpenCV Zoo YuNet directory](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet); checked-in `face_detection_yunet_2023mar.onnx`; upstream directory includes its license |
| Haar detector / cascade XML | [OpenCV cascade tutorial](https://docs.opencv.org/4.x/db/d28/tutorial_cascade_classifier.html); cascade distributed with the OpenCV Python package |
| NumPy / PyYAML | [NumPy](https://numpy.org/), [PyYAML](https://pyyaml.org/); arrays and SG4 YAML configuration |
| jsonschema | [python-jsonschema](https://python-jsonschema.readthedocs.io/); validation of native SG4 input in the handoff regression suite |
| Optional MediaPipe Face Landmarker | [Google MediaPipe](https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker); detailed SG1 landmarks; separate task model and dependency environment |

The model hash and restored source hashes are recorded in provenance.json.
Fresh benchmark/live runs also hash the actual models they use. Dependency and
model upstream licenses continue to apply; this package does not assign a new
license to other subgroups' code or external binaries.
