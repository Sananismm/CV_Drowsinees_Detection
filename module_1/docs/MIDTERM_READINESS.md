# SG-1 Midterm Readiness

Last checked: 2026-10-27.

## Evidence map

| Objective | State | Evidence | Remaining risk |
|---|---|---|---|
| Runnable face/landmark baseline | Ready locally | `sg1_detector.py`, setup smoke test and five real-video reruns | Rehearse and confirm permission for the chosen clip |
| Compare alternatives | Ready | Three configurations in `experiment.json`; `MIDTERM_METHOD_DECISION.md` | Backup is the same model at a different input size |
| Quantitative evidence | Ready with limits | `MIDTERM_REAL_VIDEO_RESULTS.md` and sanitized tables | Reference boxes are AI-assisted and unreviewed; no landmark ground truth |
| Versioned interface | Implemented, not accepted | V1 contract, schema and fixtures | SG-2/SG-3/SG-6 sign-off absent |
| Failure behavior | Ready locally | `NO_FACE` fixture, black-frame test, failure CSV check | Robustness set is incomplete |
| Reproducible setup | Ready locally | lock file, verified model hash, setup script | Jetson package compatibility unknown |
| Automated checks | Ready locally | 60 unit/contract/preview tests passed on 2026-10-27; experiment verifier passed on each of five full clips and five short demo runs | Check CI for the current branch head after updates |
| Real downstream integration | Blocked | SG-2 adapter fixture exists | Neighbor modules have not accepted it |
| Jetson readiness | Not demonstrated | test plan exists | Requires SG-6 and target hardware |

## Non-negotiable claims

- Coverage is availability, not accuracy.
- Desktop FPS is not Jetson FPS.
- The configured threshold is not an observed confidence score.
- A generated demo video is not a robustness dataset.
- The V1 contract is not frozen until consumers accept it.

## External actions required

1. Confirm usage permission for a downloaded driver clip and rehearse its real-video demo.
2. SG-2 confirms eye indices and consumes both SG-2 fixtures.
3. SG-3 supplies the mouth indices it needs and consumes both SG-1 fixtures.
4. SG-6 validates fixture loading and reports Jetson environment constraints.
5. Review the current SG-1 branch changes and present the method and limitations accurately.
