"""TemporalEngine: per-frame cues in, SG-5 indicator vector out at 10 Hz.

    engine = TemporalEngine()
    for record in records:          # dicts in any format adapters.py understands
        vec = engine.push(record)   # None, or a sg4.output.v1.1 dict every 100 ms
        if vec: send_to_sg5(vec)

Per frame: sync/validate -> ring buffer (PERCLOS, validity, head-down,
face-absent running sums) -> event trackers (closures, yawns, nods).
Per output tick: read the running sums and event windows, update baseline
and trend, build the vector with sg5_output.to_sg5().
"""
from typing import Any, Dict, List, Optional, Union

from . import events as ev
from .adapters import to_cue
from .baseline import Baseline, Trend
from .config import Config, load_config
from .indicators import IndicatorState, empty_state, perclos, rate_per_min, share
from .ring_buffer import RingBuffer
from .schema import CueRecord, ValidCue
from .sg5_output import to_sg5
from .sync import Synchronizer

COLUMNS = ("valid_ms", "closed_ms", "face_absent_ms", "head_down_ms", "frames", "valid_frames")


class TemporalEngine:
    def __init__(self, cfg: Optional[Config] = None, keep_event_log: bool = False):
        self.cfg = cfg = cfg or load_config()
        self.sync = Synchronizer(cfg)
        self.buf = RingBuffer(cfg.buffer_capacity, COLUMNS, {
            "perclos": cfg.perclos_window_s * 1000,
            "validity": cfg.validity_window_s * 1000,
            "blink": cfg.blink_window_s * 1000,
        })
        self.closure = ev.ClosureTracker(cfg)
        self.yawn = ev.SegmentTracker(cfg.yawn_on, cfg.yawn_off, cfg.min_yawn_ms, cfg.yawn_merge_gap_ms)
        self.nod = ev.SegmentTracker(-cfg.nod_on_deg, -cfg.nod_off_deg, cfg.min_nod_ms, cfg.nod_merge_gap_ms)
        self.long_win = ev.EventWindow(cfg.long_blink_window_s * 1000)
        self.blink_win = ev.EventWindow(cfg.blink_window_s * 1000)     # value = duration ms
        self.slow_win = ev.EventWindow(cfg.blink_window_s * 1000)
        self.closure_win = ev.EventWindow(cfg.blink_window_s * 1000)   # all real closures, for longest
        self.yawn_win = ev.EventWindow(cfg.yawn_window_s * 1000)
        self.nod_win = ev.EventWindow(cfg.nod_window_s * 1000)
        self.baseline = Baseline(cfg)
        self.trend = Trend(cfg)

        self.last: Optional[ValidCue] = None
        self.next_out_ms: Optional[int] = None
        self._last_head_ms: Optional[int] = None
        self._last_pitch = 0.0
        self._face_lost_ms: Optional[int] = None
        self.event_log: Optional[List[Dict[str, Any]]] = [] if keep_event_log else None

    # ------------------------------------------------------------------ input
    def push(self, record: Union[Dict[str, Any], CueRecord]) -> Optional[Dict[str, Any]]:
        """Process one frame. Returns the output vector when a 100 ms tick is due."""
        cue = record if isinstance(record, CueRecord) else to_cue(record)
        v = self.sync.process(cue)
        if v is None:
            return None
        self._update(v)
        self.last = v
        period = self.cfg.output_period_ms
        if self.next_out_ms is None:
            self.next_out_ms = v.t_ms
        if v.t_ms < self.next_out_ms:
            return None
        self.next_out_ms += period * ((v.t_ms - self.next_out_ms) // period + 1)
        return to_sg5(self.state())

    def _update(self, v: ValidCue) -> None:
        cfg, t, dt = self.cfg, v.t_ms, v.dt_ms
        closed = v.eye_valid and v.closure_prob >= cfg.p80_threshold
        head_down = v.head_valid and v.pitch_deg <= cfg.nod_on_deg
        self.buf.push(t, (
            dt if v.eye_valid else 0,
            dt if closed else 0,
            0 if v.face_valid else dt,
            dt if head_down else 0,
            1,
            1 if v.eye_valid else 0,
        ))

        long_now, done = self.closure.update(t, v.eye_valid, v.closure_prob)
        if long_now:
            self.long_win.add(t)
        if done is not None:
            self._on_closure(done)

        if self.yawn.update(t, v.mouth_valid, v.yawn_prob):
            self.yawn_win.add(t)
            self._log("yawn", self.yawn.seg_start, t)

        if self.nod.update(t, v.head_valid, -v.pitch_deg, self._head_drop_lost_face(v)):
            self.nod_win.add(t)
            self._log("nod", self.nod.seg_start, t)
        self._after_frame(v, closed)

    def _on_closure(self, c: ev.Closure) -> None:
        d = c.duration_ms
        if c.kind == ev.LONG and not c.long_reported:   # reached 500 ms across a frame gap
            self.long_win.add(c.end_ms)
        if c.kind in (ev.BLINK, ev.SLOW):
            self.blink_win.add(c.end_ms, d)
            if c.kind == ev.SLOW:
                self.slow_win.add(c.end_ms)
        if c.kind in (ev.BLINK, ev.SLOW, ev.LONG):
            self.closure_win.add(c.end_ms, d)
        self._log(c.kind, c.start_ms, c.end_ms)

    def _head_drop_lost_face(self, v: ValidCue) -> bool:
        """Face lost shortly after the head was pitched down = head drop (counts as a nod)."""
        if v.head_valid:
            self._last_head_ms, self._last_pitch = v.t_ms, v.pitch_deg
        if v.face_valid:
            self._face_lost_ms = None
            return False
        if self._face_lost_ms is None:
            self._face_lost_ms = v.t_ms
        return (self._last_head_ms is not None
                and self._last_pitch <= self.cfg.nod_off_deg
                and self._face_lost_ms - self._last_head_ms <= self.cfg.nod_face_loss_ms)

    def _log(self, kind: str, start_ms: int, end_ms: int) -> None:
        if self.event_log is not None:
            self.event_log.append({"kind": kind, "start_ms": start_ms, "end_ms": end_ms})

    # Hooks for alternative approaches (baselines_alt.py)
    def _after_frame(self, v: ValidCue, closed: bool) -> None:
        pass

    def _perclos_value(self) -> float:
        return perclos(self.buf.sum("perclos", "closed_ms"), self.buf.sum("perclos", "valid_ms"))

    # ----------------------------------------------------------------- output
    def state(self) -> IndicatorState:
        """Indicators at the latest frame (empty vector if no frame yet)."""
        if self.last is None:
            return empty_state()
        cfg, now = self.cfg, self.last.t_ms
        for w in (self.long_win, self.blink_win, self.slow_win, self.closure_win, self.yawn_win, self.nod_win):
            w.prune(now)
        buf = self.buf
        p = self._perclos_value()
        blink_rate = rate_per_min(self.blink_win.count(), buf.sum("blink", "valid_ms"),
                                  cfg.min_valid_for_rate_s * 1000)
        live_ms = self.closure.live_ms(now)
        self.baseline.update(now, p, blink_rate)
        calibrating = self.baseline.calibrating(now)
        self.trend.update(now / 1000.0, p)
        return IndicatorState(
            time_s=now / 1000.0,
            perclos=p,
            face_valid=self.last.face_valid,
            long_blinks=self.long_win.count(),
            yawn_count=self.yawn_win.count(),
            eye_closure_s=live_ms / 1000.0,
            nod_count=self.nod_win.count(),
            validity_score=share(buf.sum("validity", "valid_frames"), buf.sum("validity", "frames")),
            calibrating=calibrating,
            blink_rate_bpm=blink_rate,
            mean_blink_ms=self.blink_win.mean(),
            slow_blinks=self.slow_win.count(),
            longest_closure_s=max(self.closure_win.max(), live_ms) / 1000.0,
            head_down_s=buf.sum("validity", "head_down_ms") / 1000.0,
            face_absent_s=buf.sum("validity", "face_absent_ms") / 1000.0,
            perclos_vs_baseline=None if calibrating else self.baseline.relative_perclos(p),
            trend=None if calibrating else self.trend.label(),
        )

    def snapshot(self) -> Dict[str, Any]:
        """Current vector regardless of the 10 Hz schedule (also valid with no input)."""
        return to_sg5(self.state())
