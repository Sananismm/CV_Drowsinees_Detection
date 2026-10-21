from pathlib import Path
import sys
import unittest


MODULE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_ROOT / "scripts"))

from evaluate_boxes import iou, score_boxes  # noqa: E402


class IoUTests(unittest.TestCase):
    def test_identical_boxes(self):
        self.assertEqual(iou([0, 0, 10, 10], [0, 0, 10, 10]), 1.0)

    def test_disjoint_boxes(self):
        self.assertEqual(iou([0, 0, 10, 10], [10, 10, 20, 20]), 0.0)

    def test_partial_overlap(self):
        self.assertAlmostEqual(
            iou([0, 0, 10, 10], [5, 5, 15, 15]), 25 / 175
        )

    def test_zero_area_box(self):
        self.assertEqual(iou([0, 0, 0, 10], [0, 0, 10, 10]), 0.0)

    def test_empty_ground_truth_is_a_true_negative(self):
        result = score_boxes({7: None}, {7: None})
        self.assertEqual(result["annotated_frames"], 1)
        self.assertEqual(result["false_positive"], 0)
        self.assertEqual(result["false_negative"], 0)
        self.assertEqual(result["errors"], [])

    def test_detection_on_empty_ground_truth_is_false_positive(self):
        result = score_boxes({7: [1, 1, 5, 5]}, {7: None})
        self.assertEqual(result["false_positive"], 1)
        self.assertEqual(result["false_negative"], 0)


if __name__ == "__main__":
    unittest.main()
