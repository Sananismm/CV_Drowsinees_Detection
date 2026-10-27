"""Run the team's real SG4 v1.1 engine without inventing confidence values.

Native ``sg4.input.v1`` records follow SG4's unchanged confidence gates and
produce byte-for-byte-equivalent values to its committed golden streams.

Live SG1/SG2/SG3 transport has a separate, explicit availability path: SG2
provides a hard OPEN/CLOSED state, not a calibrated closure probability, and
SG3 provides a valid mouth-open flag, not a yawn probability. Their original
confidence values remain None. A narrow Synchronizer subclass changes only
the availability gate; the actual SG4 clock handling, buffers, aggregation,
event debounce and output writer are retained. This adapter needs upstream
owner acceptance; it is not a claim of calibrated probabilities or P80 truth.
"""

from dataclasses import dataclass, replace
import math
from pathlib import Path
import sys
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
SG4_SOURCE = REPO_ROOT / "module_4" / "src"
if str(SG4_SOURCE) not in sys.path:
    sys.path.insert(0, str(SG4_SOURCE))

from sg4.engine import TemporalEngine  # noqa: E402
from sg4.schema import CueRecord, INPUT_SCHEMA_ID, validate_input  # noqa: E402
from sg4.sync import Synchronizer  # noqa: E402


@dataclass
class AvailabilityCue(CueRecord):
    """Synchronized hard-state transport, not a replacement SG4 wire schema."""

    eye_available: bool = False
    mouth_available: bool = False
    head_available: bool = False


class AvailabilitySynchronizer(Synchronizer):
    """Retain SG4 timing while honoring genuine hard-state availability flags."""

    def process(self, cue):
        previous_t = self.last_t
        validated = super().process(cue)
        if validated is None or not isinstance(cue, AvailabilityCue):
            return validated
        face_valid = bool(cue.face_present) and (
            cue.face_conf is None or cue.face_conf >= self.cfg.face_conf_min
        )
        eye_valid = face_valid and cue.eye_available and cue.closure_prob is not None
        mouth_valid = face_valid and cue.mouth_available and cue.yawn_prob is not None
        head_valid = face_valid and cue.head_available and cue.pitch_deg is not None
        # SG4 caps integrated dt but its event trackers use absolute time.
        # Censor the first post-gap hard-state observation so an unobserved
        # interval cannot become a continuous eye closure or yawn segment.
        # Native SG4 records retain upstream behavior and golden parity.
        if previous_t is not None and cue.t_ms - previous_t > self.cfg.gap_ms:
            eye_valid = mouth_valid = head_valid = False
        return replace(
            validated,
            face_valid=face_valid,
            eye_valid=eye_valid,
            closure_prob=float(cue.closure_prob) if eye_valid else 0.0,
            mouth_valid=mouth_valid,
            yawn_prob=float(cue.yawn_prob) if mouth_valid else 0.0,
            head_valid=head_valid,
            pitch_deg=float(cue.pitch_deg) if head_valid else 0.0,
            ear=cue.ear if eye_valid else None,
        )


def _number(value, name, minimum=0.0):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a finite number" % name)
    if not math.isfinite(value) or value < minimum:
        raise ValueError("%s must be finite and >= %s" % (name, minimum))
    return float(value)


def _frame_id(record, name):
    value = record.get("frame_id")
    if type(value) is not int or value < 0:
        raise ValueError("%s.frame_id must be a nonnegative integer" % name)
    return value


def _source_time(record, name):
    if "timestamp_ms" in record:
        return _number(record["timestamp_ms"], name + ".timestamp_ms") / 1000.0
    for key in ("timestamp", "timestamp_sec", "time_s"):
        if key in record:
            return _number(record[key], name + "." + key)
    raise ValueError("%s must provide its source timestamp" % name)


