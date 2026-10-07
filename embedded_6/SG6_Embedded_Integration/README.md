\# SG6 — Embedded Deployment \& System Integration



\## Driver Drowsiness Monitoring System



\*\*Course:\*\* CS-477 Computer Vision  

\*\*Project:\*\* Driver Drowsiness Monitoring  

\*\*Sub-Group:\*\* SG6 — Embedded Deployment \& System Integration  

\*\*Week:\*\* Week 5  



\---



\## 1. Overview



SG6 is responsible for the embedded deployment and system integration layer of the Driver Drowsiness Monitoring project.



The final objective of SG6 is to integrate the computer vision modules developed by SG1–SG5 and deploy the complete drowsiness-monitoring pipeline on the target embedded platform.



At the current stage, Jetson hardware has not yet been issued to the project group. Therefore, Week 5 SG6 work focuses on:



\- Understanding the complete system pipeline.

\- Defining how SG1–SG5 modules connect together.

\- Verifying expected module inputs and outputs.

\- Preparing the repository for future integration.

\- Identifying dependencies between sub-groups.

\- Preparing the software architecture for later Jetson deployment.



Hardware-specific benchmarking such as FPS, latency, GPU utilization, and memory usage will be performed once the Jetson platform becomes available.



\---



\# 2. Overall System Pipeline



The Driver Drowsiness Monitoring system follows the pipeline:



```text

Camera

&#x20;  │

&#x20;  ▼

SG1 — Face \& Landmark Detection

&#x20;  │

&#x20;  ▼

&#x20;┌─────────────────────────────┐

&#x20;│                             │

&#x20;▼                             ▼

SG2 — Eye / Blink          SG3 — Yawn /

Analysis                   Facial Cue Analysis

&#x20;│                             │

&#x20;└──────────────┬──────────────┘

&#x20;               │

&#x20;               ▼

SG4 — Temporal Behaviour Analysis

&#x20;               │

&#x20;               ▼

SG5 — Drowsiness Decision \& Alert Logic

&#x20;               │

&#x20;               ▼

SG6 — Embedded Integration

&#x20;               │

&#x20;               ▼

&#x20;            ALERT

