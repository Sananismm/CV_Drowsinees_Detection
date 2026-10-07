"""Regression tests for confidence handling, state timing and interface limits."""

import unittest
from copy import deepcopy

from compare import evaluate, intervals
from decision_logic import DecisionEngine, load_configs, make_engine, validate_input
from make_mock_data import NORMAL, RECOVERY_BAND, STRONG, build_rows, input_message


class DecisionTests(unittest.TestCase):
    def setUp(self):
        self.engine = make_engine("week5_stable")

    def message(self, second, values=NORMAL, confidence=0.92):
        return input_message("test", second, values, confidence)

    def test_normal_then_warning_then_drowsy(self):
        self.assertEqual(self.engine.decide(self.message(0))["state"], "ALERT")
        self.assertEqual(self.engine.decide(self.message(1, STRONG))["state"], "CAUTION")
        self.assertEqual(self.engine.decide(self.message(2, STRONG))["state"], "CAUTION")
        self.assertEqual(self.engine.decide(self.message(3, STRONG))["state"], "DROWSY")

    def test_single_spike_does_not_sound_alarm(self):
        self.engine.decide(self.message(0))
        self.assertEqual(self.engine.decide(self.message(1, STRONG))["alert_action"], "VISUAL")
        self.assertNotEqual(self.engine.decide(self.message(2))["alert_action"], "AUDIO_VISUAL")

    def test_five_seconds_of_low_risk_needed_for_release(self):
        for second in range(3):
            self.engine.decide(self.message(second, STRONG))
        for second in range(3, 8):
            self.assertEqual(self.engine.decide(self.message(second))["state"], "DROWSY")
        self.assertEqual(self.engine.decide(self.message(8))["state"], "ALERT")

    def test_middle_band_does_not_clear_drowsiness(self):
        for second in range(3):
            self.engine.decide(self.message(second, STRONG))
        for second in range(3, 12):
            self.assertEqual(self.engine.decide(self.message(second, RECOVERY_BAND))["state"], "DROWSY")

    def test_low_risk_timer_must_be_continuous(self):
        for second in range(3):
            self.engine.decide(self.message(second, STRONG))
        self.engine.decide(self.message(3))
        self.engine.decide(self.message(4, RECOVERY_BAND))
        for second in range(5, 10):
            self.assertEqual(self.engine.decide(self.message(second))["state"], "DROWSY")
        self.assertEqual(self.engine.decide(self.message(10))["state"], "ALERT")

    def test_low_confidence_is_unknown_and_resets_entry(self):
        self.engine.decide(self.message(0, STRONG))
        result = self.engine.decide(self.message(1, STRONG, 0.2))
        self.assertEqual((result["state"], result["alert_action"]), ("UNKNOWN", "NONE"))
        self.assertEqual(self.engine.decide(self.message(2, STRONG))["state"], "CAUTION")

    def test_confidence_is_gated_before_rounding(self):
        result = self.engine.decide(self.message(0, STRONG, 0.5499))
        self.assertEqual(result["state"], "UNKNOWN")

    def test_missing_invalid_or_nonfinite_fields_rejected(self):
        for change in ("missing", "range", "nan", "boolean", "extra"):
            with self.subTest(change=change):
                message = self.message(0)
                if change == "missing":
                    del message["yawn"]["count"]
                elif change == "range":
                    message["eye"]["perclos"] = 1.2
                elif change == "nan":
                    message["eye"]["confidence"] = float("nan")
                elif change == "boolean":
                    message["timestamp_ms"] = True
                else:
                    message["label"] = "DROWSY"
                with self.assertRaises(ValueError):
                    self.engine.decide(message)

    def test_out_of_order_timestamp_rejected(self):
        self.engine.decide(self.message(2))
        with self.assertRaises(ValueError):
            self.engine.decide(self.message(1))

    def test_data_gap_cannot_complete_a_timer(self):
        self.engine.decide(self.message(0, STRONG))
        self.assertEqual(self.engine.decide(self.message(10, STRONG))["state"], "CAUTION")

    def test_driver_change_starts_fresh(self):
        for second in range(3):
            self.engine.decide(self.message(second, STRONG))
        message = self.message(3)
        message["driver_track_id"] = "another-driver"
        self.assertEqual(self.engine.decide(message)["state"], "ALERT")

    def test_windows_with_equal_yawn_rate_have_equal_risk(self):
        first = self.message(0)
        first["yawn"].update(count=2, total_duration_ms=4000)
        second = deepcopy(first)
        second["window_ms"] = 30000
        second["yawn"].update(count=1, total_duration_ms=2000)
        a = make_engine("week5_stable").decide(first)
        b = make_engine("week5_stable").decide(second)
        self.assertEqual(a["risk_score"], b["risk_score"])

    def test_thresholds_include_upper_state_at_boundary(self):
        config = load_configs()["week5_stable"]
        config["drowsy_entry_ms"] = 0
        message = self.message(0, (1.0, 3000, 0, 0, 0.5))
        self.assertEqual(DecisionEngine(config).decide(message)["state"], "DROWSY")

    def test_all_mock_messages_and_outputs_follow_v1(self):
        expected = {"schema_version", "session_id", "driver_track_id", "timestamp_ms", "state", "risk_score", "confidence", "alert_action", "evidence", "reason"}
        for name in load_configs():
            engine = make_engine(name)
            for row in build_rows():
                validate_input(row["input"])
                result = engine.decide(row["input"])
                self.assertEqual(set(result), expected)
                self.assertEqual(result["schema_version"], "sg5.decision.v1")
                self.assertGreaterEqual(result["risk_score"], 0)
                self.assertLessEqual(result["risk_score"], 1)

    def test_episode_intervals(self):
        self.assertEqual(intervals([False, True, True, False, True]), [(1, 2), (4, 4)])
        self.assertEqual(intervals([]), [])

    def test_evaluator_counts_false_event_and_samples_separately(self):
        rows = [
            {"label": "ALERT", "input": self.message(0)},
            {"label": "ALERT", "input": self.message(1, STRONG)},
            {"label": "ALERT", "input": self.message(2)},
            {"label": "ALERT", "input": self.message(3)},
        ]
        summary, _, episodes = evaluate("week4_baseline", {"false-spike": rows})
        self.assertEqual(summary["false_alert_events"], 1)
        self.assertEqual(summary["false_positive_samples"], 3)
        self.assertEqual(episodes, [])
        candidate, _, _ = evaluate("week5_stable", {"false-spike": rows})
        self.assertEqual(candidate["false_alert_events"], 0)

    def test_evaluator_does_not_report_missed_episode_as_zero_latency(self):
        rows = [
            {"label": "DROWSY", "input": self.message(0, STRONG)},
            *[{"label": "ALERT", "input": self.message(i)} for i in range(1, 7)],
        ]
        baseline, _, episodes = evaluate("week4_baseline", {"short-episode": rows})
        self.assertEqual(baseline["detected_episodes"], 1)
        self.assertEqual(episodes[0]["alert_latency_ms"], 0)
        self.assertEqual(baseline["false_positive_samples"], 5)
        self.assertEqual(baseline["false_alert_events"], 0)
        candidate, _, episodes = evaluate("week5_stable", {"short-episode": rows})
        self.assertEqual(candidate["missed_episodes"], 1)
        self.assertEqual(episodes[0]["alert_latency_ms"], "")
        self.assertEqual(candidate["mean_alert_latency_ms"], "")


if __name__ == "__main__":
    unittest.main()
