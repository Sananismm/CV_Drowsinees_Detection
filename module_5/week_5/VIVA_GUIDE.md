# SG5 Week 5 viva guide

## What our task is

Compare at least two ways of converting temporal eye, yawn and fatigue evidence into a drowsiness state and warning. Show transitions, count false/missed sound alerts, measure alert delay, retain the Week 4 baseline, and choose a preliminary rule for Week 6.

The lab sheet calls the states Normal, Warning and Drowsy. Our earlier V1 interface calls them ALERT, CAUTION and DROWSY respectively. ALERT means the driver is awake; alert_action is a separate field.

## What happens inside SG5

1. SG-4 sends a recent temporal summary. We receive numbers, not camera frames or face images.
2. We validate the fields and take the minimum cue confidence. Below 0.55 we output UNKNOWN and no drowsiness sound.
3. We put each cue on a 0-to-1 scale, then calculate a weighted risk score.
4. We choose a driver state using thresholds and saved timestamps.
5. We return the state, score, confidence, action and evidence to SG-6. SG-6 handles the actual buzzer, display and event log.

## How the score is calculated

```text
eye_risk = max(PERCLOS, min(longest_closure_ms / 3000, 1))

yawn_risk = min((yawns_per_minute / 3
                + yawn_duration_per_minute_ms / 9000) / 2, 1)

risk = 0.55 * eye_risk + 0.25 * yawn_risk + 0.20 * persistence
```

Example: PERCLOS 0.52, closure 2800 ms, 3 yawns lasting 7500 ms in a 60-second window, persistence 0.84.

```text
eye_risk = max(0.52, 2800/3000) = 0.9333
yawn_risk = (3/3 + 7500/9000)/2 = 0.9167
risk = 0.55(0.9333) + 0.25(0.9167) + 0.20(0.84)
     = 0.9105, displayed as 0.911
```

The 3-second and 3-yawn normalizers, weights and thresholds are baseline choices for testing. Do not present them as proven universal drowsiness limits. A risk of 0.911 is a heuristic score, not a 91.1% probability.

## The Week 4 rule

Risk below 0.35 asks for ALERT; 0.35 to below 0.65 asks for CAUTION; at least 0.65 asks for DROWSY. High risk produces a sound alert immediately.

We preserved the original code unchanged. It has a known limitation: it can switch immediately from DROWSY to CAUTION when risk falls below 0.65, and can return to ALERT in the 0.25-0.35 middle band. Its stated recovery delay is not consistently enforced. The comparison makes this visible.

## The Week 5 rule

The weights and risk thresholds are unchanged. High risk first produces CAUTION/visual warning. If it stays at or above 0.65 for 2000 ms, the state becomes DROWSY and requests sound plus visual warning.

After CAUTION/DROWSY, risk must stay below 0.25 for 5000 ms to return to ALERT. If it rises again, the recovery timer restarts. DROWSY stays active through the middle band. This makes it stable, but can keep the warning active longer than necessary after recovery.

At one input per second, high risk at 12s, 13s and 14s spans two elapsed seconds: the sound starts at 14s. We use elapsed timestamps, not an arbitrary number of frames.

This confirmation concerns the final decision. SG-4 already aggregates visual cues; SG-5 adds a separate policy for when to activate and release the warning.

## Commands to show the examiner

```powershell
python demo.py --config week4_baseline --scenario progression
python demo.py --config week5_stable --scenario progression --delay 0.2
python demo.py --config week4_baseline --scenario false_spike
python demo.py --config week5_stable --scenario false_spike
python compare.py
python -m unittest -v
```

Open results/report.md and results/summary.csv afterwards. The demo prints Time, Label, Risk, State and Action. Label is the scripted ground truth; the engine never sees it. --delay just slows the terminal presentation. No real buzzer is activated by the demo.

## What the results mean

The fixture has 310 one-second messages, nine scenarios and six true drowsiness episodes. Both configurations use exactly this same fixture.

The baseline produces five wholly false sound-alert events and misses two true episodes. The candidate produces zero wholly false sound-alert events but misses three true episodes. Its mean onset-to-sound delay is 3000 ms versus 750 ms for the baseline, calculated only on the episodes each configuration detected. On the progression example specifically, the delay is 2000 ms versus 0 ms.

The candidate makes fewer state changes (19 versus 25). However, its sample recall and F1 are lower: F1 is about 0.5085 versus 0.5606. That is a real trade-off in this fixture, so do not say the candidate wins every metric. Reduced false sound events are not proof of better sensitivity or real-world accuracy.

The one-second true episode and the erroneous one-second spike intentionally produce similar measured cues. A rule cannot distinguish them from a single message; requiring persistence avoids the erroneous spike at the cost of missing the short true event. Both configurations miss weak evidence and abstain during low confidence.

Carry the candidate into Week 6 as a stability candidate alongside the baseline. Then use real labelled recordings and sweep delays/weights/thresholds to decide the acceptable trade-off. Further improvements may include a separate immediate rule for prolonged closure and stepping down to CAUTION during recovery.

## Metric questions

**What is a false alert?** A continuous sound-alert interval with no overlap with an actual scripted drowsiness episode. We also count false-positive seconds, including alerts held after recovery.

**What is a missed episode?** A contiguous labelled DROWSY interval during which no sound alert is produced. Low-confidence abstention during a true drowsy episode still counts as a miss in the end-to-end metric.

**What is precision?** Of predicted DROWSY seconds, how many were actually labelled DROWSY: TP / (TP + FP).

**What is recall?** Of actual DROWSY seconds, how many produced sound alerts: TP / (TP + FN).

**What is F1?** 2 * precision * recall / (precision + recall).

**Is alert delay the same as processing time?** No. Alert delay is simulated time from ground-truth onset to the first sound request. Processing time is CPU time spent inside decide() for one message. We have not benchmarked Jetson.

**Why not use SIFT from the lab?** This module receives scalar temporal features. SIFT extracts image keypoints, which is unrelated to the input contract for SG-5's fusion rule.

**Why no neural network?** A transparent weighted rule gives a simple baseline, runs with little computation, and can be tested without a training dataset. A learned fusion model would require sufficiently representative labelled data and a separate comparison.

**Why keep one engine object?** It stores the state and when high/low risk began. Recreating it per message loses the timers.

**How will it integrate?** SG-4 passes its V1 dictionary to engine.decide(); SG-6 acts on the returned alert_action. Session/driver IDs and timestamps let us trace the decision. Adjacent subgroups still need to confirm the local V1 contract.

## Suggested work split

Rafed can explain the fusion equations and state-transition code. Filza can explain the mock scenarios, metrics and regression tests. Both should run the whole demo and explain the interface. This is a proposed division, not a claim that those contributions have already been made individually.
