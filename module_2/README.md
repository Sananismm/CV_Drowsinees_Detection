# SG-2: Eye State & Blink Analysis

## Purpose

SG-2 is responsible for eye-state and local eye-closure analysis in the Driver Drowsiness Monitoring system.

The module receives eye/face information from SG-1 and produces frame-level eye-state and eye-closure evidence for SG-4.

SG-2 does not make the final drowsiness decision. Longer-term temporal analysis is performed by SG-4.

## Week 5 Objective

For Week 5, the existing Eye Aspect Ratio (EAR) baseline was maintained and a controlled threshold comparison was performed.

Three EAR thresholds were tested:

- 0.15
- 0.20
- 0.25

The same manually labelled samples were used for all configurations.

## Dataset Used

Dataset: NITYMED (Night Time Yawning, Microsleep, Eyeblink and Distraction)

Test video:
- Category: Microsleep
- File: P1043106_720.mp4
- Resolution: 1280 x 720
- Frame rate: 25 FPS
- Duration: approximately 124 seconds

The dataset video is not included in this module.

## Method

For independent Week 5 testing, MediaPipe Face Landmarker was used to obtain facial landmarks.

EAR was calculated using six landmarks from each eye.

Left eye indices:
33, 160, 158, 133, 153, 144

Right eye indices:
362, 385, 387, 263, 373, 380

EAR is calculated as:

EAR = (||P2-P6|| + ||P3-P5||) / (2 * ||P1-P4||)

An open eye normally produces a higher EAR, while EAR decreases as the eye closes.

Example observations:
- Open-eye example: EAR = 0.314
- Closed-eye example: EAR = 0.068

During final integration, SG-2 is expected to receive the required eye information through the SG-1 to SG-2 interface.

## Eye-State Classification

The baseline classifier uses:

EAR < threshold -> CLOSED

EAR >= threshold -> OPEN

If valid eye information is unavailable:

eye_state -> UNKNOWN

An invalid or occluded eye is therefore not automatically classified as CLOSED.

## Week 5 Threshold Experiment

40 frames were sampled across the test video and manually inspected.

Two ambiguous samples were labelled UNKNOWN and excluded from the threshold accuracy calculation, leaving 38 evaluated samples.

| EAR Threshold | Correct | Total | Accuracy | False Open | False Closed |
|---|---:|---:|---:|---:|---:|
| 0.15 | 38 | 38 | 100.00% | 0 | 0 |
| 0.20 | 37 | 38 | 97.37% | 0 | 1 |
| 0.25 | 34 | 38 | 89.47% | 0 | 4 |

Based on this preliminary Week 5 subset, 0.15 was selected as the preliminary EAR threshold.

The 100% result applies only to the preliminary 38-frame manually labelled subset and does not represent overall system accuracy.

## Full-FPS Temporal Test

After selecting the threshold, approximately the first 30 seconds of the video were processed at the original 25 FPS.

Results:
- Frames analysed: 751
- OPEN: 608
- CLOSED: 143

At 25 FPS, consecutive frames are approximately 0.04 seconds apart. This provides better temporal resolution for short eye closures than the earlier sampled analysis.

## Eye-Closure Events

Continuous CLOSED frames were grouped into eye-closure events.

For each event, SG-2 records:
- Start time
- End time
- Duration

In the approximately 30-second test:
- 15 closure events were detected
- Durations ranged from 0.12 to 0.80 seconds

These are described as eye-closure or blink-related events rather than assuming every event is a normal blink.

Longer-term interpretation is left to SG-4.

## SG-2 Input

Example input is provided in:

sg2_mock_input.json

The SG-2 input includes information such as:
- frame_id
- timestamp
- validity information
- eye/face landmark information

## SG-2 Output

Example output is provided in:

sg2_mock_output.json

SG-2 output contains information such as:
- frame_id
- timestamp_sec
- eye_state
- ear
- ear_threshold
- valid
- closure_event

Possible eye states are:
- OPEN
- CLOSED
- UNKNOWN

This timestamped evidence can then be used by SG-4 for temporal behaviour analysis.

## Files

eye_analysis.py
- Reusable SG-2 EAR and eye-state processing code.

SG2_Week5_Eye_Blink_Analysis.ipynb
- Week 5 experimental notebook.

threshold_comparison.csv
- Results of the EAR threshold comparison.

closure_events.csv
- Detected eye-closure event timings and durations.

sg2_mock_input.json
- Example input expected by SG-2.

sg2_mock_output.json
- Example SG-2 output for downstream integration.

## Dependencies

The Week 5 experiment uses:
- Python
- NumPy
- Pandas
- OpenCV
- MediaPipe
- Matplotlib

## How to Run

Open SG2_Week5_Eye_Blink_Analysis.ipynb in Google Colab.

Provide the NITYMED test video at the path specified in the notebook and run the experiment cells in order.

The reusable SG-2 processing functions are also available separately in eye_analysis.py.

## Current Limitations

- Current evaluation is based on one test video/subject.
- Only 38 confidently labelled frames were evaluated in the threshold experiment.
- Ground-truth labels were manually assigned.
- The current results cannot be treated as general system accuracy.
- A fixed EAR threshold may behave differently for different subjects.
- Landmark quality may be affected by head pose, illumination and occlusion.
- Confidence values have not yet been calibrated.
- Additional subjects and difficult conditions still need to be evaluated.

## Preliminary Week 5 Decision

EAR threshold = 0.15 is retained as the preliminary SG-2 configuration because it produced the best result among the tested thresholds on the current labelled subset.

This threshold will be evaluated further and is not considered permanently fixed.

## Week 6 Plan

1. Test the selected EAR configuration on additional videos and subjects.
2. Evaluate more difficult pose, illumination and occlusion conditions.
3. Analyse failure cases and threshold generalization.
4. Maintain compatibility with the SG-1 -> SG-2 -> SG-4 interface.
5. Consider comparison with a lightweight learned eye-state classifier if required.
