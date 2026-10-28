# SG6 Integration Interfaces

Review date: 28 October 2026. The executable snapshot is under `~/CV_Drowsinees_Detection/embedded_6/integrated/`; its provenance is in integrated/BRANCH_AUDIT.md and integrated/README.md. The primary YuNet/Haar detector demo is separate. The following describes the snapshot, not a newly agreed project-wide contract.

| Stage | Input → output | Units, nulls and limitations | Source |
|---|---|---|---|
| SG1 | Frame → sg1.v1 record: frame_id, timestamp_ms, image_width/height, status, face_bbox_xyxy, landmark_count and landmarks_xy_normalized; nullable detection_confidence | Nonnegative identity and capture milliseconds; 478 normalized xy points for OK. NO_FACE has empty points and null box. Confidence may be null and is not invented. | module_1/scripts/sg1_contract.py and sg1_detector.py |
| SG2 | SG1 landmarks → EAR and eye state plus semantic SG4 cue | Converts ms to seconds; six points per eye, dimensions for pixel geometry. OPEN/CLOSED/UNKNOWN, nullable EAR/confidence. Invalid identity/time raises; invalid geometry becomes unavailable. Selected method EAR threshold 0.15 and two-frame opening confirmation; see final_method.json. | module_2/adapters.py, processor.py, eye_analysis.py |
| SG3 | SG1 mouth points → SG5-side experimental mouth/yawn adapter | MAR is dimensionless; event based on observed duration. Snapshot adapter uses hard availability rather than calibrated yawn confidence. Not equivalent to verified full SG3 live module; head pitch unavailable. | module_5/midterm/sg3_adapter.py; integrated/README.md |
| SG4 | Proposed sg4.input.v1 JSONL or SG5 availability bridge → sg4.output.v1.1 | Input has frame_id, timestamp_ms, face/eye/mouth/head blocks, which can be null. Native schema confidence gates must not be bypassed implicitly. SG5-side synchronized_frame uses explicit hard-state availability without claiming probabilities. | interfaces/sg4_input_v1.schema.json, module_5/midterm/sg4_bridge.py |
| SG5 | SG4 temporal vector → sg5.sg6.v2 decision | time_s, face_valid, perclos, eye_closure_s, long_blinks and yawn_count are required. Status indicates OK, insufficient evidence or stale; inspect status before interpreting state/alert. | module_4/src/sg4/sg5_output.py, module_5/midterm/engine.py |

## Timing, temporal output and required distinctions

The proposed SG4 input uses monotonic capture timestamps in milliseconds; video mode derives time from frame index and reported video FPS, whereas camera mode uses monotonic elapsed capture time. Never mix time bases. SG4 output uses seconds and a fractional perclos from 0 to 1, plus counts and closure seconds. Its schema describes 10 Hz output, 60-second PERCLOS and yawn windows, 30-second long-blink window, and no-data face_valid=0. Written confirmation of the SG4→SG5 agreement remains pending per the schema. The older notebook reference uses 0–100 PERCLOS, so convert only in an explicitly tested adapter; do not pass 20 where 0.20 is expected. Binary eye state used by this bridge is a closure indicator, not a validated P80 eyelid-occlusion measurement.

A record must carry a valid integer frame_id and timestamp; missing/negative identity or time is rejected rather than guessed. The pipeline checks SG1 records. Missing face and invalid eyes produce UNKNOWN/insufficient evidence, and SG5 has explicit stale/quality handling. The SG5 output contains a state even when status is not OK: consumers must honor status, not treat that state as current reliable evidence. SG4 ignores duplicate/out-of-order timing under its specified policy and flags gaps over 200 ms. Inherited timing and reset behavior must be assessed with subgroup owners under real frame rates.

## Integration status and gaps

- **Fixtures:** Integration/validate_interfaces.py checks SG6 mock format and warns when landmark lists are empty; it does not verify subgroup contracts.
- **Synthetic actual-module path:** integrated/tests/test_pipeline.py checks SG1 record validation, SG2 eye cues, SG4/SG5 propagation, timestamps, synthetic mouth opening, prolonged closure, invalid landmarks and missing face. Four tests passed in the earlier 28 October session.
- **Recorded video:** integrated/README.md documents 120 frames through SG1–SG5 at roughly 14 FPS; no raw execution log was located for this review. Treat this as a documented historical observation.
- **Live:** the optional run_integrated.py contains a camera path, but a live capture-to-decision run is not evidenced. The main YuNet demo has no live SG2–SG5 wiring; YuNet's five points cannot provide SG2 EAR.
- **Pending:** owner acceptance of SG1/SG2 mapping, SG3 mouth semantics, SG4 input confidence and PERCLOS interpretation, SG5 status/alert handling, physical hardware and real-device robustness. Copies do not update automatically with upstream branches. Sources are owned by their respective subgroups.


**Fixture provenance clarification:** The SG1 positive landmark fixture used in these controlled tests was generated from an existing tracked SG1 sample image, not generated entirely from artificial landmarks. Tests alter those coordinates and use synthetic frames/scenarios; they do not prove live camera-to-decision operation or accuracy. See the upstream `module_1/scripts/generate_interface_fixtures.py` and `interfaces/examples/sg1_v1_ok.json` on the main branch.
