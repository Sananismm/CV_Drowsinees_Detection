"""Status-aware SG6 handoff consumer; requests only, no hardware side effects.

Run with ``--input decisions.jsonl --events-only`` or pipe JSONL to stdin.
This is a proposed SG5 -> SG6 v2 integration boundary, not a statement of
approval by the SG6 team or proof of execution on Jetson hardware.
"""

import argparse
import json
import math
import sys
import time


FIELDS = {
    "schema_version", "time_s", "session_id", "driver_state", "alert",
    "alert_level", "score", "smoothed_score", "quality", "status", "reason",
    "transition", "alert_event", "config_id",
}
STATES = ("NORMAL", "WARNING", "DROWSY")
STATUSES = ("OK", "INSUFFICIENT_EVIDENCE", "STALE")


def _number(value, name, maximum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a finite number" % name)
    if not math.isfinite(value) or value < 0 or (maximum is not None and value > maximum):
        raise ValueError("%s is outside its permitted range" % name)
    return float(value)


def validate_decision(decision):
    """Reject foreign, incomplete or internally inconsistent v2 messages."""
    if not isinstance(decision, dict) or set(decision) != FIELDS:
        raise ValueError("expected the exact 14-field SG5 v2 decision payload")
    if decision["schema_version"] != "sg5.sg6.v2":
        raise ValueError("unsupported SG5 schema version")
    if decision["driver_state"] not in STATES or decision["status"] not in STATUSES:
        raise ValueError("invalid driver_state or observation status")
    _number(decision["time_s"], "time_s")
    for field in ("score", "smoothed_score", "quality"):
        _number(decision[field], field, maximum=1.0)
    for field in ("session_id", "reason", "config_id"):
        if not isinstance(decision[field], str) or not decision[field].strip():
            raise ValueError("%s must be a nonempty string" % field)
    for field in ("alert", "transition", "alert_event"):
        if type(decision[field]) is not bool:
            raise ValueError("%s must be a boolean" % field)
    if type(decision["alert_level"]) is not int or decision["alert_level"] not in (0, 1, 2):
        raise ValueError("alert_level must be integer 0, 1 or 2")
    level = STATES.index(decision["driver_state"])
    usable = decision["status"] == "OK"
    if decision["alert_level"] != (level if usable else 0):
        raise ValueError("alert_level disagrees with state or observation status")
    if decision["alert"] != (usable and level > 0):
        raise ValueError("alert disagrees with state or observation status")
    if decision["alert_event"] and (not usable or level == 0 or not decision["transition"]):
        raise ValueError("alert_event must be a usable upward state transition")
    return decision


def hardware_request(decision):
    """Convert a usable state to idempotent driver requests; never operate GPIO.

    Repeated buzzer_requested=True means keep the alarm enabled, not restart a
    beep every message. Non-OK status produces a distinct sensor-fault request;
    its retained driver_state must never be displayed as a fresh awake result.
    """
    validate_decision(decision)
    usable = decision["status"] == "OK"
    return {
        "time_s": decision["time_s"],
        "session_id": decision["session_id"],
        "driver_state": decision["driver_state"],
        "status": decision["status"],
        "buzzer_requested": usable and decision["driver_state"] == "DROWSY",
        "visual_warning": usable and decision["driver_state"] != "NORMAL",
        "sensor_fault": not usable,
        "alert_event": decision["alert_event"],
    }


class DeliveryWatchdog:
    """Arrival-clock hook for a continuously running SG6 transport loop.

    The application must call poll() while waiting for input, not only after a
    message arrives. Capture timestamps are deliberately not compared against
    host monotonic time. This offline JSONL CLI is not a delivery monitor.
    """

    def __init__(self, timeout_s=1.0):
        self.timeout_s = _number(timeout_s, "timeout_s")
        if self.timeout_s == 0:
            raise ValueError("timeout_s must be positive")
        self.last_arrival_s = None
        self.last_request = None

    def observe(self, decision, now_s=None):
        now = _number(time.monotonic() if now_s is None else now_s, "arrival clock")
        if self.last_arrival_s is not None and now < self.last_arrival_s:
            raise ValueError("arrival clock must not go backwards")
        request = hardware_request(decision)
        self.last_arrival_s, self.last_request = now, request
        return dict(request)

    def poll(self, now_s=None):
        now = _number(time.monotonic() if now_s is None else now_s, "arrival clock")
        if self.last_arrival_s is not None:
            if now < self.last_arrival_s:
                raise ValueError("arrival clock must not go backwards")
            if now - self.last_arrival_s <= self.timeout_s:
                return None
        # No new capture observation is invented. time_s is the last known
        # producer time, or None before the first message.
        previous = self.last_request or {}
        return {
            "time_s": previous.get("time_s"),
            "session_id": previous.get("session_id"),
            "driver_state": previous.get("driver_state"),
            "status": "STALE",
            "buzzer_requested": False,
            "visual_warning": False,
            "sensor_fault": True,
            "alert_event": False,
        }


def consume(lines, *, events_only=False):
    """Yield requests from a finite replay; reject backward same-session time."""
    previous_key = None
    previous_session = previous_time = None
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            decision = json.loads(line)
            request = hardware_request(decision)
            if decision["session_id"] == previous_session and decision["time_s"] <= previous_time:
                raise ValueError("same-session capture timestamps must strictly increase")
        except (ValueError, TypeError) as exc:
            raise ValueError("input line %d: %s" % (number, exc)) from exc
        previous_session, previous_time = decision["session_id"], decision["time_s"]
        key = (decision["session_id"], decision["driver_state"], decision["status"])
        if not events_only or key != previous_key or decision["alert_event"]:
            yield request
        previous_key = key


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", help="SG5 v2 JSONL file; default is standard input")
    parser.add_argument("--events-only", action="store_true", help="print state/status changes only")
    args = parser.parse_args(argv)
    source = None
    try:
        source = open(args.input, encoding="utf-8") if args.input else sys.stdin
        count = 0
        for request in consume(source, events_only=args.events_only):
            print(json.dumps(request, separators=(",", ":")), flush=True)
            count += 1
        if count == 0:
            print(json.dumps(DeliveryWatchdog().poll(), separators=(",", ":")), flush=True)
    except (OSError, ValueError) as exc:
        print("SG5 handoff error: %s" % exc, file=sys.stderr)
        return 2
    finally:
        if source is not None and source is not sys.stdin:
            source.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
