# Proposed SG-4 issues for the team project board (not created yet)

Every issue gets the label `SG-4`; blockers also get `blocked`. Assign the owners before creating them. Run the commands below from the team repo once `gh auth login` is done.

| # | Title | Owner | Status | Labels |
|---|---|---|---|---|
| 1 | SG-4: V1 input contract and SG-5 v1.1 output schema | `<owner>` | Done | SG-4 |
| 2 | SG-4: mock cue generator with ground truth (5 scenarios) | `<owner>` | Done | SG-4 |
| 3 | SG-4: sync + ring buffer + O(1) PERCLOS | `<owner>` | Done | SG-4 |
| 4 | SG-4: event state machines (blink / slow / long, yawn, nod) | `<owner>` | Done | SG-4 |
| 5 | SG-4: baseline, trend and 10 Hz engine | `<owner>` | Done | SG-4 |
| 6 | SG-4: SG-5 contract test, golden files, compat checker | `<owner>` | Done | SG-4 |
| 7 | SG-4: evaluation, backup approaches, ablation | `<owner>` | Done | SG-4 |
| 8 | SG-4: stand-in MediaPipe extractor (test harness) | `<owner>` | In progress (not yet run with a camera) | SG-4 |
| 9 | SG-4: run benchmark on Jetson Orin Nano | `<owner>` | Blocked | SG-4, blocked |
| 10 | SG-4: annotate team clips and evaluate on real video | `<owner>` | Todo | SG-4 |
| 11 | Waiting for SG-2 eye closure probability / confidence | `<owner>` | Blocked | SG-4, blocked |
| 12 | Waiting for SG-3 output format and head-pitch sign convention | `<owner>` | Blocked | SG-4, blocked |
| 13 | Waiting for SG-5 written confirmation of v1.1 windows | `<owner>` | Blocked | SG-4, blocked |

```bash
gh label create SG-4 --color 5319e7 2>/dev/null; gh label create blocked --color d73a4a 2>/dev/null
gh issue create --title "SG-4: run benchmark on Jetson Orin Nano" --label SG-4,blocked --assignee <owner> \
  --body "Run: python3 module_4/tools/benchmark.py --frames 30000 --csv module_4/results/benchmark_jetson.csv. Target < 2 ms/update, < 50 MB. Blocked on Jetson access (SG-6)."
gh issue create --title "Waiting for SG-2 eye closure probability / confidence" --label SG-4,blocked --assignee <owner> \
  --body "SG-2 draft sends eye_closure_prob=null and eye_valid (bool). SG-4 falls back to OPEN/CLOSED. Ask: calibrated prob or threshold, and per-frame confidence. See documentation/interface_tracking.md."
gh issue create --title "Waiting for SG-3 output format and head-pitch sign convention" --label SG-4,blocked --assignee <owner> \
  --body "Need yawn_prob, mar, pitch/yaw/roll, confidence per frame. Convention proposed: pitch negative = head down."
gh issue create --title "Waiting for SG-5 written confirmation of v1.1 windows" --label SG-4,blocked --assignee <owner> \
  --body "Non-blocking. Golden files: interfaces/mocks/sg5_expected/. Checker: module_4/tools/check_sg5_compat.py."
# Issues 1-7: create them, then close each with a link to the PR:  gh issue close <n> --comment "Done in #<pr>"
```
