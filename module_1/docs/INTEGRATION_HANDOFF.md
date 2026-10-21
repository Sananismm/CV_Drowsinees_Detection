# SG-1 Integration Handoff

## Handoff targets

Direct targets:

- SG-2 Eye/Blink Analysis.
- SG-3 Yawn/Facial Cues.

Integration owner:

- SG-6 Embedded/Integration.

## What SG-1 hands over

- Reviewed code commit.
- V1 interface contract.
- Exact dependency lock.
- Model source and checksum.
- Experiment configuration.
- Full positive fixture.
- `NO_FACE` fixture.
- Malformed fixture.
- Contract tests.
- Known limitations.
- Demo command.

Current local artifact locations:

- Contract: `module_1/docs/INTERFACE_CONTRACT.md`
- Machine schema: `interfaces/sg1_v1.schema.json`
- SG-1 fixtures: `interfaces/examples/sg1_v1_*.json`
- Proposed SG-2 packets: `interfaces/examples/sg1_to_sg2_v1_*.json`
- Runtime validator and adapters: `module_1/scripts/sg1_contract.py`
- Automated tests: `module_1/tests/`
- Setup check: `module_1/scripts/verify_setup.py`
- SG-2 AI handoff: `interfaces/SG1_TO_SG2_AI_HANDOFF.md`
- SG-3 AI handoff: `interfaces/SG1_TO_SG3_AI_HANDOFF.md`

The handoff is not complete until these files are in a reviewed commit.

## Torch-pass sequence

1. SG-1 gets the local diff reviewed by both SG-1 members.
2. SG-1 commits the reviewed files on the team's shared SG-1 module branch.
3. SG-1 opens or updates the pull request.
4. SG-2, SG-3 and SG-6 check out that exact commit.
5. Each consumer runs the SG-1 contract tests.
6. SG-2 runs both proposed SG-2 packet fixtures through its module.
7. SG-3 records its required mouth indices, then runs both SG-1 fixtures.
8. SG-6 tests version rejection and both valid states.
9. Owners record the commit SHA and result in the meeting table.
10. Only then may the team label `sg1.v1` as frozen.

Consumer pre-check from the repository root:

```powershell
module_1\.venv\Scripts\python.exe -m unittest module_1.tests.test_contract -v
module_1\.venv\Scripts\python.exe module_1\scripts\validate_output.py interfaces\examples\sg1_v1_ok.json
module_1\.venv\Scripts\python.exe module_1\scripts\validate_output.py interfaces\examples\sg1_v1_no_face.json
```

## Required SG-2 actions

1. Read `INTERFACE_CONTRACT.md`.
2. Confirm eye landmark indices.
3. Accept normalized `[x,y]` arrays.
4. Stop expecting landmark objects with `.x` and `.y`.
5. Convert `timestamp_ms` to seconds only inside the SG-2 adapter.
6. Return `UNKNOWN` for invalid SG-1 records.
7. Run EAR on a real SG-1 result.
8. Preserve frame ID and timestamp.
9. Add a contract test.
10. Record acceptance.

## Required SG-3 actions

1. Read `INTERFACE_CONTRACT.md`.
2. Confirm mouth landmark indices.
3. Replace synthetic-only input with a real SG-1 adapter.
4. Calculate MAR or the selected cue from SG-1 landmarks.
5. Return invalid or unknown for `NO_FACE`.
6. Preserve frame ID and timestamp.
7. Add a contract test.
8. Record acceptance.

## Required SG-6 actions

1. Replace the old SG-1 mock schema.
2. Use `status` instead of `face_detected`.
3. Use `face_bbox_xyxy` instead of `face_bbox`.
4. Do not require numeric `face_confidence`.
5. Validate the schema version.
6. Test an `OK` record.
7. Test a `NO_FACE` record.

## Acceptance test

The handoff passes when one saved frame follows this path:

```text
Frame
  -> SG-1 face and landmarks
  -> SG-2 EAR and eye state
  -> SG-3 MAR and facial cue
```

Required checks:

- Same frame ID in all outputs.
- Same timestamp in all outputs.
- No second face detector.
- Valid landmark indices.
- `NO_FACE` becomes unknown or invalid.
- No false closure or yawn from missing data.

## Handoff meeting record

Complete this table during the interface meeting.

| Item | Owner | Status | Commit / evidence |
|---|---|---|---|
| SG-1 schema reviewed | SG-1 | Pending | |
| Eye indices accepted | SG-2 | Pending | |
| Mouth indices accepted | SG-3 | Pending | |
| Mock schema updated | SG-6 | Pending | |
| Positive fixture passes | SG-2/SG-3 | Pending | |
| No-face fixture passes | SG-2/SG-3 | Pending | |
| V1 frozen | Team | Pending | |

## Completion rule

Documentation alone is not a handoff.
At least one real SG-1 output must run through SG-2 and SG-3.
