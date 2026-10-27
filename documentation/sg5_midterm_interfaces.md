# SG5 midterm interface handoff

Updated 28 October 2026. SG5 members: Rafed Aftab and Filza Umar, driver
drowsiness team G1 D2. The implementation consumes the current SG4 v1.1
temporal vector, produces a status-aware proposed SG6 v2 decision, and keeps
the old three-field SG6 output available only for usable observations.

The source revisions and original Git-blob SHA-256 values are recorded in
[`integration/sg5_midterm_sources.json`](../integration/sg5_midterm_sources.json).
The snapshots were imported at `6eabe80d78f2e16c1272cd70a203024cc57830ee` on
`sg5-midterm-integration`; this does not establish that the branch was reviewed
or merged into main.

## Executed module boundary

The integration imports SG1's actual detector and record validator, SG2's
selected EAR processor, SG4's actual `TemporalEngine`, and SG5's new headless
decision engine. A causal SG3-side adapter reuses the teammate's mouth indices,
geometry and thresholds while sharing SG1's landmarks. It is an explicit
adaptation, not an unchanged execution of the Colab script.

The runtime sequence is SG1 frame record to SG2 eye state and SG3 mouth state,
then synchronized SG4 cue, SG4 temporal vector, SG5 decision and SG6 hardware
request. All streams preserve frame identity and source timing. A shared source
frame is processed once; frame IDs or timestamps are not invented to join
unrelated observations.

## SG4 v1.1 consumer contract

The producer is `module_4/src/sg4/engine.py` from branch `saman` at
`1019abe55a5f2b24c318c01b7d9660e3597767f4`. The older `sg4` branch notebook
uses different fields and units and is not the integration target.

| Field | Meaning consumed by SG5 |
| --- | --- |
| `time_s` | Increasing SG1 capture timestamp in seconds |
| `perclos` | Fraction 0-1 of valid eye-closed time in the last 60 seconds, not percent |
| `face_valid` | Integer 0/1 for the current face observation |
| `long_blinks` | Eye-closure events of at least 0.5 seconds in the last 30 seconds |
| `yawn_count` | Debounced yawn events in the last 60 seconds, not yawn frames |
| `eye_closure_s` | Duration of the current ongoing closure; zero when open or invalid |

SG5-side consumption of these names, types and units is implemented and tested.
All five committed native SG4 mock streams are executed through the actual
engine and compared exactly with `interfaces/mocks/sg5_expected/*.jsonl`.
This verifies implementation compatibility; it does not invent a human approval
or meeting attendance. SG4's original alignment note remains unchanged.

SG4 extras such as `validity_score`, `calibrating` and `nod_count` retain their
producer meanings. `validity_score` describes valid eye observations over a
historical window, not a model's certainty or current face visibility.
Calibration changes SG4 baseline extras, not the validity of its six primary
fields. SG5 does not force early observations to NORMAL merely because SG4 is
calibrating.

The old synthetic generator uses a 30-second PERCLOS window; the actual current
SG4 implementation uses 60 seconds. Identical field names therefore do not make
these two data distributions equivalent. Weights and thresholds selected on the
synthetic drives require re-evaluation on the real SG4 stream; synthetic scores
must not be reported as accuracy of the connected video pipeline.

## Explicit hard-state availability adapter

SG2's selected EAR method provides `OPEN`, `CLOSED` or `UNKNOWN` and an
`eye_valid` flag. It does not provide calibrated closure probability, and the
actual SG1 detector confidence can be null. SG3's adapter similarly provides
mouth availability and an active mouth-opening flag, not yawn probability.

`module_5/midterm/sg4_bridge.py` preserves these absent confidence values as
`None`. Its narrow `AvailabilitySynchronizer` retains SG4's original timestamp,
duplicate, ordering and gap handling, but uses genuine hard-state availability
flags instead of inventing numeric confidence to pass the old gate. The real
SG4 aggregation, duration tracking, debounce and writer are unchanged.
Internal 0/1 hard-state encodings are not calibrated probabilities or validated
P80 eyelid-occlusion measurements.

The direct in-process path adds `eye_valid`, `quality_kind` and
`availability_source` as SG5-side metadata. These additions are not silently
published as new fields of the frozen SG4 wire schema. In particular,
`face_valid=1` with `eye_valid=false` is unusable even if the historical
`validity_score` remains high. Consumers of a bare six-field recording do not
receive that additional current-eye observation and must not claim otherwise.

