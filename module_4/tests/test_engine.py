"""Engine behaviour tests, including the required cases from the kickoff (Phase 3.5).

Most streams use a 40 ms frame step (25 FPS) so expected values are exact.
"""
import pytest

from conftest import rec, run_frames, stream
from sg4.engine import TemporalEngine
from sg4.schema import validate_output


def closure(t_start, dur_ms, step=40, **kw):
    return stream(t_start, t_start + dur_ms, step, closure=0.95, **kw)


def test_long_blink_0p7s_counts_and_live_closure_rises_then_resets():
    e = TemporalEngine()
    frames = stream(0, 5000) + closure(5000, 700) + stream(5700, 7000)
    outs = run_frames(e, frames)
    during = [o for o in outs if 5000 <= o["time_s"] * 1000 < 5700]
    assert max(o["eye_closure_s"] for o in during) == pytest.approx(0.6, abs=0.05)
    partial = TemporalEngine()
    run_frames(partial, stream(0, 5000) + closure(5000, 700))
    assert partial.snapshot()["eye_closure_s"] == pytest.approx(0.68)   # live value at the last closed frame (5680 ms)
    after = [o for o in outs if o["time_s"] * 1000 >= 5700]
    assert after[0]["eye_closure_s"] == 0.0
    assert after[-1]["long_blinks"] == 1
    assert after[-1]["longest_closure_s"] == pytest.approx(0.7)
    # Counted the moment the closure reaches 0.5 s, not after it ends
    first = next(o for o in outs if o["long_blinks"] == 1)
    assert 5.5 <= first["time_s"] <= 5.6


def test_slow_blink_0p45s_is_slow_not_long():
    e = TemporalEngine()
    outs = run_frames(e, stream(0, 5000) + closure(5000, 440) + stream(5440, 7000))
    assert outs[-1]["slow_blinks"] == 1
    assert outs[-1]["long_blinks"] == 0
    assert outs[-1]["mean_blink_ms"] == 440


def test_one_yawn_of_90_frames_is_one_event():
    e = TemporalEngine()
    frames = [rec(t, yawn=0.9) for t in range(5000, 5000 + 90 * 33, 33)]
    outs = run_frames(e, stream(0, 5000) + frames + stream(8000, 10000))
    assert outs[-1]["yawn_count"] == 1


def test_short_mouth_openings_merged_or_ignored():
    e = TemporalEngine()
    talk = stream(5000, 5500, yawn=0.7) + stream(5500, 6000) + stream(6000, 6400, yawn=0.7)
    yawn_a = stream(10000, 12000, yawn=0.9)
    gap = stream(12000, 12600)                                # < 1 s -> same yawn
    yawn_b = stream(12600, 14000, yawn=0.9)
    outs = run_frames(e, stream(0, 5000) + talk + stream(6400, 10000) + yawn_a + gap + yawn_b + stream(14000, 16000))
    assert outs[-1]["yawn_count"] == 1


def test_face_lost_mid_closure():
    e = TemporalEngine()
    outs = run_frames(e, stream(0, 10000) + closure(10000, 320) + stream(10320, 15320, face=False)
                      + stream(15320, 16000))
    lost = [o for o in outs if 10320 <= o["time_s"] * 1000 < 15320]
    assert lost and all(o["face_valid"] == 0 and o["eye_closure_s"] == 0.0 for o in lost)
    # PERCLOS over valid time only: 320 ms closed / (9960 open + 320 closed) ms
    assert lost[-1]["perclos"] == pytest.approx(320 / 10280.0, abs=1e-4)
    assert lost[-1]["long_blinks"] == 0                     # unknown true length -> not a microsleep


def test_low_confidence_face_is_invalid_not_closed():
    e = TemporalEngine()
    outs = run_frames(e, stream(0, 5000) + stream(5000, 8000, closure=0.99, face_conf=0.2))
    assert outs[-1]["face_valid"] == 0
    assert outs[-1]["perclos"] == 0.0
    assert outs[-1]["long_blinks"] == 0


