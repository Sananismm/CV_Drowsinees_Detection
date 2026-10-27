# =============================================================================
# SG5 FINAL - Drowsiness Decision & Alert Logic using the chosen METHOD C
#             (state machine with smoothing, hysteresis and micro-sleep override)
# =============================================================================
# RUN FROM TERMINAL (VS Code PowerShell) - copy and paste:
#
#   cd "C:\Users\Hp Probook\Desktop\7th sem\cv\project\SG5_drowsiness_decision\SG5_drowsiness_decision"
#   & "$env:USERPROFILE\anaconda3\envs\ganenv\python.exe" sg5_final.py
#
# Options (add after sg5_final.py):
#   --drive drive2_synthetic   use the other test drive (default drive1_synthetic)
#   --speed 20                 replay alerts 20x faster than real time (default 0 = instant)
#   --no-beep                  no sound
# Example (live-style demo, with beeps):
#   & "$env:USERPROFILE\anaconda3\envs\ganenv\python.exe" sg5_final.py --speed 20
#
# WHAT IT DOES
#   1. Reads SG4 input  data/<drive>.csv  (one row every 0.1 s)
#   2. DECIDES the driver state with Method C          (decision logic, this file)
#   3. ALERTS on WARNING / DROWSY via alert_ui.py      (alert output, separate file)
#   4. Saves SG5 output  results/<drive>_sg5_output.csv
#   5. Compares with ground truth, prints metrics, opens one graph window
#
# INPUT  (from SG4):  time_s, face_valid, perclos, eye_closure_s, long_blinks, yawn_count
#                     (+ gt_state in test data only, never used for deciding)
# OUTPUT (from SG5):  time_s, state (NORMAL/WARNING/DROWSY), alert_level (0/1/2),
#                     score (0..1), reason
# =============================================================================
import argparse
import csv
import math
import os
import sys
import time

import matplotlib.pyplot as plt
import numpy as np

from alert_ui import show_alert          # alert output lives in a separate file

for _backend in ("TkAgg", "QtAgg", "Qt5Agg"):   # make graphs open in a window
    try:
        plt.switch_backend(_backend)
        break
    except Exception:
        continue

HERE = os.path.dirname(os.path.abspath(__file__))
STATES = ["NORMAL", "WARNING", "DROWSY"]

# ----------------------------- PARAMETERS (Method C) -------------------------
SCORE_INPUTS = {            # column: (low, high, weight) -> scaled 0..1, weighted
    "perclos":       (0.05, 0.30, 0.45),
    "eye_closure_s": (0.40, 2.00, 0.20),
    "long_blinks":   (1,    6,    0.20),
    "yawn_count":    (0,    3,    0.15),
}
C_PARAMS = dict(
    enter_warn=0.20,   exit_warn=0.14,      # go UP to WARNING at 0.20, back DOWN below 0.14
    enter_drowsy=0.65, exit_drowsy=0.53,    # go UP to DROWSY at 0.65, back DOWN below 0.53
    smoothing_s=2.0,                        # score averaged over ~2 s
    confirm_s=1.0,                          # must stay high 1 s before going up
    min_hold_s=3.0,                         # must stay low 3 s before going down
    microsleep_s=1.5,                       # eyes closed >= 1.5 s -> DROWSY at once
)
WARMUP_S = 5.0                              # first 5 s: SG4 windows still filling


# ----------------------------- DECISION LOGIC --------------------------------
def drowsiness_score(row):
    total = sum(w for _, _, w in SCORE_INPUTS.values())
    return sum(w * min(1.0, max(0.0, (row[c] - lo) / (hi - lo)))
               for c, (lo, hi, w) in SCORE_INPUTS.items()) / total


