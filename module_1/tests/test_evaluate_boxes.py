from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


MODULE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_ROOT / "scripts"))

from evaluate_boxes import iou, main, read_labels, read_predictions, score_boxes  # noqa: E402


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

    def test_missing_prediction_frame_is_not_a_no_face_result(self):
        with self.assertRaisesRegex(ValueError, "missing 1 annotated frame.*7"):
            score_boxes({}, {7: [1, 1, 5, 5]})

    def test_explicit_no_face_prediction_is_a_false_negative(self):
        result = score_boxes({7: None}, {7: [1, 1, 5, 5]})
        self.assertEqual(result["false_negative"], 1)

    def test_missing_prediction_cannot_be_counted_as_a_true_negative(self):
        with self.assertRaisesRegex(ValueError, "missing 1 annotated frame.*7"):
            score_boxes({}, {7: None})

    def test_low_overlap_counts_as_one_false_positive_and_false_negative(self):
        result = score_boxes(
            {0: [1, 1, 5, 5], 1: [10, 10, 15, 15], 2: None},
            {0: [1, 1, 5, 5], 1: [1, 1, 5, 5], 2: None},
        )
        self.assertEqual((result["true_positive"], result["false_positive"], result["false_negative"]), (1, 1, 1))
        self.assertEqual((result["precision"], result["recall"], result["f1"]), (0.5, 0.5, 0.5))

    def test_empty_label_set_is_not_a_valid_evaluation(self):
        with self.assertRaisesRegex(ValueError, "at least one annotated frame"):
            score_boxes({}, {})


class EvaluationInputTests(unittest.TestCase):
    def read(self, reader, filename, contents):
        with patch.object(Path, "open", return_value=StringIO(contents)):
            return reader(Path(filename))

    def test_prediction_file_rejects_duplicate_frame_ids(self):
        with self.assertRaisesRegex(ValueError, "duplicate prediction frame_id 7"):
            self.read(
                read_predictions,
                "predictions.jsonl",
                '{"frame_id":7,"face_bbox_xyxy":null}\n'
                '{"frame_id":7,"face_bbox_xyxy":[1,1,5,5]}\n',
            )

    def test_prediction_without_box_field_is_not_no_face(self):
        with self.assertRaisesRegex(ValueError, "missing face_bbox_xyxy"):
            self.read(read_predictions, "predictions.jsonl", '{"frame_id":7}\n')

    def test_label_file_rejects_duplicate_frame_ids(self):
        with self.assertRaisesRegex(ValueError, "duplicate label frame_idx 7"):
            self.read(read_labels, "labels.csv", "frame_idx,x1,y1,x2,y2\n7,1,1,5,5\n7,,,,\n")

    def test_fully_empty_box_is_explicit_no_face(self):
        self.assertEqual(
            self.read(read_labels, "labels.csv", "frame_idx,x1,y1,x2,y2\n7,,,,\n"),
            {7: None},
        )

    def test_label_file_rejects_partial_or_truncated_box(self):
        for row in ("7,1,,5,5", "7,", "7,1,2,3"):
            with self.subTest(row=row):
                with self.assertRaises(ValueError):
                    self.read(read_labels, "labels.csv", f"frame_idx,x1,y1,x2,y2\n{row}\n")

    def test_label_file_rejects_invalid_box_coordinates(self):
        for row in ("7,a,1,5,5", "7,nan,1,5,5", "7,-1,1,5,5", "7,5,1,5,5", "7,1,5,5,1"):
            with self.subTest(row=row):
                with self.assertRaises(ValueError):
                    self.read(read_labels, "labels.csv", f"frame_idx,x1,y1,x2,y2\n{row}\n")

    def test_label_file_accepts_finite_decimal_pixel_coordinates(self):
        self.assertEqual(
            self.read(read_labels, "labels.csv", "frame_idx,x1,y1,x2,y2\n7,1.5,2,5.5,6\n"),
            {7: [1.5, 2.0, 5.5, 6.0]},
        )

    def test_cli_rejects_output_that_would_overwrite_predictions(self):
        argv = [
            "evaluate_boxes.py", "--predictions", "p.jsonl", "--labels", "l.csv",
            "--output", "p.jsonl",
        ]
        error = StringIO()
        with patch.object(sys, "argv", argv), \
                patch("evaluate_boxes.read_predictions", return_value={7: None}), \
                patch("evaluate_boxes.read_labels", return_value={7: None}), \
                redirect_stderr(error), self.assertRaises(SystemExit):
            main()
        self.assertIn("output must differ", error.getvalue())


if __name__ == "__main__":
    unittest.main()
