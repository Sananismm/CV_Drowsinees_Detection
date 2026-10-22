"""Compare both decision rules on exactly the same labelled mock stream."""

import argparse
import csv
import hashlib
import json
import platform
import statistics
import time
from collections import defaultdict
from pathlib import Path

from decision_logic import load_configs, make_engine, validate_input
from make_mock_data import DATA_PATH


def intervals(flags):
    """Find consecutive true samples; return inclusive start/end indices."""
    spans = []
    start = None
    for index, flag in enumerate(flags + [False]):
        if flag and start is None:
            start = index
        elif not flag and start is not None:
            spans.append((start, index - 1))
            start = None
    return spans


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def evaluate(name, grouped):
    decisions = []
    episodes = []
    timings = []
    tp = fp = fn = tn = unknown = changes = false_events = 0

    for scenario, rows in grouped.items():
        engine = make_engine(name)  # Each independent recording gets a fresh state.
        predictions = []
        truth = []
        previous_state = None
        for row in rows:
            start = time.perf_counter_ns()
            output = engine.decide(row["input"])
            timings.append((time.perf_counter_ns() - start) / 1_000_000)
            actual = row["label"] == "DROWSY"
            predicted = output["alert_action"] == "AUDIO_VISUAL"
            predictions.append(predicted)
            truth.append(actual)
            tp += int(actual and predicted)
            fp += int(not actual and predicted)
            fn += int(actual and not predicted)
            tn += int(not actual and not predicted)
            unknown += int(output["state"] == "UNKNOWN")
            changes += int(previous_state is not None and output["state"] != previous_state)
            previous_state = output["state"]
            decisions.append({
                "config": name, "scenario": scenario,
                "timestamp_ms": output["timestamp_ms"], "label": row["label"],
                "state": output["state"], "risk_score": output["risk_score"],
                "confidence": output["confidence"], "alert_action": output["alert_action"],
            })

        # A false event is an uninterrupted sound-alert interval with no
        # overlap with a labelled drowsiness episode. Recovery overhang is
        # still counted separately as false-positive samples.
        for first, last in intervals(predictions):
            false_events += int(not any(truth[first:last + 1]))
        for first, last in intervals(truth):
            detection = next((i for i in range(first, last + 1) if predictions[i]), None)
            onset = rows[first]["input"]["timestamp_ms"]
            latency = "" if detection is None else rows[detection]["input"]["timestamp_ms"] - onset
            episodes.append({
                "config": name, "scenario": scenario, "onset_ms": onset,
                "last_drowsy_sample_ms": rows[last]["input"]["timestamp_ms"],
                "detected": detection is not None, "alert_latency_ms": latency,
            })

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    latencies = [e["alert_latency_ms"] for e in episodes if e["detected"]]
    summary = {
        "config": name, "samples": len(decisions), "true_positives": tp,
        "false_positive_samples": fp, "false_negative_samples": fn,
        "true_negatives": tn, "precision": round(precision, 4),
        "recall": round(recall, 4), "f1": round(f1, 4),
        "false_alert_events": false_events, "drowsy_episodes": len(episodes),
        "detected_episodes": len(latencies), "missed_episodes": len(episodes) - len(latencies),
        "mean_alert_latency_ms": round(statistics.mean(latencies), 2) if latencies else "",
        "unknown_samples": unknown, "state_changes": changes,
        "mean_compute_ms": round(statistics.mean(timings), 4),
    }
    return summary, decisions, episodes


