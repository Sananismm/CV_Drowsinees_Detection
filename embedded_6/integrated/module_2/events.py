"""Timestamp-based eye closures; duration bounds are engineering configuration."""
from .adapters import finite, integer


class ClosureTracker:
    def __init__(self, max_gap_sec=0.2, blink_min_sec=0.1, blink_max_sec=0.4):
        if not all(finite(x) for x in (max_gap_sec, blink_min_sec, blink_max_sec)) or not (max_gap_sec > 0 and 0 <= blink_min_sec <= blink_max_sec):
            raise ValueError("invalid closure tracker configuration")
        self.max_gap = max_gap_sec
        self.blink_min, self.blink_max = blink_min_sec, blink_max_sec
        self.active = None
        self.previous = None
        self.previous_id = None
        self.previous_state = None

    def _finish(self, end_sec, end_frame, reason):
        if self.active is None:
            return None
        event = dict(self.active, end_sec=end_sec, end_frame=end_frame,
                     duration_sec=end_sec-self.active["start_sec"], end_reason=reason,
                     complete=reason == "reopened" and not self.active["left_censored"])
        event["is_blink_candidate"] = event["complete"] and self.blink_min <= event["duration_sec"] <= self.blink_max
        self.active = None
        return event

    def update(self, output):
        t, fid = output["timestamp_sec"], output["frame_id"]
        if not finite(t) or t < 0 or not integer(fid):
            raise ValueError("invalid event identity/time")
        if self.previous is not None and (t <= self.previous or fid <= self.previous_id):
            raise ValueError("frames and timestamps must strictly increase; reset for a new stream")
        gap = self.previous is not None and t-self.previous > self.max_gap
        event = None
        state = output["eye_state"] if output["valid"] else "UNKNOWN"
        if gap or state == "UNKNOWN":
            event = self._finish(self.previous, self.previous_id, "gap" if gap else "invalid")
        if state == "CLOSED":
            if self.active is None:
                self.active = dict(event_type="EYE_CLOSURE", start_sec=t, start_frame=fid,
                                   left_censored=gap or self.previous_state != "OPEN")
        elif state == "OPEN" and self.active is not None:
            event = self._finish(t, fid, "reopened")
        self.previous, self.previous_id, self.previous_state = t, fid, state
        return event

    def flush(self):
        """EOF closes at last observed timestamp, with right censoring."""
        return self._finish(self.previous, self.previous_id, "end_of_stream")
