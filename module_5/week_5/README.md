# SG5 Week 5 tasks

Rafed Aftab and Filza Umar - G1-D2 Driver Drowsiness Monitoring

SG-5 receives temporal eye/yawn/fatigue evidence from SG-4 and returns a driver state and alert action to SG-6. Week 5 compares the unchanged Week 4 baseline with a rule that confirms high risk before a sound alert and releases warnings consistently.

## Run in VS Code

Open this folder in VS Code and open Terminal > New Terminal. Python 3.10 or later is sufficient. There are no third-party libraries to install: the code uses Python's standard library. OpenCV, NumPy and a webcam are not needed for this subgroup experiment.

```powershell
python --version
python demo.py
python compare.py
python -m unittest -v
```

For the local copy, first change directory if your terminal starts in the Computer Vision parent folder:

```powershell
cd ".\Project\SG5 tasks\Week 5 tasks"
```

After cloning the GitHub project, the equivalent directory is:

```powershell
cd ".\module_5\week_5"
```

If VS Code uses the wrong Python, choose Python Select Interpreter from the command palette. On Windows, `py` can replace `python` if that is your installed launcher.

## Week 5 requirements and evidence

| Requirement from the SG-5 section | Files and demonstration |
| --- | --- |
| Retain a working Week 4 baseline | `week4_baseline.py`, copied unchanged from the earlier SG-5 prototype |
| Compare at least two configurations | `configs.json`, `decision_logic.py`, `compare.py` |
| Normal to Warning to Drowsy examples | `python demo.py --scenario progression` |
| False and missed alerts | `results/summary.csv`, `results/episodes.csv`, failure scenarios |
| Alert latency | simulated onset-to-alert delay in `results/episodes.csv` |
| Selected preliminary rule and analysis | `results/report.md`, `VIVA_GUIDE.md` |
| Mock temporal input and documented V1 output | `data/mock_temporal_inputs.jsonl`, `INTERFACE.md`, `interfaces/` |
| Decision logic separate from alert UI | `decision_logic.py` returns dictionaries; `demo.py` only prints them |
| Reproducibility and versioned parameters | fixed input data, configurations, regression tests, result manifest |

`ALERT` means awake/normal, `CAUTION` means warning, and `DROWSY` means a sound plus visual alert. These names preserve the existing local V1 contract.

## What changes between the rules

| Setting | week4_baseline | week5_stable |
| --- | --- | --- |
| Eye / yawn / persistence weights | 0.55 / 0.25 / 0.20 | 0.55 / 0.25 / 0.20 |
| Minimum confidence | 0.55 | 0.55 |
| Caution / drowsy thresholds | 0.35 / 0.65 | 0.35 / 0.65 |
| Confirm high risk before sound | No delay | 2000 ms of continuous high risk |
| Return to awake | Original Week 4 behaviour, including its middle-band limitation | 5000 ms continuously below 0.25 |
| Reject malformed input and reset interrupted timers | Original limited checks | Full required-field/range checks, gap/driver/session handling |

The comparison fixture always uses the same 60-second window. The Week 5 code also normalizes yawn evidence for other window lengths, but this study does not compare different windows. SG-4 remains responsible for extracting/aggregating the temporal indicators.

`week4_baseline` ignores edits to its record in configs.json because its settings are defined inside the preserved original file. Edit only the Week 5 configuration for new studies, or add a new candidate deliberately; do not alter the baseline snapshot.

## Demo commands for the viva

```powershell
# Slow the display so the class can follow the transitions.
python demo.py --scenario progression --config week5_stable --delay 0.2

# Compare a spurious high-risk spike.
python demo.py --scenario false_spike --config week4_baseline
python demo.py --scenario false_spike --config week5_stable

# Show an honest failure caused by waiting for confirmation.
python demo.py --scenario short_true_episode --config week5_stable

# Show complete SG-6 output dictionaries.
python demo.py --scenario visibility_loss --json

# Reproduce the experiment table and check correctness.
python compare.py
python -m unittest -v
```

The demo uses timestamps in the input messages. `--delay` changes presentation speed only; a displayed 2-second alert delay remains 2 simulated seconds even when the replay runs instantly. `--json` prints the V1 dictionaries; explanatory terminal headers are not a machine transport protocol.

## Test data

The committed fixture has 310 messages across nine independent scenarios: progression, normal driving, a false spike, threshold jitter, weak drowsiness, a short true episode, visibility loss, recovery in the middle band, and late strong evidence. Labels are scripted ground truth, not annotations from real driving footage.

Regenerate the exact fixture with `python make_mock_data.py`. `compare.py` accepts another JSONL fixture through `--input`, using the same wrapper shown in INTERFACE.md. The evaluator currently requires one sample per second and one driver/session per scenario.

Inspect these generated files:

- `summary.csv`: sample precision/recall/F1, false events, missed episodes, state changes and CPU call timing.
- `episodes.csv`: each true episode and its first sound-alert delay, or a missed outcome.
- `decisions.csv`: the complete labelled replay for both configurations.
- `report.md`: definitions, results, failure analysis and the preliminary Week 6 choice.
- `run_manifest.json`: exact configurations and input/baseline checksums.

## Current limitations and next step

This is a controlled mock experiment, not a measurement of real-driver accuracy or Jetson speed. The thresholds and weights are initial engineering settings, not validated physiological limits. The risk score and confidence are not probabilities of drowsiness. Existing Week 3 metrics/test recordings were not present in the supplied files; the experiment uses the earlier SG-5 metric plan and explicitly scripted mock cases until those recordings are available.

The two-second confirmation prevents a sound alert on a single spike, but it also misses a one-second true episode. Keeping DROWSY active until low risk persists increases recovery overhang. The minimum-confidence gate blocks the whole decision if any required cue is unreliable. UNKNOWN suppresses a drowsiness warning and must be logged by SG-6; a separate sensor-visibility warning needs a team policy decision.

The original baseline is kept so its limitations can be demonstrated instead of silently repaired. All nine-scenario input messages and both engines' output fields match the earlier local V1 schemas. Team approval of these interfaces still needs to be confirmed with SG-4 and SG-6; the common GitHub interfaces folder was empty when checked.

Carry the stable candidate into Week 6 as a stability experiment, alongside the baseline. Use real labelled SG-4 streams to choose the delay/threshold trade-off, test one-cue failures, and profile on Jetson with SG-6.

## GitHub and team coordination

Only `module_5` files should be added by this work. Use the `feature/sg5-week5-decision-comparison` branch and a reviewed pull request. `TASK_BOARD.md` contains ready-to-enter SG-5 task descriptions for the team's project board. The shared board, meeting record and optional reference-screening bonus require the major team's own coordination; this package does not claim they have been completed.

Source: CS477 Week 5 Subgroup Tasks GitHub Readiness Assessment, Project Stream B, SG5 Drowsiness Decision and Alert Logic (page 6).
