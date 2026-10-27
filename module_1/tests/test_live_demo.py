from argparse import Namespace
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

import numpy as np


MODULE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_ROOT / "scripts"))

import live_demo  # noqa: E402
from sg1_detector import DetectorConfig  # noqa: E402


class FakeCapture:
    def __init__(self, frames, *, opened=True, fps=25):
        self.frames = list(frames)
        self.opened = opened
        self.fps = fps
        self.released = False

    def isOpened(self):
        return self.opened

    def read(self):
        if not self.frames:
            return False, None
        return True, self.frames.pop(0)

    def get(self, _property):
        return self.fps

    def release(self):
        self.released = True


class FakeDetector:
    def __init__(self, statuses):
        self.statuses = list(statuses)
        self.timestamps = []
        self.closed = False

    def process(self, _frame, frame_id, timestamp_ms):
        self.timestamps.append((frame_id, timestamp_ms))
        return {"status": self.statuses.pop(0)}

    def close(self):
        self.closed = True


def args(**overrides):
    defaults = dict(video=None, camera=None, headless=True, max_frames=0, display_width=1280)
    defaults.update(overrides)
    return Namespace(**defaults)


class LiveDemoTests(unittest.TestCase):
    def setUp(self):
        self.frame = np.zeros((48, 64, 3), dtype=np.uint8)
        self.config = DetectorConfig("lower_resolution", 192, 0.5, 0.5, 0.5)
        self.model = Path("example.task")

    def run_fake(self, options, capture, detector, *, clock=lambda: 0.0):
        return live_demo.run_preview(
            options, self.config, self.model,
            capture_factory=lambda _source: capture,
            detector_factory=lambda _model, _config: detector,
            clock=clock,
        )

    def test_source_options_are_mutually_exclusive(self):
        parser = live_demo.build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["--camera", "0", "--video", "example.mp4"])

    def test_headless_camera_requires_a_frame_limit(self):
        parser = live_demo.build_parser()
        options = parser.parse_args(["--headless"])
        with self.assertRaises(SystemExit):
            live_demo.validate_args(parser, options)

    def test_headless_camera_uses_default_index_and_monotonic_timestamps(self):
        capture = FakeCapture([self.frame.copy() for _ in range(3)])
        detector = FakeDetector(["OK", "NO_FACE", "OK"])
        capture_factory = Mock(return_value=capture)
        with patch.object(live_demo.cv2, "imshow") as imshow:
            result = live_demo.run_preview(
                args(max_frames=3), self.config, self.model,
                capture_factory=capture_factory,
                detector_factory=lambda _model, _config: detector,
                clock=lambda: 0.0,
            )
        capture_factory.assert_called_once_with(0)
        imshow.assert_not_called()
        self.assertEqual(result["processed"], 3)
        self.assertEqual((result["faces"], result["no_face"]), (2, 1))
        self.assertEqual(detector.timestamps, [(0, 0), (1, 1), (2, 2)])
        self.assertTrue(capture.released)
        self.assertTrue(detector.closed)

    def test_saved_video_uses_source_frame_timestamps_and_stops_at_eof(self):
        capture = FakeCapture([self.frame.copy(), self.frame.copy()], fps=25)
        detector = FakeDetector(["OK", "NO_FACE"])
        result = self.run_fake(args(video=Path("sample.mp4")), capture, detector)
        self.assertEqual(result["processed"], 2)
        self.assertEqual(detector.timestamps, [(0, 0), (1, 40)])
        self.assertTrue(capture.released)
        self.assertTrue(detector.closed)

    def test_quit_keys_close_gui_and_release_resources(self):
        for key in (ord("q"), ord("Q"), 27):
            with self.subTest(key=key):
                capture = FakeCapture([self.frame.copy(), self.frame.copy()])
                detector = FakeDetector(["NO_FACE", "OK"])
                with patch.object(live_demo.cv2, "namedWindow"), \
                     patch.object(live_demo.cv2, "imshow"), \
                     patch.object(live_demo.cv2, "waitKey", return_value=key), \
                     patch.object(live_demo.cv2, "destroyAllWindows") as destroy, \
                     patch.object(live_demo, "_display_frame", return_value=self.frame):
                    result = self.run_fake(args(headless=False), capture, detector)
                self.assertEqual((result["processed"], result["no_face"]), (1, 1))
                destroy.assert_called_once()
                self.assertTrue(capture.released)
                self.assertTrue(detector.closed)

    def test_closing_window_stops_preview(self):
        capture = FakeCapture([self.frame.copy(), self.frame.copy()])
        detector = FakeDetector(["OK", "OK"])
        with patch.object(live_demo.cv2, "namedWindow"), \
             patch.object(live_demo.cv2, "imshow"), \
             patch.object(live_demo.cv2, "waitKey", return_value=-1), \
             patch.object(live_demo.cv2, "getWindowProperty", return_value=0), \
             patch.object(live_demo.cv2, "destroyAllWindows"), \
             patch.object(live_demo, "_display_frame", return_value=self.frame):
            result = self.run_fake(args(headless=False), capture, detector)
        self.assertEqual(result["processed"], 1)
        self.assertTrue(capture.released)
        self.assertTrue(detector.closed)

    def test_camera_open_failure_releases_capture(self):
        capture = FakeCapture([], opened=False)
        detector_factory = Mock()
        with self.assertRaisesRegex(RuntimeError, "Could not open Camera: 0"):
            live_demo.run_preview(args(), self.config, self.model, capture_factory=lambda _source: capture,
                                  detector_factory=detector_factory, clock=lambda: 0.0)
        self.assertTrue(capture.released)
        detector_factory.assert_not_called()

    def test_detector_setup_failure_releases_capture(self):
        capture = FakeCapture([self.frame])
        detector_factory = Mock(side_effect=RuntimeError("model failed"))
        with self.assertRaisesRegex(RuntimeError, "model failed"):
            live_demo.run_preview(args(), self.config, self.model, capture_factory=lambda _source: capture,
                                  detector_factory=detector_factory, clock=lambda: 0.0)
        self.assertTrue(capture.released)

    def test_camera_read_failure_releases_detector_and_capture(self):
        capture = FakeCapture([self.frame])
        detector = FakeDetector(["OK"])
        with self.assertRaisesRegex(RuntimeError, "Could not read a frame from the camera"):
            self.run_fake(args(), capture, detector)
        self.assertTrue(capture.released)
        self.assertTrue(detector.closed)

    def test_detector_processing_failure_releases_resources(self):
        capture = FakeCapture([self.frame])
        detector = FakeDetector([])
        detector.process = Mock(side_effect=RuntimeError("inference failed"))
        with self.assertRaisesRegex(RuntimeError, "inference failed"):
            self.run_fake(args(), capture, detector)
        self.assertTrue(capture.released)
        self.assertTrue(detector.closed)


if __name__ == "__main__":
    unittest.main()
