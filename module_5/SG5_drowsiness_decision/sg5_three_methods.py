# =============================================================================
# SG5 - Drowsiness Decision & Alert Logic: compare 3 methods with ground truth
# =============================================================================
#
#   C:\Users\Hp Probook\Desktop\SG5_drowsiness_decision\SG5_drowsiness_decision
#   & "$env:USERPROFILE\anaconda3\envs\ganenv\python.exe" -m pip install numpy matplotlib
#   & "$env:USERPROFILE\anaconda3\envs\ganenv\python.exe" sg5_three_methods.py
#
# (The pip line is only needed once.)
#
# WHAT IT DOES
#   1. Reads the SG4-style input data in data/*.csv (one row every 0.1 s).
#   2. Runs Method A, Method B and Method C on every row.
#   3. Compares each method's output (NORMAL / WARNING / DROWSY) with the
#      ground truth column gt_state.
#   4. Prints a results table and OPENS the graphs in windows
#      (close all graph windows to end the program).
#      Decisions are also saved to results/<drive>_predictions.csv for alert_ui.py.
#
# INPUT  (each row of data/*.csv, from SG4):
#   time_s, face_valid, perclos, eye_closure_s, long_blinks, yawn_count, gt_state
# OUTPUT (each method, each row):
#   state = NORMAL / WARNING / DROWSY
#
# Change the numbers in the PARAMETERS section to try other settings.
# =============================================================================
import csv
import glob
import math
import os
import sys

import matplotlib.pyplot as plt
import numpy as np

# Make sure graphs open in a WINDOW. Some environments default to a
# non-interactive backend ("Agg"), where plt.show() silently shows nothing.
for _backend in ("TkAgg", "QtAgg", "Qt5Agg"):
    try:
        plt.switch_backend(_backend)
        break
    except Exception:
        continue
else:
    print("WARNING: no window backend found, graphs cannot open.\n"
          "Fix: & \"$env:USERPROFILE\\anaconda3\\envs\\ganenv\\python.exe\" -m pip install pyqt5")

HERE = os.path.dirname(os.path.abspath(__file__))
STATES = ["NORMAL", "WARNING", "DROWSY"]

# ----------------------------- PARAMETERS ------------------------------------
A_PARAMS = dict(drowsy_perclos=0.22, drowsy_closure_s=1.5,
                warn_perclos=0.10, warn_yawns=2, warn_long_blinks=3)

# Score used by B and C: each input scaled to 0..1 between (low, high), then weighted
SCORE_INPUTS = {            # column: (low, high, weight)
    "perclos":       (0.05, 0.30, 0.45),
    "eye_closure_s": (0.40, 2.00, 0.20),
    "long_blinks":   (1,    6,    0.20),
    "yawn_count":    (0,    3,    0.15),
}
B_PARAMS = dict(warn_score=0.20, drowsy_score=0.50)
C_PARAMS = dict(enter_warn=0.20, exit_warn=0.14, enter_drowsy=0.65, exit_drowsy=0.53,
                smoothing_s=2.0, confirm_s=1.0, min_hold_s=3.0, microsleep_s=1.5)
WARMUP_S = 5.0    # all methods output NORMAL for the first 5 s (SG4 windows still filling)


def drowsiness_score(row):
    total = sum(w for _, _, w in SCORE_INPUTS.values())
    s = 0.0
    for col, (lo, hi, w) in SCORE_INPUTS.items():
        s += w * min(1.0, max(0.0, (row[col] - lo) / (hi - lo)))
    return s / total


# ----------------------------- METHOD A --------------------------------------
def method_A(rows):
    """Threshold rules: check each row on its own, no memory."""
    p, out, state = A_PARAMS, [], "NORMAL"
    for r in rows:
        if r["time_s"] < WARMUP_S:
            state = "NORMAL"
        elif not r["face_valid"]:
            pass                                    # face lost: keep last state
        elif r["perclos"] >= p["drowsy_perclos"] or r["eye_closure_s"] >= p["drowsy_closure_s"]:
            state = "DROWSY"
        elif (r["perclos"] >= p["warn_perclos"] or r["yawn_count"] >= p["warn_yawns"]
              or r["long_blinks"] >= p["warn_long_blinks"]):
            state = "WARNING"
        else:
            state = "NORMAL"
        out.append(state)
    return out


