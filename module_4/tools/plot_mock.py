"""Plot a mock cue stream (closure_prob, yawn_prob, pitch) with its ground-truth events,
optionally overlaid with SG-4 output (perclos, eye_closure_s).

    python module_4/tools/plot_mock.py interfaces/mocks/drowsy.jsonl --out results/drowsy_mock.png
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_sg4 import read_jsonl, run  # noqa: E402

COLORS = {"blink": "#9ecae1", "slow_blink": "#fdae6b", "long_blink": "#e6550d",
          "interrupted": "#bdbdbd", "yawn": "#74c476", "nod": "#9e9ac8", "invalid": "#d9d9d9"}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-engine", action="store_true", help="do not overlay SG-4 output")
    a = ap.parse_args(argv)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    recs = sorted(read_jsonl(a.input), key=lambda r: r["timestamp_ms"])
    gt_path = Path(a.input).with_name(Path(a.input).name.replace(".jsonl", ".gt.json"))
    gt = json.load(open(str(gt_path))) if gt_path.exists() else None
    t = [r["timestamp_ms"] / 1000.0 for r in recs]

    def series(block, key):
        return [(r.get(block) or {}).get(key) for r in recs]

    fig, axes = plt.subplots(4, 1, figsize=(12, 8), sharex=True)
    axes[0].plot(t, series("eye", "closure_prob"), lw=0.6, color="#3b6ea5")
    axes[0].axhline(0.8, ls="--", lw=0.8, color="k")
    axes[0].set_ylabel("closure_prob")
    axes[1].plot(t, series("mouth", "yawn_prob"), lw=0.6, color="#31a354")
    axes[1].set_ylabel("yawn_prob")
    axes[2].plot(t, series("head", "pitch_deg"), lw=0.6, color="#756bb1")
    axes[2].axhline(-15, ls="--", lw=0.8, color="k")
    axes[2].set_ylabel("pitch_deg")
    if gt:
        for c in gt["closures"]:
            axes[0].axvspan(c["start_ms"] / 1e3, c["end_ms"] / 1e3, color=COLORS[c["class"]], alpha=0.6, lw=0)
        for y in gt["yawns"]:
            axes[1].axvspan(y["start_ms"] / 1e3, y["end_ms"] / 1e3, color=COLORS["yawn"], alpha=0.4, lw=0)
        for n in gt["nods"]:
            axes[2].axvspan(n["start_ms"] / 1e3, n["end_ms"] / 1e3, color=COLORS["nod"], alpha=0.4, lw=0)
        for ax in axes[:3]:
            for iv in gt["invalid"]:
                ax.axvspan(iv["start_ms"] / 1e3, iv["end_ms"] / 1e3, color=COLORS["invalid"], alpha=0.7, lw=0)
    if not a.no_engine:
        _, outs = run(recs)
        to = [o["time_s"] for o in outs]
        axes[3].step(to, [o["perclos"] for o in outs], where="post", label="perclos (60 s)")
        axes[3].step(to, [o["eye_closure_s"] for o in outs], where="post", label="eye_closure_s")
        axes[3].step(to, [o["long_blinks"] for o in outs], where="post", label="long_blinks (30 s)")
        axes[3].legend(fontsize=7, loc="upper left")
    axes[3].set_ylabel("SG-4 out")
    axes[3].set_xlabel("time (s)")
    for ax in axes:
        ax.grid(alpha=0.3)
    fig.suptitle("%s  (shaded = ground truth: blue blink, orange slow, red long, grey invalid)" % Path(a.input).name,
                 fontsize=9)
    fig.tight_layout()
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(a.out, dpi=110)
    print("plot ->", a.out)


if __name__ == "__main__":
    main()
