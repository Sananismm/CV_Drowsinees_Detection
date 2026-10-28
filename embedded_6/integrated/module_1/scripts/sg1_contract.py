"""Validation and adapter helpers for the SG-1 V1 output contract."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from numbers import Real


SCHEMA_VERSION = "sg1.v1"
LANDMARK_TOPOLOGY = "mediapipe_face_landmarker_478"
EXPECTED_LANDMARK_COUNT = 478

LEFT_EYE_INDICES = (33, 160, 158, 133, 153, 144)
RIGHT_EYE_INDICES = (362, 385, 387, 263, 373, 380)

REQUIRED_FIELDS = {
    "schema_version",
    "frame_id",
    "timestamp_ms",
    "image_width",
    "image_height",
    "status",
    "face_bbox_xyxy",
    "landmarks_xy_normalized",
    "landmark_count",
    "landmark_topology",
    "detection_confidence",
    "config_name",
    "inference_ms",
}


class ContractValidationError(ValueError):
    """Raised when a record does not satisfy the SG-1 V1 contract."""

    def __init__(self, errors: Sequence[str]):
        self.errors = tuple(errors)
        super().__init__("; ".join(self.errors))


def _is_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_finite_number(value: object) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(value)


def _validate_dimensions(record: Mapping[str, object], errors: list[str]) -> None:
    for field in ("frame_id", "timestamp_ms"):
        value = record.get(field)
        if not _is_integer(value) or value < 0:
            errors.append(f"{field} must be a non-negative integer")

    for field in ("image_width", "image_height"):
        value = record.get(field)
        if not _is_integer(value) or value < 1:
            errors.append(f"{field} must be a positive integer")


def _validate_landmarks(
    landmarks: object,
    expected_count: int,
    required_indices: Sequence[int],
    errors: list[str],
) -> None:
    if not isinstance(landmarks, list):
        errors.append("landmarks_xy_normalized must be a list")
        return

    if len(landmarks) != expected_count:
        errors.append(
            "landmark_count must match the number of normalized landmarks"
        )

    for point_index, point in enumerate(landmarks):
        if not isinstance(point, list) or len(point) != 2:
            errors.append(f"landmark {point_index} must be an [x,y] list")
            continue
        if not all(_is_finite_number(value) for value in point):
            errors.append(f"landmark {point_index} values must be finite numbers")

    for index in required_indices:
        if not _is_integer(index) or index < 0:
            errors.append("required landmark indices must be non-negative integers")
        elif index >= len(landmarks):
            errors.append(f"required landmark index {index} is missing")


def _validate_bbox(record: Mapping[str, object], errors: list[str]) -> None:
    box = record.get("face_bbox_xyxy")
    width = record.get("image_width")
    height = record.get("image_height")
    if not isinstance(box, list) or len(box) != 4:
        errors.append("face_bbox_xyxy must be a four-item list for status OK")
        return
    if not all(_is_integer(value) for value in box):
        errors.append("face_bbox_xyxy values must be integers")
        return
    if not _is_integer(width) or not _is_integer(height):
        return
    x1, y1, x2, y2 = box
    if not (0 <= x1 < x2 <= width):
        errors.append("face_bbox_xyxy x coordinates are outside the image")
    if not (0 <= y1 < y2 <= height):
        errors.append("face_bbox_xyxy y coordinates are outside the image")


def validate_sg1_record(
    record: Mapping[str, object], required_indices: Sequence[int] = ()
) -> Mapping[str, object]:
    """Validate one SG-1 output record or raise ContractValidationError."""

    if not isinstance(record, Mapping):
        raise ContractValidationError(("record must be a mapping",))

    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(record))
    if missing:
        errors.append(f"missing required fields: {', '.join(missing)}")
    unexpected = sorted(set(record) - REQUIRED_FIELDS)
    if unexpected:
        errors.append(f"unexpected fields: {', '.join(unexpected)}")

    if record.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must equal {SCHEMA_VERSION}")
    if record.get("landmark_topology") != LANDMARK_TOPOLOGY:
        errors.append(f"landmark_topology must equal {LANDMARK_TOPOLOGY}")

    _validate_dimensions(record, errors)

    status = record.get("status")
    if status not in {"OK", "NO_FACE"}:
        errors.append("status must be OK or NO_FACE")

    count = record.get("landmark_count")
    if not _is_integer(count) or count < 0:
        errors.append("landmark_count must be a non-negative integer")
        count = -1

    landmarks = record.get("landmarks_xy_normalized")
    if status == "OK":
        if count != EXPECTED_LANDMARK_COUNT:
            errors.append(
                f"status OK requires {EXPECTED_LANDMARK_COUNT} landmarks"
            )
        _validate_landmarks(landmarks, count, required_indices, errors)
        _validate_bbox(record, errors)
    elif status == "NO_FACE":
        if record.get("face_bbox_xyxy") is not None:
            errors.append("status NO_FACE requires a null face_bbox_xyxy")
        if landmarks != []:
            errors.append("status NO_FACE requires an empty landmark list")
        if count != 0:
            errors.append("status NO_FACE requires landmark_count 0")

    confidence = record.get("detection_confidence")
    if confidence is not None and (
        not _is_finite_number(confidence) or not 0 <= confidence <= 1
    ):
        errors.append("detection_confidence must be null or between 0 and 1")

    config_name = record.get("config_name")
    if not isinstance(config_name, str) or not config_name.strip():
        errors.append("config_name must be a non-empty string")

    inference_ms = record.get("inference_ms")
    if not _is_finite_number(inference_ms) or inference_ms < 0:
        errors.append("inference_ms must be a non-negative finite number")

    if errors:
        raise ContractValidationError(errors)
    return record


def is_face_valid(
    record: Mapping[str, object], required_indices: Sequence[int] = ()
) -> bool:
    """Return True only for a valid SG-1 face record."""

    try:
        validate_sg1_record(record, required_indices)
    except ContractValidationError:
        return False
    return record["status"] == "OK"


def _selected_points(
    record: Mapping[str, object], indices: Sequence[int]
) -> list[list[float]]:
    if not is_face_valid(record, indices):
        return []
    landmarks = record["landmarks_xy_normalized"]
    return [landmarks[index] for index in indices]


def to_sg2_input(record: Mapping[str, object]) -> dict[str, object]:
    """Adapt one SG-1 record to the current SG-2 eye-landmark input."""

    required = LEFT_EYE_INDICES + RIGHT_EYE_INDICES
    valid = is_face_valid(record, required)
    return {
        "frame_id": record.get("frame_id"),
        "timestamp_sec": (
            round(record["timestamp_ms"] / 1000.0, 3)
            if _is_integer(record.get("timestamp_ms"))
            else None
        ),
        "image_width": record.get("image_width"),
        "image_height": record.get("image_height"),
        "face_valid": valid,
        "eyes_valid": valid,
        "landmark_format": LANDMARK_TOPOLOGY,
        "coordinate_system": "normalized_xy",
        "left_eye_landmark_indices": list(LEFT_EYE_INDICES),
        "right_eye_landmark_indices": list(RIGHT_EYE_INDICES),
        "left_eye_points_xy_normalized": (
            _selected_points(record, LEFT_EYE_INDICES) if valid else []
        ),
        "right_eye_points_xy_normalized": (
            _selected_points(record, RIGHT_EYE_INDICES) if valid else []
        ),
    }


def to_sg3_input(
    record: Mapping[str, object], mouth_indices: Sequence[int]
) -> dict[str, object]:
    """Adapt one SG-1 record using mouth indices approved by SG-3."""

    if not mouth_indices:
        raise ValueError("SG-3 must provide at least one agreed mouth index")
    valid = is_face_valid(record, mouth_indices)
    return {
        "frame_id": record.get("frame_id"),
        "timestamp_sec": (
            round(record["timestamp_ms"] / 1000.0, 3)
            if _is_integer(record.get("timestamp_ms"))
            else None
        ),
        "image_width": record.get("image_width"),
        "image_height": record.get("image_height"),
        "face_valid": valid,
        "mouth_valid": valid,
        "landmark_format": LANDMARK_TOPOLOGY,
        "coordinate_system": "normalized_xy",
        "mouth_landmark_indices": list(mouth_indices),
        "mouth_points_xy_normalized": (
            _selected_points(record, mouth_indices) if valid else []
        ),
    }
