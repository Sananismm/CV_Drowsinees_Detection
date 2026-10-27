"""Headless fixed-data SG5 comparison with strict, versioned evaluation.

Run from the repository root: python -m module_5.midterm.evaluate --plot
Original Week 5 A/B/C functions are extracted without importing their GUI code.
No settings are selected on held-out real-driver data: these two synthetic
drives are development diagnostics, not evidence of real-world accuracy.
"""

import argparse
import ast
import csv
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
from statistics import mean
import time

import numpy as np

from .metrics import STATES, PREDICTED_STATES, evaluate_predictions


HERE = Path(__file__).resolve().parent
BASELINE_ROOT = HERE.parent / "SG5_drowsiness_decision"
FIELDS = ("time_s", "face_valid", "perclos", "eye_closure_s", "long_blinks", "yawn_count")
METHOD_LABELS = {
    "week5_A": "A threshold reference", "week5_B": "B weighted reference",
    "week5_C": "C Week 5 reference", "stable_c": "C robust midterm",
    "c_fast_recovery": "C faster recovery",
}


def load_baselines():
    """Compile only preserved constants/functions; never run imports or main."""
    path = BASELINE_ROOT / "sg5_three_methods.py"
    source = ast.parse(path.read_text(encoding="utf-8"))
    constants = {"STATES", "A_PARAMS", "B_PARAMS", "C_PARAMS", "SCORE_INPUTS", "WARMUP_S"}
    functions = {"drowsiness_score", "method_A", "method_B", "method_C"}
    nodes = [node for node in source.body
             if (isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in constants
                                                      for t in node.targets))
             or (isinstance(node, ast.FunctionDef) and node.name in functions)]
    namespace = {"np": np, "math": math, "csv": csv}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
    return {letter: namespace["method_" + letter] for letter in "ABC"}


def load_rows(path):
    """Validate the committed test representation, retaining labels separately."""
    rows = []
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if set(reader.fieldnames or []) != set(FIELDS) | {"gt_state"}:
            raise ValueError("unexpected synthetic CSV columns: " + str(path))
        for row in reader:
            if row["face_valid"] not in ("0", "1"):
                raise ValueError("face_valid must be 0 or 1")
            parsed = {name: float(row[name]) for name in ("time_s", "perclos", "eye_closure_s")}
            parsed.update(face_valid=row["face_valid"] == "1", gt_state=row["gt_state"])
            for name in ("long_blinks", "yawn_count"):
                parsed[name] = int(row[name])
                if parsed[name] < 0:
                    raise ValueError("counts cannot be negative")
            if (not all(math.isfinite(parsed[name]) and parsed[name] >= 0
                        for name in ("time_s", "perclos", "eye_closure_s"))
                    or parsed["perclos"] > 1 or parsed["gt_state"] not in STATES):
                raise ValueError("invalid value in " + str(path))
            rows.append(parsed)
    if not rows or any(b["time_s"] <= a["time_s"] for a, b in zip(rows, rows[1:])):
        raise ValueError("test rows must be nonempty with strictly increasing times")
    return rows


def input_observation(row):
    """Explicit allowlist prevents ground-truth leakage into any implementation."""
    return {name: row[name] for name in FIELDS}


def configurations():
    from .engine import CONFIGURATIONS
    stable = CONFIGURATIONS["stable_c"]
    return {"stable_c": stable,
            "c_fast_recovery": replace(stable, config_id="c_fast_recovery", enter_warn=.18,
                                       exit_warn=.12, release_s=1.5)}


def candidate_outputs(inputs, config):
    from .engine import DecisionEngine
    engine = DecisionEngine(config)
    return [engine.step(row) for row in inputs]


def run_candidate(inputs, config):
    outputs = candidate_outputs(inputs, config)
    # The retained state on unavailable observations is explicitly untrusted.
    return [out["driver_state"] if out["status"] == "OK" else "UNKNOWN" for out in outputs]


def _percentile(values, fraction):
    values = sorted(values)
    position = (len(values) - 1) * fraction
    low = int(position)
    high = min(low + 1, len(values) - 1)
    return values[low] + (values[high] - values[low]) * (position - low)


def _timing(runs_ms, rows):
    return {"clock": "time.perf_counter", "repeats": len(runs_ms),
            "scope": "whole-drive decision processing; parsing, metrics, plots and file I/O excluded",
            "run_ms": runs_ms, "mean_run_ms": mean(runs_ms),
            "p95_run_ms": _percentile(runs_ms, .95),
            "mean_amortized_ms_per_row": mean(runs_ms) / rows,
            "p95_amortized_ms_per_row": _percentile(runs_ms, .95) / rows,
            "limitation": "Batch amortized CPU timings, not per-callback p95, alert delay or Jetson measurements"}


