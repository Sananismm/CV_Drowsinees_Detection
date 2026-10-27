"""Replay actual SG4 source and publish status-aware SG6 decisions, headlessly."""

import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import time

from .engine import CONFIGURATIONS, DecisionEngine
from .sg4_bridge import iter_temporal


ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = ("alert", "drowsy", "face_lost", "noisy", "yawns_nods")


def records(path):
    with Path(path).open(encoding="utf-8") as stream:
        for line_no, line in enumerate(stream, 1):
            if line.strip():
                try:
                    yield json.loads(line)
                except ValueError as exc:
                    raise ValueError("Invalid JSON on line %d of %s" % (line_no, path)) from exc


def replay(source, output, *, config_name="stable_c", session_id="midterm-demo"):
    source, output = Path(source), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    config = CONFIGURATIONS[config_name]
    engine = DecisionEngine(config, session_id=session_id)
    states, statuses, transitions = Counter(), Counter(), []
    previous = None
    count = 0
    begin = time.perf_counter()
    with (output / "sg4_stream.jsonl").open("w", encoding="utf-8") as upstream, (output / "sg6_stream.jsonl").open("w", encoding="utf-8") as downstream:
        # SG4's own confidence-gated mocks exercise its actual implementation,
        # not precomputed SG5 rows or our standalone decision simulator.
        for row in iter_temporal(records(source), annotate_eye_valid=True):
            decision = engine.step(row)
            upstream.write(json.dumps(row, allow_nan=False) + "\n")
            downstream.write(json.dumps(decision, allow_nan=False) + "\n")
            count += 1
            states[decision["driver_state"]] += 1
            statuses[decision["status"]] += 1
            signature = decision["driver_state"], decision["status"]
            if signature != previous:
                item = {k: decision[k] for k in ("time_s", "driver_state", "status", "reason")}
                transitions.append(item)
                print("%7.3fs  %-7s  %-21s  %s" % (row["time_s"], *signature, decision["reason"]))
                previous = signature
    summary = {
        "evidence_kind": "real_SG4_implementation_on_synthetic_frame_cues",
        "input_file": source.relative_to(ROOT).as_posix() if source.is_relative_to(ROOT) else str(source),
        "input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "sg4_vectors": count, "states": dict(states), "statuses": dict(statuses),
        "transitions": transitions, "processing_wall_seconds": time.perf_counter() - begin,
        "config": asdict(config),
        "note": "SG4 is real code; frame cues are synthetic. No real-driver accuracy or Jetson execution is claimed.",
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print("\nWrote %d SG6 decisions to %s" % (count, output / "sg6_stream.jsonl"))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=SCENARIOS, default="drowsy")
    parser.add_argument("--sg4-input", help="alternative native sg4.input.v1 JSONL")
    parser.add_argument("--output")
    parser.add_argument("--config", choices=tuple(CONFIGURATIONS), default="stable_c")
    args = parser.parse_args()
    source = Path(args.sg4_input).resolve() if args.sg4_input else ROOT / "interfaces/mocks" / (args.scenario + ".jsonl")
    destination = Path(args.output).resolve() if args.output else ROOT / "module_5/midterm/results" / ("demo_" + args.scenario)
    replay(source, destination, config_name=args.config, session_id="mock-" + args.scenario)


if __name__ == "__main__":
    main()
