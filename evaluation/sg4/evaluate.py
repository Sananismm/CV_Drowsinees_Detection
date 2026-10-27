"""SG-4 evaluation: engine output vs mock ground truth, primary vs backup approaches.

    python evaluation/sg4/evaluate.py                # committed mock scenarios (default seeds)
    python evaluation/sg4/evaluate.py --seeds 10     # 10 seeds per scenario, aggregated

Writes module_4/results/metrics[_<n>seeds].md and .csv. Every number in the
README / experiments log comes from here.

Metrics (all from timestamps, at the 10 Hz outputs):
  perclos_err_pts   |perclos - GT| x 100 on outputs with a full 60 s window (mean / max)
  blink_rate_err    |blink_rate_bpm - GT| on full-window outputs (mean)
  ms_recall/prec    microsleep (long blink) events matched to GT by overlap
  closure_err_ms    |eye_closure_s - GT ongoing closure| over all outputs (mean)
  yawn_err          |yawn_count - GT| on full-window outputs (mean)
  lag_s             time from GT microsleep end until eye_closure_s returns to 0 (max)
  false_alerts      onsets of a PROXY SG-5 alert rule with no GT alert within +-1 s
                    (rule: eye_closure_s >= 1.0 or perclos >= 0.15 or long_blinks >= 3).
                    The proxy rule is ours, for ablation only; SG-5 owns the real decision.
"""
import argparse
import csv
import sys
from pathlib import Path

import numpy as np

_here = Path(__file__).resolve()
MODULE = _here.parents[2] / "module_4"
sys.path.insert(0, str(MODULE / "src"))
sys.path.insert(0, str(MODULE / "tools"))

import mock_stream  # noqa: E402
from run_sg4 import run  # noqa: E402
from sg4.config import load_config  # noqa: E402

APPROACHES = ("primary", "ema", "naive")
ALERT = {"eye_closure_s": 1.0, "perclos": 0.15, "long_blinks": 3}


def _alert(eye_closure_s, perclos, long_blinks):
    return (eye_closure_s >= ALERT["eye_closure_s"] or perclos >= ALERT["perclos"]
            or long_blinks >= ALERT["long_blinks"])


class GroundTruth:
    """1 ms resolution truth arrays with prefix sums for O(1) window queries."""

    def __init__(self, gt, cfg):
        self.gt, self.cfg = gt, cfg
        D = gt["duration_ms"] + 1
        valid = np.ones(D, dtype=np.int64)
        for iv in gt["invalid"]:
            valid[iv["start_ms"]:iv["end_ms"]] = 0
        closed = np.zeros(D, dtype=np.int64)
        for c in gt["closures"]:
            closed[c["start_ms"]:c["end_ms"]] = 1
        self.valid_cum = np.concatenate([[0], np.cumsum(valid)])
        self.closed_cum = np.concatenate([[0], np.cumsum(closed * valid)])
        self.D = D
        self.long = [c for c in gt["closures"] if c["class"] == "long_blink"]
        self.blinks = [c for c in gt["closures"] if c["class"] in ("blink", "slow_blink")]
        self.valid_closures = [c for c in gt["closures"] if c["class"] != "interrupted"]

    def _win(self, cum, t_ms, length_ms):
        a, b = max(0, t_ms - length_ms), min(self.D, t_ms)
        return int(cum[b] - cum[a])

    def perclos(self, t_ms):
        v = self._win(self.valid_cum, t_ms, int(self.cfg.perclos_window_s * 1000))
        return self._win(self.closed_cum, t_ms, int(self.cfg.perclos_window_s * 1000)) / v if v else 0.0

    def blink_rate(self, t_ms):
        L = int(self.cfg.blink_window_s * 1000)
        n = sum(1 for c in self.blinks if t_ms - L < c["end_ms"] <= t_ms)
        v = self._win(self.valid_cum, t_ms, L)
        return n * 60000.0 / v if v else 0.0

    def long_blinks(self, t_ms):
        L, m = int(self.cfg.long_blink_window_s * 1000), self.cfg.long_blink_ms
        return sum(1 for c in self.long if t_ms - L < c["start_ms"] + m <= t_ms)

    def yawns(self, t_ms):
        L, m = int(self.cfg.yawn_window_s * 1000), self.cfg.min_yawn_ms
        return sum(1 for y in self.gt["yawns"] if t_ms - L < y["start_ms"] + m <= t_ms)

    def closure_s(self, t_ms):
        for c in self.gt["closures"]:
            if c["start_ms"] <= t_ms < c["end_ms"]:
                for iv in self.gt["invalid"]:
                    if iv["start_ms"] <= t_ms < iv["end_ms"]:
                        return 0.0
                return (t_ms - c["start_ms"]) / 1000.0
        return 0.0


