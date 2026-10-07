# SG5 Week 5 comparison

This report uses fixed, hand-labelled synthetic SG-4 messages. These results demonstrate decision logic, not accuracy on real drivers.

Both configurations see the identical 60-second-window messages, updated once per simulated second. Each scenario starts with a fresh engine. Ground-truth labels stay outside the V1 input and are never passed to the engine.

## Configuration comparison

Weights and thresholds are held constant. Week 4 enters DROWSY immediately and keeps its original release behaviour. Week 5 requires 2000 ms of continuous high risk, preserves warnings through the middle band, and releases only after 5000 ms below 0.25. The study therefore isolates state-transition logic on this fixture.

| Configuration | False alert events | Missed episodes | Sample precision | Sample recall | F1 | Mean alert delay ms | State changes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| week4_baseline | 5 | 2 | 0.5522 | 0.5692 | 0.5606 | 750 | 25 |
| week5_stable | 0 | 3 | 0.5660 | 0.4615 | 0.5085 | 3000 | 19 |

## Episode evidence

| Configuration | Scenario | Detected | Alert delay ms |
| --- | --- | --- | ---: |
| week4_baseline | progression | True | 0 |
| week4_baseline | weak_drowsiness | False | Missed |
| week4_baseline | short_true_episode | True | 0 |
| week4_baseline | visibility_loss | False | Missed |
| week4_baseline | recovery_band | True | 0 |
| week4_baseline | late_strong_evidence | True | 3000 |
| week5_stable | progression | True | 2000 |
| week5_stable | weak_drowsiness | False | Missed |
| week5_stable | short_true_episode | False | Missed |
| week5_stable | visibility_loss | False | Missed |
| week5_stable | recovery_band | True | 2000 |
| week5_stable | late_strong_evidence | True | 5000 |

## Failure analysis and Week 6 decision

The original engine responds immediately to strong evidence, including an isolated erroneous spike. Near 0.65 it can repeatedly switch between CAUTION and DROWSY. It can also clear a warning in the 0.25-0.35 band even though its documented release threshold has not been met.

The stable candidate rejects isolated spikes and avoids that chatter, but waits 2 seconds before a sound alert. It misses the deliberately short true episode and keeps sound alerts active longer during recovery. This can increase false-positive samples even while it reduces wholly false alert events. Both engines miss the weak-evidence case and abstain on the low-confidence case.

Carry week5_stable forward as the preliminary Week 6 candidate for stability, while retaining week4_baseline as a fast-response comparator. Do not claim the candidate is more accurate for real drivers. Sweep entry delays (0, 500, 1000, 2000 ms), thresholds and weights on labelled SG-4/video recordings, separating development and held-out clips. Decide whether long eye closure needs a separate immediate escalation rule, and whether recovery should step down from DROWSY to CAUTION before ALERT. Any decision-policy change needs team review.

## Metric definitions

- Positive class: ground-truth DROWSY. Positive prediction: AUDIO_VISUAL. CAUTION/visual warnings are not sound alerts.
- False alert event: a continuous AUDIO_VISUAL interval with no overlap with a labelled drowsiness episode.
- False-positive sample: a sound alert during any non-drowsy labelled second, including delayed recovery. False-negative sample includes a missed DROWSY second and an UNKNOWN second during drowsiness.
- Missed episode: no sound alert within a contiguous labelled DROWSY episode.
- Alert delay: first sound-alert timestamp minus episode-onset timestamp. The mean excludes missed episodes; read the missed count alongside it.
- State changes: transitions between consecutive output states within each scenario.
- mean_compute_ms in summary.csv measures the Python decide call on the development PC. It is neither alert delay nor a Jetson benchmark.

## Reproduction

Run `python compare.py`. Input SHA256:

`cf9f9e8a3f568b21a75cbee9311e827ead4cfad6c347300bb6f68d7355867867`

See run_manifest.json for configurations, interpreter version and baseline checksum. Wall-clock compute timings vary between runs; predictions and simulated alert delays do not.
