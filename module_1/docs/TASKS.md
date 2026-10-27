# SG-1 Task Board

Update this file with the GitHub project board.
Every task needs an owner and evidence.

## P0 - Before midterm

| Task | Owner | Status | Evidence |
|---|---|---|---|
| Review new SG-1 documentation | Sharjeel, Bilal | In progress | `docs/README.md` |
| Add schema fields to detector output | Sharjeel | Review | `scripts/sg1_detector.py`; tests pass |
| Add machine-readable JSON schema | Sharjeel | Review | `interfaces/sg1_v1.schema.json`; schema tests pass |
| Add full positive fixture | Sharjeel | Review | `interfaces/examples/sg1_v1_ok.json` |
| Add no-face fixture to shared interfaces | Sharjeel | Review | `interfaces/examples/sg1_v1_no_face.json` |
| Add setup verification command | Sharjeel | Review | `scripts/verify_setup.py`; local PASS |
| Add unit tests | Sharjeel, Bilal | Review | 60 tests pass locally; confirm CI for current head |
| Run generated fallback demo | Sharjeel | Review | `results/midterm_demo/comparison.csv`; verifier PASS |
| Run downloaded-video demo | Sharjeel, Bilal | Review | Five clips processed; verify usage permission and rehearse |
| Review reference boxes independently | SG-1 | Todo | 20 AI-assisted boxes, human review pending |
| Review interface with SG-2 | SG-1 and SG-2 | Blocked | Requires SG-2 acceptance record |
| Review interface with SG-3 | SG-1 and SG-3 | Blocked | Requires SG-3 mouth-index decision |
| Update SG-6 mock schema | SG-1 and SG-6 | Blocked | Requires SG-6 branch and review |
| Prepare midterm demonstration | Sharjeel, Bilal | In progress | `docs/MIDTERM_DEMO.md`; rehearsal pending |
| Review shared SG-1 branch evidence | Sharjeel, Bilal | In progress | Review current branch head and results |

## P1 - Integration gate

| Task | Owner | Status | Evidence |
|---|---|---|---|
| Connect real SG-1 output to SG-2 | SG-1 and SG-2 | Blocked | Adapter and real fixture ready; SG-2 acceptance absent |
| Connect real SG-1 output to SG-3 | SG-1 and SG-3 | Blocked | Generic adapter ready; mouth indices and acceptance absent |
| Preserve frame ID and timestamp | SG-1, SG-2, SG-3 | Review | Adapter tests pass locally |
| Test invalid-face propagation | SG-1, SG-2, SG-3 | Review | SG-2 no-face fixture and adapter test pass locally |
| Replace duplicate downstream detection | SG-2 and SG-3 | Blocked | Downstream code change belongs to SG-2/SG-3 |
| Freeze V1 interface | Team | Blocked | Consumer acceptance absent |

## P2 - Robustness and Jetson

| Task | Owner | Status | Evidence |
|---|---|---|---|
| Expand manual labels | SG-1 | Todo | Label manifest |
| Add no-face negatives | SG-1 | Todo | Metrics |
| Test profile pose | SG-1 | Todo | Results |
| Test glasses and occlusion | SG-1 | Todo | Results |
| Test lighting and blur | SG-1 | Todo | Results |
| Run on Jetson | SG-1 and SG-6 | Todo | Run log |
| Compare 192 px and 256 px on Jetson | SG-1 and SG-6 | Todo | Metrics table |
| Record memory and compute use | SG-6 with SG-1 | Todo | Profile log |

## Status rules

- `Todo`: no work started.
- `In progress`: an owner is actively working.
- `Blocked`: the blocker and owner are recorded.
- `Review`: implementation exists and needs review.
- `Done`: evidence is linked and accepted.

Do not mark a task done because a document says it should exist.
Mark it done only when the evidence exists.
