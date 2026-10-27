"""Pool verified SG-1 clip runs and provisional face-box agreement.

Each immediate subdirectory of --runs-dir must be named after its source-video
stem and contain one complete run_experiment.py result. The label directory
must contain <clip>_boxes.csv for every run. Aggregate outputs are written to
a new directory and intentionally contain neither paths nor landmarks.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path, PureWindowsPath
import statistics

import numpy as np

from evaluate_boxes import read_labels, read_predictions, score_boxes
from verify_experiment import verify_experiment


IOU_THRESHOLD = 0.5

OUTPUT_FIELDS = {
    "aggregate_comparison.csv": [
        "config_name", "clips", "processed_frames", "returned_face_frames",
        "face_coverage_availability", "frames_with_landmarks", "no_face_frames",
        "mean_inference_ms", "p95_inference_ms", "approx_inference_fps",
        "combined_end_to_end_fps",
    ],
    "provisional_box_metrics_summary.csv": [
        "config_name", "annotated_frames", "true_positive", "false_positive",
        "false_negative", "iou_threshold", "precision", "recall", "f1",
    ],
    "per_clip_comparison.csv": [
        "clip", "config_name", "input_long_side", "min_face_detection_confidence",
        "min_face_presence_confidence", "min_tracking_confidence", "source_frames",
        "processed_frames", "returned_face_frames", "face_coverage_availability",
        "frames_with_landmarks", "no_face_frames", "mean_inference_ms",
        "p95_inference_ms", "end_to_end_processed_fps", "wall_seconds",
    ],
    "mismatch_cases.csv": ["clip", "config_name", "frame_idx", "iou", "mismatch_type"],
}


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def _safe_filename(value: str, field: str) -> str:
    if not value or Path(value).name != value or PureWindowsPath(value).name != value:
        raise ValueError(f"{field} must be a filename, not a path")
    return value


def _positive_float(value: str, field: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"{field} must be a positive finite number")
    return number


def _mismatch_type(error: dict) -> str:
    if error["ground_truth"] is None:
        return "false_positive_on_no_face_reference"
    if error["prediction"] is None:
        return "no_face_prediction_for_reference_face"
    return "below_iou_threshold"


def collect_summaries(runs_dir: Path, labels_dir: Path, require_complete: bool = False) -> dict:
    """Validate run folders and return sanitized aggregate/per-clip rows."""
    runs_dir, labels_dir = Path(runs_dir), Path(labels_dir)
    if not runs_dir.is_dir():
        raise ValueError(f"runs directory does not exist: {runs_dir}")
    if not labels_dir.is_dir():
        raise ValueError(f"labels directory does not exist: {labels_dir}")
    clip_dirs = sorted(path for path in runs_dir.iterdir() if path.is_dir())
    if not clip_dirs:
        raise ValueError("runs directory contains no clip subdirectories")

    expected_configs = expected_model = expected_stride = None
    totals = {}
    per_clip, mismatches = [], []

    for clip_dir in clip_dirs:
        clip = clip_dir.name
        comparison_path = clip_dir / "comparison.csv"
        metadata_path = clip_dir / "run_metadata.json"
        rows = _read_rows(comparison_path)
        for row in rows:
            _safe_filename(row["predictions_file"], "predictions_file")
            _safe_filename(row["failures_file"], "failures_file")
        verify_experiment(clip_dir)
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        input_video = _safe_filename(metadata["input_video"], "input_video")
        if Path(input_video).stem != clip:
            raise ValueError(f"{clip}: run folder must match input-video stem")

        configurations = metadata["configurations"]
        configs = {item["name"]: item for item in configurations}
        if (
            not configs
            or len(configs) != len(configurations)
            or any(not isinstance(name, str) or not name.strip() for name in configs)
        ):
            raise ValueError(f"{clip}: configuration names must be unique and non-empty")
        if expected_configs is None:
            expected_configs = configs
            expected_model = metadata["model_sha256"]
            expected_stride = int(metadata["frame_stride"])
            for name in configs:
                totals[name] = {
                    "processed": 0, "faces": 0, "landmarks": 0, "no_face": 0,
                    "wall_seconds": 0.0, "times": [], "annotated": 0,
                    "tp": 0, "fp": 0, "fn": 0,
                }
        elif set(configs) != set(expected_configs):
            raise ValueError(f"{clip}: configuration names differ between clips")
        elif configs != expected_configs:
            raise ValueError(f"{clip}: configuration parameters differ between clips")
        elif metadata["model_sha256"] != expected_model:
            raise ValueError(f"{clip}: model SHA-256 differs between clips")
        elif int(metadata["frame_stride"]) != expected_stride:
            raise ValueError(f"{clip}: frame stride differs between clips")

        if require_complete and int(metadata["frame_stride"]) != 1:
            raise ValueError(f"{clip}: complete runs require frame_stride 1")
        labels_path = labels_dir / f"{clip}_boxes.csv"
        if not labels_path.is_file():
            raise ValueError(f"{clip}: missing labels file {labels_path.name}")
        labels = read_labels(labels_path)

        for row in rows:
            name = row["config_name"]
            if row.get("video") != input_video:
                raise ValueError(f"{clip}/{name}: comparison video differs from metadata")
            for field in (
                "input_long_side", "min_face_detection_confidence",
                "min_face_presence_confidence", "min_tracking_confidence",
            ):
                if float(row[field]) != float(configs[name][field]):
                    raise ValueError(f"{clip}/{name}: comparison {field} differs from configuration")
            processed, source_frames = int(row["processed_frames"]), int(row["source_frames"])
            width, height = int(row["source_width"]), int(row["source_height"])
            if processed <= 0 or source_frames <= 0 or width <= 0 or height <= 0:
                raise ValueError(f"{clip}/{name}: frame counts and dimensions must be positive")
            wall = _positive_float(row["wall_seconds"], f"{clip}/{name} wall_seconds")
            pred_path = clip_dir / row["predictions_file"]
            predictions = read_predictions(pred_path)
            with pred_path.open(encoding="utf-8") as stream:
                records = [json.loads(line) for line in stream if line.strip()]
            ids = [item["frame_id"] for item in records]
            if require_complete and (processed != source_frames or ids != list(range(source_frames))):
                raise ValueError(f"{clip}/{name}: run is incomplete (processed {processed} of {source_frames})")
            if any(item["config_name"] != name for item in records):
                raise ValueError(f"{clip}/{name}: prediction configuration differs from comparison")
            if any((item["image_width"], item["image_height"]) != (width, height) for item in records):
                raise ValueError(f"{clip}/{name}: prediction dimensions differ from comparison")
            for frame_id, box in labels.items():
                if box is not None and (box[2] > width or box[3] > height):
                    raise ValueError(f"{clip}: label frame {frame_id} is outside image bounds")
            scores = score_boxes(predictions, labels, IOU_THRESHOLD)
            times = [float(item["inference_ms"]) for item in records]
            faces = sum(item["status"] == "OK" for item in records)
            landmarks = sum(item["landmark_count"] > 0 for item in records)
            no_face = processed - faces
            total = totals[name]
            total["processed"] += processed
            total["faces"] += faces
            total["landmarks"] += landmarks
            total["no_face"] += no_face
            total["wall_seconds"] += wall
            total["times"].extend(times)
            total["annotated"] += scores["annotated_frames"]
            total["tp"] += scores["true_positive"]
            total["fp"] += scores["false_positive"]
            total["fn"] += scores["false_negative"]
            per_clip.append({
                "clip": clip, "config_name": name,
                **{field: row[field] for field in (
                    "input_long_side", "min_face_detection_confidence",
                    "min_face_presence_confidence", "min_tracking_confidence",
                )},
                "source_frames": source_frames, "processed_frames": processed,
                "returned_face_frames": faces,
                "face_coverage_availability": round(faces / processed, 6),
                "frames_with_landmarks": landmarks, "no_face_frames": no_face,
                "mean_inference_ms": round(statistics.mean(times), 3),
                "p95_inference_ms": round(float(np.percentile(times, 95)), 3),
                "end_to_end_processed_fps": row["end_to_end_processed_fps"],
                "wall_seconds": row["wall_seconds"],
            })
            mismatches.extend({
                "clip": clip, "config_name": name, "frame_idx": error["frame_idx"],
                "iou": error["iou"], "mismatch_type": _mismatch_type(error),
            } for error in scores["errors"])

    aggregate, box_metrics = [], []
    for name, total in totals.items():
        mean = statistics.mean(total["times"])
        aggregate.append({
            "config_name": name, "clips": len(clip_dirs),
            "processed_frames": total["processed"], "returned_face_frames": total["faces"],
            "face_coverage_availability": round(total["faces"] / total["processed"], 6),
            "frames_with_landmarks": total["landmarks"], "no_face_frames": total["no_face"],
            "mean_inference_ms": round(mean, 3),
            "p95_inference_ms": round(float(np.percentile(total["times"], 95)), 3),
            "approx_inference_fps": round(1000 / mean, 3) if mean else 0.0,
            "combined_end_to_end_fps": round(total["processed"] / total["wall_seconds"], 3),
        })
        tp, fp, fn = total["tp"], total["fp"], total["fn"]
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        box_metrics.append({
            "config_name": name, "annotated_frames": total["annotated"],
            "true_positive": tp, "false_positive": fp, "false_negative": fn,
            "iou_threshold": IOU_THRESHOLD, "precision": round(precision, 6),
            "recall": round(recall, 6), "f1": round(f1, 6),
        })
    return {
        "aggregate_comparison.csv": aggregate,
        "provisional_box_metrics_summary.csv": box_metrics,
        "per_clip_comparison.csv": per_clip,
        "mismatch_cases.csv": mismatches,
    }


def write_summaries(output_dir: Path, summaries: dict) -> None:
    """Write to a new directory only; never overwrite existing results."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    for filename, fields in OUTPUT_FIELDS.items():
        with (output_dir / filename).open("x", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="raise")
            writer.writeheader()
            writer.writerows(summaries[filename])


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-dir", type=Path, required=True)
    parser.add_argument("--labels-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True, help="New directory; must not exist")
    parser.add_argument("--require-complete", action="store_true", help="Require every source frame to be processed")
    args = parser.parse_args(argv)
    if args.output_dir.exists():
        parser.error(f"output directory already exists: {args.output_dir}")
    try:
        summaries = collect_summaries(args.runs_dir, args.labels_dir, args.require_complete)
        write_summaries(args.output_dir, summaries)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(f"Wrote four summaries to {args.output_dir}")
    print("Face coverage is returned-face availability, not driver correctness or accuracy.")
    print("Box metrics are agreement with supplied reference boxes, not independently validated accuracy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
