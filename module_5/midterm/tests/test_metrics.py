"""Regression tests for strict event matching and honest abstention accounting."""

import csv
from pathlib import Path
import unittest

from module_5.midterm.metrics import evaluate_predictions


class MetricsTests(unittest.TestCase):
    def test_unknown_predictions_stay_in_denominator_and_confusion(self):
        out = evaluate_predictions([0, 1, 2], ["NORMAL", "WARNING", "DROWSY"],
                                   ["NORMAL", "UNKNOWN", "DROWSY"])
        self.assertAlmostEqual(out["accuracy"], 2 / 3)
        self.assertEqual(out["confusion"]["counts"][1], [0, 0, 0, 1])
        self.assertEqual(out["per_class"]["WARNING"]["fn"], 1)
        self.assertEqual(out["unknown_duration_s"], 1)
        self.assertEqual(out["evaluated_prediction_changes"], 2)
        self.assertIsNone(out["driver_state_changes"])
        self.assertIsNone(out["availability_status_changes"])

    def test_native_states_and_availability_transitions_are_not_conflated(self):
        out = evaluate_predictions(range(3), ["NORMAL"] * 3,
            ["NORMAL", "UNKNOWN", "NORMAL"], driver_states=["NORMAL"] * 3,
            statuses=["OK", "INSUFFICIENT_EVIDENCE", "OK"], valid=[True, False, True])
        self.assertEqual(out["evaluated_prediction_changes"], 2)
        self.assertEqual(out["driver_state_changes"], 0)
        self.assertEqual(out["availability_status_changes"], 2)
        self.assertEqual(out["input_availability_changes"], 2)

    def test_onset_must_be_within_episode_and_latency_nonnegative(self):
        out = evaluate_predictions(range(7),
            ["NORMAL", "DROWSY", "DROWSY", "NORMAL", "NORMAL", "NORMAL", "NORMAL"],
            ["NORMAL", "NORMAL", "DROWSY", "DROWSY", "NORMAL", "NORMAL", "NORMAL"])
        self.assertEqual(out["events"]["detected_events"], 1)
        self.assertEqual(out["events"]["latencies_s"], [1])
        self.assertEqual(out["false_drowsy_duration_s"], 1)

    def test_preexisting_alert_is_coverage_not_a_new_detection(self):
        out = evaluate_predictions(range(5),
            ["NORMAL", "NORMAL", "DROWSY", "DROWSY", "NORMAL"],
            ["NORMAL", "DROWSY", "DROWSY", "DROWSY", "NORMAL"])
        events = out["events"]
        self.assertEqual(events["detected_events"], 0)
        self.assertEqual(events["covered_events"], 1)
        self.assertEqual(events["preexisting_alert_events"], 1)
        self.assertEqual(events["false_alert_events"], 1)
        self.assertIsNone(events["mean_latency_s"])

    def test_one_long_prediction_cannot_detect_multiple_episodes(self):
        out = evaluate_predictions(range(7),
            ["NORMAL", "DROWSY", "DROWSY", "NORMAL", "DROWSY", "DROWSY", "NORMAL"],
            ["NORMAL", "DROWSY", "DROWSY", "DROWSY", "DROWSY", "DROWSY", "NORMAL"])
        events = out["events"]
        self.assertEqual(events["detected_events"], 1)
        self.assertEqual(events["missed_events"], 1)
        self.assertEqual(events["covered_events"], 2)

    def test_late_alert_not_promoted_to_detected(self):
        out = evaluate_predictions(range(6),
            ["NORMAL", "DROWSY", "NORMAL", "NORMAL", "NORMAL", "NORMAL"],
            ["NORMAL", "NORMAL", "NORMAL", "DROWSY", "NORMAL", "NORMAL"])
        self.assertEqual(out["events"]["detected_events"], 0)
        self.assertEqual(out["events"]["late_alert_events"], 1)
        self.assertEqual(out["events"]["false_alert_events"], 1)
        self.assertIsNone(out["events"]["mean_latency_s"])

    def test_two_predicted_onsets_in_one_episode_match_only_once(self):
        out = evaluate_predictions(range(6), ["DROWSY"] * 5 + ["NORMAL"],
            ["DROWSY", "DROWSY", "NORMAL", "DROWSY", "DROWSY", "NORMAL"])
        self.assertEqual(out["events"]["detected_events"], 1)
        self.assertEqual(out["events"]["false_alert_events"], 1)
        self.assertEqual(out["events"]["latencies_s"], [0])

    def test_episode_end_boundary_is_not_an_in_episode_onset(self):
        out = evaluate_predictions(range(4), ["NORMAL", "DROWSY", "NORMAL", "NORMAL"],
                                   ["NORMAL", "NORMAL", "DROWSY", "NORMAL"])
        self.assertEqual(out["events"]["detected_events"], 0)
        self.assertEqual(out["events"]["late_alert_events"], 1)

    def test_no_events_have_null_latency_and_undefined_event_rates(self):
        out = evaluate_predictions([0, 1], ["NORMAL"] * 2, ["NORMAL"] * 2)
        self.assertIsNone(out["events"]["mean_latency_s"])
        self.assertIsNone(out["events"]["event_precision"])
        self.assertIsNone(out["events"]["event_recall"])
        self.assertEqual(out["events"]["latencies_s"], [])

    def test_final_interval_and_invalid_duration_are_explicit(self):
        out = evaluate_predictions([0, .1, .3], ["NORMAL"] * 3,
            ["DROWSY", "NORMAL", "DROWSY"], valid=[False, True, False], final_dt=.05)
        self.assertEqual(out["duration_s"], .35)
        self.assertEqual(out["false_drowsy_duration_s"], .15)
        self.assertEqual(out["invalid_duration_s"], .15)
        inferred = evaluate_predictions([0, .1, .3], ["NORMAL"] * 3, ["NORMAL"] * 3)
        self.assertEqual(inferred["duration_s"], .45)

    def test_single_row_requires_interval(self):
        with self.assertRaises(ValueError):
            evaluate_predictions([0], ["DROWSY"], ["DROWSY"])
        out = evaluate_predictions([0], ["DROWSY"], ["DROWSY"], final_dt=.1)
        self.assertEqual(out["events"]["detected_events"], 1)
        self.assertEqual(out["duration_s"], .1)

    def test_arrays_reject_truncation_bad_time_and_bad_states(self):
        invalid = [([], [], []), ([0, 1], ["NORMAL"], ["NORMAL"]),
                   ([0, 0], ["NORMAL"] * 2, ["NORMAL"] * 2),
                   ([1, 0], ["NORMAL"] * 2, ["NORMAL"] * 2),
                   ([0, float("nan")], ["NORMAL"] * 2, ["NORMAL"] * 2),
                   ([0, True], ["NORMAL"] * 2, ["NORMAL"] * 2),
                   ([0, 1], ["UNKNOWN"] * 2, ["NORMAL"] * 2),
                   ([0, 1], ["NORMAL"] * 2, ["AWAKE"] * 2)]
        for args in invalid:
            with self.subTest(args=args), self.assertRaises(ValueError):
                evaluate_predictions(*args)
        with self.assertRaises(ValueError):
            evaluate_predictions([0, 1], ["NORMAL"] * 2, ["NORMAL"] * 2, valid=[True])

    def test_macro_f1_is_over_three_documented_classes(self):
        out = evaluate_predictions([0, 1, 2], ["NORMAL", "WARNING", "DROWSY"],
                                   ["NORMAL", "WARNING", "DROWSY"])
        self.assertEqual(out["macro_f1"], 1)
        self.assertEqual(out["drowsy_f1"], 1)


class BaselineParityTests(unittest.TestCase):
    def test_label_and_unapproved_fields_are_not_sent_to_engines(self):
        from module_5.midterm.evaluate import input_observation, FIELDS
        source = dict(time_s=0., face_valid=True, perclos=.1, eye_closure_s=.0,
                      long_blinks=0, yawn_count=0, gt_state="DROWSY", answer="DROWSY")
        self.assertEqual(set(input_observation(source)), set(FIELDS))

    def test_original_methods_match_committed_prediction_files(self):
        from module_5.midterm.evaluate import load_baselines, load_rows, input_observation, BASELINE_ROOT
        methods = load_baselines()
        for path in sorted((BASELINE_ROOT / "data").glob("drive*_synthetic.csv")):
            rows = load_rows(path)
            with (BASELINE_ROOT / "results" / (path.stem + "_predictions.csv")).open(newline="") as handle:
                saved = list(csv.DictReader(handle))
            self.assertEqual(len(rows), len(saved))
            for letter, function in methods.items():
                expected = [row[letter] for row in saved]
                with self.subTest(drive=path.name, method=letter):
                    self.assertEqual(function([input_observation(row) for row in rows]), expected)


if __name__ == "__main__":
    unittest.main()
