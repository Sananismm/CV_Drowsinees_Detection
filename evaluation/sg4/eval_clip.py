"""Evaluate SG-4 on one annotated clip (real video, after cue extraction).

    python module_4/tools/standin_extractor.py --video clip.mp4 --out clip.jsonl
    python evaluation/sg4/eval_clip.py --cues clip.jsonl --labels clip_labels.csv

Labels CSV (one row per manually annotated event; times in seconds on the
same clock as the cue timestamps; see datasets/sg4_manifest.md):

    type,start_s,end_s
    blink,3.20,3.41
    long_blink,12.05,13.30
    yawn,20.0,24.5
    nod,31.2,32.0
    invalid,40.0,43.5        # face not usable (turned away, occluded)

Prints the same metrics as evaluate.py for primary, ema and naive approaches.
"""
import argparse
import csv
import json

import evaluate as ev

CLOSURE_TYPES = ("blink", "slow_blink", "long_blink")


def labels_to_gt(path, records):
    gt = {"closures": [], "yawns": [], "nods": [], "invalid": [], "artifacts": []}
    with open(path) as f:
        for row in csv.DictReader(f):
            kind = row["type"].strip()
            s, e = int(float(row["start_s"]) * 1000), int(float(row["end_s"]) * 1000)
            if kind in CLOSURE_TYPES:
                gt["closures"].append({"start_ms": s, "end_ms": e, "class": kind})
            elif kind == "yawn":
                gt["yawns"].append({"start_ms": s, "end_ms": e})
            elif kind == "nod":
                gt["nods"].append({"start_ms": s, "end_ms": e})
            elif kind == "invalid":
                gt["invalid"].append({"start_ms": s, "end_ms": e, "reason": "annotated"})
            else:
                raise ValueError("unknown label type %r" % kind)
    gt["duration_ms"] = max(r["timestamp_ms"] for r in records)
    return gt


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cues", required=True)
    ap.add_argument("--labels", required=True)
    a = ap.parse_args(argv)
    with open(a.cues) as f:
        records = [json.loads(x) for x in f if x.strip()]
    gt = labels_to_gt(a.labels, records)
    cfg = ev.load_config()
    for approach in ev.APPROACHES:
        r = ev.evaluate(records, gt, approach, cfg)
        print(approach, json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}))


if __name__ == "__main__":
    main()