def _overlap(a, b):
    return a["start_ms"] < b["end_ms"] and b["start_ms"] < a["end_ms"]


def evaluate(records, gt, approach, cfg):
    engine, outs = run(records, approach, keep_event_log=True)
    T = GroundTruth(gt, cfg)
    full = [o for o in outs if o["time_s"] >= cfg.perclos_window_s]
    tms = lambda o: int(round(o["time_s"] * 1000))  # noqa: E731

    perclos_err = [abs(o["perclos"] - T.perclos(tms(o))) * 100 for o in full]
    blink_err = [abs(o["blink_rate_bpm"] - T.blink_rate(tms(o))) for o in full] if approach != "naive" else []
    yawn_err = [abs(o["yawn_count"] - T.yawns(tms(o))) for o in full]
    closure_err = [abs(o["eye_closure_s"] - T.closure_s(tms(o))) * 1000 for o in outs]

    pred = [e for e in engine.event_log if e["kind"] == "long_blink"]
    hit_gt = sum(1 for g in T.long if any(_overlap(g, p) for p in pred))
    hit_pred = sum(1 for p in pred if any(_overlap(g, p) for g in T.long))

    lags = []
    for g in T.long:
        after = [o for o in outs if tms(o) >= g["end_ms"] and o["eye_closure_s"] == 0.0]
        if after:
            lags.append(after[0]["time_s"] - g["end_ms"] / 1000.0)

    gt_alert = [_alert(T.closure_s(tms(o)), T.perclos(tms(o)), T.long_blinks(tms(o))) for o in outs]
    fa, prev = 0, False
    for i, o in enumerate(outs):
        a = _alert(o["eye_closure_s"], o["perclos"], o["long_blinks"])
        if a and not prev:
            lo, hi = max(0, i - 10), min(len(outs), i + 11)
            if not any(gt_alert[lo:hi]):
                fa += 1
        prev = a
    hours = gt["duration_ms"] / 3.6e6

    def mean(x):
        return float(np.mean(x)) if x else float("nan")

    return {
        "perclos_err_mean": mean(perclos_err), "perclos_err_max": max(perclos_err) if perclos_err else float("nan"),
        "blink_rate_err": mean(blink_err), "yawn_err": mean(yawn_err),
        "closure_err_ms": mean(closure_err),
        "ms_gt": len(T.long), "ms_pred": len(pred), "ms_hit_gt": hit_gt, "ms_hit_pred": hit_pred,
        "lag_max_s": max(lags) if lags else float("nan"),
        "false_alerts": fa, "hours": hours,
    }