The annotated SG5 consumer path censors the first observation following a
capture gap over SG4's configured 200 ms, for both native SG4 cues and the
hard-state transport. This breaks unsupported eye, mouth and head runs rather
than turning unobserved time into a long closure. A present face does not make
that first post-gap eye observation usable. The next uninterrupted frame may
start a new closure, but cannot inherit the missing interval.

Unannotated native reference replay (`iter_temporal` with its default
`annotate_eye_valid=False`) retains the original SG4 behavior and exact golden
parity. Enabling annotations for the actual SG5 consumer also enables its native
gap guard. These two modes are explicit and tested separately; SG4's original
source and schema are unchanged. Native SG4's event trackers use absolute
timestamps, so its upstream gap policy still needs owner review.

The availability adapter is implemented and tested on PC but still requires
SG4 semantic acceptance. SG3's causal pixel-geometry adaptation and threshold
calibration separately require SG3 review.

## SG5 proposed SG6 v2 output

`DecisionEngine.step(vector)` returns exactly fourteen fields:

| Field | Type and interpretation |
| --- | --- |
| `schema_version` | `sg5.sg6.v2` |
| `time_s` | Capture-clock seconds for this observation or tick |
| `session_id` | Nonempty source session identifier |
| `driver_state` | `NORMAL`, `WARNING` or `DROWSY`; retained state is untrusted when status is not OK |
| `status` | `OK`, `INSUFFICIENT_EVIDENCE` or `STALE` |
| `score` | Current weighted engineering evidence score, 0-1 |
| `smoothed_score` | Smoothed engineering evidence score, 0-1 |
| `quality` | Observation availability/validity fraction, 0-1, not drowsiness probability |
| `alert` | True for actionable WARNING/DROWSY only while status is OK |
| `alert_level` | Actionable 0/1/2; always 0 while status is not OK |
| `transition` | Whether the retained driver state changed |
| `alert_event` | True only for an actionable upward state transition |
| `reason` | Nonempty explanation |
| `config_id` | Versioned rules identifier |

No learned probability is claimed. Risk scores must not be renamed confidence.
`INSUFFICIENT_EVIDENCE` and `STALE` suppress a trusted drowsiness action and
raise a distinct sensor-fault request. This proposed fault policy requires SG6
acceptance before actual hardware use; it is not a validated safety policy.

## SG6 consumer and legacy compatibility

`embedded_6/sg5_handoff/consume.py` strictly validates the proposed v2 shape and
returns hardware requests without GPIO or sound side effects:

| Request | Condition |
| --- | --- |
| `buzzer_requested` | Status OK and state DROWSY |
| `visual_warning` | Status OK and state WARNING or DROWSY |
| `sensor_fault` | Status INSUFFICIENT_EVIDENCE or STALE |

Repeated requests are idempotent, not commands to restart an alarm at 10 Hz.
The status-aware consumer and the hardware repetition/fault policy still need
SG6 owner approval. Hardware and Jetson execution of this new handoff are
not verified.

`to_legacy_sg6(decision)` provides exactly `driver_state`, `alert` and
`confidence` for status OK. The legacy name confidence means observed quality
here, not model probability. The adapter raises for stale/insufficient results
because the old three-field format cannot represent them. Tests execute SG6's
actual `validate_interfaces.validate_module("sg5", payload)` against this
legacy adapter. Passing that validator proves structural compatibility only.

## Clock and stream lifecycle

Use one engine per continuous driver session. A new session explicitly resets
state and may restart the capture clock. Observations within a session must
have increasing capture timestamps; ordinary same-session source gaps restart
confirmation evidence.

`DecisionEngine.tick(now_s)` uses the same capture clock as SG4 `time_s`, not
host wall time. Separately, `DeliveryWatchdog.observe/poll` uses host monotonic
arrival time to detect a stopped decision transport. SG6 must poll while no
message is arriving; the offline file/stdin CLI is not a live watchdog loop.
Before the first message or after a delivery timeout, do not display a retained
NORMAL string as a fresh awake observation.

## Reproduce the boundary tests

From the repository root with the core dependencies installed:

```powershell
python -m unittest module_5.midterm.tests.test_sg4_bridge module_5.midterm.tests.test_sg6_contract -v
```

The tests cover all five native goldens, current-eye invalidity, real closure
and yawn aggregation, mismatched identities/times, ordering/gap behavior,
all five real SG4 streams through SG5 and SG6, strict message validation,
legacy compatibility, stale transport, stdin and empty-input fault handling.
