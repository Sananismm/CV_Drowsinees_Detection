"""Seeded synthetic cue generator (sg4.input.v1) WITH ground-truth events.

Stands in for SG-1/SG-2/SG-3 until their outputs exist. Every scenario is
deterministic for a given seed. Ground truth is written to <name>.gt.json:

  closures   true eye closures [start_ms, end_ms) and class (blink / slow_blink /
             long_blink / interrupted = face lost mid-closure, true length unknown)
  yawns      true yawn events (two yawns < 1 s apart are ONE event)
  nods       true nod / head-drop events (incl. head drops that lose the face)
  invalid    intervals with no usable face (looking away, low confidence)
  artifacts  things that must NOT be counted: talking, single-frame noise spikes

Scenarios: alert, drowsy, yawns_nods, face_lost, noisy (drowsy + noise, dropped
frames, jitter, out-of-order and duplicate frames, talking, spikes).

    python module_4/tools/mock_stream.py --all              # regenerate interfaces/mocks/
    python module_4/tools/mock_stream.py --scenario drowsy --seed 7 --out /tmp/d.jsonl
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from sg4.config import load_config  # noqa: E402
from sg4.events import classify_closure  # noqa: E402
from sg4.paths import interfaces_dir  # noqa: E402

SCENARIOS = ("alert", "drowsy", "yawns_nods", "face_lost", "noisy")
DEFAULT_SEEDS = {"alert": 1, "drowsy": 2, "yawns_nods": 3, "face_lost": 4, "noisy": 5}


def _overlaps(s, e, intervals, margin=300):
    return any(s < b + margin and e > a - margin for a, b in intervals)


class _Plan:
    """Ground-truth timeline for one scenario."""

    def __init__(self, duration_ms):
        self.duration_ms = duration_ms
        self.closures = []      # [start, end, class]
        self.yawns = []         # [start, end]  (yawn_prob high)
        self.yawn_events = []   # [start, end]  (after merging < 1 s)
        self.nods = []          # [start, end, pitch]
        self.head_drops = []    # [start, end]: pitch ramps down, then face lost until end
        self.invalid = []       # [start, end, reason]
        self.talking = []       # [start, end]
        self.spikes = []        # [t]
        self.open_level = lambda t: 0.1   # mean closure_prob of an open eye at time t

    def reserved(self):
        r = [(s, e) for s, e, _ in self.closures] + [(s, e) for s, e, _ in self.invalid]
        return r + [(s, e) for s, e, _ in self.nods] + [tuple(h) for h in self.head_drops]

    def add_blinks(self, rng, start, end, every_ms, dur_ms):
        """Blinks roughly every `every_ms` (jittered) with duration from dur_ms(rng, t)."""
        t = start + rng.uniform(300, every_ms)
        while t < end:
            d = int(dur_ms(rng, t))
            s, e = int(t), int(t) + d
            if e < self.duration_ms and not _overlaps(s, e, self.reserved()):
                self.closures.append([s, e, None])
            t += rng.uniform(0.6, 1.4) * every_ms


def _build(scenario, rng, duration_ms):
    p = _Plan(duration_ms)
    D = duration_ms
    if scenario == "alert":
        p.add_blinks(rng, 0, D, 3500, lambda r, t: r.uniform(100, 300))
        p.nods.append([70000, 70400, -18.0])    # brief glance down (mirror check): a real nod-shaped event
    elif scenario in ("drowsy", "noisy"):
        for s, d in ((50000, 800), (62000, 1200), (68500, 650), (74000, 1800), (80000, 900), (85500, 2000)):
            p.closures.append([s, s + d, None])
        p.yawns += [[30000, 34000], [55000, 59500]]
        p.nods.append([77000, 77900, -24.0])
        p.add_blinks(rng, 0, D, 3000,
                     lambda r, t: r.uniform(120, 320) if t < 40000 else r.uniform(250, 480))
        p.open_level = lambda t: 0.08 + 0.25 * min(1.0, t / float(D))   # drooping lids, still < 0.5
        if scenario == "noisy":
            p.talking += [[12000, 12500], [12900, 13300], [44000, 44600]]
            p.spikes += [8000, 21000, 36000, 47000]
    elif scenario == "yawns_nods":
        p.yawns += [[10000, 14000], [25000, 29000], [29600, 31600], [45000, 50000]]   # 2nd+3rd merge
        p.talking += [[18000, 18600], [19000, 19500], [37000, 37700]]
        p.nods += [[40000, 40800, -22.0], [55000, 56000, -26.0], [57500, 58300, -20.0]]
        p.head_drops.append([70000, 72000])
        p.add_blinks(rng, 0, D, 3500, lambda r, t: r.uniform(100, 300))
    elif scenario == "face_lost":
        p.invalid += [[15000, 19000, "look_away"], [35000, 37500, "look_away"],
                      [50000, 53000, "low_confidence"], [65300, 67300, "look_away"]]
        p.closures.append([65000, 66000, None])   # closure starts, face lost 300 ms in
        p.add_blinks(rng, 0, D, 3500, lambda r, t: r.uniform(100, 300))
    else:
        raise ValueError("unknown scenario %r" % scenario)

    cfg = load_config()
    lost = [(s, e) for s, e, _ in p.invalid] + [(s + 400, e) for s, e in p.head_drops]
    for c in p.closures:
        c[2] = "interrupted" if _overlaps(c[0], c[1], lost, margin=0) else classify_closure(c[1] - c[0], cfg)
    p.closures.sort()
    for s, e in sorted(p.yawns):             # merge yawns < merge gap apart into one event
        if p.yawn_events and s - p.yawn_events[-1][1] < cfg.yawn_merge_gap_ms:
            p.yawn_events[-1][1] = e
        else:
            p.yawn_events.append([s, e])
    return p


def _inside(t, intervals):
    for iv in intervals:
        if iv[0] <= t < iv[1]:
            return iv
    return None


def _frame(p, t, i, rng, noisy):
    head_drop = _inside(t, p.head_drops)
    invalid = _inside(t, p.invalid)
    face_lost = (invalid is not None and invalid[2] == "look_away") or (
        head_drop is not None and t >= head_drop[0] + 400)
    rec = {"schema": "sg4.input.v1", "frame_id": i, "timestamp_ms": t}
    if face_lost:
        rec.update(face={"present": False, "confidence": round(rng.uniform(0.0, 0.2), 3)},
                   eye=None, mouth=None, head=None)
        return rec
    conf = rng.uniform(0.3, 0.45) if invalid is not None else rng.uniform(0.88, 0.99)
    rec["face"] = {"present": True, "confidence": round(conf, 3)}

    if _inside(t, p.closures) is not None:
        cp = rng.uniform(0.85, 1.0)
    elif noisy and int(t) in p._spike_frames:
        cp = 0.9                                   # single-frame measurement spike
    else:
        cp = p.open_level(t) + rng.normal(0, 0.06 if noisy else 0.03)
        cp = min(0.45, max(0.0, cp))
    rec["eye"] = {"closure_prob": round(cp, 3), "state": "closed" if cp >= 0.5 else "open",
                  "ear": round(0.31 * (1 - cp) + 0.02, 3), "confidence": round(rng.uniform(0.85, 0.98), 3)}

    if _inside(t, p.yawns) is not None:
        yp = rng.uniform(0.8, 0.97)
    elif _inside(t, p.talking) is not None:
        yp = rng.uniform(0.62, 0.75)                # mouth opens while talking: short, not a yawn
    else:
        yp = rng.uniform(0.01, 0.15)
    rec["mouth"] = {"yawn_prob": round(yp, 3), "mar": round(0.25 + 0.6 * yp, 3),
                    "confidence": round(rng.uniform(0.85, 0.98), 3)}

    nod = _inside(t, p.nods)
    if nod is not None:
        pitch = nod[2] + rng.normal(0, 1.0)
    elif head_drop is not None:                     # ramp from -5 to -14 deg over 400 ms, then face lost
        pitch = -5.0 - 9.0 * (t - head_drop[0]) / 400.0
    else:
        pitch = -3.0 + rng.normal(0, 1.5)
    rec["head"] = {"pitch_deg": round(pitch, 2), "yaw_deg": round(rng.normal(0, 3), 2),
                   "roll_deg": round(rng.normal(0, 2), 2), "confidence": round(rng.uniform(0.85, 0.98), 3)}
    return rec


def generate(scenario, seed=None, fps=30.0, duration_s=90.0):
    """Return (records in emitted order, ground-truth dict)."""
    seed = DEFAULT_SEEDS.get(scenario, 0) if seed is None else seed
    rng = np.random.default_rng(seed)
    D = int(duration_s * 1000)
    p = _build(scenario, rng, D)
    noisy = scenario == "noisy"
    n = int(duration_s * fps)
    times = [int(round(i * 1000.0 / fps)) for i in range(n)]
    p._spike_frames = set(min(times, key=lambda x: abs(x - s)) for s in p.spikes)

    records = []
    for i, t in enumerate(times):
        if noisy and (rng.random() < 0.03 or 20000 <= t < 20300 or 66000 <= t < 66300):
            continue                                # dropped frames + two 300 ms bursts
        rec = _frame(p, t, i, rng, noisy)           # content follows the true time...
        if noisy:                                   # ...the reported clock is jittered
            rec["timestamp_ms"] = max(0, t + int(round(rng.normal(0, 2.0))))
        records.append(rec)
    if noisy:
        out = []
        for r in records:
            out.append(r)
            if rng.random() < 0.005:
                out.append(dict(r))                 # duplicate
        for k in range(1, len(out) - 1):
            if rng.random() < 0.005:
                out[k], out[k + 1] = out[k + 1], out[k]   # out-of-order pair
        records = out

    gt = {
        "scenario": scenario, "seed": seed, "fps": fps, "duration_ms": D,
        "closures": [{"start_ms": s, "end_ms": e, "class": c} for s, e, c in p.closures],
        "yawns": [{"start_ms": s, "end_ms": e} for s, e in p.yawn_events],
        "nods": ([{"start_ms": s, "end_ms": e, "kind": "nod"} for s, e, _ in p.nods]
                 + [{"start_ms": s, "end_ms": e, "kind": "head_drop_face_lost"} for s, e in p.head_drops]),
        "invalid": ([{"start_ms": s, "end_ms": e, "reason": r} for s, e, r in p.invalid]
                    + [{"start_ms": s + 400, "end_ms": e, "reason": "head_drop"} for s, e in p.head_drops]),
        "artifacts": ([{"start_ms": s, "end_ms": e, "kind": "talking"} for s, e in p.talking]
                      + [{"start_ms": t, "end_ms": t + 1, "kind": "spike"} for t in sorted(p._spike_frames)]),
        "dropped_records_note": "noisy: ~3% random drops, bursts at 20.0-20.3 s and 66.0-66.3 s" if noisy else None,
    }
    gt["nods"].sort(key=lambda x: x["start_ms"])
    gt["invalid"].sort(key=lambda x: x["start_ms"])
    return records, gt


def write_jsonl(path, rows):
    with open(str(path), "w") as f:
        for r in rows:
            f.write(json.dumps(r, separators=(",", ":")) + "\n")


def write_scenario(scenario, out_path, seed=None, fps=30.0, duration_s=90.0):
    records, gt = generate(scenario, seed, fps, duration_s)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(out_path, records)
    gt_path = out_path.with_name(out_path.name.replace(".jsonl", "") + ".gt.json")
    with open(str(gt_path), "w") as f:
        json.dump(gt, f, indent=1)
    return out_path, gt_path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scenario", choices=SCENARIOS)
    ap.add_argument("--all", action="store_true", help="write every scenario to interfaces/mocks/")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--fps", type=float, default=30.0)
    ap.add_argument("--duration", type=float, default=90.0, help="seconds")
    ap.add_argument("--out", help="output .jsonl (ground truth goes next to it as .gt.json)")
    a = ap.parse_args(argv)
    if a.all:
        for s in SCENARIOS:
            print("wrote", *write_scenario(s, interfaces_dir() / "mocks" / (s + ".jsonl"), None, a.fps, a.duration))
    elif a.scenario:
        print("wrote", *write_scenario(a.scenario, a.out or (a.scenario + ".jsonl"), a.seed, a.fps, a.duration))
    else:
        ap.error("give --scenario or --all")


if __name__ == "__main__":
    main()
