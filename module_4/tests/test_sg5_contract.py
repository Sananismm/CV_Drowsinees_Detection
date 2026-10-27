"""SG-5 contract test (CLAUDE.md section 5): every output on every mock scenario has
exactly the v1.1 fields with the right types and ranges, and the golden files
SG-5 develops against are what the current engine produces.
"""
import json

import pytest

import check_sg5_compat
import mock_stream
from run_sg4 import run
from sg4.paths import interfaces_dir
from sg4.schema import OUTPUT_SCHEMA_ID, validate_output
from sg4.sg5_output import EXTRA_FIELDS, SG5_FIELDS

MOCKS = interfaces_dir() / "mocks"
EXPECTED_KEYS = {"schema"} | set(SG5_FIELDS) | set(EXTRA_FIELDS)


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


@pytest.fixture(scope="module", params=mock_stream.SCENARIOS)
def outputs(request):
    records, _ = mock_stream.generate(request.param)
    return run(records)[1]


def test_sg5_fields_exact(outputs):
    prev = -1.0
    for o in outputs:
        assert set(o) == EXPECTED_KEYS
        assert o["schema"] == OUTPUT_SCHEMA_ID
        assert isinstance(o["time_s"], float) and o["time_s"] > prev
        prev = o["time_s"]
        assert isinstance(o["perclos"], float) and 0.0 <= o["perclos"] <= 1.0
        assert o["face_valid"] in (0, 1) and _is_int(o["face_valid"])
        for k in ("long_blinks", "yawn_count", "nod_count", "slow_blinks"):
            assert _is_int(o[k]) and o[k] >= 0
        assert isinstance(o["eye_closure_s"], float) and o["eye_closure_s"] >= 0.0
        if o["face_valid"] == 0:
            assert o["eye_closure_s"] == 0.0
        if o["calibrating"]:
            assert o["perclos_vs_baseline"] is None


def test_outputs_validate_against_schema(outputs):
    for o in outputs:
        assert validate_output(o) == []


def test_output_rate_is_10hz(outputs):
    span = outputs[-1]["time_s"] - outputs[0]["time_s"]
    assert len(outputs) == pytest.approx(span * 10, rel=0.02)


@pytest.mark.parametrize("scenario", mock_stream.SCENARIOS)
def test_golden_files_match_engine(scenario):
    """interfaces/mocks/sg5_expected/*.jsonl must be regenerated whenever behaviour changes."""
    with open(str(MOCKS / (scenario + ".jsonl"))) as f:
        records = [json.loads(x) for x in f]
    with open(str(MOCKS / "sg5_expected" / (scenario + ".jsonl"))) as f:
        golden = [json.loads(x) for x in f]
    assert run(records)[1] == golden


def test_mock_files_are_reproducible_from_seed():
    records, _ = mock_stream.generate("noisy")
    with open(str(MOCKS / "noisy.jsonl")) as f:
        assert [json.loads(x) for x in f] == records


def test_compat_checker_passes_golden_and_flags_bad(tmp_path):
    for s in mock_stream.SCENARIOS:
        assert check_sg5_compat.main([str(MOCKS / "sg5_expected" / (s + ".jsonl"))]) == 0
    bad = tmp_path / "bad.jsonl"
    bad.write_text(json.dumps({"schema": "sg4.output.v1.1", "time_s": 1.0, "perclos": 18.0, "face_valid": 1,
                               "long_blinks": 0, "yawn_count": 0, "eye_closure_s": 0.0, "nod_count": 0}) + "\n")
    assert check_sg5_compat.main([str(bad)]) == 1
