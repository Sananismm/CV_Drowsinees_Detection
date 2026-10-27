"""Portable causal adapter for SG3's mouth aspect ratio experiment.

Source: sg3 at e3661b7575ebd06eea67a072f901ecd1fcf08a0c,
module_3/Week 8 Progress.py. The three vertical gaps, mouth indices and
0.50 / 0.45 / 1.5-second settings come from that teammate implementation.

Unlike the Colab export, this adapter shares SG1 landmarks, converts them to
pixels, and never examines future frames. These geometry/causality corrections
and inherited thresholds require SG3 owner review and real-video calibration.
No detector confidence or yawn probability is invented.

SG4 must debounce ``yawn_active`` itself. ``yawn_confirmed`` and ``event`` are
diagnostics, not inputs for another persistence timer, which would double delay.
"""

from math import hypot, isfinite
from numbers import Real


MOUTH_INDICES = (61, 291, 13, 14, 82, 87, 312, 317)
SOURCE = {
    "branch": "sg3",
    "commit": "e3661b7575ebd06eea67a072f901ecd1fcf08a0c",
    "path": "module_3/Week 8 Progress.py",
}


def _finite(value):
    return isinstance(value, Real) and not isinstance(value, bool) and isfinite(value)


def _integer(value, minimum=0):
    return isinstance(value, int) and not isinstance(value, bool) and value >= minimum


def _mar(record):
    if record.get("status") != "OK":
        return None, "face_unavailable"
    if record.get("schema_version") != "sg1.v1":
        return None, "unsupported_schema"
    if record.get("landmark_topology") != "mediapipe_face_landmarker_478":
        return None, "unsupported_landmark_topology"
    width, height = record.get("image_width"), record.get("image_height")
    if not _integer(width, 1) or not _integer(height, 1):
        return None, "invalid_image_dimensions"
    landmarks = record.get("landmarks_xy_normalized")
    if (not isinstance(landmarks, list) or len(landmarks) != 478
            or record.get("landmark_count") != 478):
        return None, "invalid_landmark_count"
    points = {}
    for index in MOUTH_INDICES:
        point = landmarks[index]
        if (not isinstance(point, (list, tuple)) or len(point) != 2
                or not all(_finite(v) and 0 <= v <= 1 for v in point)):
            return None, "invalid_mouth_landmarks"
        points[index] = (point[0] * width, point[1] * height)

    def distance(a, b):
        return hypot(points[a][0] - points[b][0], points[a][1] - points[b][1])

    mouth_width = distance(61, 291)
    if mouth_width < 1e-6:
        return None, "zero_mouth_width"
    vertical = sum(distance(a, b) for a, b in ((13, 14), (82, 87), (312, 317))) / 3
    return vertical / mouth_width, None


class YawnAdapter:
    """One instance per monotonic, single-driver stream; no third-party imports."""

    def __init__(self, start_threshold=0.50, hold_threshold=0.45,
                 duration_s=1.5, max_gap_s=0.2):
        values = (start_threshold, hold_threshold, duration_s, max_gap_s)
        if (not all(_finite(v) for v in values)
                or not 0 < hold_threshold <= start_threshold
                or duration_s <= 0 or max_gap_s <= 0):
            raise ValueError("invalid yawn thresholds or timing settings")
        self.start_threshold = start_threshold
        self.hold_threshold = hold_threshold
        self.duration_s = duration_s
        self.max_gap_s = max_gap_s
        self.last_time = self.last_frame = None
        self._clear_opening()

    def _clear_opening(self):
        self.open_start = None
        self.confirmed = False

    def step(self, record):
        if not isinstance(record, dict):
            self._clear_opening()
            raise ValueError("SG1 record must be a dictionary")
        frame_id, timestamp_ms = record.get("frame_id"), record.get("timestamp_ms")
        if not _integer(frame_id) or not _integer(timestamp_ms):
            self._clear_opening()
            raise ValueError("frame_id and timestamp_ms must be nonnegative integers")
        t = timestamp_ms / 1000.0
        if self.last_time is not None:
            if t <= self.last_time or frame_id <= self.last_frame:
                self._clear_opening()
                raise ValueError("SG1 frame IDs and timestamps must strictly increase")
            if t - self.last_time > self.max_gap_s + 1e-9:
                self._clear_opening()
        self.last_time, self.last_frame = t, frame_id
        mar, reason = _mar(record)
        event = False
        if mar is None:
            self._clear_opening()
        elif self.open_start is None:
            if mar >= self.start_threshold:
                self.open_start = t
        elif mar < self.hold_threshold:
            self._clear_opening()
        if self.open_start is not None and not self.confirmed:
            if t - self.open_start + 1e-9 >= self.duration_s:
                self.confirmed = event = True
        return {
            "time_s": t,
            "frame_id": frame_id,
            "valid": mar is not None,
            "mar": mar,
            "yawn_active": self.open_start is not None,
            "yawn_confirmed": self.confirmed,
            "event": event,
            "confidence": None,
            "invalid_reason": reason,
            "source": dict(SOURCE),
        }
