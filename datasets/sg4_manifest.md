# SG-4 dataset manifest

**No raw data is committed.** Videos stay outside the repo (e.g. `~/data/`); `.gitignore` blocks `data/`, `*.mp4`, `*.avi`.

| Dataset | Use in SG-4 | How to obtain | Licence / notes |
|---|---|---|---|
| **NTHU-DDD** (NTHU Driver Drowsiness Detection) | Real drowsy / alert driving clips with per-frame drowsiness, eye and mouth labels → PERCLOS, microsleep, yawn evaluation | Request access from the NTHU Computer Vision Lab (the ACCV 2016 DDD workshop dataset page); academic use only, signed agreement | Per-frame labels are sequence-level states, not blink onsets. Blink/microsleep start-end times must be annotated by us (see below). |
| **YawDD** (Yawning Detection Dataset, Abtahi et al., MMSys 2014) | Yawning vs talking vs singing clips → yawn-event precision, talking false positives | Request via the dataset page (University of Ottawa / IEEE DataPort) | Mirror- and dash-mounted cameras. Yawn intervals need our own start/end annotation. |
| **Team-recorded clips** | Annotated blinks, slow blinks, microsleeps (simulated), nods, look-aways, glasses, low light | Record with the team camera (the same USB/CSI camera SG-6 uses on the Jetson), 30 FPS, 1–3 min per clip | Get written consent from everyone recorded. Store outside the repo; commit only label CSVs. |

## Annotation format (what we commit)

`datasets/sg4_labels/<clip_id>.csv`, timestamps in seconds on the clip clock:

```
type,start_s,end_s
blink,3.20,3.41
slow_blink,7.80,8.25
long_blink,12.05,13.30
yawn,20.0,24.5
nod,31.2,32.0
invalid,40.0,43.5
```

Closure = from the first frame the eyelids cover ≥ 80% of the iris to the first frame they reopen past 50%. This matches the engine's P80 + hysteresis definition. Annotate with any frame-stepping player (e.g. VLC with frame-by-frame stepping, or CVAT) and record the clip FPS.

## Running an evaluation on a clip

```bash
python module_4/tools/standin_extractor.py --video ~/data/clip01.mp4 --out /tmp/clip01.jsonl
python evaluation/sg4/eval_clip.py --cues /tmp/clip01.jsonl --labels datasets/sg4_labels/clip01.csv
```

Once SG-2/SG-3 deliver real outputs, replace the stand-in step with their output files (`adapters.py` maps the fields).
