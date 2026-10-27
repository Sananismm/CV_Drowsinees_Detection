# SG5 Midterm Viva Guide

**Rafed Aftab 457967 and Filza Umar 464340** · **G1-D2**

Use `scripts.md` for the runnable sequence. This guide explains what the code
does and the limits of the evidence; it is not a claim that marks or subgroup
interface acceptance have already been awarded.

## Opening explanation

"Our subgroup is responsible for drowsiness decisions and alert logic. We take
temporal eye and yawn indicators from SG4, validate their availability, combine
the evidence and maintain NORMAL, WARNING or DROWSY. We send a state, quality
status and explicit alert information to SG6. At midterm we can replay the real
SG4 engine, run the available vision stages on a saved video, compare decisions
on fixed labelled synthetic inputs and test the SG6 consumer."

## Where the inputs come from

There are three distinct demonstrations. Do not describe them as the same data.

| Demonstration | Input source | What it proves |
| --- | --- | --- |
| Native SG4 scenario replay | Versioned mock frame cues, processed by the actual SG4 engine | Repeatable temporal-to-decision and consumer integration |
| Saved-video pipeline | Real video through SG1, SG2 and the SG3 adapter, then SG4 and SG5 | Available implementation stages execute together |
| Method evaluation | Two preserved synthetic temporal CSV drives with 5,400 labelled rows | Controlled A/B/C and parameter comparisons on those development examples |

SG1 uses a pretrained MediaPipe landmark model. The integrated SG2 path uses
EAR geometry. The SG3 adapter derives mouth aspect ratio from the shared SG1
landmarks, with causal timing rather than looking into future frames. SG4
maintains observation windows, closure duration and event counts. SG5 receives
the following, not raw video:

- `time_s`: capture-clock seconds.
- `face_valid`: current face availability.
- `perclos`: closed-eye fraction over SG4's 60-second window.
- `eye_closure_s`: current continuous eye closure.
- `long_blinks`: long-blink events in 30 seconds.
- `yawn_count`: yawn events in 60 seconds.

The bridge also carries current `eye_valid` and historical `validity_score`.
The maintained SG4 code was found on `saman`; the `sg4` branch is older. The
integration does not silently switch percentage PERCLOS into fractional PERCLOS.

The two preserved synthetic CSV drives use a 30-second PERCLOS window, whereas
the actual SG4 producer uses 60 seconds. Equal field names do not mean equal
input distributions, so our synthetic results do not validate the real-stream
thresholds.

## Are we training anything

"No SG5 training is performed. Our rules and their weights are manually
configured. SG1 runs pretrained inference. The synthetic generator creates
test measurements and reference labels; it does not fit the decision rules."

The real video does not have independent drowsiness labels. It therefore
supports execution and timing evidence, not an accuracy or real-world safety
claim. A ground-truth label in the synthetic CSV is passed only to evaluation,
never to the engine.

## How A B and C work

**A threshold reference:** DROWSY if PERCLOS is at least 0.22 or reported eye
closure reaches 1.5 seconds. Lower thresholds give WARNING. It is easy to audit
but individual threshold crossings can repeatedly change the state.

**B weighted reference:** normalize each measurement to 0-1, then combine
45% PERCLOS, 20% closure duration, 20% long blinks and 15% yawns. WARNING starts
at score 0.20 and DROWSY at 0.50. Other weak cues can dilute an isolated long
closure; it misses the short drowsiness episode in these drives.

**C state machine:** use weighted evidence, exponential score smoothing and
different entry and exit thresholds. WARNING enters at 0.20 and exits below
0.14; DROWSY enters at 0.65 and exits below 0.53. Upward evidence must be valid
and continuous for one second; lower-risk evidence must persist for three
seconds. Valid reported eye closure of at least 1.5 seconds overrides the score
and immediately requests DROWSY. A two-second smoothing time constant is not
an exact two-second moving-average window.

Normalization means scaling a cue using its configured low and high limits,
clipping to 0-1, then applying its weight. The resulting score is not a learned
probability of sleep. Quality describes observed availability, not risk.

## Why retain robust C as the primary

"We are investigating a temporal decision method, not selecting the largest
accuracy number. Robust C fixes invalid-time accumulation, target confirmation,
quality handling and stale-stream behavior while retaining the closure override.
A is our simple backup. These engineering properties motivate the provisional
choice, but further independent labelled data is necessary."

