# Driver Drowsiness Monitoring System

CS-477 Computer Vision  
SEECS CV Face-Off 2026

## Overview

This project develops a real-time embedded Driver Drowsiness Monitoring System
deployed on the NVIDIA Jetson Orin Nano 8GB.

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