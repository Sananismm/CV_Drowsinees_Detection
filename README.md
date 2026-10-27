# Driver Drowsiness Monitoring System

CS-477 Computer Vision  
SEECS CV Face-Off 2026

## Overview

This project develops a Driver Drowsiness Monitoring System targeting deployment
on the NVIDIA Jetson Orin Nano 8GB. PC integration and physical target validation
are reported separately; this description is not a claim of complete deployment.

The system observes a driver's facial and behavioral cues over time and determines
whether the driver is awake, showing signs of fatigue, or drowsy.

The complete system follows the pipeline:

Camera → Face & Landmark Detection → Eye / Facial Cue Analysis →
Temporal Behaviour Analysis → Drowsiness Decision → Alert

The project is divided into six technical sub-groups. Each sub-group develops and
evaluates its module independently using agreed input/output interfaces before
progressive integration into the complete embedded system.

---

## System Pipeline

```text
Camera
   │
   ▼
┌───────────────────────────────┐
│ SG-1                         │
│ Driver Face & Landmark       │
│ Detection                    │
│                              │
│ Frame → Face / Landmarks     │
└──────────────┬────────────────┘
               │
        ┌──────┴───────┐
        │              │
        ▼              ▼
┌───────────────┐ ┌─────────────────┐
│ SG-2          │ │ SG-3            │
│ Eye State &   │ │ Yawn & Facial   │
│ Blink Analysis│ │ Cue Analysis    │
└───────┬───────┘ └────────┬────────┘
        │                  │
        └─────────┬────────┘
                  │
                  ▼
        ┌──────────────────────┐
        │ SG-4                 │
        │ Temporal Behaviour   │
        │ Analysis             │
        └──────────┬───────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │ SG-5                 │
        │ Drowsiness Decision  │
        │ & Alert Logic        │
        └──────────┬───────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │ SG-6                 │
        │ Embedded Deployment  │
        │ & System Integration │
        │                      │
        │ NVIDIA Jetson Orin   │
        │ Nano                 │
        └──────────┬───────────┘
                   │
                   ▼
             Driver Alert
```

## SG5 midterm integration checkpoint

On branch `sg5-midterm-integration`, SG5 consumes the actual SG4 temporal engine
and connects the available SG1 and SG2 source with a documented causal SG3
adapter. The status-aware SG6 consumer produces hardware requests without
operating physical GPIO. Original subgroup work is preserved and attributed.

- [SG5 setup and module documentation](module_5/midterm/README.md)
- [Exact viva command sequence](module_5/midterm/scripts.md)
- [Midterm evidence report](module_5/midterm/report/SG5_Midterm_Report.pdf)
- [Interface and owner acceptance tracking](documentation/sg5_midterm_interfaces.md)
- [Pinned upstream source provenance](integration/sg5_midterm_sources.json)
- [Team project board](https://github.com/users/Sananismm/projects/2) (team access)
- [Outstanding semantic and hardware acceptance](https://github.com/Sananismm/CV_Drowsinees_Detection/issues/20)

Saved-video execution demonstrates software interoperability, not independently
labelled driver accuracy or live Jetson camera readiness. Midterm requirements
and remaining hardware checks are mapped in the report and SG5 documentation.
