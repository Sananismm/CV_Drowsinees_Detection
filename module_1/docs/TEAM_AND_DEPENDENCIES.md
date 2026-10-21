# Team and Module Dependencies

Roster source: group allocation image provided by Muhammad Sharjeel Hanif.
Confirm all names before formal publication.

## Group 1 - Driver Drowsiness Monitoring

| Subgroup | Scope | Members |
|---|---|---|
| SG-1 | Face/Landmarks | Muhammad Sharjeel Hanif; Muhammad Bilal Maqbool |
| SG-2 | Eye/Blink Analysis | Rameen Shirazi; Syeda Maleeka Abbas |
| SG-3 | Yawn/Facial Cues | Abdul Moeed; Saad Ahmed Butt |
| SG-4 | Temporal Analysis | Saman Iqbal; Syeda Musfirah Hamid |
| SG-5 | Drowsiness Decision | Rafed Aftab; Filza Umar |
| SG-6 | Embedded/Integration | Muhammad Sanan Khan; Muhammad Sami |

This roster records assigned ownership.
It does not prove individual contribution.
Git commits and task evidence must record contribution separately.
Both SG-1 members must review the contract and demo evidence before handoff.

## Dependency direction

| Producer | Consumer | Data |
|---|---|---|
| Camera/video | SG-1 | BGR frames and timing |
| SG-1 | SG-2 | Face validity, image dimensions and eye landmarks |
| SG-1 | SG-3 | Face validity, image dimensions and mouth landmarks |
| SG-2 | SG-4 | Eye state, EAR, blink and closure evidence |
| SG-3 | SG-4 | Yawn and facial-cue evidence |
| SG-4 | SG-5 | Temporal indicators |
| SG-5 | SG-6 | Driver state and alert request |
| SG-6 | Whole system | Runtime, camera, deployment and alert execution |

## SG-1 coordination contacts

SG-1 must coordinate directly with:

- SG-2 for eye indices and invalid-face behavior.
- SG-3 for mouth indices and invalid-face behavior.
- SG-6 for schema versioning, runtime and Jetson compatibility.

SG-1 does not need SG-4 or SG-5 to finish before starting integration.

## Required shared decisions

- V1 schema fields.
- Timestamp unit.
- Coordinate convention.
- Landmark topology.
- Eye indices.
- Mouth indices.
- Invalid-face behavior.
- Camera resolution and FPS.
- Jetson Python and library versions.
- Ownership of adapters and contract tests.
