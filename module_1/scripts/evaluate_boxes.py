import argparse
import csv
import json
import math
from pathlib import Path


def iou(a, b):
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area_a = max(0, a[2] - a[0]) * max(0, a[3] - a[1])
    area_b = max(0, b[2] - b[0]) * max(0, b[3] - b[1])
    union = area_a + area_b - inter
    return inter / union if union else 0.0


def score_boxes(predictions, labels, iou_threshold=0.5):
    """Score optional prediction/ground-truth boxes keyed by frame ID."""

    if not math.isfinite(iou_threshold) or not 0 <= iou_threshold <= 1:
        raise ValueError("iou_threshold must be between 0 and 1")
    if not labels:
        raise ValueError("labels must contain at least one annotated frame")
    missing = sorted(set(labels) - set(predictions))
    if missing:
        preview = ", ".join(str(frame_id) for frame_id in missing[:10])
        suffix = " ..." if len(missing) > 10 else ""
        raise ValueError(
            f"predictions missing {len(missing)} annotated frame(s): {preview}{suffix}"
        )
    tp = fp = fn = 0
    errors = []
    for frame_idx, gt in labels.items():
        pred = predictions[frame_idx]
        _validate_box(gt, f"label frame {frame_idx}")
        _validate_box(pred, f"prediction frame {frame_idx}")
        if gt is None and pred is None:
            continue
        overlap = iou(gt, pred) if gt is not None and pred is not None else 0.0
        if gt is not None and pred is not None and overlap >= iou_threshold:
            tp += 1
        else:
            if pred is not None:
                fp += 1
            if gt is not None:
                fn += 1
            errors.append(
                {
                    "frame_idx": frame_idx,
                    "ground_truth": gt,
                    "prediction": pred,
                    "iou": round(overlap, 4),
                }
            )
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "annotated_frames": len(labels),
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "f1": round(f1, 6),
        "errors": errors,
    }


def _validate_box(box, context):
    """Require a finite, positive-area pixel box, or None for no face."""

    if box is None:
        return
    if not isinstance(box, (list, tuple)) or len(box) != 4:
        raise ValueError(f"{context}: box must contain four coordinates or be empty")
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        for value in box
    ):
        raise ValueError(f"{context}: box coordinates must be finite numbers")
    x1, y1, x2, y2 = box
    if x1 < 0 or y1 < 0 or x2 <= x1 or y2 <= y1:
        raise ValueError(f"{context}: box must have non-negative, ordered coordinates and positive area")


def read_predictions(path):
    """Load one prediction per frame, preserving explicit no-face records."""

    predictions = {}
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc.msg}") from exc
            if not isinstance(item, dict):
                raise ValueError(f"{path}:{line_number}: prediction must be an object")
            idx = item.get("frame_id")
            if not isinstance(idx, int) or isinstance(idx, bool) or idx < 0:
                raise ValueError(f"{path}:{line_number}: frame_id must be a non-negative integer")
            if idx in predictions:
                raise ValueError(f"{path}:{line_number}: duplicate prediction frame_id {idx}")
            if "face_bbox_xyxy" not in item:
                raise ValueError(f"{path}:{line_number}: missing face_bbox_xyxy")
            box = item["face_bbox_xyxy"]
            _validate_box(box, f"{path}:{line_number}")
            predictions[idx] = box
    return predictions


def read_labels(path):
    """Load manual CSV boxes; a fully empty box denotes a no-face frame."""

    labels = {}
    required = ("frame_idx", "x1", "y1", "x2", "y2")
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None or not set(required).issubset(reader.fieldnames):
            raise ValueError(f"{path}: expected CSV columns {', '.join(required)}")
        if len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError(f"{path}: duplicate CSV column names")
        for row_number, row in enumerate(reader, start=2):
            if None in row or any(row.get(key) is None for key in required):
                raise ValueError(f"{path}:{row_number}: malformed CSV row")
            try:
                idx = int(row["frame_idx"].strip())
            except ValueError as exc:
                raise ValueError(f"{path}:{row_number}: invalid frame_idx") from exc
            if idx < 0:
                raise ValueError(f"{path}:{row_number}: frame_idx must be non-negative")
            if idx in labels:
                raise ValueError(f"{path}:{row_number}: duplicate label frame_idx {idx}")
            vals = [row[key].strip() for key in required[1:]]
            if not any(vals):
                box = None
            elif not all(vals):
                raise ValueError(f"{path}:{row_number}: box coordinates must be all present or all empty")
            else:
                try:
                    box = [float(value) for value in vals]
                except ValueError as exc:
                    raise ValueError(f"{path}:{row_number}: invalid box coordinate") from exc
                _validate_box(box, f"{path}:{row_number}")
            labels[idx] = box
    return labels


def main():
    parser = argparse.ArgumentParser(description="Score single-driver face boxes against labeled frames.")
    parser.add_argument("--predictions", required=True, type=Path)
    parser.add_argument("--labels", required=True, type=Path)
    parser.add_argument("--iou-threshold", type=float, default=0.5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    try:
        predictions = read_predictions(args.predictions)
        labels = read_labels(args.labels)
        scores = score_boxes(predictions, labels, args.iou_threshold)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    result = {
        "predictions": str(args.predictions),
        "labels": str(args.labels),
        "iou_threshold": args.iou_threshold,
        **scores,
    }
    output = args.output or args.predictions.with_name("box_metrics_" + args.predictions.stem.removeprefix("predictions_") + ".json")
    if output.resolve() in {args.predictions.resolve(), args.labels.resolve()}:
        parser.error("output must differ from the predictions and labels files")
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "errors"}, indent=2))
    print(f"Saved error cases to {output}")


if __name__ == "__main__":
    main()
