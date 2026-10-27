"""Backup approaches produce the same contract and show the expected weaknesses."""
import mock_stream
from run_sg4 import run
from sg4.schema import validate_output


def test_naive_counts_looking_away_as_microsleep():
    records, _ = mock_stream.generate("face_lost")
    naive = run(records, "naive")[1]
    primary = run(records, "primary")[1]
    assert max(o["long_blinks"] for o in naive) > 0           # face lost -> "closed" frames
    assert max(o["long_blinks"] for o in primary) == 0
    assert max(o["eye_closure_s"] for o in naive) >= 3.0      # would fire SG-5's micro-sleep override


def test_alternatives_emit_valid_contract():
    records, _ = mock_stream.generate("drowsy")
    for approach in ("naive", "ema"):
        outs = run(records, approach)[1]
        assert all(validate_output(o) == [] for o in outs)
        assert all(0.0 <= o["perclos"] <= 1.0 for o in outs)
