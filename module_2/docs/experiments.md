# Method Comparison

## Sample

The earlier project comparison used 50 sampled frames across five clips. There were 28 clear labels (20 OPEN and 8 CLOSED) and 22 ambiguous frames, which were excluded from binary accuracy. The project notes describe one reviewer and a purposive diagnostic sample containing disagreement/difficult cases; all clips had been viewed during method development. There is no independent held-out result or inter-rater measurement. [Recorded comparison summary](../final_method.json)

## Recorded predictions for the 28 clear frames

The following rows reproduce the existing project prediction records. UNKNOWN is an abstention; it is excluded from accuracy on classified frames but counted as an error in strict accuracy over all 28 clear labels. These rows are not new model predictions or new manual labels. [Summary and scope](../final_method.json)

| Clip | Frame | Manual label | EAR | CNN bilateral | Earlier EAR-first | EAR + OPEN2 |
|---|---:|---|---|---|---|---|
| P1042801_720 | 12 | CLOSED | CLOSED | CLOSED | CLOSED | CLOSED |
| P1042801_720 | 156 | OPEN | OPEN | UNKNOWN | OPEN | OPEN |
| P1042801_720 | 314 | CLOSED | OPEN | OPEN | OPEN | OPEN |
| P1042801_720 | 368 | CLOSED | CLOSED | CLOSED | CLOSED | CLOSED |
| P1042801_720 | 490 | OPEN | OPEN | OPEN | OPEN | OPEN |
| P1042801_720 | 509 | CLOSED | CLOSED | CLOSED | CLOSED | CLOSED |
| P1043061_720 | 22 | CLOSED | CLOSED | CLOSED | CLOSED | CLOSED |
| P1043061_720 | 92 | OPEN | OPEN | OPEN | OPEN | OPEN |
| P1043061_720 | 222 | OPEN | OPEN | UNKNOWN | OPEN | OPEN |
| P1043061_720 | 412 | OPEN | OPEN | CLOSED | CLOSED | OPEN |
| P1043061_720 | 619 | OPEN | OPEN | CLOSED | CLOSED | OPEN |
| P1043079_720 | 40 | OPEN | OPEN | CLOSED | OPEN | OPEN |
| P1043079_720 | 75 | OPEN | OPEN | CLOSED | CLOSED | OPEN |
| P1043079_720 | 150 | OPEN | OPEN | CLOSED | CLOSED | OPEN |
| P1043079_720 | 221 | OPEN | OPEN | CLOSED | OPEN | OPEN |
| P1043079_720 | 294 | OPEN | OPEN | CLOSED | CLOSED | OPEN |
| P1043079_720 | 353 | OPEN | OPEN | CLOSED | CLOSED | OPEN |
| P1043079_720 | 399 | OPEN | CLOSED | CLOSED | CLOSED | CLOSED |
| P1043079_720 | 489 | OPEN | OPEN | OPEN | OPEN | OPEN |
| P1043079_720 | 524 | OPEN | OPEN | CLOSED | CLOSED | OPEN |
| P1043079_720 | 566 | OPEN | OPEN | CLOSED | OPEN | OPEN |
| P1043080_720 | 138 | OPEN | OPEN | CLOSED | CLOSED | OPEN |
| P1043080_720 | 261 | OPEN | OPEN | UNKNOWN | OPEN | OPEN |
| P1043080_720 | 387 | OPEN | OPEN | CLOSED | OPEN | OPEN |
| P1043080_720 | 434 | CLOSED | CLOSED | CLOSED | CLOSED | CLOSED |
| P1043128_720 | 215 | CLOSED | CLOSED | CLOSED | CLOSED | CLOSED |
| P1043128_720 | 350 | CLOSED | CLOSED | CLOSED | CLOSED | CLOSED |
| P1043128_720 | 489 | OPEN | OPEN | CLOSED | CLOSED | OPEN |

EAR and EAR+OPEN2 each match 26/28 labels (92.9%). CNN matches 10/25 classified frames (40.0%), with three UNKNOWNs; its strict result is 10/28 (35.7%). Earlier EAR-first matches 17/28 (60.7%). False-CLOSED counts on the 20 OPEN-labelled frames are 1 for EAR, 14 for CNN, and 10 for earlier EAR-first. [Recorded summary](../final_method.json)

The equal raw/smoothed EAR score on these sampled frames does not independently measure temporal stability or blink accuracy. The continuous 590-frame example has no event ground truth; its 10 closures and 5 candidates are descriptive predictions. [Run results](../results/live_integration_summary.json) [Event rules](../events.py)

## What we kept

We kept EAR at threshold 0.15 with the existing OPEN confirmation, rather than allowing CNN predictions to change the current output. The comparison was small and exploratory, so it supports a project choice rather than a general claim that EAR is always better. The old selection grid and metrics remain historical; the current selected method is recorded in final_method.json. [Current settings](../final_method.json) [Decision code](../fusion.py)
