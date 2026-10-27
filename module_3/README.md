Week 5 — SG3 Yawn \& Facial-Cue Analysis

1\. Introduction

During Week 5 of the CS-477 Computer Vision Semester Project, our subgroup was assigned SG3 — Yawn \& Facial-Cue Analysis for the Driver Drowsiness Monitoring system.

The overall drowsiness-monitoring pipeline is:

Camera → Face/Landmarks → Eye/Yawn Cues → Temporal Behaviour Analysis → Drodwsiness Decision → Alert

Our responsibility was to investigate how mouth-related facial cues can be used to detect yawning and provide a reliable input to the later temporal behaviour and drowsiness-decision modules. The Week 5 task required comparison of different yawn/facial-cue configurations involving geometric mouth measurements, thresholds, persistence, or classifier-based approaches.

For this experiment, we focused on a geometric Mouth Aspect Ratio (MAR) approach combined with temporal persistence.

2\. Objective

The main objectives of our Week 5 experiment were:

1\. Develop a working yawn/facial-cue analysis module.

2\. Represent mouth opening using the Mouth Aspect Ratio (MAR).

3\. Investigate different MAR thresholds.

4\. Investigate the effect of requiring the mouth to remain open for multiple consecutive frames.

5\. Compare different configurations using quantitative metrics.

6\. Examine the trade-off between sensitivity and resistance to short facial/speech artifacts.

7\. Produce a reproducible cue output for integration with the downstream drowsiness modules.

3\. Methodology

3.1 Mouth Aspect Ratio

The main facial feature used in our experiment was the Mouth Aspect Ratio (MAR).

MAR provides a geometric representation of mouth opening. A relatively small MAR represents a normal resting or speaking mouth, while a larger MAR indicates a more open mouth and can therefore act as a cue for yawning.

Instead of relying only on a single frame, our implementation also introduced a persistence requirement. This was important because normal speech can temporarily produce a large mouth opening that should not necessarily be classified as a yawn.

4\. Test Data / Experimental Sequence

For controlled testing, we generated a simulated driver MAR sequence representing normal facial activity, speech-related variation, and two extended yawn events.

The normal baseline was generated around a MAR value of approximately 0.20, with random variation to represent normal resting and speaking behaviour.

Two artificial yawn events were introduced:

\- Yawn Event 1: frames 50–89

\- Yawn Event 2: frames 180–229

At 30 FPS, these correspond approximately to:

\- Event 1: 40 frames ≈ 1.33 seconds

\- Event 2: 50 frames ≈ 1.67 seconds

A short speech-related mouth-opening spike was also introduced between frames 130–134. This allowed us to investigate whether temporal persistence could distinguish a sustained yawn from a short speech artifact.

The MAR values were clipped to a valid range of 0.10–0.95.

This controlled sequence allowed us to evaluate the detector under repeatable conditions rather than relying only on visual judgement.

5\. Detection Algorithm

The detector processes the MAR sequence frame by frame.

For every frame:

1\. The current MAR value is compared with the selected MAR threshold.

2\. If MAR is greater than or equal to the threshold, the consecutive-high counter is increased.

3\. If MAR falls below the threshold, the counter is reset.

4\. A yawn cue is generated once the number of consecutive high-MAR frames reaches the selected persistence requirement.

The basic decision rule is:

MAR ≥ threshold → increase persistence counter

MAR < threshold → reset persistence counter

Persistence ≥ required frames → Yawn detected

This prevents a short isolated increase in mouth opening from immediately becoming a yawn detection.

The implementation evaluates true positives (TP), false positives (FP), true negatives (TN), and false negatives (FN) and calculates precision, recall, and F1-score.

6\. Experimental Configurations

Four configurations were tested.

Configuration	MAR Threshold	Persistence	Purpose

Configuration 1	0.40	1 frame	High-sensitivity configuration

Configuration 2	0.50	1 frame	Baseline frame-level detector

Configuration 3	0.50	10 frames	Threshold + temporal persistence

Configuration 4	0.60	15 frames	Higher threshold + stronger persistence





The four configurations are directly defined in the experimental code.

Configuration 3 corresponds to approximately 0.33 seconds of persistence at 30 FPS, while Configuration 4 requires approximately 0.5 seconds.

7\. Experimental Evaluation

For each configuration, the system calculated:

\- Precision

\- Recall

\- F1-score

\- False-positive frames

\- False-negative frames

\- Average processing latency per frame

These metrics provide quantitative evidence for comparing the different detector configurations, as required by the Week 5 assessment.

The implementation automatically stores these measurements in a Pandas results table.

7.1 Configuration Analysis

Configuration 1 — MAR ≥ 0.40, 1 frame

This configuration prioritizes sensitivity. Since only one frame is required to cross the threshold, short mouth-opening events can be detected easily. However, this also makes the detector more susceptible to non-yawn facial activity and speech-related spikes.

