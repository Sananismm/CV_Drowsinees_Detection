# SG6 GitHub Evidence and Task Tracker

> **Repository availability:** This report describes a Jetson worktree snapshot. The revised demo, its tests, and `embedded_6/integrated/` were local and uncommitted at the time of publication and are not present on `main`; commands that use those files require that local snapshot. Do not assume a fresh `main` checkout can run them.

Review: 28 October 2026 via GitHub branch/PR/issue listing and local source. The checkout is sg6-week5-integration at b4bf9ec; local uncommitted demo, integration and documentation changes are not evidence of a remote commit. Local remote-tracking references were stale; a direct fetch was blocked by protected Git metadata. Current GitHub branch listing reported SG6 b4bf9ec, main a5570c4, SG1 5fcb936, SG2 midterm ca73a39, SG3 e3661b7, SG4 059705b, saman 1019abe and SG5 midterm bf15c3b. Heads can change after review.

## Verified commits

| Commit | Visible message | Evidence |
|---|---|---|
| b4bf9ec | SG6: Add Jetson integration tests and face detector benchmarks | [commit](https://github.com/Sananismm/CV_Drowsinees_Detection/commit/b4bf9ec42c8b5aa119eae5f78c7c499665822911) |
| 661bd0d | doc(sg6): Mock data used | [commit](https://github.com/Sananismm/CV_Drowsinees_Detection/commit/661bd0d3898ac76c0a41f79bc5cf5242f556e4ef) |
| 02709ad | docs(sg6): add Week 5 integration pipeline documentation | [commit](https://github.com/Sananismm/CV_Drowsinees_Detection/commit/02709adbe23c35286f5752ebaf0e10a19de80dda) |

The copied SG2/SG4/SG5 reference modules remain attributed to their original subgroups; newer integrated files are a pinned snapshot, not proof of formal acceptance. See integrated/BRANCH_AUDIT.md and reference_modules/README.md in the checkout.

## Coordination evidence

- [PR #21](https://github.com/Sananismm/CV_Drowsinees_Detection/pull/21), SG5 midterm and SG6 handoff, was merged on 27 October 2026 UTC.
- [PR #2](https://github.com/Sananismm/CV_Drowsinees_Detection/pull/2), SG1 face/landmark experiment, was merged on 20 October 2026 UTC.
- [Issue #20](https://github.com/Sananismm/CV_Drowsinees_Detection/issues/20), SG5–SG6 review and hardware acceptance, was open at inspection.
- [Issue #12](https://github.com/Sananismm/CV_Drowsinees_Detection/issues/12), SG4 input/output contracts, and [issue #17](https://github.com/Sananismm/CV_Drowsinees_Detection/issues/17), SG4–SG5 contract tests, were open. These are evidence of tracked work, not evidence that owners approved the local snapshot.
- Project board and individual meeting activity were not independently verified. No SG6-specific PR was identified in the returned PR list; do not imply one exists.

## Pending coordination

Agree SG1→SG2 geometry and timestamp rules; SG3 mouth events; SG4 confidence, closure fraction and output units; SG5 stale/insufficient evidence and physical alerts. Compare pinned copies against current upstream source before refreshing. See [evaluation checklist](SG6_EVALUATION_CHECKLIST.md) for priorities and acceptance criteria. No branch merges, commits, pushes, issue updates or messages were performed for this documentation package.
