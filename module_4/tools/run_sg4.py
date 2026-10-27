"""Run SG-4 on a JSONL cue stream and write the SG-5 vector stream (10 Hz).

    python module_4/tools/run_sg4.py --input interfaces/mocks/drowsy.jsonl --output out.jsonl
    python module_4/tools/run_sg4.py --input in.jsonl --output out.jsonl --plot out.png
    python module_4/tools/run_sg4.py --input in.jsonl --output out.jsonl --approach naive

Input may be sg4.input.v1 records or SG-2's native eye records (see adapters.py).
Every output line is validated against interfaces/sg4_output_v1_1.schema.json.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from sg4.baselines_alt import EmaPerclosEngine, NaiveFrameCounter  # noqa: E402
from sg4.engine import TemporalEngine  # noqa: E402
from sg4.schema import validate_output  # noqa: E402

APPROACHES = {"primary": TemporalEngine, "naive": NaiveFrameCounter, "ema": EmaPerclosEngine}


def read_jsonl(path):
    with open(str(path), "r") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def run(records, approach="primary", keep_event_log=False):
    """Return (engine, list of output vectors). Empty input still yields one vector."""
    engine = APPROACHES[approach](keep_event_log=keep_event_log)
    outputs = [o for o in (engine.push(r) for r in records) if o is not None]
    if not outputs:
        outputs.append(engine.snapshot())
    return engine, outputs


def plot(outputs, png_path, title=""):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    t = [o["time_s"] for o in outputs]
    rows = [("perclos", "PERCLOS (0-1)"), ("eye_closure_s", "eye_closure_s"),
            ("long_blinks", "long_blinks (30 s)"), ("yawn_count", "yawn_count (60 s)"),
            ("nod_count", "nod_count (60 s)"), ("face_valid", "face_valid")]
    fig, axes = plt.subplots(len(rows), 1, figsize=(10, 9), sharex=True)
    for ax, (k, label) in zip(axes, rows):
        ax.step(t, [o[k] for o in outputs], where="post", lw=1.2, color="#3b6ea5")
        ax.set_ylabel(label, rotation=0, ha="right", va="center", fontsize=8)
        ax.grid(alpha=0.3)
    axes[-1].set_xlabel("time_s")
    fig.suptitle(title or "SG-4 output")
    fig.tight_layout()
    fig.savefig(str(png_path), dpi=110)
    plt.close(fig)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--approach", choices=sorted(APPROACHES), default="primary")
    ap.add_argument("--plot", metavar="PNG", help="save a plot of the SG-5 fields")
    ap.add_argument("--no-validate", action="store_true")
    a = ap.parse_args(argv)

    engine, outputs = run(read_jsonl(a.input), a.approach)
    errors = 0
    if not a.no_validate:
        for i, o in enumerate(outputs):
            errs = validate_output(o)
            if errs:
                errors += 1
                if errors <= 5:
                    print("line %d invalid: %s" % (i + 1, errs[0]), file=sys.stderr)
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    with open(a.output, "w") as f:
        for o in outputs:
            f.write(json.dumps(o, separators=(",", ":")) + "\n")
    stats = getattr(engine, "sync", None)
    msg = "%d vectors -> %s" % (len(outputs), a.output)
    if stats is not None:
        s = stats.stats
        msg += " | accepted %d, dropped dup %d, out-of-order %d, gaps %d" % (
            s.accepted, s.dropped_duplicate, s.dropped_out_of_order, s.gaps)
    print(msg + (" | schema: %d invalid" % errors if not a.no_validate else ""))
    if a.plot:
        plot(outputs, a.plot, "%s (%s)" % (Path(a.input).name, a.approach))
        print("plot ->", a.plot)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
