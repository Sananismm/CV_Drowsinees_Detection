# SG-1 Midterm Readiness

Last checked: 2026-10-21.

## Evidence map

| Objective | State | Evidence | Remaining risk |
|---|---|---|---|
| Runnable face/landmark baseline | Ready locally | `sg1_detector.py`, setup smoke test | Windows only in this run |
| Compare alternatives | Ready | Three configurations in `experiment.json` | Fallback video is not benchmark data |
| Quantitative evidence | Ready with limits | Week 5 records and `results/midterm_demo/comparison.csv` | Small label set; no landmark ground truth |
| Versioned interface | Implemented, not accepted | V1 contract, schema and fixtures | SG-2/SG-3/SG-6 sign-off absent |
| Failure behavior | Ready locally | `NO_FACE` fixture, black-frame test, failure CSV check | Robustness set is incomplete |
| Reproducible setup | Ready locally | lock file, verified model hash, setup script | Jetson package compatibility unknown |
| Automated checks | Ready locally | 31 tests and experiment verifier | No remote CI run yet |
| Real downstream integration | Blocked | SG-2 adapter fixture exists | Neighbor modules have not accepted it |
| Jetson readiness | Not demonstrated | test plan exists | Requires SG-6 and target hardware |

## Non-negotiable claims

- Coverage is availability, not accuracy.
- Desktop FPS is not Jetson FPS.
- The configured threshold is not an observed confidence score.
- A generated demo video is not a robustness dataset.
- The V1 contract is not frozen until consumers accept it.

## External actions required

1. Sharjeel or Bilal supplies an approved raw driver clip.
2. SG-2 confirms eye indices and consumes both SG-2 fixtures.
3. SG-3 supplies the mouth indices it needs and consumes both SG-1 fixtures.
4. SG-6 validates fixture loading and reports Jetson environment constraints.
5. A team member reviews the local diff before commit and pull request.
