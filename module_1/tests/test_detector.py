from pathlib import Path
import sys
import unittest

import numpy as np


MODULE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_ROOT / "scripts"))

from sg1_contract import validate_sg1_record  # noqa: E402
from sg1_detector import (  # noqa: E402
    DetectorConfig,
    SG1FaceLandmarkDetector,
    clamped_landmark_box,
)


class DetectorTests(unittest.TestCase):
    def test_landmark_box_is_clamped_to_image(self):
        box = clamped_landmark_box(
            np.asarray([[-0.2, -0.1], [1.3, 1.1]], dtype=np.float32),
            image_width=640,
            image_height=360,
        )
        self.assertEqual(box, [0, 0, 640, 360])

    @classmethod
    def setUpClass(cls):
        cls.config = DetectorConfig("test", 192, 0.5, 0.5, 0.5)
        cls.model_path = MODULE_ROOT / "models" / "face_landmarker.task"

    def test_resize_preserves_aspect_ratio(self):
        detector = object.__new__(SG1FaceLandmarkDetector)
        detector.config = self.config
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        resized = detector._resize(frame)
        self.assertEqual(resized.shape[:2], (108, 192))

    def test_small_frame_is_not_enlarged(self):
        detector = object.__new__(SG1FaceLandmarkDetector)
        detector.config = self.config
        frame = np.zeros((100, 120, 3), dtype=np.uint8)
        self.assertIs(detector._resize(frame), frame)

    def test_model_no_face_and_timestamp_monotonicity(self):
        if not self.model_path.exists():
            self.skipTest("model is not downloaded")
        detector = SG1FaceLandmarkDetector(self.model_path, self.config)
        try:
            frame = np.zeros((240, 320, 3), dtype=np.uint8)
            first = detector.process(frame, 0, 0)
            second = detector.process(frame, 1, 0)
        finally:
            detector.close()
        validate_sg1_record(first)
        validate_sg1_record(second)
        self.assertEqual(first["status"], "NO_FACE")
        self.assertEqual(first["face_bbox_xyxy"], None)
        self.assertEqual(first["landmarks_xy_normalized"], [])
        self.assertEqual(second["timestamp_ms"], first["timestamp_ms"] + 1)


if __name__ == "__main__":
    unittest.main()
