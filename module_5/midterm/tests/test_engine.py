"""Standard-library regressions for the status-aware SG5 streaming core."""

from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
import subprocess
import sys
import unittest

from module_5.midterm.engine import CONFIGURATIONS, Config, DecisionEngine, drowsiness_score, to_legacy_sg6


def row(t=0.0, **changes):
    value = {"time_s": t, "face_valid": 1, "perclos": 0.05,
             "eye_closure_s": 0.0, "long_blinks": 0, "yawn_count": 0}
    value.update(changes)
    return value


def high(t, **changes):
    return row(t, perclos=0.30, long_blinks=6, yawn_count=3, **changes)


class ConfigTests(unittest.TestCase):
    def test_config_is_frozen(self):
        with self.assertRaises(FrozenInstanceError):
            Config().confirm_s = 0
        with self.assertRaises(TypeError):
            CONFIGURATIONS["other"] = Config()

    def test_invalid_configurations_are_rejected(self):
        cases = [{"method": "D"}, {"weights": [0.45, 0.2, 0.2, 0.15]},
                 {"weights": (0, 0, 0, 0)}, {"smoothing_s": 0}, {"max_gap_s": 0},
                 {"min_quality": 2}, {"exit_warn": 0.3}, {"confirm_s": -1},
                 {"a_warn_yawns": 1.2}, {"config_id": ""}]
        for changes in cases:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                Config(**changes)

    def test_score_normalizes_before_weighting(self):
        self.assertAlmostEqual(drowsiness_score(row(perclos=0.175)), 0.225)
        self.assertAlmostEqual(drowsiness_score(row(perclos=1, eye_closure_s=10, long_blinks=10, yawn_count=10)), 1.0)
        self.assertEqual(drowsiness_score(row()), 0.0)

    def test_alternatives_keep_thresholds(self):
        a = DecisionEngine(CONFIGURATIONS["threshold_a"])
        self.assertEqual(a.step(row(perclos=0.22))["driver_state"], "DROWSY")
        b = DecisionEngine(CONFIGURATIONS["weighted_b"])
        self.assertEqual(b.step(row(eye_closure_s=2.0))["driver_state"], "WARNING")
        self.assertEqual(b.step(high(0.1))["driver_state"], "DROWSY")


