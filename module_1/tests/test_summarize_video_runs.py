import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest


MODULE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_ROOT / "scripts"))

from sg1_contract import LANDMARK_TOPOLOGY, SCHEMA_VERSION  # noqa: E402
from summarize_video_runs import collect_summaries, write_summaries  # noqa: E402


def config(name):
    return {
        "name": name,
        "input_long_side": 256 if name == "baseline" else 192,
        "min_face_detection_confidence": 0.5,
        "min_face_presence_confidence": 0.5,
        "min_tracking_confidence": 0.5,
    }


def record(frame_id, name, box, elapsed):
    return {
        "schema_version": SCHEMA_VERSION,
        "frame_id": frame_id,
        "timestamp_ms": frame_id * 40,
        "image_width": 100,
        "image_height": 100,
        "status": "OK" if box is not None else "NO_FACE",
        "face_bbox_xyxy": box,
        "landmarks_xy_normalized": [[0.5, 0.5]] * 478 if box is not None else [],
        "landmark_count": 478 if box is not None else 0,
        "landmark_topology": LANDMARK_TOPOLOGY,
        "detection_confidence": None,
        "config_name": name,
        "inference_ms": elapsed,
    }


def write_csv(path, fields, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def make_clip(runs, labels, clip, boxes, times, wall, names=("baseline", "alternative"), source_frames=None):
    path = runs / clip
    path.mkdir(parents=True)
    labels.mkdir(parents=True, exist_ok=True)
    configs = [config(name) for name in names]
    metadata = {
        "schema_version": SCHEMA_VERSION,
        "landmark_topology": LANDMARK_TOPOLOGY,
        "model_filename": "face_landmarker.task",
        "model_sha256": "a" * 64,
        "python_version": "3.12",
        "mediapipe_version": "test",
        "opencv_version": "test",
        "numpy_version": "test",
        "input_video": f"{clip}.mp4",
        "input_video_sha256": "b" * 64,
        "frame_stride": 1,
        "configurations": configs,
    }
    (path / "run_metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    rows = []
    for item in configs:
        name = item["name"]
        records = [record(i, name, box, times[i]) for i, box in enumerate(boxes)]
        (path / f"predictions_{name}.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in records), encoding="utf-8"
        )
        failures = [
            {"frame_idx": row["frame_id"], "timestamp_ms": row["timestamp_ms"], "reason": "NO_FACE"}
            for row in records if row["status"] == "NO_FACE"
        ]
        write_csv(path / f"failures_{name}.csv", ["frame_idx", "timestamp_ms", "reason"], failures)
        found = sum(box is not None for box in boxes)
        rows.append({
            "config_name": name,
            **{k: v for k, v in item.items() if k != "name"},
            "video": f"{clip}.mp4", "source_width": 100, "source_height": 100,
            "source_frames": len(boxes) if source_frames is None else source_frames,
            "processed_frames": len(boxes), "faces_found": found,
            "face_coverage": round(found / len(boxes), 6),
            "no_face_frames": len(boxes) - found,
            "end_to_end_processed_fps": round(len(boxes) / wall, 3), "wall_seconds": wall,
            "predictions_file": f"predictions_{name}.jsonl",
            "failures_file": f"failures_{name}.csv",
        })
    write_csv(path / "comparison.csv", list(rows[0]), rows)
    # Clip A has one matching box, one IoU mismatch, and one true no-face.
    # Clip B has one matching box and one missing prediction.
    label_rows = [
        {"frame_idx": i, "x1": 1, "y1": 1, "x2": 5, "y2": 5}
        for i in range(len(boxes))
    ]
    if clip == "clipA":
        label_rows[2] = {"frame_idx": 2, "x1": "", "y1": "", "x2": "", "y2": ""}
    write_csv(labels / f"{clip}_boxes.csv", ["frame_idx", "x1", "y1", "x2", "y2"], label_rows)


class VideoSummaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.runs = self.root / "runs"
        self.labels = self.root / "labels"
        make_clip(self.runs, self.labels, "clipA", [[1, 1, 5, 5], [10, 10, 15, 15], None], [1, 2, 3], 2)
        make_clip(self.runs, self.labels, "clipB", [[1, 1, 5, 5], None], [4, 10], 1)

    def test_pools_frame_latencies_counts_and_provisional_metrics(self):
        summaries = collect_summaries(self.runs, self.labels, require_complete=True)
        aggregate = summaries["aggregate_comparison.csv"][0]
        self.assertEqual(aggregate["config_name"], "baseline")
        self.assertEqual((aggregate["clips"], aggregate["processed_frames"]), (2, 5))
        self.assertEqual((aggregate["returned_face_frames"], aggregate["no_face_frames"]), (3, 2))
        self.assertEqual(aggregate["face_coverage_availability"], 0.6)
        self.assertEqual(aggregate["mean_inference_ms"], 4.0)
        self.assertEqual(aggregate["p95_inference_ms"], 8.8)
        self.assertEqual(aggregate["combined_end_to_end_fps"], 1.667)
        metrics = summaries["provisional_box_metrics_summary.csv"][0]
        self.assertEqual((metrics["annotated_frames"], metrics["true_positive"], metrics["false_positive"], metrics["false_negative"]), (5, 2, 1, 2))
        self.assertEqual((metrics["precision"], metrics["recall"], metrics["f1"]), (0.666667, 0.5, 0.571429))
        mismatches = [row for row in summaries["mismatch_cases.csv"] if row["config_name"] == "baseline"]
        self.assertEqual([(row["clip"], row["frame_idx"], row["mismatch_type"]) for row in mismatches], [
            ("clipA", 1, "below_iou_threshold"),
            ("clipB", 1, "no_face_prediction_for_reference_face"),
        ])

        destination = self.root / "summaries"
        write_summaries(destination, summaries)
        self.assertEqual(len(list(destination.iterdir())), 4)
        for path in destination.iterdir():
            text = path.read_text(encoding="utf-8")
            self.assertNotIn(str(self.root), text)
            self.assertNotIn("landmarks_xy_normalized", text)

    def test_rejects_incomplete_run_when_required(self):
        path = self.runs / "clipA" / "comparison.csv"
        with path.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        for row in rows:
            row["source_frames"] = "4"
        write_csv(path, list(rows[0]), rows)
        with self.assertRaisesRegex(ValueError, "run is incomplete"):
            collect_summaries(self.runs, self.labels, require_complete=True)

    def test_rejects_missing_labels_and_missing_prediction_frame(self):
        path = self.labels / "clipB_boxes.csv"
        path.unlink()
        with self.assertRaisesRegex(ValueError, "missing labels file"):
            collect_summaries(self.runs, self.labels)
        write_csv(path, ["frame_idx", "x1", "y1", "x2", "y2"], [
            {"frame_idx": 99, "x1": 1, "y1": 1, "x2": 5, "y2": 5},
        ])
        with self.assertRaisesRegex(ValueError, "predictions missing 1 annotated frame"):
            collect_summaries(self.runs, self.labels)

    def test_rejects_inconsistent_configuration_names(self):
        other_runs = self.root / "other_runs"
        other_labels = self.root / "other_labels"
        make_clip(other_runs, other_labels, "clipA", [[1, 1, 5, 5], [10, 10, 15, 15], None], [1, 2, 3], 2)
        make_clip(other_runs, other_labels, "clipB", [[1, 1, 5, 5], None], [4, 10], 1, names=("baseline", "different"))
        with self.assertRaisesRegex(ValueError, "configuration names differ"):
            collect_summaries(other_runs, other_labels)

    def test_rejects_same_named_configuration_with_different_parameters(self):
        metadata_path = self.runs / "clipB" / "run_metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["configurations"][0]["input_long_side"] = 128
        metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "configuration parameters differ"):
            collect_summaries(self.runs, self.labels)

    def test_existing_destination_is_never_overwritten(self):
        destination = self.root / "existing"
        destination.mkdir()
        sentinel = destination / "aggregate_comparison.csv"
        sentinel.write_text("preserve me", encoding="utf-8")
        summaries = collect_summaries(self.runs, self.labels)
        with self.assertRaises(FileExistsError):
            write_summaries(destination, summaries)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "preserve me")


if __name__ == "__main__":
    unittest.main()