# ----------------------------- METHOD B --------------------------------------
def method_B(rows):
    """Weighted score: combine all cues into one 0..1 score, then two thresholds."""
    p, out, state = B_PARAMS, [], "NORMAL"
    for r in rows:
        if r["time_s"] < WARMUP_S:
            state = "NORMAL"
        elif r["face_valid"]:
            s = drowsiness_score(r)
            state = "DROWSY" if s >= p["drowsy_score"] else "WARNING" if s >= p["warn_score"] else "NORMAL"
        out.append(state)
    return out


# ----------------------------- METHOD C --------------------------------------
def method_C(rows):
    """State machine: smoothed score + separate enter/exit thresholds (hysteresis),
    must stay high for confirm_s before going up, must stay low for min_hold_s
    before going down, and a long eye closure (micro-sleep) jumps straight to DROWSY."""
    p, out = C_PARAMS, []
    level, smooth, last_t, pending, last_support = 0, None, None, None, 0.0
    for r in rows:
        t = r["time_s"]
        if t < WARMUP_S:
            out.append("NORMAL")
            last_t, last_support = t, t
            continue
        if not r["face_valid"]:
            out.append(STATES[level])              # face lost: keep last state
            last_t = t
            continue
        s = drowsiness_score(r)
        dt = t - last_t if last_t is not None else 0.0
        smooth = s if smooth is None else smooth + (1 - math.exp(-dt / p["smoothing_s"])) * (s - smooth)
        last_t = t

        if r["eye_closure_s"] >= p["microsleep_s"]:          # micro-sleep override
            level, pending, last_support = 2, None, t
            out.append("DROWSY")
            continue
        up = 2 if smooth >= p["enter_drowsy"] else 1 if smooth >= p["enter_warn"] else 0
        down = 2 if smooth >= p["exit_drowsy"] else 1 if smooth >= p["exit_warn"] else 0
        if down >= level:
            last_support = t
        if up > level:                                       # going up: confirm first
            pending = t if pending is None else pending
            if t - pending >= p["confirm_s"]:
                level, pending, last_support = up, None, t
        else:
            pending = None
            if down < level and t - last_support >= p["min_hold_s"]:   # going down: hold first
                level, last_support = down, t
        out.append(STATES[level])
    return out


METHODS = {"A: Threshold": (method_A, "#d62728"),
           "B: Weighted score": (method_B, "#ff7f0e"),
           "C: State machine": (method_C, "#2ca02c")}


# ----------------------------- EVALUATION ------------------------------------
def episodes(times, flags):
    """Turn a True/False list into [(start_time, end_time), ...]."""
    eps, start = [], None
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
    """DROWSY event is 'detected' if the method says DROWSY during it (or up to 5 s after).
    A 'false alert' is a DROWSY period of the method that matches no real DROWSY event."""
    gt_eps = episodes(times, [g == "DROWSY" for g in gt])
    pr_eps = episodes(times, [p == "DROWSY" for p in pred])
    used, latencies = set(), []
    for gs, ge in gt_eps:
        hits = [i for i, (ps, pe) in enumerate(pr_eps) if ps <= ge + 5 and pe >= gs]
        if hits:
            used.update(hits)
            latencies.append(min(pr_eps[i][0] for i in hits) - gs)
    return {
        "accuracy": float(np.mean([g == p for g, p in zip(gt, pred)])),
        "drowsy_events": len(gt_eps),
        "detected": len(latencies),
        "missed": len(gt_eps) - len(latencies),
        "false_alerts": len(pr_eps) - len(used),
        "latency_s": float(np.mean(latencies)) if latencies else float("nan"),
        "state_changes": sum(a != b for a, b in zip(pred, pred[1:])),
        "confusion": np.array([[sum(1 for g, p in zip(gt, pred) if g == a and p == b)
                                for b in STATES] for a in STATES]),
    }


