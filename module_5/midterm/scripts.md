# SG5 Midterm Viva Command Sequence

Run these commands one at a time in VS Code PowerShell. All paths below assume
the repository root. The current midterm has A 15 marks, B 10 marks and C 5
marks; it is not the earlier Week 5 ten-mark assessment. Marks are awarded by
the examiner, not guaranteed by a command succeeding.

## Before the assessment

```powershell
cd "C:\Users\Lenovo\Desktop\7th Semester\Computer Vision\Project\SG5 tasks\Midterm"
.\.venv\Scripts\python.exe --version
```

If the environment or model is missing, finish this setup before the viva:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r module_5/midterm/requirements-pc.txt
.\.venv\Scripts\python.exe module_1/scripts/download_model.py
```

Use Windows Python 3.11. No environment activation or execution-policy change
is needed. Installation and downloading are preparation, not a demonstration
of embedded readiness.

## 1 Shared repository evidence

```powershell
git branch --show-current
git log -5 --oneline
git status --short
```

Show the subgroup branch and actual commits, the module README, linked review
work and the team's active GitHub Project board. Explain only real ownership
and coordination evidence. This contributes to **B 10 marks**: shared repository
3, active board 3, usable documentation 2 and coordination 2. SG5 cannot claim
that the whole team has completed those requirements solely from its own code.

## 2 Working SG4 to SG5 to SG6 demonstration

```powershell
.\.venv\Scripts\python.exe -m module_5.midterm.demo --scenario drowsy --output module_5/midterm/results/demo_drowsy
.\.venv\Scripts\python.exe embedded_6/sg5_handoff/consume.py --input module_5/midterm/results/demo_drowsy/sg6_stream.jsonl --events-only
```

Show the NORMAL, WARNING or DROWSY state/status changes that occur, the
SG4 measurements and SG6 requests. The exact path taken depends on the cues;
the eye-closure override may legitimately jump directly to DROWSY. Explain:
"These mock cues pass through the actual SG4 temporal implementation, our SG5
decision engine and the SG6 status-aware consumer. No driver model is trained."

This supports **A working prototype 7 marks** and **A V1 and reproducibility
2 marks**. The richer v2 contract is proposed, not owner-approved V1; show the
valid-only legacy adapter and state the outstanding acceptance requirement.

## 3 Actual vision integration

```powershell
.\.venv\Scripts\python.exe -m module_5.midterm.pipeline --video module_1/data/videos/driver_sample_01.mp4 --output module_5/midterm/results/video01 --annotated
```

Add `--show` only if you want a preview. Open the saved annotated video and
`results/video01/summary.json`. Explain SG1 landmarks, SG2 EAR, the SG3 causal
mouth adapter, real SG4 aggregation, SG5 decisions and SG6 packets. Distinguish
this real-video integration from the labelled synthetic comparison. There is
no independent drowsiness ground truth for this video, so do not quote an
accuracy from its predictions. The preview is optional; a camera is not required
for this reproducible saved-video run.

## 4 Controlled method selection

```powershell
.\.venv\Scripts\python.exe -m module_5.midterm.evaluate --plot
```

Open `results/evaluation/summary.csv`, `overall_comparison.png` and the timeline
PNGs. Explain the preserved A threshold, B weighted and C state-machine rules,
then the robust C and faster-recovery experiment. These use the same 5,400
synthetic rows, with labels excluded from the engine inputs.

This supports **A primary and backup selection 4 marks**. C is the provisional
primary for correct timing and missing-data handling; A is the transparent
backup. B's greater overall sample accuracy does not prevent it missing the
short episode. Do not claim that new C beats the references in accuracy or
flicker. Its 27 changes include abstentions; preserved C has 11. Faster recovery
is an exploratory setting, not a held-out result.

## 5 Failure case and tests

```powershell
.\.venv\Scripts\python.exe -m module_5.midterm.demo --scenario face_lost --output module_5/midterm/results/demo_face_lost
.\.venv\Scripts\python.exe embedded_6/sg5_handoff/consume.py --input module_5/midterm/results/demo_face_lost/sg6_stream.jsonl --events-only
.\.venv\Scripts\python.exe -m unittest discover -s module_5/midterm/tests -v
```

Point out insufficient evidence and the sensor-fault request. A retained NORMAL
string is not a trusted awake observation. Explain time validation, current eye
validity, gap resets and the silence watchdog. The consumer prints requests;
it does not drive GPIO or prove that a Jetson buzzer works.

This supports **A testing and limitations 2 marks**. Be ready to explain the
strict onset-matching definition, false-DROWSY duration and missing detections,
not only the chart appearance.

## 6 Report and embedded readiness

Open `module_5/midterm/report/SG5_Midterm_Report.pdf`. Summarize the selected
method, measurements, subgroup interfaces, failure cases and next steps.

For **C embedded readiness 5 marks**, SG6 must show actual platform boot 2,
software stack 1 and camera readiness 2. Our portable core, validated stream
and consumer are supporting handoff evidence only. Do not substitute a PC run
or a platform screenshot from elsewhere for the team's actual hardware checks.

Both members should be able to explain every stage and their actual work. See
`VIVA_GUIDE.md` for short answers and limitations.

### Platform evidence collector

For a PC environment record, without opening a camera:

```powershell
.\.venv\Scripts\python.exe embedded_6/sg5_handoff/check_platform.py --output module_5/midterm/results/platform_pc.json
```

This correctly reports that the PC is not a Jetson. SG6 should run the following
on the actual device from the cloned repository root, using its validated Python:

```bash
python3 embedded_6/sg5_handoff/check_platform.py --camera 0 --frames 30 --output module_5/midterm/results/platform_jetson.json --strict
```

Only that explicit camera command opens a camera. A successful scoped check
does not establish CUDA, exact 8 GB SKU, GPIO or full-pipeline performance.

All `results/...` paths mentioned above are inside `module_5/midterm/` in the
repository. On this PC the five annotated videos have already been generated.
