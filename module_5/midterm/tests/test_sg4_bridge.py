"""Integration checks against the actual SG4 package and its versioned goldens."""

import json
from pathlib import Path
import unittest

from module_5.midterm.sg4_bridge import (
    AvailabilityCue,
    SG4Bridge,
    iter_temporal,
    synchronized_frame,
)
from sg4.schema import validate_output


ROOT = Path(__file__).resolve().parents[3]
MOCKS = ROOT / "interfaces" / "mocks"


def load_jsonl(path):
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def transport(index=0, state="OPEN", mouth=False, *, valid=True, face=True):
    time_s = index / 30.0
    sg1 = {"frame_id": index, "timestamp_ms": round(time_s * 1000),
           "status": "OK" if face else "NO_FACE", "detection_confidence": None}
    sg2 = {"frame_id": index, "timestamp": time_s, "eye_state": state if valid else "UNKNOWN",
           "eye_valid": valid, "eye_closure_prob": None, "face_confidence": None,
           "ear": 0.10 if state == "CLOSED" else 0.30}
    sg3 = {"frame_id": index, "timestamp": time_s, "valid": True,
           "yawn_active": mouth, "mar": 0.8 if mouth else 0.2}
    return sg1, sg2, sg3


class GoldenStreamTests(unittest.TestCase):
    def test_all_five_native_mock_streams_match_actual_sg4_goldens(self):
        for name in ("alert", "drowsy", "face_lost", "noisy", "yawns_nods"):
            with self.subTest(scenario=name):
                records = load_jsonl(MOCKS / (name + ".jsonl"))
                golden = load_jsonl(MOCKS / "sg5_expected" / (name + ".jsonl"))
                produced = list(iter_temporal(records))
                self.assertEqual(produced, golden)
                for vector in produced:
                    self.assertEqual(validate_output(vector), [])

    def test_empty_input_is_real_sg4_invalid_snapshot(self):
        rows = list(iter_temporal([]))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["face_valid"], 0)
        self.assertEqual(rows[0]["validity_score"], 0)
        self.assertEqual(rows[0]["eye_closure_s"], 0)
        self.assertEqual(validate_output(rows[0]), [])

    def test_current_invalid_eye_annotation_is_not_historical_validity(self):
        bridge = SG4Bridge()
        for i in range(60):
            bridge.push(synchronized_frame(*transport(i)))
        for i in range(60, 64):
            vector = bridge.push(synchronized_frame(*transport(i, valid=False)))
            if vector is not None:
                self.assertEqual(vector["face_valid"], 1)
                self.assertFalse(vector["eye_valid"])
                self.assertGreater(vector["validity_score"], 0.9)
                self.assertEqual(vector["eye_closure_s"], 0)
                self.assertEqual(vector["quality_kind"], "observed_availability")
        self.assertFalse(bridge.snapshot()["eye_valid"])