def make_report(summaries, episodes, input_hash):
    lines = [
        "# SG5 Week 5 comparison", "",
        "This report uses fixed, hand-labelled synthetic SG-4 messages. These results demonstrate decision logic, not accuracy on real drivers.", "",
        "Both configurations see the identical 60-second-window messages, updated once per simulated second. Each scenario starts with a fresh engine. Ground-truth labels stay outside the V1 input and are never passed to the engine.", "",
        "## Configuration comparison", "",
        "Weights and thresholds are held constant. Week 4 enters DROWSY immediately and keeps its original release behaviour. Week 5 requires 2000 ms of continuous high risk, preserves warnings through the middle band, and releases only after 5000 ms below 0.25. The study therefore isolates state-transition logic on this fixture.", "",
        "| Configuration | False alert events | Missed episodes | Sample precision | Sample recall | F1 | Mean alert delay ms | State changes |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for s in summaries:
        lines.append(f"| {s['config']} | {s['false_alert_events']} | {s['missed_episodes']} | {s['precision']:.4f} | {s['recall']:.4f} | {s['f1']:.4f} | {s['mean_alert_latency_ms']} | {s['state_changes']} |")
    lines += [
        "", "## Episode evidence", "",
        "| Configuration | Scenario | Detected | Alert delay ms |",
        "| --- | --- | --- | ---: |",
    ]
    for e in episodes:
        delay = e["alert_latency_ms"] if e["detected"] else "Missed"
        lines.append(f"| {e['config']} | {e['scenario']} | {e['detected']} | {delay} |")
    lines += [
        "", "## Failure analysis and Week 6 decision", "",
        "The original engine responds immediately to strong evidence, including an isolated erroneous spike. Near 0.65 it can repeatedly switch between CAUTION and DROWSY. It can also clear a warning in the 0.25-0.35 band even though its documented release threshold has not been met.", "",
        "The stable candidate rejects isolated spikes and avoids that chatter, but waits 2 seconds before a sound alert. It misses the deliberately short true episode and keeps sound alerts active longer during recovery. This can increase false-positive samples even while it reduces wholly false alert events. Both engines miss the weak-evidence case and abstain on the low-confidence case.", "",
        "Carry week5_stable forward as the preliminary Week 6 candidate for stability, while retaining week4_baseline as a fast-response comparator. Do not claim the candidate is more accurate for real drivers. Sweep entry delays (0, 500, 1000, 2000 ms), thresholds and weights on labelled SG-4/video recordings, separating development and held-out clips. Decide whether long eye closure needs a separate immediate escalation rule, and whether recovery should step down from DROWSY to CAUTION before ALERT. Any decision-policy change needs team review.", "",
        "## Metric definitions", "",
        "- Positive class: ground-truth DROWSY. Positive prediction: AUDIO_VISUAL. CAUTION/visual warnings are not sound alerts.",
        "- False alert event: a continuous AUDIO_VISUAL interval with no overlap with a labelled drowsiness episode.",
        "- False-positive sample: a sound alert during any non-drowsy labelled second, including delayed recovery. False-negative sample includes a missed DROWSY second and an UNKNOWN second during drowsiness.",
        "- Missed episode: no sound alert within a contiguous labelled DROWSY episode.",
        "- Alert delay: first sound-alert timestamp minus episode-onset timestamp. The mean excludes missed episodes; read the missed count alongside it.",
        "- State changes: transitions between consecutive output states within each scenario.",
        "- mean_compute_ms in summary.csv measures the Python decide call on the development PC. It is neither alert delay nor a Jetson benchmark.", "",
        "## Reproduction", "", "Run `python compare.py`. Input SHA256:", "", f"`{input_hash}`", "",
        "See run_manifest.json for configurations, interpreter version and baseline checksum. Wall-clock compute timings vary between runs; predictions and simulated alert delays do not.", "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Compare SG-5 Week 4 and Week 5 rules")
    parser.add_argument("--input", type=Path, default=DATA_PATH)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "results")
    args = parser.parse_args()
    raw = args.input.read_bytes()
    grouped = defaultdict(list)
    for line_number, line in enumerate(raw.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if row["label"] not in ("ALERT", "CAUTION", "DROWSY"):
            raise ValueError(f"unknown ground-truth label on line {line_number}")
        validate_input(row["input"])
        grouped[row["scenario"]].append(row)
    if not grouped:
        raise ValueError("no samples to evaluate")
    for scenario, rows in grouped.items():
        timestamps = [r["input"]["timestamp_ms"] for r in rows]
        if any(b - a != 1000 for a, b in zip(timestamps, timestamps[1:])):
            raise ValueError(f"{scenario}: this evaluator requires one sample per second")
        contexts = {(r["input"]["session_id"], r["input"]["driver_track_id"]) for r in rows}
        if len(contexts) != 1:
            raise ValueError(f"{scenario}: one driver/session is required")

    summaries, decisions, episodes = [], [], []
    for name in load_configs():
        summary, output_rows, episode_rows = evaluate(name, grouped)
        summaries.append(summary)
        decisions.extend(output_rows)
        episodes.extend(episode_rows)
    args.output.mkdir(parents=True, exist_ok=True)
    write_csv(args.output / "summary.csv", summaries)
    write_csv(args.output / "decisions.csv", decisions)
    if episodes:
        write_csv(args.output / "episodes.csv", episodes)
    input_hash = hashlib.sha256(raw).hexdigest()
    (args.output / "report.md").write_text(make_report(summaries, episodes, input_hash), encoding="utf-8")
    manifest = {
        "data_source": "synthetic hand-labelled SG-4 temporal messages",
        "input_sha256": input_hash, "scenario_count": len(grouped),
        "samples_per_config": sum(len(r) for r in grouped.values()),
        "python_version": platform.python_version(), "platform": platform.system(),
        "configs": load_configs(),
        "week4_baseline_sha256": hashlib.sha256((Path(__file__).parent / "week4_baseline.py").read_bytes()).hexdigest(),
    }
    (args.output / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("SG-5 Week 5 comparison - SYNTHETIC DATA")
    print(f"{'Configuration':<19} {'False events':>12} {'Missed ep.':>11} {'F1':>7} {'Alert delay':>13} {'Changes':>8}")
    for s in summaries:
        print(f"{s['config']:<19} {s['false_alert_events']:>12} {s['missed_episodes']:>11} {s['f1']:>7.3f} {str(s['mean_alert_latency_ms']) + ' ms':>13} {s['state_changes']:>8}")
    print(f"\nEvidence saved in {args.output.resolve()}")


if __name__ == "__main__":
    main()
