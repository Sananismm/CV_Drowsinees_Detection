# SG-1 Decision Log

Use this file for decisions that affect code, data, interfaces or integration.

## D-001 - Use MediaPipe Face Landmarker

Date: 2026-10-07

Status: Accepted for prototype.

Reason:

- Produces a dense face mesh.
- Supports VIDEO mode.
- Provides eye and mouth geometry.
- Runs fast enough for desktop experiments.

Limits:

- Jetson compatibility is not confirmed.
- The high-level result has no observed face-confidence value.

## D-002 - Configure one face

Date: 2026-10-07

Status: Accepted.

Reason:

- The camera targets one driver.
- It reduces unnecessary work.

Risk:

- A passenger or background face may be selected in a poor camera view.

## D-003 - Use landmark-derived face box

Date: 2026-10-07

Status: Accepted for prototype.

Reason:

- The Face Landmarker output already contains face geometry.
- No second detector is needed.

Limit:

- The box is not an independent detector output.
- Manual box conventions can differ from landmark bounds.

## D-004 - Keep observed confidence null

Date: 2026-10-07

Status: Accepted.

Reason:

- The API does not expose a per-face observed confidence.
- Configured thresholds are not measured scores.

Integration effect:

- Downstream modules must use validity state.
- They must not require fabricated confidence.

## D-005 - Carry 192 px forward as provisional candidate

Date: 2026-10-07

Status: Provisional.

Reason:

- Same observed coverage on the current clips.
- Same 20-frame box metrics.
- Higher desktop throughput.

Required before final acceptance:

- More labels.
- More difficult conditions.
- Jetson comparison.

## D-006 - Keep JSONL for saved experiments

Date: 2026-10-21

Status: Implemented draft. Consumer acceptance pending.

Reason:

- One record maps to one frame.
- It supports streaming writes.
- It is readable by all groups.

Live integration:

- Use the same dictionary in memory.
- Do not write and reread JSON for every live frame.

## D-007 - Version the interface

Date: 2026-10-21

Status: Proposed.

Decision:

- Emit `schema_version`.
- Emit `landmark_topology`.
- Use `sg1.v1` for the implemented draft.
- Do not call V1 frozen until SG-2, SG-3 and SG-6 accept it.

Open question:

- Whether SG-1 also emits explicit eye and mouth ROI fields.

## D-008 - Separate fallback demonstration from accuracy evidence

Date: 2026-10-21

Status: Accepted.

Decision:

- Build a reproducible local fallback from the tracked qualitative image.
- Use it to demonstrate setup, overlays, output records and failure handling.
- Do not use it for precision, recall or robustness claims.

Reason:

- The approved raw Week 5 videos are not present locally.
- Generated or repeated frames are not a valid substitute for benchmark data.
