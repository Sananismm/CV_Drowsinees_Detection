"""Check an SG-4 output stream against SG-5's input contract (v1.1). Standard library only.

    python module_4/tools/check_sg5_compat.py interfaces/mocks/sg5_expected/drowsy.jsonl

Prints PASS/FAIL per SG-5 field and exits non-zero on any failure. SG-5 (or
anyone) can run this at Integration Gate 1 without installing SG-4.
"""
import json
import math
import sys

# SG-5 contract: field -> (description, check(value) -> bool)
def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _count(v):
    return isinstance(v, int) and not isinstance(v, bool) and v >= 0


CHECKS = [
    ("time_s", "float seconds, increasing", lambda v: _num(v) and v >= 0),
    ("perclos", "float in [0, 1] (not %)", lambda v: _num(v) and 0.0 <= v <= 1.0),
    ("face_valid", "int 0 or 1", lambda v: isinstance(v, int) and not isinstance(v, bool) and v in (0, 1)),
    ("long_blinks", "int >= 0 (closures >= 0.5 s in 30 s)", _count),
    ("yawn_count", "int >= 0 (yawn events in 60 s)", _count),
    ("eye_closure_s", "float >= 0 (ongoing closure)", lambda v: _num(v) and v >= 0),
    ("nod_count", "int >= 0 (optional extra)", _count),
]


def check(lines):
    fails = {k: [] for k, _, _ in CHECKS}
    fails["schema"] = []
    fails["time_s increasing"] = []
    fails["face lost -> eye_closure_s 0"] = []
    prev_t = None
    n = 0
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
        n += 1
        try:
            o = json.loads(line)
        except ValueError as e:
            fails["schema"].append((i, "not JSON: %s" % e))
            continue
        if o.get("schema") != "sg4.output.v1.1":
            fails["schema"].append((i, o.get("schema")))
        for key, _, ok in CHECKS:
            if key not in o:
                fails[key].append((i, "missing"))
            elif not ok(o[key]):
                fails[key].append((i, o[key]))
        t = o.get("time_s")
        if _num(t):
            if prev_t is not None and t <= prev_t:
                fails["time_s increasing"].append((i, "%s after %s" % (t, prev_t)))
            prev_t = t
        if o.get("face_valid") == 0 and o.get("eye_closure_s", 0) != 0:
            fails["face lost -> eye_closure_s 0"].append((i, o.get("eye_closure_s")))
    return n, fails


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(__doc__)
        return 2
    worst = 0
    for path in argv:
        with open(path) as f:
            n, fails = check(f)
        print("%s  (%d records)" % (path, n))
        desc = {k: d for k, d, _ in CHECKS}
        for key, bad in fails.items():
            status = "PASS" if not bad and n else "FAIL"
            extra = "" if not bad else "  e.g. line %s: %r (%d bad)" % (bad[0][0], bad[0][1], len(bad))
            print("  %-4s %-30s %s%s" % (status, key, desc.get(key, ""), extra))
            if status == "FAIL":
                worst = 1
        if n == 0:
            print("  FAIL no records")
            worst = 1
    print("OVERALL:", "PASS" if worst == 0 else "FAIL")
    return worst


if __name__ == "__main__":
    sys.exit(main())
