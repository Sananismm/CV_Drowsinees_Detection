"""Hand-checkable unit tests for each indicator building block."""
import pytest

from conftest import rec
from sg4 import adapters
from sg4.baseline import Baseline, Trend, slope_per_min
from sg4.events import BLINK, LONG, NOISE, SLOW, ClosureTracker, EventWindow, SegmentTracker, classify_closure
from sg4.indicators import perclos, rate_per_min, share
from sg4.ring_buffer import RingBuffer
from sg4.sync import Synchronizer


# ---------------------------------------------------------------- indicators
def test_perclos_formula():
    assert perclos(300, 1000) == pytest.approx(0.3)
    assert perclos(0, 0) == 0.0
    assert perclos(1200, 1000) == 1.0          # clipped


def test_share_and_rate():
    assert share(45, 50) == pytest.approx(0.9)
    assert share(0, 0) == 0.0
    assert rate_per_min(5, 30000, 5000) == pytest.approx(10.0)
    assert rate_per_min(5, 4000, 5000) == 0.0  # not enough valid time yet


# --------------------------------------------------------------- ring buffer
def test_ring_buffer_window_sums():
    rb = RingBuffer(16, ["a"], {"w3": 3000, "w5": 5000})
    for t in range(0, 10000, 1000):            # t = 0..9000, value = t/1000
        rb.push(t, [t // 1000])
    assert rb.sum("w3", "a") == 7 + 8 + 9      # rows with t > 6000
    assert rb.sum("w5", "a") == 5 + 6 + 7 + 8 + 9
    assert rb.count("w3") == 3


def test_ring_buffer_capacity_forces_eviction():
    rb = RingBuffer(4, ["a"], {"w": 60000})
    for t in range(10):
        rb.push(t * 10, [1])
    assert rb.sum("w", "a") == 4 and rb.forced_evictions == 6


# -------------------------------------------------------------------- events
def test_classify_closure(cfg):
    assert classify_closure(50, cfg) == NOISE
    assert classify_closure(200, cfg) == BLINK
    assert classify_closure(400, cfg) == BLINK
    assert classify_closure(450, cfg) == SLOW
    assert classify_closure(500, cfg) == LONG


def test_hysteresis_ignores_flicker_around_threshold(cfg):
    ct = ClosureTracker(cfg)
    finished = []
    for i, p in enumerate([0.1, 0.85, 0.7, 0.79, 0.81, 0.6, 0.55, 0.4, 0.1]):
        _, done = ct.update(i * 100, True, p)
        if done:
            finished.append(done)
    assert len(finished) == 1                  # one closure 100..700 ms, not three
    assert finished[0].duration_ms == 600 and finished[0].kind == LONG


def test_invalid_eye_ends_closure(cfg):
    ct = ClosureTracker(cfg)
    ct.update(0, True, 0.9)
    ct.update(100, True, 0.9)
    assert ct.live_ms(100) == 100
    _, done = ct.update(200, False, 0.0)
    assert ct.live_ms(200) == 0 and done.kind == "interrupted" and done.end_ms == 100


def test_segment_tracker_min_duration_and_merge():
    st = SegmentTracker(on=0.6, off=0.4, min_ms=1000, merge_gap_ms=1000)
    counts = 0
    levels = [0.9] * 5 + [0.1] * 3 + [0.9] * 8 + [0.1] * 20 + [0.9] * 3 + [0.1] * 5   # 200 ms steps
    for i, lv in enumerate(levels):
        counts += st.update(i * 200, True, lv)
    # 1st segment 0.8 s (< min) + gap 0.6 s + 1.6 s -> merged, counted once; last 0.6 s segment too short
    assert counts == 1


def test_event_window():
    w = EventWindow(30000)
    w.add(1000, 200)
    w.add(20000, 400)
    w.prune(31000)
    assert w.count() == 1 and w.mean() == 400 and w.max() == 400


# ---------------------------------------------------------------------- sync
def test_sync_validity_and_dt(cfg):
    s = Synchronizer(cfg)
    a = s.process(adapters.to_cue(rec(0)))
    b = s.process(adapters.to_cue(rec(1000)))
    assert a.dt_ms == 0 and b.dt_ms == cfg.max_frame_dt_ms and s.stats.gaps == 1
    c = s.process(adapters.to_cue(rec(1040, face_conf=0.2)))
    assert not c.face_valid and not c.eye_valid and not c.mouth_valid
    d = s.process(adapters.to_cue(rec(1080, closure=None)))
    assert d.face_valid and not d.eye_valid


# ------------------------------------------------------------------ adapters
def test_sg2_adapter_maps_state_when_prob_is_null():
    r = adapters.merge_upstream({"frame_id": 7, "timestamp": 1.234, "eye_state": "CLOSED",
                                 "eye_valid": True, "eye_closure_prob": None, "ear": 0.1})
    assert r["timestamp_ms"] == 1234
    assert r["eye"]["closure_prob"] == 1.0 and r["face"]["present"] is True
    r = adapters.merge_upstream({"frame_id": 8, "timestamp": 1.267, "eye_state": "UNKNOWN", "eye_valid": False})
    assert r["eye"] is None and r["face"]["present"] is False


def test_sg2_adapter_merges_sg1_and_sg3():
    r = adapters.merge_upstream({"frame_id": 1, "timestamp": 0.5, "eye_state": "OPEN", "eye_valid": True},
                                sg1_face={"present": True, "confidence": 0.9},
                                sg3={"yawn_prob": 0.2, "pitch_deg": -5.0, "confidence": 0.8})
    cue = adapters.from_v1(r)
    assert cue.closure_prob == 0.0 and cue.face_conf == 0.9
    assert cue.yawn_prob == 0.2 and cue.pitch_deg == -5.0


# ------------------------------------------------------------------ baseline
def test_slope_per_min():
    assert slope_per_min([0, 30, 60], [0.1, 0.15, 0.2]) == pytest.approx(0.1)
    assert slope_per_min([5], [0.1]) == 0.0


def test_trend_labels(cfg):
    tr = Trend(cfg)
    for i in range(31):
        tr.update(float(i), 0.1 + 0.002 * i)   # +0.12 per minute
    assert tr.label() == "worsening"


def test_baseline_relative(cfg):
    b = Baseline(cfg)
    b.update(0, 0.05, 15.0)
    assert b.calibrating(30000) and b.relative_perclos(0.1) is None
    b.update(60000, 0.05, 15.0)
    assert not b.calibrating(60000)
    assert b.relative_perclos(0.1) == pytest.approx(2.0)
    b2 = Baseline(cfg)
    b2.update(0, 0.0, 0.0)
    b2.update(60000, 0.0, 0.0)
    assert b2.relative_perclos(0.04) == pytest.approx(2.0)   # floor 0.02