def synchronized_frame(sg1, sg2, sg3=None):
    """Merge matching SG1, native SG2 v2 and optional SG3 adapter outputs.

    SG1 is authoritative for frame identity and source time. At most 1 ms of
    timestamp rounding difference is accepted. Missing SG3 means unavailable,
    not a negative yawn observation. SG3 ``yawn_active`` is a hard mouth flag;
    SG4's real persistence/debounce tracker decides completed yawn events.
    """
    if not isinstance(sg1, dict) or not isinstance(sg2, dict):
        raise ValueError("SG1 and SG2 records must be dictionaries")
    frame_id, timestamp = _frame_id(sg1, "SG1"), _source_time(sg1, "SG1")
    for name, record in (("SG2", sg2), ("SG3", sg3)):
        if record is None:
            continue
        if not isinstance(record, dict):
            raise ValueError("%s record must be a dictionary" % name)
        if _frame_id(record, name) != frame_id:
            raise ValueError("%s frame_id does not match SG1" % name)
        if abs(_source_time(record, name) - timestamp) > 0.001000001:
            raise ValueError("%s timestamp does not match SG1" % name)

    if "status" in sg1:
        if sg1["status"] not in ("OK", "NO_FACE", "INVALID"):
            raise ValueError("Unsupported SG1 status")
        face_present = sg1["status"] == "OK"
    elif type(sg1.get("face_valid")) is bool:
        face_present = sg1["face_valid"]
    else:
        raise ValueError("SG1 must explicitly provide face presence")
    confidence = sg1.get("detection_confidence", sg2.get("face_confidence"))
    if confidence is not None:
        confidence = _number(confidence, "observed face confidence")
        if confidence > 1:
            raise ValueError("observed face confidence must be <= 1")

    state = sg2.get("eye_state")
    eye_valid = sg2.get("eye_valid")
    if state not in ("OPEN", "CLOSED", "UNKNOWN") or type(eye_valid) is not bool:
        raise ValueError("SG2 must provide an explicit hard eye state and validity")
    if eye_valid != (state != "UNKNOWN"):
        raise ValueError("SG2 eye state and validity disagree")
    ear = sg2.get("ear")
    if ear is not None:
        ear = _number(ear, "SG2.ear")

    mouth_valid = False
    mouth_active = None
    if sg3 is not None:
        if type(sg3.get("valid")) is not bool:
            raise ValueError("SG3 must explicitly provide mouth validity")
        mouth_valid = sg3["valid"]
        if mouth_valid:
            if type(sg3.get("yawn_active")) is not bool:
                raise ValueError("valid SG3 output must provide boolean yawn_active")
            mouth_active = sg3["yawn_active"]

    return AvailabilityCue(
        frame_id=frame_id,
        t_ms=int(round(timestamp * 1000.0)),
        face_present=face_present,
        face_conf=confidence,
        closure_prob=float(state == "CLOSED") if eye_valid else None,
        eye_state=state.lower(),
        eye_conf=None,
        ear=ear if eye_valid else None,
        yawn_prob=float(mouth_active) if mouth_valid else None,
        mouth_conf=None,
        pitch_deg=None,
        head_conf=None,
        eye_available=eye_valid,
        mouth_available=mouth_valid,
        head_available=False,
    )


class SG4Bridge:
    """Own one genuine SG4 TemporalEngine for one continuous source stream.

    With annotations enabled, ``eye_valid`` describes the current synchronized
    frame, not the window's historical validity fraction. ``quality_kind``
    identifies availability rather than calibrated model confidence. These
    are SG5-side annotations, not additions to SG4's frozen wire schema.
    """

    def __init__(self, cfg=None, *, annotate_eye_valid=True):
        self.engine = TemporalEngine(cfg)
        self.engine.sync = AvailabilitySynchronizer(self.engine.cfg)
        self.annotate_eye_valid = annotate_eye_valid
        self._source_kind = "sg4_confidence_gated"

    def _annotate(self, vector):
        if vector is None or not self.annotate_eye_valid:
            return vector
        return dict(
            vector,
            eye_valid=bool(self.engine.last and self.engine.last.eye_valid),
            quality_kind="observed_availability",
            availability_source=self._source_kind,
        )

    def push(self, record):
        if not isinstance(record, AvailabilityCue):
            if not isinstance(record, dict) or record.get("schema") != INPUT_SCHEMA_ID:
                raise ValueError("provide sg4.input.v1 or use synchronized_frame for native subgroup outputs")
            errors = validate_input(record)
            if errors:
                raise ValueError("invalid sg4.input.v1 record: " + errors[0])
        self._source_kind = (
            "sg1_sg2_sg3_hard_state" if isinstance(record, AvailabilityCue)
            else "sg4_confidence_gated"
        )
        return self._annotate(self.engine.push(record))

    def snapshot(self):
        return self._annotate(self.engine.snapshot())


def iter_temporal(records: Iterable, *, annotate_eye_valid=False, cfg=None):
    """Yield real SG4 vectors; default output exactly preserves v1.1 fields.

    Enable annotations for the direct in-process SG5 pipeline. For an empty
    stream emit SG4's actual no-data snapshot, not a fabricated awake row.
    """
    bridge = SG4Bridge(cfg, annotate_eye_valid=annotate_eye_valid)
    emitted = False
    for record in records:
        vector = bridge.push(record)
        if vector is not None:
            emitted = True
            yield vector
    if not emitted:
        yield bridge.snapshot()
