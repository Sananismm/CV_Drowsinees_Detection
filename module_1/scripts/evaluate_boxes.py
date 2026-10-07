import argparse
import csv
import json
from pathlib import Path


def iou(a, b):
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area_a = max(0, a[2] - a[0]) * max(0, a[3] - a[1])
    area_b = max(0, b[2] - b[0]) * max(0, b[3] - b[1])
    union = area_a + area_b - inter
    return inter / union if union else 0.0


def main():
    parser = argparse.ArgumentParser(description="Score single-driver face boxes against labeled frames.")
    parser.add_argument("--predictions", required=True, type=Path)
    parser.add_argument("--labels", required=True, type=Path)
    parser.add_argument("--iou-threshold", type=float, default=0.5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    predictions = {}
    with args.predictions.open(encoding="utf-8") as stream:
        for line in stream:
            item = json.loads(line)
            predictions[int(item["frame_id"])] = item.get("face_bbox_xyxy")
    labels = {}
    with args.labels.open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            idx = int(row["frame_idx"])
            vals = [row.get(k, "").strip() for k in ("x1", "y1", "x2", "y2")]
            labels[idx] = [int(float(v)) for v in vals] if all(vals) else None

    tp = fp = fn = 0
    annotated = 0
    errors = []
    for frame_idx, gt in labels.items():
        annotated += 1
        pred = predictions.get(frame_idx)
        if gt is not None and pred is not None and iou(gt, pred) >= args.iou_threshold:
            tp += 1
        else:
            if pred is not None:
                fp += 1
            if gt is not None:
                fn += 1
            errors.append({"frame_idx": frame_idx, "ground_truth": gt, "prediction": pred, "iou": round(iou(gt, pred), 4) if gt and pred else 0.0})
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    result = {
        "predictions": str(args.predictions),
        "labels": str(args.labels),
        "iou_threshold": args.iou_threshold,
        "annotated_frames": annotated,
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "f1": round(f1, 6),
        "errors": errors,
    }
    output = args.output or args.predictions.with_name("box_metrics_" + args.predictions.stem.removeprefix("predictions_") + ".json")
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "errors"}, indent=2))
    print(f"Saved error cases to {output}")


if __name__ == "__main__":
    main()