# ----------------------------- MAIN ------------------------------------------
def load(path):
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f):
            rows.append({"time_s": float(r["time_s"]), "face_valid": r["face_valid"] == "1",
                         "perclos": float(r["perclos"]), "eye_closure_s": float(r["eye_closure_s"]),
                         "long_blinks": int(r["long_blinks"]), "yawn_count": int(r["yawn_count"]),
                         "gt_state": r["gt_state"]})
    return rows


def plot_drive(name, rows, preds, results):
    t = [r["time_s"] for r in rows]
    gt = [STATES.index(r["gt_state"]) for r in rows]
    fig, ax = plt.subplots(5, 1, figsize=(13, 11), sharex=True)
    ax[0].plot(t, [r["perclos"] for r in rows], label="PERCLOS")
    ax[0].plot(t, [r["eye_closure_s"] / 3 for r in rows], lw=.7, label="eye closure (s) / 3")
    ax[0].plot(t, [r["yawn_count"] / 5 for r in rows], lw=.7, label="yawn count / 5")
    ax[0].set_ylabel("SG4 input"); ax[0].legend(fontsize=7, loc="upper right")
    ax[1].step(t, gt, "k", where="post", lw=2)
    ax[1].set_ylabel("Ground truth")
    for i, (m, (_, color)) in enumerate(METHODS.items()):
        p = [STATES.index(s) for s in preds[m]]
        r = results[m]
        a = ax[2 + i]
        a.step(t, gt, "k--", where="post", lw=1, alpha=.5, label="ground truth")
        a.step(t, p, color=color, where="post", lw=2, label=m)
        a.fill_between(t, -.3, 2.3, where=[x != y for x, y in zip(p, gt)], step="post",
                       color="red", alpha=.12, label="wrong")
        a.set_ylabel(m.split(":")[0], fontsize=11)
        a.set_title(f"{m}:  accuracy {r['accuracy']:.0%},  DROWSY events caught {r['detected']}/"
                    f"{r['drowsy_events']},  false alerts {r['false_alerts']}", fontsize=9, loc="left")
        a.legend(fontsize=7, loc="upper right")
    for a in ax[1:]:
        a.set_yticks([0, 1, 2]); a.set_yticklabels(STATES, fontsize=8); a.set_ylim(-.3, 2.3); a.grid(alpha=.3)
    ax[-1].set_xlabel("time (s)")
    fig.suptitle(f"{name}: three methods vs ground truth (red = wrong)", fontsize=13)
    fig.tight_layout()


def plot_summary(totals):
    names = list(METHODS)
    colors = [c for _, c in METHODS.values()]
    panels = [("accuracy", "Accuracy vs ground truth\n(higher is better)", "{:.0%}"),
              ("detected_pct", "DROWSY events caught\n(higher is better)", "{:.0%}"),
              ("false_alerts", "False DROWSY alerts\n(lower is better)", "{:.0f}"),
              ("latency_s", "Avg. alert delay (s)\n(lower is better)", "{:.1f}"),
              ("state_changes", "State changes / flicker\n(lower is better)", "{:.0f}")]
    fig, axs = plt.subplots(1, 5, figsize=(17, 4.5))
    for a, (key, title, fmt) in zip(axs, panels):
        vals = [totals[n][key] for n in names]
        bars = a.bar(range(3), vals, color=colors)
        a.bar_label(bars, labels=[fmt.format(v) for v in vals], fontsize=9)
        a.set_title(title, fontsize=10); a.set_xticks(range(3))
        a.set_xticklabels([n.split(":")[0] for n in names]); a.grid(axis="y", alpha=.3)
        a.set_ylim(0, max(vals) * 1.25 if max(vals) > 0 else 1)
    fig.suptitle("Overall comparison (all drives)  -  A: Threshold,  B: Weighted score,  C: State machine")
    fig.tight_layout()

    fig, axs = plt.subplots(1, 3, figsize=(14, 4.3))
    for a, n in zip(axs, names):
        cm = totals[n]["confusion"]
        cmn = cm / np.maximum(cm.sum(axis=1, keepdims=True), 1)
        a.imshow(cmn, cmap="Blues", vmin=0, vmax=1)
        for i in range(3):
            for j in range(3):
                a.text(j, i, f"{cmn[i, j]:.0%}", ha="center", va="center",
                       color="white" if cmn[i, j] > .5 else "black")
        a.set_xticks(range(3)); a.set_xticklabels(STATES, fontsize=8)
        a.set_yticks(range(3)); a.set_yticklabels(STATES, fontsize=8)
        a.set_xlabel("Method said"); a.set_ylabel("Ground truth"); a.set_title(n)
    fig.suptitle("Confusion matrices: for each true state, what did each method say?")
    fig.tight_layout()