def test_long_blink_older_than_30s_drops_out():
    e = TemporalEngine()
    outs = run_frames(e, stream(0, 2000) + closure(2000, 800) + stream(2800, 40000))
    by_t = {round(o["time_s"], 1): o for o in outs}
    assert by_t[30.0]["long_blinks"] == 1                   # counted at 2.5 s, still inside (0.0, 30.0]
    assert by_t[33.0]["long_blinks"] == 0
    assert by_t[33.0]["perclos"] > 0                        # perclos window is 60 s


def test_perclos_always_in_unit_range():
    import numpy as np
    rng = np.random.default_rng(0)
    e = TemporalEngine()
    frames = [rec(t, closure=float(rng.random()), face=bool(rng.random() > 0.1)) for t in range(0, 70000, 33)]
    for o in run_frames(e, frames):
        assert 0.0 <= o["perclos"] <= 1.0
        assert 0.0 <= o["validity_score"] <= 1.0


def test_empty_input_still_yields_valid_vector():
    v = TemporalEngine().snapshot()
    assert validate_output(v) == []
    assert v["face_valid"] == 0 and v["validity_score"] == 0.0 and v["eye_closure_s"] == 0.0
    assert v["long_blinks"] == v["yawn_count"] == v["nod_count"] == 0


def test_output_rate_10hz_and_time_s_is_latest_timestamp():
    e = TemporalEngine()
    outs = run_frames(e, stream(0, 3000, step=33))
    assert len(outs) == 30
    assert outs[0]["time_s"] == 0.0
    assert all(round(o["time_s"] * 1000) % 33 == 0 for o in outs)  # each is a real frame timestamp
    assert all(b["time_s"] > a["time_s"] for a, b in zip(outs, outs[1:]))


def test_nod_and_head_drop_that_loses_face():
    e = TemporalEngine()
    nod = stream(5000, 5600, pitch=-25.0)
    drop = stream(10000, 10400, pitch=-13.0) + stream(10400, 12000, face=False)
    outs = run_frames(e, stream(0, 5000) + nod + stream(5600, 10000) + drop + stream(12000, 13000))
    assert outs[-1]["nod_count"] == 2
    assert outs[-1]["head_down_s"] == pytest.approx(0.6)


def test_looking_away_is_not_a_nod_or_closure():
    e = TemporalEngine()
    outs = run_frames(e, stream(0, 5000) + stream(5000, 9000, face=False) + stream(9000, 10000))
    assert outs[-1]["nod_count"] == 0 and outs[-1]["long_blinks"] == 0
    assert outs[-1]["face_absent_s"] == pytest.approx(4.0)


def test_calibration_and_baseline():
    e = TemporalEngine()
    outs = run_frames(e, stream(0, 70000))
    assert outs[0]["calibrating"] is True and outs[0]["perclos_vs_baseline"] is None
    assert outs[-1]["calibrating"] is False
    assert outs[-1]["trend"] == "stable"
    assert outs[-1]["perclos_vs_baseline"] == 0.0


def test_out_of_order_and_duplicate_frames_are_dropped():
    e = TemporalEngine()
    run_frames(e, [rec(0), rec(40), rec(40), rec(20), rec(80), rec(500)])
    s = e.sync.stats
    assert (s.accepted, s.dropped_duplicate, s.dropped_out_of_order, s.gaps) == (4, 1, 1, 1)


def test_sg2_native_records_are_accepted():
    e = TemporalEngine()
    frames = []
    for i in range(150):
        t = i / 30.0
        closed = 30 <= i < 54                          # 0.8 s closure
        frames.append({"frame_id": i, "timestamp": t, "eye_state": "CLOSED" if closed else "OPEN",
                       "eye_valid": True, "eye_closure_prob": None, "ear": 0.1 if closed else 0.3})
    outs = run_frames(e, frames)
    assert outs[-1]["long_blinks"] == 1
    assert outs[-1]["face_valid"] == 1
