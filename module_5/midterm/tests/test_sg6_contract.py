"""Run real SG4 -> SG5 -> SG6 consumer checks without hardware side effects."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

from embedded_6.sg5_handoff.consume import (
    DeliveryWatchdog, consume, hardware_request, validate_decision,
)
from module_5.midterm.engine import DecisionEngine, to_legacy_sg6
from module_5.midterm.sg4_bridge import SG4Bridge, synchronized_frame


ROOT = Path(__file__).resolve().parents[3]


def observation(time_s=0.0, closure=0.0, valid=True):
    return {"time_s": time_s, "face_valid": int(valid), "perclos": 0.05,
            "long_blinks": 0, "yawn_count": 0, "eye_closure_s": closure,
            "eye_valid": valid, "validity_score": 1.0 if valid else 0.0}


def sg6_legacy_validator():
    path = ROOT / "embedded_6" / "Integration" / "validate_interfaces.py"
    spec = importlib.util.spec_from_file_location("actual_sg6_validator", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate_module


class SG6ConsumerTests(unittest.TestCase):
    def test_normal_requests_no_warning_and_no_fault(self):
        decision = DecisionEngine().step(observation())
        request = hardware_request(decision)
        self.assertFalse(request["buzzer_requested"])
        self.assertFalse(request["visual_warning"])
        self.assertFalse(request["sensor_fault"])

    def test_drowsy_requests_sound_and_visual_only_while_usable(self):
        engine = DecisionEngine()
        decision = engine.step(observation(closure=1.6))
        request = hardware_request(decision)
        self.assertTrue(request["buzzer_requested"])
        self.assertTrue(request["visual_warning"])
        self.assertTrue(request["alert_event"])
        invalid = engine.step(observation(0.1, valid=False))
        self.assertEqual(invalid["driver_state"], "DROWSY")
        request = hardware_request(invalid)
        self.assertFalse(request["buzzer_requested"])
        self.assertTrue(request["sensor_fault"])
        self.assertFalse(request["alert_event"])

    def test_warning_is_visual_not_drowsiness_buzzer(self):
        engine = DecisionEngine()
        row = observation()
        row.update(perclos=0.2, yawn_count=2)
        for i in range(12):
            row["time_s"] = i / 10.0
            decision = engine.step(row)
        self.assertEqual(decision["driver_state"], "WARNING")
        request = hardware_request(decision)
        self.assertTrue(request["visual_warning"])
        self.assertFalse(request["buzzer_requested"])

    def test_stale_normal_is_a_fault_not_a_fresh_awake_result(self):
        engine = DecisionEngine()
        engine.step(observation())
        stale = engine.tick(0.6)
        self.assertEqual(stale["driver_state"], "NORMAL")
        self.assertTrue(hardware_request(stale)["sensor_fault"])
        with self.assertRaises(ValueError):
            to_legacy_sg6(stale)

    def test_adapter_matches_real_sg6_legacy_validator(self):
        validator = sg6_legacy_validator()
        for closure in (0, 1.6):
            decision = DecisionEngine().step(observation(closure=closure))
            legacy = to_legacy_sg6(decision)
            self.assertEqual(set(legacy), {"driver_state", "alert", "confidence"})
            self.assertEqual(validator("sg5", legacy), ([], []))
        invalid = DecisionEngine().step(observation(valid=False))
        with self.assertRaises(ValueError):
            to_legacy_sg6(invalid)

    def test_malformed_foreign_or_inconsistent_messages_raise(self):
        good = DecisionEngine().step(observation())
        variants = []
        for key, value in (("schema_version", "foreign.v1"), ("time_s", float("nan")),
                           ("score", 1.1), ("quality", True), ("alert", 1),
                           ("alert_level", True), ("status", "UNKNOWN"),
                           ("driver_state", "AWAKE"), ("alert_event", True)):
            bad = dict(good)
            bad[key] = value
            variants.append(bad)
        missing = dict(good)
        del missing["status"]
        variants.append(missing)
        extra = dict(good, confidence=0.99)
        variants.append(extra)
        for decision in variants:
            with self.subTest(decision=decision), self.assertRaises(ValueError):
                validate_decision(decision)

    def test_events_only_retains_status_changes_even_if_state_is_unchanged(self):
        engine = DecisionEngine()
        decisions = [engine.step(observation(0)), engine.step(observation(0.1)),
                     engine.step(observation(0.2, valid=False)),
                     engine.step(observation(0.3, valid=False))]
        lines = [json.dumps(row) for row in decisions]
        requests = list(consume(lines, events_only=True))
        self.assertEqual(len(requests), 2)
        self.assertEqual([r["status"] for r in requests], ["OK", "INSUFFICIENT_EVIDENCE"])

    def test_backward_same_session_replay_is_rejected(self):
        first = DecisionEngine().step(observation(1.0))
        second = dict(first, time_s=0.5)
        with self.assertRaisesRegex(ValueError, "timestamps"):
            list(consume([json.dumps(first), json.dumps(second)]))

    def test_arrival_watchdog_uses_separate_clock_and_does_not_fabricate_capture_time(self):
        watchdog = DeliveryWatchdog(timeout_s=1.0)
        self.assertTrue(watchdog.poll(now_s=100)["sensor_fault"])
        self.assertIsNone(watchdog.poll(now_s=100)["time_s"])
        decision = DecisionEngine().step(observation(2.0))
        watchdog.observe(decision, now_s=100.0)
        self.assertIsNone(watchdog.poll(now_s=100.9))
        fault = watchdog.poll(now_s=101.1)
        self.assertTrue(fault["sensor_fault"])
        self.assertEqual(fault["status"], "STALE")
        self.assertEqual(fault["time_s"], 2.0)
        with self.assertRaises(ValueError):
            watchdog.poll(now_s=99.0)

    def test_real_sg4_mock_streams_flow_into_status_aware_sg6_requests(self):
        for scenario in ("alert", "drowsy", "face_lost", "noisy", "yawns_nods"):
            with self.subTest(scenario=scenario):
                engine, bridge = DecisionEngine(session_id=scenario), SG4Bridge()
                count = 0
                with (ROOT / "interfaces" / "mocks" / (scenario + ".jsonl")).open() as source:
                    for line in source:
                        vector = bridge.push(json.loads(line))
                        if vector is not None:
                            decision = engine.step(vector)
                            hardware_request(decision)
                            count += 1
                self.assertGreater(count, 100)

    def test_real_sg4_hard_state_bridge_to_sg6_detects_sustained_closure(self):
        bridge, engine = SG4Bridge(), DecisionEngine(session_id="hard-state-test")
        requests = []
        for i in range(90):
            t = i / 30.0
            sg1 = {"frame_id": i, "timestamp_ms": round(t * 1000),
                   "status": "OK", "detection_confidence": None}
            sg2 = {"frame_id": i, "timestamp": t, "eye_state": "CLOSED",
                   "eye_valid": True, "eye_closure_prob": None,
                   "face_confidence": None, "ear": 0.10}
            vector = bridge.push(synchronized_frame(sg1, sg2))
            if vector is not None:
                requests.append(hardware_request(engine.step(vector)))
        self.assertTrue(any(r["buzzer_requested"] for r in requests))
        self.assertFalse(any(r["sensor_fault"] for r in requests))

    def test_stdin_cli_emits_requests_and_rejects_foreign_json(self):
        command = [sys.executable, str(ROOT / "embedded_6" / "sg5_handoff" / "consume.py"),
                   "--events-only"]
        decision = DecisionEngine().step(observation(closure=1.6))
        result = subprocess.run(command, input=json.dumps(decision) + "\n",
                                text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["buzzer_requested"])
        result = subprocess.run(command, input='{"driver_state":"NORMAL"}\n',
                                text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 2)
        self.assertIn("exact 14-field", result.stderr)

    def test_empty_cli_input_emits_a_fault_instead_of_silent_normal(self):
        command = [sys.executable, str(ROOT / "embedded_6" / "sg5_handoff" / "consume.py")]
        result = subprocess.run(command, input="", text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        request = json.loads(result.stdout)
        self.assertTrue(request["sensor_fault"])
        self.assertIsNone(request["driver_state"])


if __name__ == "__main__":
    unittest.main()
