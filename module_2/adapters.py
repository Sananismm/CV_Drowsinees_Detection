"""SG-1 array inputs and an honest SG-4 bridge.
Contracts: SG-1 f946306, SG-4 059705b (see README links).
"""
import math
from numbers import Real
import numpy as np
from .eye_analysis import LEFT_EYE, RIGHT_EYE, create_output_packet

TOPOLOGY = "mediapipe_face_landmarker_478"


def finite(value):
    return isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(value)


def integer(value, minimum=0):
    return isinstance(value, int) and not isinstance(value, bool) and value >= minimum


def point_array(points, count):
    """Reject numeric strings/booleans just as the upstream contract does."""
    raw = np.asarray(points, dtype=object)
    if raw.shape != (count, 2) or not all(finite(v) for v in raw.flat):
        raise ValueError("expected finite numeric xy pairs")
    return np.asarray(points, dtype=float)


def eye_packet(record):
    """Accept SG-1 full output (current V1 or main's legacy) or its eye adapter.

    Invalid geometry becomes an invalid eye packet. Bad identity/time raises;
    inventing those would destroy synchronization.
    """
    if not isinstance(record, dict) or not integer(record.get("frame_id")):
        raise ValueError("frame_id must be a nonnegative integer")
    if "timestamp_ms" in record:
        if not integer(record["timestamp_ms"]):
            raise ValueError("timestamp_ms must be a nonnegative integer")
        timestamp = record["timestamp_ms"] / 1000.0
    else:
        timestamp = record.get("timestamp_sec")
    if not finite(timestamp) or timestamp < 0:
        raise ValueError("timestamp_sec must be finite and nonnegative")
    packet = dict(record, timestamp_sec=timestamp)
    reason = None
    if not all(integer(record.get(k), 1) for k in ("image_width", "image_height")):
        reason = "invalid_image_dimensions"
    if "landmarks_xy_normalized" in record:
        landmarks = record["landmarks_xy_normalized"]
        # main predates V1: absence of version/topology is accepted explicitly.
        if record.get("schema_version", "sg1.v1") != "sg1.v1" or record.get("landmark_topology", TOPOLOGY) != TOPOLOGY:
            reason = "unsupported_landmark_schema"
        try:
            points = point_array(landmarks, 478)
            if record.get("status") != "OK" or not integer(record.get("landmark_count")) or record.get("landmark_count") != 478 or points.shape != (478, 2) or not np.isfinite(points).all():
                reason = "invalid_face_or_landmarks"
            box = record.get("face_bbox_xyxy")
            if not isinstance(box, list) or len(box) != 4 or not all(integer(x) for x in box):
                reason = reason or "invalid_face_box"
            elif not (0 <= box[0] < box[2] <= record.get("image_width", 0) and 0 <= box[1] < box[3] <= record.get("image_height", 0)):
                reason = reason or "invalid_face_box"
            if reason is None:
                packet["left_eye_points_xy_normalized"] = points[LEFT_EYE].tolist()
                packet["right_eye_points_xy_normalized"] = points[RIGHT_EYE].tolist()
        except (TypeError, ValueError, IndexError):
            reason = "invalid_landmark_array"
    else:
        if record.get("face_valid") is not True or record.get("eyes_valid") is not True:
            reason = "invalid_face_or_eyes"
        if record.get("landmark_format") != TOPOLOGY or record.get("coordinate_system") != "normalized_xy":
            reason = "unsupported_landmark_schema"
        for side, indices in (("left", LEFT_EYE), ("right", RIGHT_EYE)):
            if record.get(side + "_eye_landmark_indices") != indices:
                reason = "incorrect_eye_order"
    for side in ("left", "right"):
        try:
            points = point_array(packet.get(side + "_eye_points_xy_normalized"), 6)
            if points.shape != (6, 2) or not np.isfinite(points).all():
                reason = reason or "invalid_eye_points"
        except (TypeError, ValueError):
            reason = reason or "invalid_eye_points"
    confidence = record.get("detection_confidence")
    if confidence is not None and (not finite(confidence) or not 0 <= confidence <= 1):
        reason = "invalid_detection_confidence"
    packet.update(face_valid=reason is None, eyes_valid=reason is None,
                  invalid_reason=reason, detection_confidence=confidence)
    return packet


def process_sg1_eye_packet(record, threshold=0.15):
    if not finite(threshold) or threshold <= 0:
        raise ValueError("threshold must be positive and finite")
    packet = eye_packet(record)
    left = right = average = None
    if packet["eyes_valid"]:
        # Reuse the preserved EAR implementation with local six-point arrays.
        from .eye_analysis import calculate_ear
        left = calculate_ear(packet["left_eye_points_xy_normalized"], range(6), packet["image_width"], packet["image_height"])
        right = calculate_ear(packet["right_eye_points_xy_normalized"], range(6), packet["image_width"], packet["image_height"])
        if left is not None and right is not None:
            average = (left + right) / 2
    out = create_output_packet(packet["frame_id"], packet["timestamp_sec"], average,
                               valid=average is not None, threshold=threshold)
    # Preserve full precision for downstream threshold/evaluation consistency.
    out.update(ear=None if average is None else float(average),
               left_ear=None if left is None else float(left),
               right_ear=None if right is None else float(right),
               invalid_reason=packet["invalid_reason"] or ("degenerate_eye" if average is None else None),
               face_confidence=packet["detection_confidence"])
    return out


