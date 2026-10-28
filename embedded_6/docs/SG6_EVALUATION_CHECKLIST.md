# SG6 Stage 1 Evaluation Checklist

Status as of 28 October 2026; no marks are claimed. PASS means the stated evidence was observed, not that the full rubric item is complete. See [report](SG6_MIDTERM_TECHNICAL_REPORT.md) for test provenance.

## Prototype, comparison, testing and interface readiness — 15 marks

| Requirement | Status and evidence | Missing work | Priority | Acceptance criterion |
|---|---|---|---|---|
| Face detector implementation | Implemented; real inference on private sample passed for both models | Real camera success for revised script | P0 | Show both detectors on camera with recorded metrics |
| Camera acquisition and display | Code implemented; connected USB camera and sysfs nodes observed; sandbox hid devices | Verify current revision on host and GUI | P0 | Frames, actual resolution, face/no-face and clean exit observed |
| Performance comparison | PASS for saved identical-frame benchmark, 150 images, 640×480 | Repeat if needed and document lighting/conditions | P1 | Reproducible same-frame JSON with timing boundaries |
| Robustness | Mock open/read failure, no face and Ctrl+C tests pass | Physical disconnect, multiple faces, lighting and pose | P1 | Record expected nonzero errors and safe cleanup on target |
| Interfaces | Four synthetic snapshot tests pass; SG4 schemas and bridge inspected | Cross-owner acceptance and live capture-to-decision | P1 | Agree fields/units, validate real data and missing conditions |
| Recorded-video path | Historical README reports 120 frames and ~14 FPS | Capture a reproducible run log; validate accuracy | P1 | Retained provenance, command and measured results |
| Physical alerts | Not verified | Hardware policy and test | P2 | Demonstrate agreed alert device and safe missing-data policy |

## GitHub collaboration, documentation and tasks — 10 marks

| Requirement | Status and evidence | Missing work | Priority | Acceptance criterion |
|---|---|---|---|---|
| SG6 contributions | Commit b4bf9ec and earlier documentation commits visible; branch exists | Review local uncommitted work and publish only with approval | P1 | Explain actual code, commits and local versus remote state |
| Cross-subgroup collaboration | Merged SG5 PR #21, SG1 PR #2 and open SG5–SG6 issue #20 are visible | Confirm current owner sign-off and decisions | P1 | Link relevant issue/PR and report agreed interface status |
| Project board | Not independently inspected | Check project access and task ownership | P1 | Show current board or explicitly state unavailable |
| Documentation | Package prepared; measurements and limitations traced | Place files into repository if desired, review and commit only with permission | P1 | Working links, verified commands, private data excluded |

## Hardware and environment — 5 marks

| Requirement | Status and evidence | Missing work | Priority | Acceptance criterion |
|---|---|---|---|---|
| Jetson setup | ARM64 Tegra and R36.4.7 observed; isolated OpenCV 4.14 | Confirm current setup from host | P0 | Show release, Python, OpenCV and model checks |
| Webcam | USB enumeration and video nodes in sysfs; historical Haar JSON exists | Fresh current-demo camera test | P0 | Show actual frames on host for both methods |
| Software readiness | Seven demo tests passed in isolated venv; system Python Haar tests fail | Validate GUI and dependencies at evaluation | P0 | Tests pass with documented interpreter |
| Acceleration | Zero CUDA devices reported in prior OpenCV audit; CPU baseline | Optional verified acceleration later | P2 | Make no unsupported GPU claims |

Before evaluation: execute the [demo checklist](SG6_MIDTERM_DEMO_GUIDE.md), retain private metrics and resolve errors; then get SG1–SG5 agreement on [interfaces](SG6_INTEGRATION_INTERFACES.md).
