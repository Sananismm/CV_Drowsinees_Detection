# SG6 post-midterm submission

**Course:** CS-477 Computer Vision, SEECS CV Face-Off 2026

**Group/subgroup:** SG6 - Embedded Deployment and System Integration

**Members:** Muhammad Sanan Khan and Muhammad Sami

**Prepared:** 18 November 2026

**Target:** NVIDIA Jetson Orin Nano 8 GB

This package follows the post-midterm advisory. The software and documentation are
prepared for review. Submission is **incomplete** until the evaluation README is
confirmed, demo evidence is supplied, board statuses are updated, and the email is
sent. The members report that the evaluation video is currently unavailable.

## Contents and evidence

| Advisory item | Location | Current status |
| --- | --- | --- |
| Primary and backup algorithms, reason | [README_mid_evaluation.md](README_mid_evaluation.md) | YuNet primary; Haar backup; decisions documented |
| Midterm evaluation README | [README_mid_evaluation.md](README_mid_evaluation.md) | Reconstructed from existing October documentation; exact presented version unconfirmed |
| Executable code and packages | [code/](code/), [RUN_COMMANDS.md](RUN_COMMANDS.md) | Included; camera and optional full pipeline require target checks |
| Latency / FPS | [latency.md](latency.md), [historical measurements](evidence/historical_latency.json) | Historical Jetson results attributed; no fresh Jetson benchmark claimed |
| Fresh verification | [evidence/verification.json](evidence/verification.json) | PC tests; see recorded environment and logs |
| AI/open-source disclosure | [SOURCE_ATTRIBUTION.md](SOURCE_ATTRIBUTION.md) | Codex assistance and original subgroup sources identified |
| Project tasks, owners, blockers | [TASK_STATUS.md](TASK_STATUS.md) | Existing SG6 issues mapped; live board confirmation required |
| Demo video | [demo_link.md](demo_link.md), [DEMO_RECORDING_GUIDE.md](DEMO_RECORDING_GUIDE.md) | Unavailable; no substitute represented as evaluation footage |
| Subgroup email | [EMAIL_DRAFT.md](EMAIL_DRAFT.md) | Draft only; not sent |

## Quick verification (from repository root)

Use Python 3.10 or 3.11 and an isolated environment. Linux/Jetson:

```bash
python3 -m venv .venv-sg6
.venv-sg6/bin/python -m pip install -r embedded_6/midterm/code/requirements.txt
.venv-sg6/bin/python embedded_6/midterm/code/verify.py
.venv-sg6/bin/python embedded_6/midterm/code/run_demo.py --detector yunet --headless --frames 150 --save-metrics
```

Windows PowerShell uses `.venv-sg6\Scripts\python.exe` in place of
`.venv-sg6/bin/python`. Verification needs no camera, private images, or MediaPipe
task model. Live capture processes images without recording them. The detector
model is checked in; the optional landmark model is not.

For a repeatable YuNet/Haar comparison on private images:

```bash
python embedded_6/midterm/code/benchmark.py --frames-dir embedded_6/evidence/benchmark_frames --limit 150 --repeats 3
```

Run this with the same environment interpreter. It saves per-frame timings,
input/model hashes and runtime metadata under ignored `embedded_6/evidence/`.
Publish an explicitly reviewed summary; raw face images remain local.

## Scope and readiness

SG6 owns acquisition, deployment, runtime measurement and system integration.
Face/eye/yawn/temporal/decision algorithms retain their original subgroup ownership.
Detector-only FPS excludes camera, display and SG1-SG5 processing. Coverage means
frames containing at least one reported face; it is not detection accuracy.
GPIO/buzzer operation and current live target performance are still unverified.

## AI disclosure

OpenAI Codex assisted in preparing this package, restoring SG6 implementation from
its existing branch, and writing the new utilities, tests and documentation.
This disclosure covers the November work; it does not assert the provenance of
every earlier contribution. Review [source attribution](SOURCE_ATTRIBUTION.md).
