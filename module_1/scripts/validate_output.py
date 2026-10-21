"""Validate SG-1 JSON or JSONL output against the V1 contract."""

import argparse
import json
from pathlib import Path

from sg1_contract import ContractValidationError, validate_sg1_record


def load_records(path):
    if path.suffix.lower() == ".jsonl":
        with path.open(encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, start=1):
                if line.strip():
                    yield line_number, json.loads(line)
        return
    yield 1, json.loads(path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description="Validate SG-1 V1 output.")
    parser.add_argument("path", type=Path)
    args = parser.parse_args()

    checked = 0
    failures = []
    for line_number, record in load_records(args.path):
        checked += 1
        try:
            validate_sg1_record(record)
        except ContractValidationError as error:
            failures.append(f"record {line_number}: {error}")

    if failures:
        raise SystemExit("\n".join(failures))
    print(f"Validated {checked} SG-1 V1 record(s): PASS")


if __name__ == "__main__":
    main()
