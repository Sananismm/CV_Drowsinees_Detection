# SG1 to SG2 Input

SG1 detects facial landmarks from the original frame. The video demo loads `module_1/scripts/sg1_detector.py` and passes its output and the same decoded frame to SG2. SG2 uses those landmarks rather than running another detector. [Video pipeline](demo.py) [Adapter](adapters.py)

## Supported packets

SG2 accepts the repository's legacy full SG1 record, a `sg1.v1` full record, or the compact six-point-per-eye packet. Full records contain 478 normalized xy points, source dimensions, frame ID, timestamp, detection status, face box and optional observed confidence. [Parser](adapters.py) [Full-record fixture](tests/fixtures/sg1_v1_ok.json)

Compact packets contain `frame_id`, `timestamp_sec`, dimensions, face/eye validity flags, the coordinate/topology fields, ordered landmark indices and six normalized points for each eye. The eye orders are left `[33,160,158,133,153,144]` and right `[362,385,387,263,373,380]`. [Compact fixture](tests/fixtures/sg1_to_sg2_v1_ok.json) [Adapter](adapters.py)

## Timing and invalid input

Frame IDs and timestamps must increase within a video. SG1 `timestamp_ms` becomes seconds in SG2. The matching frame ID/time must agree with the packet; up to 0.002 seconds is allowed for millisecond rounding. Normalized coordinates are scaled using the original width and height. [Processor](processor.py) [Geometry](eye_analysis.py)

Malformed identity/time or synchronization mismatches raise errors. Missing faces, invalid landmarks and degenerate eye geometry produce UNKNOWN. Process the original frame before adding annotations, and create a new processor for each recording. [Adapter](adapters.py) [Processor](processor.py) [Tests](tests/test_sg2.py)

## Example run

`P1042801_720.mp4` produced 590 SG1, SG2 and SG4 records and 590 annotated video frames. The run used the actual SG1 detector with fresh input, EAR 0.15 and the existing two-frame OPEN confirmation. These are processing counts, not accuracy measurements. [Run results](results/live_integration_summary.json) [Usage](README.md)

The demo launcher uses fresh inference by default and has no cached-landmark fallback. The lower-level demo can replay JSONL only when that mode is explicitly requested. [Launcher](in_demo.py) [CLI](demo.py)
