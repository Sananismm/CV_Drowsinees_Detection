import json
import math
import sys
from pathlib import Path

MOCK_DIR = Path(__file__).resolve().parent.parent / "mock_data"

SCHEMAS = {
    "sg1": {
        "timestamp": "number",
        "frame_id": "integer",
        "face_detected": "boolean",
        "face_bbox": "list",
        "face_confidence": "probability",
        "left_eye_landmarks": "list",
        "right_eye_landmarks": "list",
        "mouth_landmarks": "list",
    },
    "sg2": {
        "timestamp": "number",
        "frame_id": "integer",
        "eyes_closed": "boolean",
        "eye_metric": "number",
        "blink_detected": "boolean",
    },
    "sg3": {
        "timestamp": "number",
        "frame_id": "integer",
        "yawn_detected": "boolean",
        "mouth_metric": "number",
        "confidence": "probability",
    },
    "sg4": {
        "timestamp": "number",
        "eye_closure_duration": "number",
        "blink_frequency": "number",
        "yawn_duration": "number",
        "eye_warning": "boolean",
        "yawn_warning": "boolean",
    },
    "sg5": {
        "driver_state": "state",
        "alert": "boolean",
        "confidence": "probability",
    },
}


def is_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def valid_type(value, expected):
    if expected == "number":
        return is_number(value)

    if expected == "integer":
        return type(value) is int and value >= 0

    if expected == "boolean":
        return type(value) is bool

    if expected == "list":
        return isinstance(value, list)

    if expected == "probability":
        return is_number(value) and 0 <= value <= 1

    if expected == "state":
        return value in ("NORMAL", "WARNING", "DROWSY")

    return False


def validate_module(name, data):
    errors = []
    warnings = []

    for field, expected_type in SCHEMAS[name].items():
        if field not in data:
            errors.append(f"Missing field: {field}")
            continue

        if not valid_type(data[field], expected_type):
            errors.append(
                f"Invalid {field}: expected {expected_type}, "
                f"received {data[field]!r}"
            )

    if name == "sg1" and data.get("face_detected") is True:
        bbox = data.get("face_bbox")

        if (
            not isinstance(bbox, list)
            or len(bbox) != 4
            or not all(is_number(x) for x in bbox)
        ):
            errors.append("face_bbox must contain four finite numbers")

        elif bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
            errors.append("face_bbox coordinates are invalid")

        for field in (
            "left_eye_landmarks",
            "right_eye_landmarks",
            "mouth_landmarks",
        ):
            if data.get(field) == []:
                warnings.append(
                    f"{field} is empty despite face_detected=True"
                )

    if name == "sg4":
        for field in (
            "eye_closure_duration",
            "blink_frequency",
            "yawn_duration",
        ):
            if field in data and is_number(data[field]) and data[field] < 0:
                errors.append(f"{field} cannot be negative")

    return errors, warnings


def main():
    print("==========================================")
    print("SG6 MOCK INTERFACE VALIDATION")
    print("==========================================")

    failed = False
    loaded = {}

    for name in SCHEMAS:
        path = MOCK_DIR / f"{name}_output.json"

        try:
            with path.open(encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                raise ValueError("Expected a JSON object")

        except (OSError, ValueError) as exc:
            print(f"[FAIL] {name.upper()}: {exc}")
            failed = True
            continue

        loaded[name] = data
        errors, warnings = validate_module(name, data)

        if errors:
            failed = True
            print(f"[FAIL] {name.upper()}")
            for error in errors:
                print(f"  ERROR: {error}")
        else:
            print(f"[PASS] {name.upper()} mock structure")

        for warning in warnings:
            print(f"  WARNING: {warning}")

    print("\n=== CROSS-MODULE CONSISTENCY ===")

    frame_ids = {
        name: loaded[name]["frame_id"]
        for name in ("sg1", "sg2", "sg3")
        if name in loaded
        and type(loaded[name].get("frame_id")) is int
    }

    if len(set(frame_ids.values())) > 1:
        print(f"[FAIL] Frame IDs disagree: {frame_ids}")
        failed = True
    elif len(frame_ids) == 3:
        print("[PASS] SG1-SG3 frame IDs match")
    else:
        print("[WARN] Insufficient frame IDs for comparison")

    timestamps = {
        name: loaded[name]["timestamp"]
        for name in ("sg1", "sg2", "sg3")
        if name in loaded and is_number(loaded[name].get("timestamp"))
    }

    if len(timestamps) == 3:
        difference = max(timestamps.values()) - min(timestamps.values())

        if difference > 0.05:
            print(f"[FAIL] Timestamp mismatch: {timestamps}")
            failed = True
        else:
            print("[PASS] SG1-SG3 timestamps are aligned")
    else:
        print("[WARN] Insufficient timestamps for comparison")

    print("\n=== INTEGRATION LIMITATIONS ===")
    print("- Validates the existing SG6 mock format only.")
    print("- Does not execute real SG1-SG5 implementations.")
    print("- Does not prove compatibility with subgroup V1 contracts.")
    print("- Does not demonstrate end-to-end drowsiness detection.")

    print("\n==========================================")

    if failed:
        print("RESULT: FAIL")
        return 1

    print("RESULT: PASS - MOCK STRUCTURE ONLY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