def to_sg4(output):
    """Semantic cue; null means unavailable, never a fabricated probability."""
    cue = dict(schema_version="sg2.sg4.v2",timestamp=output["timestamp_sec"],frame_id=output["frame_id"],
                eye_valid=output["valid"],eye_state=output["eye_state"],
                eye_closure_prob=None,face_confidence=output.get("face_confidence"),
                is_blink=bool(output.get("closure_event") and output["closure_event"].get("is_blink_candidate")),
                closure_event=output.get("closure_event"),closure_duration_sec=output.get("closure_duration_sec"),
                method=output.get("method","EAR"),ear=output.get("ear"),left_ear=output.get("left_ear"),
                right_ear=output.get("right_ear"),ear_eye_state=output.get("ear_eye_state",output["eye_state"]),
                cnn=output.get("cnn"),invalid_reason=output.get("invalid_reason"),quality=output.get("quality"))

    validate_sg4_cue(cue)
    return cue


def validate_sg4_cue(cue):
    """Validate hard-state semantics; never substitute a probability for state."""
    required={"schema_version","timestamp","frame_id","eye_valid","eye_state","eye_closure_prob",
              "face_confidence","is_blink","closure_event","closure_duration_sec","method","ear",
              "left_ear","right_ear","ear_eye_state","cnn","invalid_reason","quality"}
    if not isinstance(cue,dict) or set(cue)!=required:raise ValueError("incorrect SG-4 cue fields")
    if cue["schema_version"]!="sg2.sg4.v2" or not integer(cue["frame_id"]) or not finite(cue["timestamp"]) or cue["timestamp"]<0:
        raise ValueError("invalid SG-4 schema/identity/time")
    if not isinstance(cue["eye_valid"],bool) or cue["eye_state"] not in ("OPEN","CLOSED","UNKNOWN") or cue["eye_valid"]!=(cue["eye_state"]!="UNKNOWN"):
        raise ValueError("inconsistent SG-4 eye validity/state")
    if cue["eye_closure_prob"] is not None:raise ValueError("no calibrated closure probability is provided")
    confidence=cue["face_confidence"]
    if confidence is not None and (not finite(confidence) or not 0<=confidence<=1):raise ValueError("invalid observed confidence")
    for field in ("ear","left_ear","right_ear","closure_duration_sec"):
        v=cue[field]
        if v is not None and (not finite(v) or v<0):raise ValueError("invalid "+field)
    if not isinstance(cue["is_blink"],bool):raise ValueError("blink candidate must be bool")
    event=cue["closure_event"]
    if event is not None:
        if not isinstance(event,dict) or not all(finite(event.get(k)) for k in ("start_sec","end_sec","duration_sec")):
            raise ValueError("invalid closure event")
        if event["start_sec"]<0 or event["end_sec"]<event["start_sec"] or event["end_sec"]>cue["timestamp"] or abs(event["duration_sec"]-(event["end_sec"]-event["start_sec"]))>1e-8:
            raise ValueError("invalid closure event interval")
    if cue["is_blink"]!=bool(event and event.get("is_blink_candidate")):
        raise ValueError("blink flag must match exactly one emitted event")
    return cue



class SG4Bridge:
    """Append SG-4's *internal* processed cue, bypassing its numeric-only gate.

    Retains the original analyzer's window/vector logic. This is selected-method
    closure fraction, NOT a validated eyelid-occlusion P80 measurement.
    SG-3 fields must be supplied explicitly; unavailable cues raise.
    """
    def __init__(self, analyzer):
        if not hasattr(analyzer, "buffer"):
            raise TypeError("expected SG-4 TemporalAnalyzer with buffer")
        self.analyzer = analyzer

    def process_frame(self, cue, *, yawn_prob, head_nod_event):
        if not finite(yawn_prob) or not 0 <= yawn_prob <= 1 or not isinstance(head_nod_event, bool):
            raise ValueError("provide actual SG-3 cues (or explicitly documented demo values)")
        confidence = cue["face_confidence"]
        valid = cue["eye_valid"] is True and cue["eye_state"] in ("OPEN", "CLOSED")
        if confidence is not None:
            valid = valid and finite(confidence) and confidence >= 0.5
        self.analyzer.buffer.append(dict(timestamp=cue["timestamp"], is_valid=valid,
            closed=valid and cue["eye_state"] == "CLOSED", is_blink=valid and cue["is_blink"],
            yawn=valid and yawn_prob >= 0.7, head_nod=valid and head_nod_event))
