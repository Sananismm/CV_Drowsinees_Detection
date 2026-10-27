# SG5 status aware handoff for SG6

This consumer turns proposed `sg5.sg6.v2` decisions into explicit hardware
requests. It performs no GPIO, camera, network, buzzer or display operations.
The consumer uses only Python's standard library and is suitable for review
with SG6 before connecting a real hardware driver. Jetson execution and GPIO
operation of this handoff have **not been verified**. Passing the PC tests is
not proof of embedded deployment or approval of a changed team interface.

## Run a saved decision stream

From the repository root, replacing the example input with the JSONL produced
by the SG5 demo:

```powershell
python embedded_6/sg5_handoff/consume.py --input path/to/decisions.jsonl --events-only
```

Without `--input`, the consumer reads JSON lines from standard input. Without
`--events-only`, it emits a request for every decision. State changes, session
changes and observation-status changes are retained in events-only mode.
Malformed or foreign messages produce an error and exit status 2; the live
integration must treat transport/process failure as a sensor fault.

## Proposed wire contract

Every message has exactly these fields:

| Field | Type and meaning |
| --- | --- |
| `schema_version` | `sg5.sg6.v2` |
| `time_s`, `session_id` | Producer capture time in seconds and source session |
| `driver_state` | `NORMAL`, `WARNING` or `DROWSY`; untrusted if status is not OK |
| `status` | `OK`, `INSUFFICIENT_EVIDENCE` or `STALE` |
| `score`, `smoothed_score` | Engineering evidence scores in 0-1, not probabilities |
| `quality` | Observed availability/validity fraction in 0-1, not model confidence |
| `alert`, `alert_level` | Actionable warning flag and level 0/1/2; false/0 for non-OK |
| `transition`, `alert_event` | State changed, and an actionable upward transition |
| `reason`, `config_id` | Explanation and versioned decision configuration |

`hardware_request(decision)` validates this contract and returns:

- `buzzer_requested`: true only for an OK DROWSY decision.
- `visual_warning`: true for OK WARNING or DROWSY.
- `sensor_fault`: true for either non-OK status, independent of retained state.
- Capture time, session, state, status and the one-shot `alert_event` flag.

Requests are idempotent: repeated `buzzer_requested=true` means keep the alarm
enabled, not restart a sound on every 10 Hz message. SG6 must choose the actual
fault indication, driver repetition/cooldown, buzzer wiring and safe hardware
policy. A stale or insufficient result must not be shown as a fresh NORMAL
observation, even if the retained `driver_state` string is NORMAL.

## Keep the two clocks separate

The decision engine's `tick(now_s)` uses the same capture-relative clock as SG4
`time_s`. Do not pass `time.time()` or an unrelated host monotonic timestamp to
it. If the producer's capture clock cannot be advanced consistently, do not
invent a tick timestamp.

A transport can also stop delivering decisions altogether. The independent
`DeliveryWatchdog` uses **host arrival monotonic time**, not capture time:

```python
from embedded_6.sg5_handoff.consume import DeliveryWatchdog

watchdog = DeliveryWatchdog(timeout_s=1.0)
# When a validated message arrives:
request = watchdog.observe(decision)
# On the transport loop's periodic timeout, including while no input arrives:
fault = watchdog.poll()
if fault is not None:
    request = fault  # sensor_fault=True; no trusted awake result
```

The live loop must call `poll()` periodically even while the input is silent.
The file/stdin CLI is a replay/inspection tool, not a continuously polling
delivery watchdog. Before any message arrives, `poll()` reports a fault with
unknown capture time, session and state rather than fabricating observations.

## Actual upstream code and compatibility status

SG5 uses the real SG4 `TemporalEngine` from branch `saman` at
`1019abe55a5f2b24c318c01b7d9660e3597767f4`, with the `sg4.output.v1.1` fields:
`time_s`, `perclos` as a fraction over 60 seconds, `face_valid`,
`long_blinks` over 30 seconds, `yawn_count` events over 60 seconds, and ongoing
`eye_closure_s`. Native SG4 streams are tested against all five versioned golden
files. No percent-to-fraction or frame-rate-to-event-count substitution is used.

For native live SG2 hard states and the SG3 mouth adapter, SG5 preserves absent
confidence as `None` and applies a narrow explicit-availability synchronizer.
It reuses SG4's clock handling, aggregation and event trackers. The direct
in-process path adds current `eye_valid` as SG5-side metadata so a present face
with unavailable eyes cannot be treated as a valid current observation. Hard
state encodings 0/1 are availability labels, not calibrated probabilities or
validated P80 eyelid-occlusion measurements. This adapter requires SG4 owner
review. The annotated SG5 path censors the first native or hard-state frame
after a capture gap so unobserved time cannot become an eye closure.
Unannotated native reference replay preserves SG4's original behavior and goldens.

The existing SG6 Week 5 three-field payload is available from
`module_5.midterm.engine.to_legacy_sg6` only for status OK. It returns exactly
`driver_state`, `alert`, and `confidence`, where that legacy confidence field
is explicitly observation quality rather than drowsiness probability. The
adapter raises for invalid/stale results because the old format cannot express
them safely. A test checks this adapter against the actual SG6
`validate_interfaces.validate_module` from branch `sg6-week5-integration` at
`b4bf9ec42c8b5aa119eae5f78c7c499665822911`.

The proposed v2 status contract and its hardware fault policy still require SG6
acceptance. Existing subgroup sources and old SG6 checks remain unchanged.

## Collect actual platform evidence

The default collector opens no camera and does not operate GPIO:

```bash
python3 embedded_6/sg5_handoff/check_platform.py --output platform.json
```

On the actual Jetson, explicitly test its camera with:

```bash
python3 embedded_6/sg5_handoff/check_platform.py --camera 0 --frames 30 --output platform_jetson.json --strict
```

Inspect the device model, runtime scope and individual checks rather than
treating an exit code as proof of the exact 8 GB SKU, CUDA, GPIO or complete
pipeline. The checked-in `module_5/midterm/results/platform_pc.json` is explicitly
an off-target Windows diagnostic, not Jetson boot or camera evidence.
