"""Replay mock SG-4 messages through SG-5; keep the UI outside decision logic."""

import argparse
import json
import time
from pathlib import Path

from decision_logic import load_configs, make_engine
from make_mock_data import DATA_PATH


def main():
    parser = argparse.ArgumentParser(description="SG-5 Week 5 console demo")
    parser.add_argument("--config", choices=load_configs(), default="week5_stable")
    parser.add_argument("--scenario", default="progression")
    parser.add_argument("--delay", type=float, default=0, help="Display delay only; simulation uses message timestamps")
    parser.add_argument("--input", type=Path, default=DATA_PATH)
    parser.add_argument("--json", action="store_true", help="Print complete V1 output messages")
    args = parser.parse_args()
    if args.delay < 0:
        parser.error("--delay cannot be negative")
    rows = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    selected = [row for row in rows if row["scenario"] == args.scenario]
    if not selected:
        parser.error("Unknown scenario. Available: " + ", ".join(sorted({r["scenario"] for r in rows})))

    engine = make_engine(args.config)
    print(f"SG-5 | {args.config} | {args.scenario} | SIMULATED INPUTS")
    print(f"{'Time':>6}  {'Label':<9} {'Risk':>5}  {'State':<9} {'Action':<13}")
    for row in selected:
        result = engine.decide(row["input"])
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"{result['timestamp_ms'] / 1000:>5.0f}s  {row['label']:<9} {result['risk_score']:>5.3f}  {result['state']:<9} {result['alert_action']:<13}")
        if args.delay:
            time.sleep(args.delay)


if __name__ == "__main__":
    main()