class MethodC:
    """Call step(row) once per SG4 row; returns (state, smoothed_score, reason)."""

    def __init__(self, p=C_PARAMS):
        self.p = p
        self.level, self.smooth, self.last_t = 0, None, None
        self.pending, self.last_support = None, 0.0

    def step(self, r):
        p, t = self.p, r["time_s"]
        if t < WARMUP_S:
            self.last_t = self.last_support = t
            return "NORMAL", 0.0, "warm-up"
        if not r["face_valid"]:
            self.last_t = t
            return STATES[self.level], self.smooth or 0.0, "face lost: hold state"

        s = drowsiness_score(r)
        dt = t - self.last_t if self.last_t is not None else 0.0
        self.smooth = s if self.smooth is None else \
            self.smooth + (1 - math.exp(-dt / p["smoothing_s"])) * (s - self.smooth)
        self.last_t = t

        if r["eye_closure_s"] >= p["microsleep_s"]:                    # 1) micro-sleep
            self.level, self.pending, self.last_support = 2, None, t
            return "DROWSY", 1.0, f"micro-sleep: eyes closed {r['eye_closure_s']:.1f} s"

        up = 2 if self.smooth >= p["enter_drowsy"] else 1 if self.smooth >= p["enter_warn"] else 0
        down = 2 if self.smooth >= p["exit_drowsy"] else 1 if self.smooth >= p["exit_warn"] else 0
        if down >= self.level:
            self.last_support = t
        if up > self.level:                                            # 2) confirm before up
            self.pending = t if self.pending is None else self.pending
            if t - self.pending >= p["confirm_s"]:
                self.level, self.pending, self.last_support = up, None, t
        else:
            self.pending = None
            if down < self.level and t - self.last_support >= p["min_hold_s"]:   # 3) hold before down
                self.level, self.last_support = down, t
        return STATES[self.level], self.smooth, f"score {self.smooth:.2f}"


# ----------------------------- EVALUATION ------------------------------------
def episodes(times, flags):
    eps, start, prev = [], None, None
    for t, f in zip(times, flags):
        if f and start is None:
            start = t
        if not f and start is not None:
            eps.append((start, prev))
            start = None
        prev = t
    if start is not None:
        eps.append((start, prev))
    return eps


def compare_with_gt(times, gt, pred):
    gt_eps = episodes(times, [g == "DROWSY" for g in gt])
    pr_eps = episodes(times, [p == "DROWSY" for p in pred])
    used, delays = set(), []
    for gs, ge in gt_eps:
        hits = [i for i, (ps, pe) in enumerate(pr_eps) if ps <= ge + 5 and pe >= gs]
        if hits:
            used.update(hits)
            delays.append(min(pr_eps[i][0] for i in hits) - gs)
    per_state = {s: (np.mean([p == s for g, p in zip(gt, pred) if g == s])
                     if s in gt else float("nan")) for s in STATES}
    return {"accuracy": float(np.mean([g == p for g, p in zip(gt, pred)])),
            "drowsy_events": len(gt_eps), "detected": len(delays),
            "false_alerts": len(pr_eps) - len(used),
            "delays": delays,
            "state_changes": sum(a != b for a, b in zip(pred, pred[1:])),
            "per_state": per_state}


# ----------------------------- MAIN ------------------------------------------
def load(path):
    with open(path) as f:
        return [{"time_s": float(r["time_s"]), "face_valid": r["face_valid"] == "1",
                 "perclos": float(r["perclos"]), "eye_closure_s": float(r["eye_closure_s"]),
                 "long_blinks": int(r["long_blinks"]), "yawn_count": int(r["yawn_count"]),
                 "gt_state": r.get("gt_state")} for r in csv.DictReader(f)]