Configuration 2 — MAR ≥ 0.50, 1 frame

Increasing the threshold reduces sensitivity to smaller mouth openings. However, because persistence is still only one frame, short events can still trigger the detector.

Configuration 3 — MAR ≥ 0.50, 10 frames

This configuration introduces temporal persistence while retaining the moderate MAR threshold. A mouth opening must remain above the threshold for approximately 10 consecutive frames before it is considered a yawn cue.

This provides a better distinction between a sustained yawn and a short speech artifact.

Configuration 4 — MAR ≥ 0.60, 15 frames

This is the most conservative configuration. Both the mouth-opening threshold and persistence requirement are increased. This can reduce false detections caused by small or short mouth movements, although stronger requirements can also increase the possibility of missing shorter or weaker yawns.

8\. False Positives and False Negatives

A major consideration in yawn detection is that mouth opening does not necessarily mean yawning.

For example, speaking can temporarily increase MAR. Our test sequence therefore included a short speech spike between frames 130 and 134.

A frame-level detector may interpret such an event as a yawn because it only considers the instantaneous MAR value.

The persistence-based approach addresses this limitation by requiring the mouth-opening condition to continue for a specified number of frames.

However, excessive persistence can create the opposite problem. If a genuine yawn is short or its MAR temporarily drops below the threshold, the detector may fail to classify part of the event, increasing false negatives.

Therefore, the threshold and persistence parameters must be considered together.

9\. Key Trade-Off

The main trade-off observed in the experiment was:

\- Lower threshold / shorter persistence → higher sensitivity but greater risk of false positives

\- Higher threshold / longer persistence → greater stability but increased risk of missed detections and detection delay

This is particularly important for the final drowsiness-monitoring system because SG3 produces a facial cue rather than making the final drowsiness decision.

The project specification emphasizes the hierarchy:

Visual cue → Temporal evidence → Drowsiness decision → Alert

10\. V1 Interface Output

A sample V1 output structure was also prepared for integration with the other project modules.

The sample output contains:

\- frame\_id

\- mouth\_aspect\_ratio

\- mar\_threshold

\- yawn\_cue\_detected

\- consecutive\_yawn\_frames

\- confidence

\- processing\_time\_ms

The code writes this information to:

sg3\_v1\_output\_sample.json

This provides a consistent representation of the facial cue for downstream modules.

11\. Sample V1 Output

A representative output generated by the implementation is:

Frame ID: 205

Mouth Aspect Ratio: 0.68

MAR Threshold: 0.50

Yawn Cue Detected: True

Consecutive Yawn Frames: 25

Confidence: 0.92

Processing Time: 0.12 ms

This demonstrates the intended SG3 output when a sustained mouth-opening event is detected.

12\. Week 5 Findings

The Week 5 experiment demonstrated that a geometric mouth-opening measure can provide a simple and computationally lightweight yawn cue.

The main findings were:

1\. MAR provides a useful geometric representation of mouth opening.

2\. A single-frame threshold is sensitive but can respond to short facial events.

3\. Adding temporal persistence makes the cue more robust against short speech-related mouth-opening events.

4\. Increasing both threshold and persistence makes the detector more conservative.

5\. Threshold and persistence should therefore be considered together.

6\. The cue should be passed to the temporal behaviour module rather than being treated as a final drowsiness decision.

7\. The JSON-style V1 output provides a clear interface for downstream integration.

13\. Limitations

The current experiment is a controlled simulation rather than a complete real-world facial landmark pipeline.

The MAR sequence is generated synthetically, so the experiment does not capture all real-world conditions such as:

\- Different face shapes

\- Head rotation

\- Camera viewpoint

\- Poor illumination

\- Facial occlusion

\- Individual differences in mouth opening

\- Real speech patterns

\- Different types and durations of yawns

Therefore, the current results should be considered a controlled parameter study and preliminary validation, rather than a final real-world performance benchmark.

Another limitation is that the current implementation focuses on the geometric MAR cue and does not compare it against a trained classifier-based yawn detector.

14\. Conclusion

During Week 5, SG3 developed and evaluated a geometric yawn/facial-cue detector based on Mouth Aspect Ratio. Four combinations of MAR threshold and temporal persistence were tested using a controlled sequence containing normal activity, a short speech artifact, and two sustained yawn events.

The experiment demonstrated the importance of temporal persistence in distinguishing sustained yawning behaviour from short mouth-opening events. Quantitative metrics including precision, recall, F1-score, false-positive frames, false-negative frames, and processing latency were incorporated into the evaluation framework.

The SG3 module also provides a reproducible V1 output structure containing the frame number, MAR value, threshold, yawn cue, persistence information, confidence, and processing time.

Overall, the Week 5 work established a functional and measurable Yawn \& Facial-Cue Analysis module suitable for integration into the broader Driver Drowsiness Monitoring system.