def benchmark(function, inputs, repeats):
    # One untimed call warms interpreter paths; each call starts fresh state.
    expected = function(inputs)
    runs = []
    for _ in range(repeats):
        before = time.perf_counter()
        result = function(inputs)
        runs.append((time.perf_counter() - before) * 1000)
        if result != expected:
            raise ValueError("nondeterministic decision replay")
    return expected, _timing(runs, len(inputs))


def check_baseline_parity(path, predictions):
    saved_path = BASELINE_ROOT / "results" / (path.stem + "_predictions.csv")
    with saved_path.open(newline="", encoding="utf-8") as handle:
        saved = list(csv.DictReader(handle))
    for letter in "ABC":
        expected = [row[letter] for row in saved]
        if predictions["week5_" + letter] != expected:
            raise ValueError("original baseline parity failed: " + path.stem + "/" + letter)


def aggregate_metrics(records):
    """Pool sample counts and event delays, never average per-drive percentages."""
    total = sum(row["sample_count"] for row in records)
    counts = [[sum(row["confusion"]["counts"][i][j] for row in records)
               for j in range(4)] for i in range(3)]
    per_class = {}
    for i, state in enumerate(STATES):
        tp, support = counts[i][i], sum(counts[i])
        n_predicted = sum(row[i] for row in counts)
        precision = tp / n_predicted if n_predicted else 0.0
        recall = tp / support if support else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[state] = {"support": support, "tp": tp, "fp": n_predicted - tp,
                            "fn": support - tp, "precision": precision, "recall": recall, "f1": f1}
    keys = ("ground_truth_events", "predicted_events", "detected_events", "missed_events",
            "false_alert_events", "late_alert_events", "covered_events", "preexisting_alert_events")
    events = {key: sum(row["events"][key] for row in records) for key in keys}
    precision = events["detected_events"] / events["predicted_events"] if events["predicted_events"] else None
    recall = events["detected_events"] / events["ground_truth_events"] if events["ground_truth_events"] else None
    events.update(event_precision=precision, event_recall=recall,
                  event_f1=((2 * precision * recall / (precision + recall) if precision + recall else 0.0)
                            if precision is not None and recall is not None else None),
                  coverage=(events["covered_events"] / events["ground_truth_events"]
                            if events["ground_truth_events"] else None))
    latencies = [delay for row in records for delay in row["events"]["latencies_s"]]
    events.update(latencies_s=latencies, mean_latency_s=mean(latencies) if latencies else None)
    result = {"sample_count": total, "accuracy": sum(counts[i][i] for i in range(3)) / total,
              "macro_f1": mean(item["f1"] for item in per_class.values()), "per_class": per_class,
              "confusion": {"rows": list(STATES), "columns": list(PREDICTED_STATES), "counts": counts},
              "events": events}
    for key in ("duration_s", "false_drowsy_duration_s", "invalid_duration_s", "unknown_duration_s",
                "state_changes", "evaluated_prediction_changes", "input_availability_changes"):
        result[key] = sum(row[key] for row in records)
    for key in ("driver_state_changes", "availability_status_changes"):
        values = [row[key] for row in records]
        result[key] = sum(values) if all(value is not None for value in values) else None
    for name in ("precision", "recall", "f1"):
        result["drowsy_" + name] = per_class["DROWSY"][name]
    # Sum corresponding repeated drive timings before calculating aggregate p95.
    run_ms = [sum(run) for run in zip(*(row["processing_benchmark"]["run_ms"] for row in records))]
    result["processing_benchmark"] = _timing(run_ms, total)
    return result


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _write_summary(path, records):
    columns = ["drive", "method", "sample_count", "accuracy", "macro_f1", "drowsy_precision",
               "drowsy_recall", "drowsy_f1", "false_drowsy_duration_s", "state_changes",
               "evaluated_prediction_changes", "driver_state_changes", "availability_status_changes",
               "input_availability_changes",
               "invalid_duration_s", "unknown_duration_s", "ground_truth_events", "detected_events",
               "missed_events", "false_alert_events", "late_alert_events", "covered_events",
               "preexisting_alert_events", "mean_latency_s", "mean_amortized_ms_per_row",
               "p95_amortized_ms_per_row"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for record in records:
            flat = dict(record, **record["events"], **record["processing_benchmark"])
            writer.writerow({key: flat.get(key) for key in columns})


def save_plots(output, traces, overall):
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt
    color = {"week5_A": "#d95f02", "week5_B": "#7570b3", "week5_C": "#1b9e77",
             "stable_c": "#2463a0", "c_fast_recovery": "#a6528f"}
    state_number = {name: i for i, name in enumerate(STATES)} | {"UNKNOWN": -1}
    for drive, trace in traces.items():
        fig, axes = plt.subplots(6, 1, figsize=(12, 11), sharex=True)
        gt = [state_number[state] for state in trace["truth"]]
        axes[0].step(trace["times"], gt, where="post", color="black")
        axes[0].set_title("Synthetic reference labels", loc="left", fontsize=10)
        for axis, (method, predictions) in zip(axes[1:], trace["predictions"].items()):
            values = [state_number[state] for state in predictions]
            axis.step(trace["times"], gt, where="post", color="black", linestyle="--", alpha=.4)
            axis.step(trace["times"], values, where="post", color=color[method])
            axis.set_title(METHOD_LABELS[method], loc="left", fontsize=10)
        for axis in axes:
            axis.set_yticks([-1, 0, 1, 2], ["UNKNOWN", "NORMAL", "WARNING", "DROWSY"], fontsize=8)
            axis.set_ylim(-1.2, 2.2)
            axis.grid(alpha=.2)
        axes[-1].set_xlabel("Source time (seconds)")
        fig.suptitle(drive + " | same inputs for all five configurations")
        fig.tight_layout()
        fig.savefig(output / (drive + "_timeline.png"), dpi=160)
        plt.close(fig)

    panels = [("macro_f1", "Sample macro F1"), ("drowsy_recall", "DROWSY sample recall"),
              ("false_drowsy_duration_s", "False DROWSY duration (s)"),
              ("driver_state_changes", "Native driver-state changes"), ("latency", "Strict event delay (s)")]
    fig, axes = plt.subplots(1, 5, figsize=(16, 4.5))
    for axis, (key, title) in zip(axes, panels):
        values = [row["events"]["mean_latency_s"] if key == "latency" else row[key] for row in overall]
        bars = axis.bar(range(len(overall)), [v if v is not None else 0 for v in values],
                        color=[color[row["method"]] for row in overall])
        axis.bar_label(bars, labels=["n/a" if v is None else f"{v:.2f}" for v in values], fontsize=8)
        axis.set_xticks(range(len(overall)), [row["method"] for row in overall], rotation=70, fontsize=8)
        axis.set_title(title, fontsize=10)
        axis.margins(y=.2)
        axis.grid(axis="y", alpha=.2)
    fig.suptitle("Development-only synthetic comparison | no real-driver accuracy claim")
    fig.tight_layout()
    fig.savefig(output / "overall_comparison.png", dpi=160)
    plt.close(fig)

    fig, axes = plt.subplots(2, 3, figsize=(13, 8))
    for axis, record in zip(axes.flat, overall):
        counts = np.asarray(record["confusion"]["counts"])
        normalized = counts / np.maximum(counts.sum(axis=1, keepdims=True), 1)
        axis.imshow(normalized, vmin=0, vmax=1, cmap="Blues")
        for i in range(3):
            for j in range(4):
                axis.text(j, i, f"{counts[i,j]}\n{normalized[i,j]:.0%}", ha="center", va="center",
                          fontsize=8, color="white" if normalized[i,j] > .5 else "black")
        axis.set_xticks(range(4), PREDICTED_STATES, rotation=30, fontsize=8)
        axis.set_yticks(range(3), STATES, fontsize=8)
        axis.set_title(METHOD_LABELS[record["method"]], fontsize=10)
        axis.set_xlabel("Predicted"); axis.set_ylabel("Synthetic reference")
    axes.flat[-1].axis("off")
    fig.suptitle("Pooled confusion matrices | UNKNOWN retained as an error")
    fig.tight_layout()
    fig.savefig(output / "confusion_matrices.png", dpi=160)
    plt.close(fig)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "results" / "evaluation")
    parser.add_argument("--plot", action="store_true", help="Save PNGs with the headless Agg backend")
    parser.add_argument("--repeats", type=int, default=3, help="Whole-drive CPU timing repeats (default 3)")
    args = parser.parse_args(argv)
    if not 1 <= args.repeats <= 100:
        parser.error("--repeats must be between 1 and 100")
    baseline = load_baselines()
    configs = configurations()
    runners = {"week5_" + letter: fn for letter, fn in baseline.items()}
    runners.update({name: (lambda inputs, config=config: run_candidate(inputs, config))
                    for name, config in configs.items()})
    records, traces, files = [], {}, []
    args.output.mkdir(parents=True, exist_ok=True)
    for filename in ("drive1_synthetic.csv", "drive2_synthetic.csv"):
        path = BASELINE_ROOT / "data" / filename
        rows = load_rows(path)
        inputs = [input_observation(row) for row in rows]
        truth = [row["gt_state"] for row in rows]
        times = [row["time_s"] for row in rows]
        predictions = {}
        for name, runner in runners.items():
            predicted, timing = benchmark(runner, inputs, args.repeats)
            outputs = candidate_outputs(inputs, configs[name]) if name in configs else None
            metrics = evaluate_predictions(times, truth, predicted,
                valid=[row["face_valid"] for row in rows],
                driver_states=[out["driver_state"] for out in outputs] if outputs is not None else predicted,
                statuses=[out["status"] for out in outputs] if outputs is not None else None)
            record = dict(metrics, drive=path.stem, method=name, processing_benchmark=timing)
            records.append(record)
            predictions[name] = predicted
        check_baseline_parity(path, predictions)
        files.append({"name": filename, "sha256": _sha256(path), "rows": len(rows),
                      "duration_s": records[-1]["duration_s"]})
        traces[path.stem] = {"times": times, "truth": truth, "predictions": predictions}
        with (args.output / (path.stem + "_predictions.csv")).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["time_s", "ground_truth", "input_valid"] + list(runners))
            writer.writerows([t, g, int(row["face_valid"])] + [predictions[name][i] for name in runners]
                             for i, (t, g, row) in enumerate(zip(times, truth, rows)))
    overall = [dict(aggregate_metrics([row for row in records if row["method"] == name]),
                    method=name, drive="OVERALL") for name in runners]
    document = {
        "schema_version": "sg5.evaluation.v2", "created_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": {"kind": "synthetic development data", "files": files,
                    "total_rows": sum(item["rows"] for item in files),
                    "ground_truth": "Simulator reference labels; not independent real-driver annotations"},
        "protocol": {"sample_classes": list(STATES), "prediction_classes": list(PREDICTED_STATES),
                     "macro_f1": "Unweighted mean of three target-class F1 values; undefined class P/R becomes zero",
                     "unknown": "Unusable engine status is scored UNKNOWN, remains an error in all denominators",
                     "strict_detection": "One-to-one new predicted DROWSY onset inside a labelled half-open interval",
                     "coverage": "Any DROWSY interval overlap; preexisting alerts reported separately, no negative latency",
                     "false_events": "All predicted DROWSY onsets not strictly matched; late alerts remain false",
                     "late_alerts": "Unmatched onset within five seconds after an unmatched labelled episode; diagnostic only",
                     "duration": "Left-constant source intervals; final interval is median positive source dt",
                     "state_changes": "state_changes/evaluated_prediction_changes include UNKNOWN abstention transitions; driver_state_changes counts native state changes; availability_status_changes is null for legacy methods without status outputs",
                     "legacy_comparison": "Original decision functions are unchanged; strict one-to-one onset scoring intentionally differs from the old overlap plus five-second grace, so event-count changes are metric changes, not algorithm changes",
                     "latency": "Nonnegative onset delay, pooled over strictly matched episodes only; null if none",
                     "fairness": "Identical six-field input rows; labels are allowlist-excluded from every engine call",
                     "selection": "Development comparison, not an independent held-out or real-video accuracy estimate"},
        "implementations": {"baseline_source": str((BASELINE_ROOT / "sg5_three_methods.py").relative_to(HERE.parents[1])),
                            "baseline_sha256": _sha256(BASELINE_ROOT / "sg5_three_methods.py"),
                            "engine_sha256": _sha256(HERE / "engine.py"),
                            "candidate_configurations": {name: asdict(config) for name, config in configs.items()}},
        "environment": {"python": platform.python_version(), "numpy": np.__version__,
                        "system": platform.system(), "architecture": platform.machine(),
                        "timing_scope": "Local CPU decision processing only; Jetson FPS/memory not measured"},
        "baseline_parity": {"status": "PASS", "drive_method_comparisons": 6,
                            "row_predictions_checked": sum(item["rows"] for item in files) * 3},
        "results": records, "overall": overall,
    }
    (args.output / "evaluation.json").write_text(json.dumps(document, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    _write_summary(args.output / "summary.csv", records + overall)
    if args.plot:
        save_plots(args.output, traces, overall)
    print(f"SG5 fixed-data evaluation: {len(runners)} configurations, {len(files)} synthetic drives, "
          f"{sum(item['rows'] for item in files)} rows")
    print("Original A/B/C parity: PASS; strict onset matching; no five-second detection grace")
    for row in overall:
        events = row["events"]
        delay = "n/a" if events["mean_latency_s"] is None else f"{events['mean_latency_s']:.2f}s"
        print(f"{row['method']:17s} accuracy={row['accuracy']:.3f} macroF1={row['macro_f1']:.3f} "
              f"caught={events['detected_events']}/{events['ground_truth_events']} "
              f"false_onsets={events['false_alert_events']} false_duration={row['false_drowsy_duration_s']:.1f}s "
              f"changes={row['state_changes']} delay={delay}")
    print("Evidence saved to:", args.output.resolve())
    print("Synthetic development diagnostics only; CPU timings are not Jetson benchmarks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