Overall preserved-reference accuracy is A 71.4%, B 75.2% and C 65.8%. A and C
detect both labelled episodes; B detects one. Robust C is about 64.1%, not an
accuracy improvement. Its 27 reported changes include entering/leaving
abstention, so comparing that count with preserved C's 11 as pure flicker is
incorrect. The faster-recovery experiment is about 64.0%; it is a sensitivity
run on the same development examples, not held-out optimization.

Be able to explain each kind of result:

- Accuracy counts all labelled rows, including unavailable observations.
- Drowsy precision and recall describe samples, not independent episodes.
- Strict event detection needs a new DROWSY onset inside a labelled episode,
  matched once. Already-active overlap is separate coverage, not a new detection.
- False-alert events are unmatched onsets under that definition. False-DROWSY
  duration separately records seconds of DROWSY prediction outside true DROWSY.
- Mean onset latency excludes missed episodes; misses must be reported beside it.
- Processing time is CPU work. It is not the confirmation delay, video frame
  rate or a Jetson benchmark.

The old evaluator allowed five seconds after an episode ended. The midterm
strict evaluator does not award detections in that grace interval. Keep old
recorded results and new definitions distinct.

## What happens on missing data

"If the face, eye or observation quality is unusable, we clear confirmation
timers and retain the last state only as untrusted history. Status becomes
INSUFFICIENT_EVIDENCE. We suppress actionable alerts and request a sensor-fault
indication rather than claiming the driver is awake."

Capture gaps reset evidence. Reversed, repeated and nonfinite timestamps are
rejected. The new core has no forced five-second NORMAL warm-up, so valid
prolonged-closure evidence can act from the first observation.

`DecisionEngine.tick()` detects silence using the same producer capture clock.
SG6's transport `DeliveryWatchdog` uses host monotonic arrival time and must be
polled even while no messages arrive. Do not mix those two clocks. A complete
transport failure cannot be detected merely by waiting for another input row.

## What SG6 receives

The proposed richer packet uses `schema_version=sg5.sg6.v2`, state, raw and
smoothed scores, quality, time, session, status, reason and alert information.
For OK observations, WARNING requests a visual warning and DROWSY requests
visual plus buzzer. Non-OK status requests a sensor fault. The provided consumer
validates packets and prints hardware requests; it does not operate GPIO.

Repeated alarm-enabled requests mean keep the alarm enabled, not replay a new
sound on every frame. SG6 owns physical buzzer/display implementation, cooldown
and the agreed fault indication. Actual Jetson boot, software and camera must
be checked on the platform, not inferred from PC results.

The legacy adapter emits exactly `driver_state`, `alert` and `confidence` only
for usable observations. Here legacy confidence explicitly means observation
quality. It raises on invalid/stale input because that old payload has no field
for unavailable evidence. Do not call the proposed v2 contract team-approved
until SG6 and the dependent subgroup owners accept it.

## Limitations and the next decision

- Only two synthetic labelled drives support the method comparison; real video is unlabelled.
- Thresholds and weights are engineering settings, not clinically validated fatigue criteria.
- The SG3 causal/pixel-geometry adapter and its thresholds need owner review and calibration.
- Native hard-state encodings represent availability, not calibrated eye/yawn probabilities or a validated P80 closure measurement.
- Temporal windows and confirmation delay can postpone recognition of gradual drowsiness and recovery.
- Holding a state on unavailable data does not reveal the true driver state; status and fault handling are essential.
- The SG6 handoff is PC-tested, not proof of Jetson performance or hardware operation.

Next: obtain subgroup-owner acceptance of the adapters and status contract,
collect independent labelled recordings, measure false-alert duration and missed
episodes, compare threshold/recovery settings without reusing the final test
set for selection, and verify SG6 execution on the actual embedded platform.

## Both members must be ready

Each member should explain a packet from SG4, the score and state timers, one
test, one metric, a failure case and the SG6 output. Explain actual individual
contributions, linked commits/issues and real coordination evidence. Do not
invent a split of work, meetings or hardware checks merely to fill a rubric.

The midterm marking structure is A 15 for subgroup technical work, B 10 for
shared repository/board/documentation/coordination, and C 5 for shared embedded
readiness. Evidence supports assessment; it does not guarantee an awarded score.
