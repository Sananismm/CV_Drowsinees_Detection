# SG5 midterm cross subgroup coordination record

Date: 28 October 2026. Team: G1 D2 Driver Drowsiness Monitoring.
SG5 members: Rafed Aftab and Filza Umar.

This is a technical integration record and action register, not minutes of a
new human meeting. It does not claim that the named students attended a meeting
today, approved a new schema, or authored work outside their actual contribution.

## Existing evidence and decisions carried forward

The existing
[`2026-10-27 SG4 SG5 alignment note`](meetings/2026-10-27_sg4_sg5_alignment.md)
was imported unchanged from SG4's `saman` branch. It records SG4 members Saman
Iqbal and Syeda Musfirah Hamid and SG5's written input-request table. That note
does not establish attendance by Rafed or Filza, and its unresolved acceptance
items are not silently marked complete.

For the midterm integration, SG5 implements consumption of the specified v1.1
field names and windows and verifies them against all five golden streams. This
is implementation evidence on SG5's side. The new hard-state availability
adapter, the causal SG3 adapter, and the proposed SG6 v2 fault/status contract
remain explicit proposals for owner review.

The current SG4 implementation is on `saman`, not the old `sg4` notebook branch.
SG1 is taken from `sg1`, SG2 from `sg2-midterm-integration`, SG3's reference from
`sg3`, the original SG5 baseline from `sg5`, and SG6 compatibility evidence from
`sg6-week5-integration`. Source revisions and hashes are versioned rather than
claiming that every branch was already integrated on main.

## Dependency and acceptance register

| Producer and consumer | Evidence available | Owner action and acceptance condition |
| --- | --- | --- |
| SG1 to SG2 and SG3 | Actual SG1 records and shared 478-point landmarks are used; source capture clock and IDs are retained | SG1/SG2 review the joined stream and real input validity; a null model confidence must remain null |
| SG2 to SG4 | Selected hard EAR state and `eye_valid` are available; no calibrated closure probability is provided | SG2 and SG4 review hard-state availability handling and the distinction between closure fraction and validated P80 measurement |
| SG3 to SG4 | Pixel-geometry, causal mouth-opening adapter uses SG3's reference indices and thresholds; SG4 performs its own persistence/debounce once | SG3 reviews geometry/causality changes and threshold calibration; no head-pose signal is invented |
| SG4 to SG5 | Current v1.1 fields and all five golden vectors execute through real SG4 and the new SG5 decision engine | SG4 owners review the explicit availability synchronizer and gap behavior; preserve names, units and windows |
| SG5 to SG6 | Versioned v2 JSONL, strict dry-run consumer, stale/insufficient fault status and legacy validator tests exist | SG6 owners review schema/fault semantics, implement the hardware driver and delivery polling, and record embedded execution |

The baseline import commit is `6eabe80d78f2e16c1272cd70a203024cc57830ee`.
Imported algorithm code remains attributed to its source subgroup. New SG5-side
adapters are separate files, so owner review does not require guessing which
parts of a teammate's original code were changed.

## Work tracking

Existing [issue 8](https://github.com/Sananismm/CV_Drowsinees_Detection/issues/8)
tracks the lower warning threshold/faster recovery experiment. Existing
[issue 9](https://github.com/Sananismm/CV_Drowsinees_Detection/issues/9) tracks
use of actual processed SG4 input. Both are assigned to Rafed Aftab and Filza
Umar and labelled SG-5 and W8 at the time of this audit. Their evidence should
link the final comparison, integration output, tests and review request.

An issue or board column alone is not completion evidence. A pull request or
branch link should be recorded after publication; closure should reflect the
stated acceptance condition, not merely file creation. This record does not
claim a reviewed main merge or an actively maintained group board without
corresponding GitHub evidence.

## Next actions by responsible subgroup

| Responsible subgroup | Next action | Evidence required |
| --- | --- | --- |
| SG5 Rafed Aftab and Filza Umar | Present the comparison and connected source-to-decision replay; explain actual individual contributions | Reproducible commands, immutable results/configurations, test output and truthful viva answers |
| SG4 Saman Iqbal and Syeda Musfirah Hamid | Accept or revise hard availability and gap behavior; confirm current-eye metadata | Written review or tracked interface decision, with regression tests |
| SG3 | Review the causal MAR adapter and test talking/yawn distinctions on labelled recordings | Reviewed geometry and calibrated thresholds with failure examples |
| SG6 Muhammad Sanan Khan and Muhammad Sami | Accept or revise proposed status-aware handoff and implement the target hardware policy | Target setup/run evidence, latency/memory report, timeout/fault tests and real driver logs |
| Team reviewer or lead | Review branch imports, current source pins and evidence; coordinate merge rather than overwrite main | Review record, PR decision and conflict/dependency notes |

No human deadline, meeting attendance or personal implementation history is
invented by this technical record. The assessment date is today; owner review
and target verification remain necessary even when local preparation is ready.
