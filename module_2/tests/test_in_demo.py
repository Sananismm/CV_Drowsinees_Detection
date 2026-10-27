"""Launcher contracts: fresh input, protected outputs, useful errors and faithful exports."""
import copy
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from unittest.mock import patch

import cv2

from module_2 import in_demo


class InstructorLauncherTests(unittest.TestCase):
    def test_discovers_original_and_never_searches_result_videos(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outputs = root / "module_2/results/instructor_demo"
            outputs.mkdir(parents=True)
            (outputs / "overlay.mp4").touch()
            with self.assertRaisesRegex(in_demo.DemoError, "No original video"):
                in_demo.find_video(repository=root)
            inputs = root / "Sg 1 data"
            inputs.mkdir()
            (inputs / "another.mp4").touch()
            preferred = inputs / "P1042801_720.mp4"
            preferred.touch()
            self.assertEqual(in_demo.find_video(repository=root), preferred.resolve())

    def test_custom_video_missing_is_an_actionable_cli_error(self):
        error = io.StringIO()
        with tempfile.TemporaryDirectory() as directory, redirect_stderr(error):
            status = in_demo.main(["--video", str(Path(directory) / "missing.mp4")])
        self.assertEqual(status, 1)
        self.assertIn("Video not found", error.getvalue())
        self.assertIn("--video", error.getvalue())

    def test_missing_model_never_uses_cached_landmarks(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(in_demo.DemoError, "Cached landmarks will not be substituted"):
                in_demo.find_model(repository=Path(directory))
            explicit = Path(directory) / "face.task"
            explicit.touch()
            self.assertEqual(in_demo.find_model(explicit), explicit.resolve())

    def test_missing_dependency_has_install_instructions(self):
        with patch.object(in_demo.importlib, "import_module", side_effect=ImportError("unavailable")):
            with self.assertRaisesRegex(in_demo.DemoError, "pip install -r module_2/requirements-demo.txt"):
                in_demo.dependencies()

    def test_output_allocation_preserves_previous_results(self):
        with tempfile.TemporaryDirectory() as directory:
            first = in_demo.new_run_directory(directory)
            historical = first / "summary.json"
            historical.write_text("protected")
            second = in_demo.new_run_directory(directory)
            self.assertNotEqual(first, second)
            self.assertEqual(historical.read_text(), "protected")

    def test_selected_method_and_protocol_integrity_guard(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "models").mkdir()
            (root / "models/best.pt").write_bytes(b"checkpoint")
            protocol = root / "selection_protocol.json"
            protocol.write_bytes(b"{}\n")
            config = dict(selected=dict(method="EAR", ear_threshold=.15, open_frames=2,
                                        max_open_delay_sec=.08, name="EAR_0.15_open2"),
                          protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),
                          checkpoint_sha256=hashlib.sha256(b"checkpoint").hexdigest())
            path = root / "final_method.json"
            path.write_text(json.dumps(config))
            self.assertEqual(in_demo.selected_settings(root), config["selected"])
            protocol.write_bytes(b"{}\r\n")
            with self.assertRaisesRegex(in_demo.DemoError, "Checksum mismatch"):
                in_demo.selected_settings(root)
            config["selected"]["method"] = "CNN"
            path.write_text(json.dumps(config))
            with self.assertRaisesRegex(in_demo.DemoError, "differs from approved EAR"):
                in_demo.selected_settings(root)

    def test_delegates_fresh_full_video_and_restores_arguments(self):
        from module_2 import demo
        previous = sys.argv
        captured = []
        with patch.object(demo, "main", side_effect=lambda: captured.extend(sys.argv)):
            in_demo.run_pipeline(Path("original video.mp4"), Path("model.task"), Path("output"))
        self.assertIs(sys.argv, previous)
        self.assertEqual(captured[captured.index("--mode") + 1], "EAR")
        self.assertEqual(captured[captured.index("--threshold") + 1], "0.15")
        self.assertEqual(Path(captured[captured.index("--sg1-source") + 1]),
                         in_demo.REPOSITORY / "module_1/scripts/sg1_detector.py")
        self.assertNotIn("--sg1-jsonl", captured)
        self.assertNotIn("--max-frames", captured)
        with patch.object(demo, "main", side_effect=RuntimeError("detector failed")):
            with self.assertRaisesRegex(RuntimeError, "detector failed"):
                in_demo.run_pipeline(Path("video"), Path("model"), Path("output"))
        self.assertIs(sys.argv, previous)

    def test_stream_truncation_is_rejected_before_video_success(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / "summary.json").write_text("{}")
            (output / "sg1.jsonl").write_text("{}\n")
            (output / "sg2.jsonl").write_text("")
            (output / "sg4.jsonl").write_text("")
            with self.assertRaisesRegex(in_demo.DemoError, "different lengths"):
                in_demo.validate_outputs(output, cv2, 25, 1)

    def test_presentation_preserves_predictions_and_nested_event_csv(self):
        records = []
        for index, state in enumerate(("UNKNOWN", "CLOSED", "OPEN")):
            value = None if state == "UNKNOWN" else .1 if state == "CLOSED" else .2
            records.append(dict(frame_id=index, timestamp_sec=index / 25, eye_state=state,
                                left_ear=value, right_ear=value, ear=value, ear_threshold=.15,
                                closure_event={"start_frame": 1, "end_frame": 2} if index == 2 else None))
        before = copy.deepcopy(records)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            in_demo.export_presentation(records, output)
            with (output / "sg2.csv").open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual([row["eye_state"] for row in rows], [row["eye_state"] for row in records])
            self.assertEqual(json.loads(rows[2]["closure_event"]), records[2]["closure_event"])
            for name in ("ear_timeline.png", "eye_state_timeline.png"):
                self.assertIsNotNone(cv2.imread(str(output / name)))
        self.assertEqual(records, before)


if __name__ == "__main__":
    unittest.main()
