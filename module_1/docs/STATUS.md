# SG-1 Status

Last updated: 2026-10-27

Overall status: **AMBER**

The detector exists.
The environment is installed.
The interface is not accepted.
Real downstream integration is not complete.

## Completed

- [x] SG-1 Week 5 implementation recovered.
- [x] Current `main` merged into the shared `sg1` branch.
- [x] Python 3.12 virtual environment created.
- [x] Dependencies installed.
- [x] Imports verified.
- [x] `pip check` passed.
- [x] Face Landmarker model downloaded.
- [x] Model SHA-256 recorded.
- [x] Exact dependency lock recorded.
- [x] Existing scripts compile.
- [x] Three configuration experiment documented.
- [x] Preliminary desktop metrics documented.
- [x] Core documentation set created.
- [x] `schema_version` and `landmark_topology` emitted by the detector.
- [x] Draft 2020-12 JSON Schema added and tested.
- [x] Real positive and standard no-face fixtures added.
- [x] Runtime output validator added.
- [x] SG-2 and SG-3 adapter helpers added.
- [x] Automated unit and contract tests added.
- [x] Experiment consistency verifier added.
- [x] Generated fallback video processed under all three configurations.
- [x] Fallback experiment evidence verified.
- [x] Path-scoped pull-request checks added.
- [x] Machine-oriented SG-2 and SG-3 integration handoffs added.
- [x] Five downloaded clips rerun under all three configurations; each full run and a 100-frame annotated demo per configuration passed the experiment verifier.
- [x] Provisional reference-box provenance, primary/backup decision and current real-video summary documented.

## In progress

- [ ] Human review of code and documentation.
- [ ] Midterm rehearsal.
- [ ] Confirm usage permission and rehearse the downloaded-video demonstration.
- [ ] Independently review the 20 AI-assisted reference boxes.

## Blocked by team agreement

- [ ] Freeze eye landmark indices with SG-2.
- [ ] Freeze mouth landmark indices with SG-3.
- [ ] Accept `face_valid` behavior.
- [ ] Update SG-6 mock schema.
- [ ] Mark V1 as frozen.

## Not started

- [ ] Real SG-1 to SG-2 integration.
- [ ] Real SG-1 to SG-3 integration.
- [ ] Expanded robustness dataset.
- [ ] Jetson deployment.
- [ ] Jetson profiling.

## Immediate next actions

1. Confirm permission for a downloaded driver video and rehearse the prepared demonstration.
2. Have Bilal review this branch.
3. Meet SG-2, SG-3 and SG-6 with the fixtures.
4. Record interface acceptance or requested changes.
5. Connect one real frame to SG-2 and SG-3.
6. Rehearse the midterm demonstration.
7. Keep the shared SG-1 branch and its evidence up to date.

## Known risks

- The current 20-frame label set is small.
- All current box labels appear to contain faces.
- Landmark accuracy is not measured.
- The selected 192 px setting is not tested on Jetson.
- MediaPipe installation on the final Jetson image is not confirmed.
- The public qualitative image contains identifiable people.
- The interface documents a proposal, not team acceptance.
- The fallback midterm video is generated from a tracked image and is not accuracy evidence.
- Check the current branch head and its CI result when presenting; prior CI success does not verify subsequent changes.