def plot_ablation(out_dir, scenario="face_lost"):
    """Primary vs naive on one scenario: what SG-5 would see (eye_closure_s, perclos)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    records, gt = mock_stream.generate(scenario)
    fig, axes = plt.subplots(2, 1, figsize=(11, 5), sharex=True)
    for name, color in (("naive", "#d62728"), ("primary", "#1f77b4")):
        outs = run(records, name)[1]
        t = [o["time_s"] for o in outs]
        axes[0].step(t, [o["eye_closure_s"] for o in outs], where="post", color=color, label=name)
        axes[1].step(t, [o["perclos"] for o in outs], where="post", color=color, label=name)
    for ax in axes:
        for iv in gt["invalid"]:
            ax.axvspan(iv["start_ms"] / 1e3, iv["end_ms"] / 1e3, color="#d9d9d9", alpha=0.8, lw=0)
        ax.grid(alpha=0.3)
    axes[0].axhline(ALERT["eye_closure_s"], ls="--", color="k", lw=0.8)
    axes[0].set_ylabel("eye_closure_s")
    axes[1].set_ylabel("perclos")
    axes[1].set_xlabel("time (s)   grey = face lost / low confidence (ground truth)")
    axes[0].legend(fontsize=8)
    fig.suptitle("Ablation on '%s': naive frame counter vs SG-4 temporal engine" % scenario)
    fig.tight_layout()
    path = Path(out_dir) / ("ablation_%s.png" % scenario)
    fig.savefig(str(path), dpi=110)
    plt.close(fig)
    return path


def _fmt(x, nd=2):
    return "-" if x != x else ("%.*f" % (nd, x))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seeds", type=int, default=0, help="0 = committed mocks; N = seeds 100..100+N-1 per scenario")
    ap.add_argument("--out", default=str(MODULE / "results"))
    ap.add_argument("--plots", action="store_true", help="also write results/ablation_face_lost.png")
    a = ap.parse_args(argv)
    cfg = load_config()
    seeds = [None] if a.seeds == 0 else list(range(100, 100 + a.seeds))

    rows = []
    for sc in mock_stream.SCENARIOS:
        for ap_name in APPROACHES:
            agg = []
            for seed in seeds:
                records, gt = mock_stream.generate(sc, seed)
                agg.append(evaluate(records, gt, ap_name, cfg))
            r = {"scenario": sc, "approach": ap_name}
            for k in ("perclos_err_mean", "perclos_err_max", "blink_rate_err", "yawn_err", "closure_err_ms",
                      "lag_max_s"):
                vals = [x[k] for x in agg if x[k] == x[k]]
                r[k] = (max(vals) if k.endswith("max") or k.startswith("lag") else float(np.mean(vals))) if vals \
                    else float("nan")
            for k in ("ms_gt", "ms_pred", "ms_hit_gt", "ms_hit_pred", "false_alerts", "hours"):
                r[k] = sum(x[k] for x in agg)
            rows.append(r)

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    tag = "" if a.seeds == 0 else "_%dseeds" % a.seeds
    with open(str(out / ("metrics%s.csv" % tag)), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    lines = ["# SG-4 metrics on mock streams (%s)" % ("committed mocks" if a.seeds == 0 else "%d seeds" % a.seeds),
             "", "Generated by `python evaluation/sg4/evaluate.py%s`. Synthetic data, not real video." % (
                 " --seeds %d" % a.seeds if a.seeds else ""), "",
             "| scenario | approach | PERCLOS err pts (mean / max) | blink-rate err bpm | microsleep recall | "
             "microsleep precision | eye_closure_s err ms | yawn err | lag after microsleep s (max) | "
             "false alerts (proxy) | false alerts / h |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        rec = r["ms_hit_gt"] / r["ms_gt"] if r["ms_gt"] else float("nan")
        prec = r["ms_hit_pred"] / r["ms_pred"] if r["ms_pred"] else float("nan")
        lines.append("| %s | %s | %s / %s | %s | %s | %s | %s | %s | %s | %d | %.0f |" % (
            r["scenario"], r["approach"], _fmt(r["perclos_err_mean"]), _fmt(r["perclos_err_max"]),
            _fmt(r["blink_rate_err"]), "-" if rec != rec else "%d/%d" % (r["ms_hit_gt"], r["ms_gt"]),
            "-" if prec != prec else "%d/%d" % (r["ms_hit_pred"], r["ms_pred"]),
            _fmt(r["closure_err_ms"], 0), _fmt(r["yawn_err"]), _fmt(r["lag_max_s"]),
            r["false_alerts"], r["false_alerts"] / r["hours"]))

    lines += ["", "## Totals vs targets", "",
              "| approach | PERCLOS err pts (mean of scenarios / worst) | microsleep recall | microsleep precision | "
              "blink-rate err bpm | lag s (max) | false alerts / h |", "|---|---|---|---|---|---|---|"]
    for ap_name in APPROACHES:
        rs = [r for r in rows if r["approach"] == ap_name]
        g, hg = sum(r["ms_gt"] for r in rs), sum(r["ms_hit_gt"] for r in rs)
        p, hp = sum(r["ms_pred"] for r in rs), sum(r["ms_hit_pred"] for r in rs)
        br = [r["blink_rate_err"] for r in rs if r["blink_rate_err"] == r["blink_rate_err"]]
        lag = [r["lag_max_s"] for r in rs if r["lag_max_s"] == r["lag_max_s"]]
        lines.append("| %s | %s / %s | %s | %s | %s | %s | %.0f |" % (
            ap_name, _fmt(np.mean([r["perclos_err_mean"] for r in rs])), _fmt(max(r["perclos_err_max"] for r in rs)),
            "%.0f%% (%d/%d)" % (100.0 * hg / g, hg, g) if g else "-",
            "%.0f%% (%d/%d)" % (100.0 * hp / p, hp, p) if p else "-",
            _fmt(float(np.mean(br))) if br else "-", _fmt(max(lag)) if lag else "-",
            sum(r["false_alerts"] for r in rs) / sum(r["hours"] for r in rs)))
    lines += ["", "Targets: PERCLOS err < 5 pts, microsleep recall >= 90%, blink-rate err < 2 bpm, lag <= 1 s.",
              "Naive approach has no blink-rate output (shown as -). False alerts/h extrapolate from %.1f min "
              "of data per approach; treat them as relative, not absolute." % (sum(
                  r["hours"] for r in rows if r["approach"] == "primary") * 60)]
    (out / ("metrics%s.md" % tag)).write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    if a.plots:
        print("plot ->", plot_ablation(out))


if __name__ == "__main__":
    main()
