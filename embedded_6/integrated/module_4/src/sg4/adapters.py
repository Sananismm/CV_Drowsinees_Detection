"""Upstream field mapping. THE ONLY FILE WHERE UPSTREAM FIELD NAMES APPEAR.

When SG-1/SG-2/SG-3 change or freeze their outputs, only this file changes.

Supported inputs:
  * sg4.input.v1 records (our proposed contract, used by mocks and the stand-in extractor)
  * SG-2 eye/blink records as shared by SG-2 (draft, Oct 2026):
      frame_id, timestamp (s), eye_state OPEN|CLOSED|UNKNOWN, eye_valid,
      closure_duration_sec, closure_event, is_blink, ear, left_ear, right_ear,
      quality, eye_closure_prob (currently null: CNN output is not calibrated)
    These carry only the eye cue. Face/mouth/head come from SG-1/SG-3 via
    merge_upstream(); until those are wired, the face is inferred from eye_valid.
"""
from typing import Any, Dict, Optional

from .schema import INPUT_SCHEMA_ID, CueRecord

_STATE_TO_PROB = {"closed": 1.0, "open": 0.0}


def _num(x: Any) -> Optional[float]:
    return None if x is None else float(x)


def _closure_prob(prob: Any, state: Optional[str]) -> Optional[float]:
    """Use the probability when given; otherwise map a hard open/closed state to 0/1."""
    if prob is not None:
        return float(prob)
    return _STATE_TO_PROB.get((state or "unknown").lower())


def from_v1(rec: Dict[str, Any]) -> CueRecord:
    """sg4.input.v1 dict -> CueRecord."""
    face = rec.get("face") or {}
    eye = rec.get("eye") or {}
    mouth = rec.get("mouth") or {}
    head = rec.get("head") or {}
    state = (eye.get("state") or "unknown").lower()
    return CueRecord(
        frame_id=int(rec["frame_id"]),
        t_ms=int(rec["timestamp_ms"]),
        face_present=bool(face.get("present", False)),
        face_conf=_num(face.get("confidence")),
        closure_prob=_closure_prob(eye.get("closure_prob"), state) if eye else None,
        eye_state=state,
        eye_conf=_num(eye.get("confidence")),
        ear=_num(eye.get("ear")),
        yawn_prob=_num(mouth.get("yawn_prob")),
        mouth_conf=_num(mouth.get("confidence")),
        pitch_deg=_num(head.get("pitch_deg")),
        head_conf=_num(head.get("confidence")),
    )


def sg2_eye_block(sg2: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """SG-2 eye record -> v1 `eye` block (None when SG-2 marks the eye invalid)."""
    if not sg2.get("eye_valid", False):
        return None
    state = str(sg2.get("eye_state") or "UNKNOWN").lower()
    prob = _closure_prob(sg2.get("eye_closure_prob"), state)
    if prob is None:
        return None
    return {"closure_prob": prob, "state": state, "ear": sg2.get("ear"), "confidence": 1.0}


def merge_upstream(sg2: Dict[str, Any],
                   sg1_face: Optional[Dict[str, Any]] = None,
                   sg3: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Build one sg4.input.v1 record from per-frame SG-1 / SG-2 / SG-3 outputs.

    SG-2's timestamp is in seconds; v1 uses integer milliseconds.
    sg1_face: {"present": bool, "confidence": float} once SG-1 provides it.
    sg3: {"yawn_prob", "mar", "pitch_deg", "yaw_deg", "roll_deg", "confidence"} (V1-PROPOSED).
    """
    eye = sg2_eye_block(sg2)
    if sg1_face is not None:
        face = {"present": bool(sg1_face.get("present")), "confidence": sg1_face.get("confidence")}
    else:
        # Interim: no SG-1 face record yet. A valid eye implies a detected face.
        face = {"present": eye is not None, "confidence": 1.0 if eye is not None else 0.0}
    mouth = head = None
    if sg3 is not None:
        conf = sg3.get("confidence")
        if sg3.get("yawn_prob") is not None:
            mouth = {"yawn_prob": sg3["yawn_prob"], "mar": sg3.get("mar"), "confidence": conf}
        if sg3.get("pitch_deg") is not None:
            head = {"pitch_deg": sg3["pitch_deg"], "yaw_deg": sg3.get("yaw_deg"),
                    "roll_deg": sg3.get("roll_deg"), "confidence": conf}
    return {
        "schema": INPUT_SCHEMA_ID,
        "frame_id": int(sg2["frame_id"]),
        "timestamp_ms": int(round(float(sg2["timestamp"]) * 1000.0)),
        "face": face, "eye": eye, "mouth": mouth, "head": head,
    }


def to_cue(rec: Dict[str, Any]) -> CueRecord:
    """Any supported upstream record -> CueRecord (format detected from its fields)."""
    if rec.get("schema") == INPUT_SCHEMA_ID or "timestamp_ms" in rec:
        return from_v1(rec)
    if "eye_state" in rec:
        return from_v1(merge_upstream(rec))
    raise ValueError("Unrecognised upstream record (keys: %s)" % sorted(rec)[:8])
