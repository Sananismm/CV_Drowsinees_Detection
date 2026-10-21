"""Verify that one SG-1 experiment output folder is internally consistent."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

import cv2

from sg1_contract import validate_sg1_record


REQUIRED_METADATA = {
    "schema_version",
    "landmark_topology",
    "model_filename",
    "model_sha256",
    "python_version",
    "mediapipe_version",
    "opencv_version",
    "numpy_version",
    "input_video",
    "input_video_sha256",
    "frame_stride",
    "configurations",
}


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    records = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                validate_sg1_record(record)
            except Exception as exc:
                raise ValueError(f"{path.name}:{line_number}: {exc}") from exc
            records.append(record)
    return records


def _read_failure_ids(path: Path) -> list[int]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if any(row.get("reason") != "NO_FACE" for row in rows):
        raise ValueError(f"{path.name}: every failure reason must be NO_FACE")
    return [int(row["frame_idx"]) for row in rows]


def _verify_video(path: Path, row: dict[str, str], expected_frames: int, stride: int) -> None:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError(f"could not open annotated video: {path.name}")
    try:
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = float(capture.get(cv2.CAP_PROP_FPS))
    finally:
        capture.release()

    expected_fps = float(row["source_fps"]) / stride
    if (width, height) != (int(row["source_width"]), int(row["source_height"])):
        raise ValueError(f"{path.name}: dimensions differ from the source")
    if frames != expected_frames:
        raise ValueError(f"{path.name}: expected {expected_frames} frames, found {frames}")
    if abs(fps - expected_fps) > 0.05:
        raise ValueError(f"{path.name}: expected {expected_fps:.3f} FPS, found {fps:.3f}")


def verify_experiment(output_dir: Path) -> list[str]:
    comparison_path = output_dir / "comparison.csv"
    metadata_path = output_dir / "run_metadata.json"
    if not comparison_path.is_file() or not metadata_path.is_file():
        raise ValueError("output folder must contain comparison.csv and run_metadata.json")

    with comparison_path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError("comparison.csv has no configuration rows")

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    missing_metadata = sorted(REQUIRED_METADATA - set(metadata))
    if missing_metadata:
        raise ValueError(f"metadata fields missing: {', '.join(missing_metadata)}")
    if len(str(metadata["model_sha256"])) != 64:
        raise ValueError("model_sha256 must contain 64 hexadecimal characters")
    if len(str(metadata["input_video_sha256"])) != 64:
        raise ValueError("input_video_sha256 must contain 64 hexadecimal characters")

    expected_configs = [item["name"] for item in metadata["configurations"]]
    actual_configs = [row["config_name"] for row in rows]
    if actual_configs != expected_configs:
        raise ValueError("comparison configurations differ from run metadata")

    common_frame_ids = None
    stride = int(metadata["frame_stride"])
    messages = []
    for row in rows:
        config_name = row["config_name"]
        predictions_path = output_dir / row["predictions_file"]
        failures_path = output_dir / row["failures_file"]
        records = _read_jsonl(predictions_path)
        processed = int(row["processed_frames"])
        if len(records) != processed:
            raise ValueError(
                f"{config_name}: comparison says {processed} records, found {len(records)}"
            )

        frame_ids = [int(record["frame_id"]) for record in records]
        if frame_ids != sorted(set(frame_ids)):
            raise ValueError(f"{config_name}: frame IDs are not unique and increasing")
        timestamps = [int(record["timestamp_ms"]) for record in records]
        if any(current <= previous for previous, current in zip(timestamps, timestamps[1:])):
            raise ValueError(f"{config_name}: timestamps are not strictly increasing")
        if common_frame_ids is None:
            common_frame_ids = frame_ids
        elif frame_ids != common_frame_ids:
            raise ValueError("configurations did not process the same source frames")

        no_face_ids = [
            int(record["frame_id"])
            for record in records
            if record["status"] == "NO_FACE"
        ]
        failure_ids = _read_failure_ids(failures_path)
        if failure_ids != no_face_ids:
            raise ValueError(f"{config_name}: failure CSV differs from NO_FACE records")

        faces_found = sum(record["status"] == "OK" for record in records)
        if faces_found != int(row["faces_found"]):
            raise ValueError(f"{config_name}: faces_found cannot be regenerated")
        if len(no_face_ids) != int(row["no_face_frames"]):
            raise ValueError(f"{config_name}: no_face_frames cannot be regenerated")
        expected_coverage = faces_found / processed if processed else 0.0
        if abs(expected_coverage - float(row["face_coverage"])) > 0.000001:
            raise ValueError(f"{config_name}: face_coverage cannot be regenerated")

        annotated_path = output_dir / f"annotated_{config_name}.mp4"
        if annotated_path.exists():
            _verify_video(annotated_path, row, processed, stride)
        messages.append(
            f"{config_name}: {processed} records, {faces_found} OK, "
            f"{len(no_face_ids)} NO_FACE"
        )

    return messages


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    try:
        messages = verify_experiment(args.output_dir.resolve())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Experiment verification: FAIL\n{exc}", file=sys.stderr)
        return 1
    for message in messages:
        print(message)
    print("Experiment verification: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
