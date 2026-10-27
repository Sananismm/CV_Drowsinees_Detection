# SG5 midterm readiness and remaining work

Updated 28 October 2026. SG5: Rafed Aftab and Filza Umar, G1 D2 driver
drowsiness team. This status distinguishes local evidence from human interface
acceptance and target-hardware verification. GREEN means the stated PC check
exists and passes, not that the whole driving system is deployment validated.

## Published midterm evidence

- Review request: [PR 21](https://github.com/Sananismm/CV_Drowsinees_Detection/pull/21), branch `sg5-midterm-integration`.
- Verification: `module_5/midterm/results/verification.json` records **255 passing tests**: 96 SG5/handoff, 114 SG1/SG4 and 45 SG2. SG2 tests use a separate existing Torch environment; the selected connected EAR path needs no Torch.
- Real saved-video execution: **2,932 frames and 1,173 validated SG6 packets** across all five shared clips. Outputs were NORMAL or WARNING with status OK; independent drowsiness labels are unavailable.
- Linux software CI passed on implementation commit `5f75731959826bc124794926304cb684a42ac534`: [recorded Actions run](https://github.com/Sananismm/CV_Drowsinees_Detection/actions/runs/40593372996).
- The [team board](https://github.com/users/Sananismm/projects/2) tracks software review in issues 8, 9 and 19; [issue 20](https://github.com/Sananismm/CV_Drowsinees_Detection/issues/20) retains blocked external acceptance and hardware evidence. No reviewed merge or hardware completion is implied.

| Area | Status | Evidence and limitation |
| --- | --- | --- |
| Current subgroup source availability | GREEN | Pinned SG1, selected SG2, SG3, current SG4 on `saman`, legacy SG5 and SG6 code are present; hashes and source revisions are recorded |
| SG4 six-field v1.1 consumption | GREEN | Actual `TemporalEngine` execution and all five native golden streams match exactly and validate against the real schema |
| Current eye availability | GREEN on PC | Annotated native and hard-state bridge paths censor first post-gap cues, distinguish current invalid eyes from historical validity, preserve null confidences, and reject mismatched frames/times; unannotated native reference replay remains unchanged |
| SG5 importable decision core | GREEN on PC | Headless standard-library engine, explicit observation status, session reset, timing and strict input checks |
| SG6 legacy structural compatibility | GREEN on PC | Actual existing SG6 validator accepts the three-field adapter for usable decisions; invalid/stale adaptation raises |
| Proposed SG6 v2 consumer | GREEN on PC, acceptance AMBER | Strict JSONL consumer, explicit fault requests and separate arrival watchdog; no GPIO side effects |
| SG4 hard-state availability semantics | AMBER | Adapter is explicit and tested but needs SG4 owner acceptance; hard state is not calibrated P80 probability |
| SG3 portable causal adapter | AMBER | Shared landmarks, pixel geometry and causal processing are implemented; owner review and real-video threshold calibration remain |
| Real-video accuracy | AMBER | An unlabelled connected execution can demonstrate processing and output, not drowsiness detection accuracy |
| Target Jetson execution | NOT VERIFIED | No new SG5 boot, memory, target FPS, GPIO or camera-delivery measurement is claimed |
| Main-branch integration | REVIEW REQUIRED | Work is prepared on `sg5-midterm-integration`; a feature branch is not evidence of reviewed merge into main |

## Delivered technical evidence

The preserved legacy A/B/C decision functions remain under
`module_5/SG5_drowsiness_decision`. The new package lives under
`module_5/midterm` and does not overwrite the reference algorithms. The
evaluation compares unchanged baseline predictions with explicitly named
candidate configurations on identical fixed development inputs. It keeps
ground-truth labels out of decision calls.

`module_5/midterm/results/evaluation/evaluation.json` records the input hashes,
configurations, environment, baseline parity and metric definitions. The newer
event protocol uses strict one-to-one predicted onsets inside labelled episodes;
it intentionally differs from the old five-second grace/overlap counting.
Changes in those event counts must not be presented as algorithm improvements.
UNKNOWN or unavailable outputs remain errors in sample metrics rather than
being silently removed from denominators.

SG4 uses a real 60-second PERCLOS window; the old synthetic drives use 30 seconds.
The old scores and thresholds are therefore development starting points, not a
calibrated decision boundary for the new real-video source. Faster recovery or
lower warning thresholds are parameter experiments, not proof of better real
driver detection. See `documentation/sg5_midterm_interfaces.md` for exact units
and the boundary-specific qualifications.

## Open work linked to existing SG5 issues

| Work item | Current evidence | Remaining action |
| --- | --- | --- |
| [Issue 8 Lower warning threshold and faster recovery](https://github.com/Sananismm/CV_Drowsinees_Detection/issues/8) | The evaluation includes a named candidate with warning entry 0.18, warning exit 0.12 and recovery delay 1.5 seconds alongside the stable defaults | Review measured trade-offs, record the selected next configuration, and link evidence before closing |
| [Issue 9 Use processed SG4 input](https://github.com/Sananismm/CV_Drowsinees_Detection/issues/9) | Real SG4 code is imported, its v1.1 goldens are verified, and a direct SG1/SG2/SG3-to-SG4 path is implemented | Obtain adapter/consumer acceptance and distinguish recorded video integration from labelled accuracy and embedded deployment |

Both issues are existing team work items. Assignees identify responsibility,
not proof that either student personally authored every imported implementation.
Individual contributions must be explained truthfully by both members.

## Embedded evidence boundary

`embedded_6/BENCHMARK_RESULTS.md`, inherited from SG6, reports a Jetson Orin Nano
face-detector comparison on 150 private recorded 640x480 frames. It reports
Haar 31.65 ms and YuNet 17.89 ms mean inference time, excluding acquisition and
downstream eye, yawn, temporal and SG5 stages. These are SG6's reported figures;
this preparation has not reproduced that run or inspected its private frames.
The old SG6 README's hardware-unavailable wording is stale relative to the
benchmark file, so neither file should be used to invent current device access.

For SG5 target acceptance, SG6 still needs to record the actual device/software
environment, dependency installation, command, model hashes, capture/processing
timing scopes, measured mean/p95 latency, throughput, memory, and fault/alert
behavior. No Jetson boot, USB-camera presence or buzzer wiring is verified here.

## Acceptance decisions needed

1. **SG4 owners Saman Iqbal and Syeda Musfirah Hamid:** review the hard-state
   availability gate and post-gap censoring while retaining frozen v1.1 fields.
2. **SG3:** review causal pixel-coordinate MAR adaptation and calibrate its
   inherited thresholds using independently labelled clips.
3. **SG6 owners Muhammad Sanan Khan and Muhammad Sami:** accept or revise the
   proposed v2 observation status and fault policy, then test the driver on the
   actual embedded target.
4. **SG5 Rafed Aftab and Filza Umar:** explain threshold/temporal trade-offs,
   evaluate on the real SG4 distribution, and record genuine individual work.
5. **Team reviewer:** inspect the integration branch and evidence, then make an
   explicit merge decision. No automatic merge or global deployment readiness
   is implied by a passing PC test suite.