class HardAvailabilityTests(unittest.TestCase):
    def test_native_sg2_cannot_silently_take_sg4s_invented_confidence_path(self):
        _, sg2, _ = transport()
        with self.assertRaisesRegex(ValueError, "synchronized_frame"):
            SG4Bridge().push(sg2)

    def test_bad_native_probability_units_are_rejected_before_sg4_processing(self):
        record = load_jsonl(MOCKS / "alert.jsonl")[0]
        record["eye"]["closure_prob"] = 95
        with self.assertRaisesRegex(ValueError, "invalid sg4.input.v1"):
            SG4Bridge().push(record)

    def test_missing_confidence_is_not_replaced_by_one(self):
        cue = synchronized_frame(*transport(state="CLOSED"))
        self.assertIsInstance(cue, AvailabilityCue)
        self.assertIsNone(cue.face_conf)
        self.assertIsNone(cue.eye_conf)
        self.assertIsNone(cue.mouth_conf)
        self.assertEqual(cue.closure_prob, 1.0)  # Hard state encoding, not a probability.
        bridge = SG4Bridge()
        row = bridge.push(cue)
        self.assertTrue(row["eye_valid"])
        self.assertEqual(row["availability_source"], "sg1_sg2_sg3_hard_state")

    def test_real_sg4_counts_one_long_closure(self):
        bridge = SG4Bridge()
        for i in range(90):
            state = "CLOSED" if 15 <= i < 75 else "OPEN"
            bridge.push(synchronized_frame(*transport(i, state=state)))
        row = bridge.snapshot()
        self.assertEqual(row["long_blinks"], 1)
        self.assertEqual(row["eye_closure_s"], 0)
        self.assertGreater(row["perclos"], 0.6)

    def test_face_loss_breaks_live_closure_even_when_eye_says_closed(self):
        bridge = SG4Bridge()
        for i in range(60):
            bridge.push(synchronized_frame(*transport(i, state="CLOSED")))
        self.assertGreater(bridge.snapshot()["eye_closure_s"], 1.5)
        bridge.push(synchronized_frame(*transport(60, state="CLOSED", face=False)))
        row = bridge.snapshot()
        self.assertEqual(row["face_valid"], 0)
        self.assertFalse(row["eye_valid"])
        self.assertEqual(row["eye_closure_s"], 0)

    def test_observed_low_face_confidence_is_still_respected(self):
        sg1, sg2, sg3 = transport(state="CLOSED")
        sg1["detection_confidence"] = 0.2
        row = SG4Bridge().push(synchronized_frame(sg1, sg2, sg3))
        self.assertEqual(row["face_valid"], 0)
        self.assertFalse(row["eye_valid"])

    def test_missing_mouth_is_unavailable_not_a_negative_measurement(self):
        sg1, sg2, _ = transport()
        cue = synchronized_frame(sg1, sg2)
        self.assertIsNone(cue.yawn_prob)
        bridge = SG4Bridge()
        bridge.push(cue)
        self.assertFalse(bridge.engine.last.mouth_valid)

    def test_mouth_frames_are_debounced_by_real_sg4_into_one_event(self):
        bridge = SG4Bridge()
        for i in range(120):
            bridge.push(synchronized_frame(*transport(i, mouth=15 <= i < 90)))
        self.assertEqual(bridge.snapshot()["yawn_count"], 1)

    def test_duplicate_and_backward_timestamps_use_original_sg4_rules(self):
        bridge = SG4Bridge()
        bridge.push(synchronized_frame(*transport(3)))
        self.assertIsNone(bridge.push(synchronized_frame(*transport(3))))
        self.assertIsNone(bridge.push(synchronized_frame(*transport(2))))
        self.assertEqual(bridge.engine.sync.stats.accepted, 1)
        self.assertEqual(bridge.engine.sync.stats.dropped_duplicate, 1)
        self.assertEqual(bridge.engine.sync.stats.dropped_out_of_order, 1)

    def test_unobserved_capture_gap_does_not_become_a_long_closure(self):
        bridge = SG4Bridge()
        bridge.push(synchronized_frame(*transport(0, state="CLOSED")))
        bridge.push(synchronized_frame(*transport(1, state="CLOSED")))
        bridge.push(synchronized_frame(*transport(90, state="CLOSED")))
        row = bridge.snapshot()
        self.assertFalse(row["eye_valid"])
        self.assertEqual(row["eye_closure_s"], 0)
        self.assertEqual(row["long_blinks"], 0)
        bridge.push(synchronized_frame(*transport(91, state="CLOSED")))
        self.assertTrue(bridge.snapshot()["eye_valid"])
        self.assertEqual(bridge.snapshot()["eye_closure_s"], 0)
        self.assertEqual(bridge.engine.sync.stats.gaps, 1)

    def test_mismatched_frame_ids_are_rejected_not_silently_joined(self):
        sg1, sg2, sg3 = transport()
        sg2["frame_id"] = 1
        with self.assertRaisesRegex(ValueError, "frame_id"):
            synchronized_frame(sg1, sg2, sg3)

    def test_mismatched_source_times_are_rejected(self):
        sg1, sg2, sg3 = transport()
        sg3["timestamp"] = 0.1
        with self.assertRaisesRegex(ValueError, "timestamp"):
            synchronized_frame(sg1, sg2, sg3)

    def test_unknown_is_neither_open_nor_closed(self):
        sg1, sg2, sg3 = transport(valid=False)
        cue = synchronized_frame(sg1, sg2, sg3)
        self.assertIsNone(cue.closure_prob)
        row = SG4Bridge().push(cue)
        self.assertFalse(row["eye_valid"])
        self.assertEqual(row["eye_closure_s"], 0)

    def test_inconsistent_sg2_validity_is_rejected(self):
        sg1, sg2, sg3 = transport(valid=False)
        sg2["eye_valid"] = True
        with self.assertRaisesRegex(ValueError, "disagree"):
            synchronized_frame(sg1, sg2, sg3)


if __name__ == "__main__":
    unittest.main()
