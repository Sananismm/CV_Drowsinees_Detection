# Subgroup Reference Modules

These files are reference snapshots used by SG6 to test
integration on the NVIDIA Jetson Orin Nano.

| File | Original source |
|---|---|
| sg2_eye_analysis.py | SG2 branch, module_2/eye_analysis.py |
| sg4_temporal.ipynb | SG4 branch, module_4/D2-SG4.ipynb |
| sg5_final.py | SG5 branch, module_5/SG5_drowsiness_decision/sg5_final.py |

## Purpose

SG6 uses these snapshots to validate execution and interfaces
without modifying the original subgroup implementations.

The original algorithms belong to their respective subgroups.
These copies are not claimed as SG6 algorithm development.

## Limitations

- SG2-to-SG4 testing uses synthetic eye measurements.
- SG5 testing uses synthetic decision inputs.
- A complete live SG1-to-SG5 pipeline has not yet been verified.
- These snapshots should eventually be replaced by imports
  from agreed, versioned subgroup interfaces.
