# SG6 midterm task tracker

Audit: 2026-10-28. Status describes evidence on this Jetson, not a grade. P0 is required for the live demo; P1 supports readiness; P2 is follow-up.

| Priority | Task / owner | Status and evidence | Acceptance / verification | Blocker |
|---|---|---|---|---|
| P0 | Connect camera and demonstrate YuNet / SG6 | BLOCKED: no `/dev/video*`; open failure verified | Run `~/sg6-yunet-env/bin/python embedded_6/Integration/run_midterm_demo.py`; show face, no face, keypoints, timings and exit; repeat `--headless --frames 150` | Camera unavailable at audit |
| P0 | Demo failure handling / SG6 | VERIFIED WORKING for mocked lifecycle: three tests pass; live success unverified | `python3 -m unittest discover -s embedded_6/Integration -p test_midterm_demo.py -v` | Physical success path still needed |
| P0 | YuNet model and environment / SG6 | VERIFIED WORKING on synthetic blank: model loaded, 0 faces; OpenCV 4.14.0, NumPy 2.2.6 | `~/sg6-yunet-env/bin/python -c 'import cv2,numpy; print(cv2.__version__,numpy.__version__)'` | No live face inference verified |
| P1 | Detector comparison / SG6 | VERIFIED WORKING on 150 private recorded images: Haar 40.74 ms; YuNet 25.02 ms on this run | `~/sg6-yunet-env/bin/python embedded_6/Integration/benchmark_detectors.py`; keep evidence private | Dataset limited, unlabelled; not accuracy or live FPS |
| P1 | Mock and reference tests / SG6 | VERIFIED WORKING: mock validator and synthetic SG2→SG4 and SG5 scripts pass | `python3 embedded_6/Integration/validate_interfaces.py`; `python3 embedded_6/Integration/test_sg2_sg4.py`; `python3 embedded_6/Integration/test_sg5.py` | Test scripts execute older snapshots; no live pipeline |
| P1 | Remote sync / SG6 | PARTIALLY IMPLEMENTED: remote mirror inspected; checkout refs stale | Fetch checkout when permitted, review divergence with `git branch -avv` and `git log --all --oneline --graph`; do not merge without approval | Protected `.git` blocked fetch |
| P1 | Reconcile SG1→SG2 / SG1, SG2, SG6 | PARTIALLY IMPLEMENTED: SG2 midterm branch has landmark adapter; SG1 emits normalized arrays and nullable confidence | Run current subgroup contract tests together and validate timestamps, dimensions, status and ARM64 execution | MediaPipe absent in system Python; availability and installation on Jetson unverified |
| P1 | Reconcile SG4→SG5 / SG4, SG5, SG6 | PARTIALLY IMPLEMENTED: old snapshot emits percent and lacks SG5 fields; newer `saman` SG4 produces fractional PERCLOS and named SG5 fields | Test agreed current revisions and missing/stale data, windows and event semantics together; review GitHub issue #20 | No live handoff or owner acceptance shown |
| P1 | SG3 live cues / SG3, SG4, SG6 | IMPLEMENTED BUT UNVERIFIED: Week 8 source is Colab-oriented video code | Agree yawn event/probability and timestamp contract; execute on target without internet | Dependencies and live interface not demonstrated |
| P1 | GPIO/buzzer / SG5, SG6 | NOT IMPLEMENTED or verified in this SG6 checkout | Agree hardware and sensor-fault policy, then verify actual GPIO and alert behavior | Hardware and ownership not established |
| P1 | GitHub issues, board and ownership / SG6 | PARTIALLY IMPLEMENTED: issues exist including #20; board/PR completeness unverified | Inspect board and PRs, assign owners, record evidence, with user approval for publishing | Board access not verified |
| P2 | Robustness / SG6 | NOT IMPLEMENTED: no controlled lighting/pose/no-face study | Privately test representative conditions and record limitations; never label coverage accuracy | Requires camera and consent |

No commits, pushes, merges, or other subgroup edits were made. Benchmark evidence remains ignored and local.

## Detector demo update (2026-10-28)

- Completed: selectable YuNet/Haar, duration and frame limits, headless status, confidence for YuNet, private JSON measurements and model/config metadata. Seven automated detector/lifecycle tests passed, using real detector inference on a private sample and synthetic/mocked camera frames.
- Completed: 150 identical private 640×480 frame benchmark; five warm-ups, default CPU. Haar 40.32 ms (24.80 inference FPS), YuNet 24.23 ms (41.27 inference FPS), both 150/150 coverage. Coverage is not accuracy.
- Completed: four synthetic current-snapshot SG1/SG2/SG4/SG5 integration tests including identity, timestamp, invalid geometry and missing face; older SG2/SG4 and SG5 synthetic checks also pass. Subgroup acceptance of adapters remains outstanding.
- Outstanding: connect camera and verify both live detectors, no-face/multiple-face behavior, disconnect, graphical display, Ctrl-C and measured end-to-end FPS. This session's `/dev/video0` open failed; no live success claimed.
- Outstanding: fetch into checkout when `.git` is writable. Remote branch heads verified through GitHub on 2026-10-28 match `integrated/BRANCH_AUDIT.md`; local refs remain stale. No merge or push performed.


## Documentation package review — 2026-10-28

- Completed: technical report, demonstration guide, evaluation checklist, interface documentation, setup guide, GitHub evidence and viva preparation prepared in the documentation package. The 150-frame saved JSON was checked; historical Haar live JSON and its missing metadata are distinguished.
- P0 outstanding: run the revised YuNet and Haar demos on the host with the connected webcam and verify GUI, frame counts, metrics, clean exit and failure recovery. USB camera and sysfs nodes were observed; assistant sandbox hid /dev nodes, so that failed open does not establish that the physical camera is absent.
- P1 outstanding: confirm interface-owner acceptance, inspect project board, validate live SG1–SG5 path, and capture a reproducible video log. Review source and evidence privacy before any commit or publication.
- The documentation package was prepared separately and published to main; the revised demo and integrated snapshot remain local and uncommitted.

**Camera clarification:** Earlier references to no `/dev/video*` describe the sandbox view, not a confirmed absence of a connected camera; USB and sysfs enumeration identified a camera. A host-side test is still needed.