def main():
    ap = argparse.ArgumentParser(description="SG5 final: Method C")
    ap.add_argument("--drive", default="drive1_synthetic")
    ap.add_argument("--speed", type=float, default=0.0)
    ap.add_argument("--no-beep", action="store_true")
    a = ap.parse_args()

    path = os.path.join(HERE, "data", f"{a.drive}.csv")
    if not os.path.exists(path):
        sys.exit(f"Not found: {path}")
    rows = load(path)

    # ---- run SG5 row by row, exactly as it would run live ----
    print(f"SG5 Method C on {a.drive}  ({rows[-1]['time_s']:.0f} s of driving)\n" + "-" * 60)
    sg5 = MethodC()
    out, prev_state, prev_t = [], "NORMAL", None
    for r in rows:
        if a.speed > 0 and prev_t is not None:
            time.sleep((r["time_s"] - prev_t) / a.speed)
        prev_t = r["time_s"]
        state, score, reason = sg5.step(r)
        if state != prev_state:
            show_alert(r["time_s"], prev_state, state, not a.no_beep)     # alert output
            prev_state = state
        out.append({"time_s": r["time_s"], "state": state, "alert_level": STATES.index(state),
                    "score": round(score, 3), "reason": reason})

    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    out_path = os.path.join(HERE, "results", f"{a.drive}_sg5_output.csv")
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=out[0].keys())
        w.writeheader()
        w.writerows(out)

    # ---- compare with ground truth ----
    t = [r["time_s"] for r in rows]
    gt = [r["gt_state"] for r in rows]
    pred = [o["state"] for o in out]
    m = compare_with_gt(t, gt, pred)
    print("-" * 60 + "\nCOMPARISON WITH GROUND TRUTH")
    print(f"  Accuracy (rows correct)      : {m['accuracy']:.0%}")
    for s in STATES:
        if not math.isnan(m["per_state"][s]):
            print(f"    correct when truly {s:8s}: {m['per_state'][s]:.0%}")
    caught = f"{m['detected']}/{m['drowsy_events']}" if m["drowsy_events"] else "none in this drive"
    print(f"  DROWSY events caught         : {caught}")
    if m["delays"]:
        print(f"  Alert delay per event (s)    : {', '.join(f'{d:.1f}' for d in m['delays'])}")
    print(f"  False DROWSY alerts          : {m['false_alerts']}")
    print(f"  State changes (flicker)      : {m['state_changes']}")
    print(f"  SG5 output saved to          : {out_path}")

    # ---- graph ----
    fig, ax = plt.subplots(3, 1, figsize=(13, 9), sharex=True)
    ax[0].plot(t, [r["perclos"] for r in rows], label="PERCLOS")
    ax[0].plot(t, [r["eye_closure_s"] / 3 for r in rows], lw=.7, label="eye closure (s) / 3")
    ax[0].plot(t, [r["yawn_count"] / 5 for r in rows], lw=.7, label="yawn count / 5")
    ax[0].set_title("SG4 input", loc="left", fontsize=10)
    ax[0].legend(fontsize=8, loc="upper right")

    ax[1].plot(t, [o["score"] for o in out], color="purple", label="smoothed drowsiness score")
    p = C_PARAMS
    for y, ls, lab in [(p["enter_drowsy"], "-", "enter DROWSY"), (p["exit_drowsy"], ":", "exit DROWSY"),
                       (p["enter_warn"], "-", "enter WARNING"), (p["exit_warn"], ":", "exit WARNING")]:
        ax[1].axhline(y, color="red" if "DROWSY" in lab else "orange", ls=ls, lw=1, label=lab)
    ms = [o["time_s"] for o in out if o["reason"].startswith("micro-sleep")]
    if ms:
        ax[1].scatter(ms, [1.0] * len(ms), color="red", s=12, zorder=3, label="micro-sleep override")
    ax[1].set_ylim(0, 1.08)
    ax[1].set_title("Method C score and thresholds (hysteresis)", loc="left", fontsize=10)
    ax[1].legend(fontsize=7, loc="upper left", ncol=3)

    gl = [STATES.index(g) for g in gt]
    pl = [STATES.index(s) for s in pred]
    ax[2].step(t, gl, "k--", where="post", lw=1.2, label="ground truth")
    ax[2].step(t, pl, color="#2ca02c", where="post", lw=2.2, label="SG5 Method C")
    ax[2].fill_between(t, -.3, 2.3, where=[x != y for x, y in zip(pl, gl)], step="post",
                       color="red", alpha=.12, label="wrong")
    ax[2].set_yticks([0, 1, 2]); ax[2].set_yticklabels(STATES); ax[2].set_ylim(-.3, 2.3)
    ax[2].set_title(f"Decision vs ground truth: accuracy {m['accuracy']:.0%}, DROWSY caught {caught}, "
                    f"false alerts {m['false_alerts']}", loc="left", fontsize=10)
    ax[2].legend(fontsize=8, loc="upper right")
    ax[2].set_xlabel("time (s)")
    for x in ax:
        x.grid(alpha=.3)
    fig.suptitle(f"SG5 final (Method C) - {a.drive}", fontsize=13)
    fig.tight_layout()
    print("\nOpening graph window (close it to finish)...")
    plt.show()


if __name__ == "__main__":
    main()