def main():
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    files = sorted(glob.glob(os.path.join(HERE, "data", "*.csv")))
    if not files:
        sys.exit("No data found in data/. Run make_synthetic_data.py first.")
    all_results = {m: [] for m in METHODS}
    summary_rows = []

    for path in files:
        name = os.path.basename(path).replace(".csv", "")
        rows = load(path)
        gt = [r["gt_state"] for r in rows]
        times = [r["time_s"] for r in rows]
        preds = {m: fn(rows) for m, (fn, _) in METHODS.items()}
        results = {m: compare_with_gt(times, gt, preds[m]) for m in METHODS}

        with open(os.path.join(HERE, "results", f"{name}_predictions.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["time_s", "ground_truth"] + [m.split(":")[0] for m in METHODS])
            for k, r in enumerate(rows):
                w.writerow([r["time_s"], gt[k]] + [preds[m][k] for m in METHODS])

        print(f"\n=== {name} ({times[-1]:.0f} s) ===")
        print(f"{'Method':20s}{'Accuracy':>9s}{'DROWSY caught':>15s}{'False alerts':>14s}"
              f"{'Delay (s)':>11s}{'State changes':>15s}")
        for m, r in results.items():
            caught = f"{r['detected']}/{r['drowsy_events']}" if r["drowsy_events"] else "none to catch"
            delay = "-" if math.isnan(r["latency_s"]) else f"{r['latency_s']:.1f}"
            print(f"{m:20s}{r['accuracy']:9.0%}{caught:>15s}{r['false_alerts']:14d}{delay:>11s}"
                  f"{r['state_changes']:15d}")
            all_results[m].append(r)
            summary_rows.append([name, m, round(r["accuracy"], 3), r["drowsy_events"], r["detected"],
                                 r["missed"], r["false_alerts"], delay, r["state_changes"]])
        plot_drive(name, rows, preds, results)

    totals = {}
    for m, rs in all_results.items():
        ev = sum(r["drowsy_events"] for r in rs)
        lat = [r["latency_s"] for r in rs if not math.isnan(r["latency_s"])]
        conf = sum(r["confusion"] for r in rs)
        totals[m] = {"accuracy": np.trace(conf) / conf.sum(),
                     "detected_pct": sum(r["detected"] for r in rs) / ev if ev else 0,
                     "false_alerts": sum(r["false_alerts"] for r in rs),
                     "latency_s": float(np.mean(lat)) if lat else 0.0,
                     "state_changes": sum(r["state_changes"] for r in rs),
                     "confusion": conf}
    plot_summary(totals)

    with open(os.path.join(HERE, "results", "summary.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["drive", "method", "accuracy", "drowsy_events", "detected", "missed",
                    "false_alerts", "avg_delay_s", "state_changes"])
        w.writerows(summary_rows)

    print("\n=== OVERALL (all drives) ===")
    for m, s in totals.items():
        print(f"{m:20s} accuracy {s['accuracy']:.0%} | DROWSY caught {s['detected_pct']:.0%} | "
              f"false alerts {s['false_alerts']} | avg delay {s['latency_s']:.1f} s | "
              f"state changes {s['state_changes']}")
    print(f"\nGraph backend: {plt.get_backend()}  ->  opening {len(plt.get_fignums())} graph windows "
          "(close them all to finish)")
    plt.show()


if __name__ == "__main__":
    main()
