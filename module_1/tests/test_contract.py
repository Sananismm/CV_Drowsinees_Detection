import json
from pathlib import Path
import sys
import unittest

from jsonschema import Draft202012Validator


MODULE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = MODULE_ROOT.parent
sys.path.insert(0, str(MODULE_ROOT / "scripts"))

from sg1_contract import (  # noqa: E402
    ContractValidationError,
    EXPECTED_LANDMARK_COUNT,
    LANDMARK_TOPOLOGY,
    SCHEMA_VERSION,
    is_face_valid,
    to_sg2_input,
    to_sg3_input,
    validate_sg1_record,
)


def valid_ok_record():
    return {
        "schema_version": SCHEMA_VERSION,
        "frame_id": 4,
        "timestamp_ms": 160,
        "image_width": 640,
        "image_height": 360,
        "status": "OK",
        "face_bbox_xyxy": [100, 50, 300, 300],
        "landmarks_xy_normalized": [
            [0.5, 0.5] for _ in range(EXPECTED_LANDMARK_COUNT)
        ],
        "landmark_count": EXPECTED_LANDMARK_COUNT,
        "landmark_topology": LANDMARK_TOPOLOGY,
        "detection_confidence": None,
        "config_name": "test",
        "inference_ms": 1.25,
    }


def valid_no_face_record():
    record = valid_ok_record()
    record.update(
        {
            "status": "NO_FACE",
            "face_bbox_xyxy": None,
            "landmarks_xy_normalized": [],
            "landmark_count": 0,
        }
    )
    return record


class ContractTests(unittest.TestCase):
    def test_valid_ok_record(self):
        record = valid_ok_record()
        self.assertIs(validate_sg1_record(record), record)
        self.assertTrue(is_face_valid(record))

    def test_valid_no_face_record(self):
        record = valid_no_face_record()
        self.assertIs(validate_sg1_record(record), record)
        self.assertFalse(is_face_valid(record))

    def test_missing_field_fails(self):
        record = valid_ok_record()
        del record["schema_version"]
        with self.assertRaises(ContractValidationError):
            validate_sg1_record(record)

    def test_unknown_field_fails(self):
        record = valid_ok_record()
        record["unexpected"] = True
        with self.assertRaises(ContractValidationError):
            validate_sg1_record(record)

    def test_wrong_schema_version_fails(self):
        record = valid_ok_record()
        record["schema_version"] = "sg1.v2"
        with self.assertRaises(ContractValidationError):
            validate_sg1_record(record)

    def test_wrong_topology_fails(self):
        record = valid_ok_record()
        record["landmark_topology"] = "unknown"
        with self.assertRaises(ContractValidationError):
            validate_sg1_record(record)

    def test_truncated_landmarks_fail(self):
        record = valid_ok_record()
        record["landmarks_xy_normalized"] = record[
            "landmarks_xy_normalized"
        ][:-1]
        record["landmark_count"] -= 1
        with self.assertRaises(ContractValidationError):
            validate_sg1_record(record)

    def test_out_of_bounds_box_fails(self):
        record = valid_ok_record()
        record["face_bbox_xyxy"] = [0, 0, 641, 300]
        with self.assertRaises(ContractValidationError):
            validate_sg1_record(record)

    def test_non_finite_landmark_fails(self):
        record = valid_ok_record()
        record["landmarks_xy_normalized"][0][0] = float("nan")
        with self.assertRaises(ContractValidationError):
            validate_sg1_record(record)

    def test_sg2_adapter_preserves_identity_and_time(self):
        packet = to_sg2_input(valid_ok_record())
        self.assertEqual(packet["frame_id"], 4)
        self.assertEqual(packet["timestamp_sec"], 0.16)
        self.assertEqual(packet["image_width"], 640)
        self.assertEqual(packet["image_height"], 360)
        self.assertTrue(packet["eyes_valid"])
        self.assertEqual(len(packet["left_eye_points_xy_normalized"]), 6)
        self.assertEqual(len(packet["right_eye_points_xy_normalized"]), 6)

    def test_sg2_adapter_invalidates_no_face(self):
        packet = to_sg2_input(valid_no_face_record())
        self.assertFalse(packet["eyes_valid"])
        self.assertEqual(packet["left_eye_points_xy_normalized"], [])

    def test_sg3_adapter_requires_approved_indices(self):
        with self.assertRaises(ValueError):
            to_sg3_input(valid_ok_record(), [])

    def test_sg3_adapter_selects_requested_points(self):
        packet = to_sg3_input(valid_ok_record(), [13, 14, 61, 291])
        self.assertTrue(packet["mouth_valid"])
        self.assertEqual(packet["image_width"], 640)
        self.assertEqual(packet["image_height"], 360)
        self.assertEqual(len(packet["mouth_points_xy_normalized"]), 4)

    def test_tracked_fixtures_validate(self):
        examples = REPOSITORY_ROOT / "interfaces" / "examples"
        for name in ("sg1_v1_ok.json", "sg1_v1_no_face.json"):
            with self.subTest(name=name):
                record = json.loads((examples / name).read_text(encoding="utf-8"))
                validate_sg1_record(record)

    def test_schema_constants_match_machine_schema(self):
        schema_path = REPOSITORY_ROOT / "interfaces" / "sg1_v1.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.assertEqual(
            schema["properties"]["schema_version"]["const"], SCHEMA_VERSION
        )
        self.assertEqual(
            schema["properties"]["landmark_topology"]["const"],
            LANDMARK_TOPOLOGY,
        )

    def test_machine_schema_is_valid_and_accepts_fixtures(self):
        schema_path = REPOSITORY_ROOT / "interfaces" / "sg1_v1.schema.json"
        examples = REPOSITORY_ROOT / "interfaces" / "examples"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        for name in ("sg1_v1_ok.json", "sg1_v1_no_face.json"):
            with self.subTest(name=name):
                record = json.loads((examples / name).read_text(encoding="utf-8"))
                self.assertEqual(list(validator.iter_errors(record)), [])

    def test_machine_schema_rejects_unknown_field(self):
        schema_path = REPOSITORY_ROOT / "interfaces" / "sg1_v1.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        record = valid_no_face_record()
        record["unexpected"] = True
        errors = list(Draft202012Validator(schema).iter_errors(record))
        self.assertTrue(errors)

    def test_invalid_fixture_is_rejected(self):
        examples = REPOSITORY_ROOT / "interfaces" / "examples"
        record = json.loads(
            (examples / "sg1_v1_invalid_missing_schema.json").read_text(
                encoding="utf-8"
            )
        )
        with self.assertRaises(ContractValidationError):
            validate_sg1_record(record)


if __name__ == "__main__":
    unittest.main()
