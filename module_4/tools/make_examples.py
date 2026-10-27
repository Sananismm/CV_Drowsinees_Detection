"""Regenerate interfaces/examples/ from the mock streams and golden SG-5 outputs.

    python module_4/tools/make_examples.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from sg4.paths import interfaces_dir  # noqa: E402

MOCKS = interfaces_dir() / "mocks"
OUT = interfaces_dir() / "examples"


def _lines(path):
    with open(str(path)) as f:
        return [json.loads(x) for x in f if x.strip()]


def _at(rows, key, t):
    return min(rows, key=lambda r: abs(r[key] - t))


def _dump(name, obj):
    with open(str(OUT / name), "w") as f:
        if isinstance(obj, list):
            f.write("".join(json.dumps(o) + "\n" for o in obj))
        else:
            json.dump(obj, f, indent=2)
            f.write("\n")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    alert_in = _lines(MOCKS / "alert.jsonl")
    _dump("input_valid.json", alert_in[300])
    face_lost_in = _lines(MOCKS / "face_lost.jsonl")
    _dump("input_valid_face_lost.json", _at(face_lost_in, "timestamp_ms", 16000))

    bad = dict(alert_in[300])
    bad["eye"] = dict(bad["eye"], closure_prob=73.0)            # % instead of 0-1
    _dump("input_invalid_closure_prob_percent.json", bad)
    bad = dict(alert_in[300])
    del bad["timestamp_ms"]
    _dump("input_invalid_missing_timestamp.json", bad)
    bad = dict(alert_in[300])
    bad["eye"] = dict(bad["eye"], state="half_open")
    _dump("input_invalid_state_enum.json", bad)

    alert = _lines(MOCKS / "sg5_expected" / "alert.jsonl")
    drowsy = _lines(MOCKS / "sg5_expected" / "drowsy.jsonl")
    face_lost = _lines(MOCKS / "sg5_expected" / "face_lost.jsonl")
    _dump("output_a_alert.json", _at(alert, "time_s", 80.0))
    _dump("output_b_microsleep.jsonl", [_at(drowsy, "time_s", t) for t in (74.2, 74.6, 75.0, 75.4, 75.8, 76.0)])
    _dump("output_c_face_lost.json", _at(face_lost, "time_s", 16.0))
    _dump("output_d_calibrating.json", _at(alert, "time_s", 10.0))
    print("examples ->", OUT)


if __name__ == "__main__":
    main()
