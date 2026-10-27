# SG5 Drowsiness Decision and Alert Logic

**Team G1-D2** · **Rafed Aftab 457967** · **Filza Umar 464340**

SG5 converts SG4 temporal eye and yawn measurements into `NORMAL`, `WARNING` or
`DROWSY`, then supplies explicit, status-aware requests for SG6. It does not
train a model. The midterm package connects the available SG1, SG2, SG3 and SG4
work instead of substituting generated predictions for upstream processing.

## Start here

- [Midterm setup and integration](midterm/README.md)
- [Commands to run in the viva](midterm/scripts.md)
- [Explanation and examiner questions](midterm/VIVA_GUIDE.md)
- [Midterm evidence report](midterm/report/SG5_Midterm_Report.pdf)
- [SG6 consumer and hardware handoff](../embedded_6/sg5_handoff/README.md)

Run commands from the **repository root**, not this module folder. The midterm
README contains the reproducible setup and the short offline demonstration.

## Two deliberately separate implementations

| Folder | Role |
| --- | --- |
| `SG5_drowsiness_decision/` | Preserved Week 5 A, B and C comparison, its original synthetic drives and recorded outputs. |
| `midterm/` | Deployable decision core, real subgroup adapters, headless evaluation, replay/video runners, regression tests and the report. |

The primary midterm method is robust C: weighted evidence with smoothing,
hysteresis, validated timing and an eye-closure override. A remains the simple
backup. C is not the accuracy winner; its use is a provisional engineering
choice, with the measured trade-offs documented in the report.

The new `sg5.sg6.v2` status contract is **proposed for review**, not silently
declared an approved replacement for V1. The exact legacy SG6 three-field
payload is available only for usable observations. SG3 geometry and the native
hard-state availability adapter also require the relevant owners' acceptance.
Jetson deployment, GPIO operation and real-driver accuracy are not established
by the PC demonstrations.