class EngineTests(unittest.TestCase):
    def test_first_sample_is_usable_without_forced_warmup(self):
        result = DecisionEngine().step(row(1000.0, eye_closure_s=1.5))
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["driver_state"], "DROWSY")
        self.assertTrue(result["alert_event"])

    def test_micro_sleep_keeps_real_scores(self):
        result = DecisionEngine().step(row(eye_closure_s=1.5))
        self.assertAlmostEqual(result["score"], 0.1375)
        self.assertAlmostEqual(result["smoothed_score"], 0.1375)
        self.assertIn("override", result["reason"])

    def test_high_score_requires_continuous_confirmation(self):
        engine = DecisionEngine()
        for t in (0.0, 0.25, 0.5, 0.75):
            self.assertEqual(engine.step(high(t))["driver_state"], "NORMAL")
        result = engine.step(high(1.0))
        self.assertEqual(result["driver_state"], "DROWSY")
        self.assertTrue(result["transition"])
        self.assertTrue(result["alert_event"])
        self.assertFalse(engine.step(high(1.1))["alert_event"])

    def test_warning_and_drowsy_have_separate_confirmation(self):
        engine = DecisionEngine(replace(Config(), smoothing_s=0.001))
        for t in (0.0, 0.25, 0.5, 0.75):
            engine.step(row(t, perclos=0.175))
        self.assertEqual(engine.step(high(1.0))["driver_state"], "NORMAL")
        for t in (1.25, 1.5, 1.75):
            self.assertEqual(engine.step(high(t))["driver_state"], "NORMAL")
        self.assertEqual(engine.step(high(2.0))["driver_state"], "DROWSY")

    def test_recovery_requires_continuous_low_evidence(self):
        engine = DecisionEngine(replace(Config(), smoothing_s=0.001))
        engine.step(row(eye_closure_s=1.5))
        for i in range(1, 13):
            self.assertEqual(engine.step(row(i * 0.25))["driver_state"], "DROWSY")
        result = engine.step(row(3.25))
        self.assertEqual(result["driver_state"], "NORMAL")
        self.assertTrue(result["transition"])
        self.assertFalse(result["alert_event"])

    def test_invalid_face_holds_untrusted_state_and_suppresses_alert(self):
        engine = DecisionEngine()
        engine.step(row(eye_closure_s=1.5))
        result = engine.step(row(0.1, face_valid=0))
        self.assertEqual(result["driver_state"], "DROWSY")
        self.assertEqual(result["status"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(result["quality"], 0)
        self.assertEqual(result["alert_level"], 0)
        self.assertFalse(result["alert"])
        self.assertFalse(result["alert_event"])

    def test_invalid_eye_cannot_use_large_closure(self):
        result = DecisionEngine().step(row(eye_valid=False, eye_closure_s=10))
        self.assertEqual(result["status"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(result["driver_state"], "NORMAL")

    def test_quality_threshold_is_inclusive(self):
        self.assertEqual(DecisionEngine().step(row(validity_score=0.55))["status"], "OK")
        result = DecisionEngine().step(row(validity_score=0.54999))
        self.assertEqual(result["status"], "INSUFFICIENT_EVIDENCE")

    def test_invalid_input_resets_upward_confirmation(self):
        engine = DecisionEngine()
        engine.step(high(0))
        engine.step(high(0.5))
        engine.step(high(0.6, face_valid=0))
        for t in (0.7, 1.0, 1.25, 1.5):
            self.assertEqual(engine.step(high(t))["driver_state"], "NORMAL")
        self.assertEqual(engine.step(high(1.75))["driver_state"], "DROWSY")

    def test_input_gap_resets_upward_confirmation(self):
        engine = DecisionEngine()
        engine.step(high(0))
        result = engine.step(high(2))
        self.assertEqual(result["driver_state"], "NORMAL")
        self.assertIn("gap", result["reason"])
        for t in (2.25, 2.5, 2.75):
            engine.step(high(t))
        self.assertEqual(engine.step(high(3.0))["driver_state"], "DROWSY")

    def test_invalid_input_resets_recovery_timer(self):
        engine = DecisionEngine(replace(Config(), smoothing_s=0.001))
        engine.step(row(eye_closure_s=1.5))
        for i in range(1, 9):
            engine.step(row(i * 0.25))
        engine.step(row(2.25, face_valid=0))
        for i in range(10, 22):
            self.assertEqual(engine.step(row(i * 0.25))["driver_state"], "DROWSY")
        self.assertEqual(engine.step(row(5.5))["driver_state"], "NORMAL")

    def test_tick_detects_silence_and_is_not_an_observation(self):
        engine = DecisionEngine()
        engine.step(row(eye_closure_s=1.5))
        self.assertEqual(engine.tick(0.5)["status"], "OK")
        result = engine.tick(0.5001)
        self.assertEqual(result["status"], "STALE")
        self.assertEqual(result["driver_state"], "DROWSY")
        self.assertFalse(result["alert"])
        self.assertFalse(result["alert_event"])
        self.assertEqual(engine.tick(0.5001)["status"], "STALE")
        self.assertEqual(engine.step(row(0.6))["status"], "OK")

    def test_watchdog_with_no_input_is_stale(self):
        self.assertEqual(DecisionEngine().tick(0)["status"], "STALE")

    def test_tick_does_not_advance_confirmation(self):
        engine = DecisionEngine()
        engine.step(high(0))
        self.assertEqual(engine.tick(1)["status"], "STALE")
        self.assertEqual(engine.step(high(1.1))["driver_state"], "NORMAL")

    def test_reversed_duplicate_and_nonfinite_times_rejected(self):
        engine = DecisionEngine()
        engine.step(row(10))
        for t in (10, 9, -1, float("nan"), float("inf"), True):
            with self.subTest(t=t), self.assertRaises(ValueError):
                engine.step(row(t))
        self.assertLessEqual(engine.step(row(10.1))["smoothed_score"], 1)
        engine.tick(10.2)
        with self.assertRaises(ValueError):
            engine.step(row(10.15))
        with self.assertRaises(ValueError):
            engine.tick(10.1)

    def test_malformed_observations_rejected_without_mutating_state(self):
        cases = [{"perclos": 22}, {"perclos": float("nan")}, {"eye_closure_s": -1},
                 {"long_blinks": 1.5}, {"long_blinks": True}, {"yawn_count": -1},
                 {"face_valid": "0"}, {"eye_valid": 2}, {"validity_score": 2},
                 {"session_id": ""}]
        for changes in cases:
            engine = DecisionEngine()
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                engine.step(row(**changes))
            self.assertEqual(engine.step(row())["status"], "OK")
        with self.assertRaises(ValueError):
            DecisionEngine().step({"time_s": 0})
        with self.assertRaises(ValueError):
            DecisionEngine().step([])

    def test_session_change_resets_state_and_capture_clock(self):
        engine = DecisionEngine(session_id="driver-a")
        engine.step(row(100, eye_closure_s=1.5))
        result = engine.step(row(0, session_id="driver-b"))
        self.assertEqual(result["session_id"], "driver-b")
        self.assertEqual(result["driver_state"], "NORMAL")
        self.assertFalse(result["alert_event"])

    def test_explicit_reset_retains_session_name(self):
        engine = DecisionEngine(session_id="driver-a")
        engine.step(row(100, eye_closure_s=1.5))
        engine.reset()
        result = engine.step(row(0))
        self.assertEqual(result["session_id"], "driver-a")
        self.assertEqual(result["driver_state"], "NORMAL")

    def test_ground_truth_and_extra_diagnostics_are_ignored(self):
        a = DecisionEngine().step(row(gt_state="DROWSY", extra_diagnostic=123))
        b = DecisionEngine().step(row(gt_state="NORMAL"))
        self.assertEqual(a, b)

    def test_output_is_finite_json_and_quality_is_not_risk(self):
        result = DecisionEngine().step(row(validity_score=0.75))
        self.assertEqual(result["quality"], 0.75)
        self.assertEqual(result["score"], 0)
        json.dumps(result, allow_nan=False)
        self.assertEqual(result["schema_version"], "sg5.sg6.v2")

    def test_legacy_adapter_has_exact_fields_and_quality(self):
        engine = DecisionEngine(CONFIGURATIONS["threshold_a"])
        result = engine.step(row(perclos=0.15, validity_score=0.75))
        self.assertEqual(to_legacy_sg6(result), {"driver_state": "WARNING", "alert": True, "confidence": 0.75})
        with self.assertRaises(ValueError):
            to_legacy_sg6(engine.tick(1))
        with self.assertRaises(ValueError):
            to_legacy_sg6(DecisionEngine().step(row(face_valid=0)))

    def test_import_has_no_optional_or_hardware_dependencies(self):
        repo = str(Path(__file__).resolve().parents[3])
        code = ("import sys; sys.path.insert(0, " + repr(repo) + "); "
                "import module_5.midterm.engine; "
                "assert not {'numpy','matplotlib','cv2','winsound'} & set(sys.modules)")
        result = subprocess.run([sys.executable, "-I", "-B", "-c", code], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
