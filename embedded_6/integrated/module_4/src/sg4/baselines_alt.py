"""Backup / alternative approaches, compared against TemporalEngine in the ablation.

Both produce the same sg4.output.v1.1 vector through sg5_output.to_sg5(), so the
comparison is like-for-like.

1. NaiveFrameCounter - the "single-frame" baseline. Each frame is classified on
   its own (closure_prob >= P80, and a frame with no visible eye is called
   closed, as a plain frame classifier would). It counts consecutive closed
   FRAMES (N = long_blink_ms at a nominal 30 FPS), uses frame-count windows,
   no hysteresis, no validity handling, no timestamps, no baseline.
2. EmaPerclosEngine - the primary engine with PERCLOS replaced by an
   exponential moving average of the closed flag (time constant = half the
   PERCLOS window). Tests whether the exact sliding window is worth it.
"""
import math
from collections import deque
from typing import Any, Dict, List, Optional

from .adapters import to_cue
from .config import Config, load_config
from .engine import TemporalEngine
from .indicators import IndicatorState, empty_state
from .schema import ValidCue
from .sg5_output import to_sg5

NOMINAL_FPS = 30.0


class NaiveFrameCounter:
    def __init__(self, cfg: Optional[Config] = None, fps: float = NOMINAL_FPS, keep_event_log: bool = False):
        self.cfg = cfg = cfg or load_config()
        self.fps = fps
        self.n_long = int(round(cfg.long_blink_ms * fps / 1000.0))
        self.out_every = int(round(fps / cfg.output_rate_hz))
        self.perclos_frames = deque(maxlen=int(cfg.perclos_window_s * fps))
        self.closed_sum = 0
        self.long_frames = deque()       # frame index at which a long blink was counted
        self.yawn_frames = deque()
        self.nod_frames = deque()
        self.run = 0                     # consecutive closed frames
        self.prev_yawn = self.prev_nod = False
        self.i = 0
        self.last_t = 0
        self.face_valid = False
        self.event_log: Optional[List[Dict[str, Any]]] = [] if keep_event_log else None

    def push(self, record) -> Optional[Dict[str, Any]]:
        cfg = self.cfg
        c = to_cue(record)
        self.i += 1
        self.last_t = c.t_ms
        self.face_valid = bool(c.face_present)
        closed = c.closure_prob is None or c.closure_prob >= cfg.p80_threshold
        if len(self.perclos_frames) == self.perclos_frames.maxlen:
            self.closed_sum -= self.perclos_frames[0]
        self.perclos_frames.append(1 if closed else 0)
        self.closed_sum += 1 if closed else 0

        if closed:
            self.run += 1
            if self.run == self.n_long:
                self.long_frames.append(self.i)
        else:
            if self.run >= self.n_long and self.event_log is not None:
                ms = 1000.0 / self.fps
                self.event_log.append({"kind": "long_blink", "start_ms": int(c.t_ms - self.run * ms),
                                       "end_ms": c.t_ms})
            self.run = 0

        yawn = c.yawn_prob is not None and c.yawn_prob >= cfg.yawn_on
        if yawn and not self.prev_yawn:
            self.yawn_frames.append(self.i)
        self.prev_yawn = yawn
        nod = c.pitch_deg is not None and c.pitch_deg <= cfg.nod_on_deg
        if nod and not self.prev_nod:
            self.nod_frames.append(self.i)
        self.prev_nod = nod

        if (self.i - 1) % self.out_every:
            return None
        return to_sg5(self.state())

    def snapshot(self) -> Dict[str, Any]:
        return to_sg5(self.state())

    def _prune(self, q: deque, window_s: float) -> int:
        while q and q[0] <= self.i - window_s * self.fps:
            q.popleft()
        return len(q)

    def state(self) -> IndicatorState:
        cfg = self.cfg
        if self.i == 0:
            return empty_state()
        s = empty_state(self.last_t / 1000.0)
        s.perclos = self.closed_sum / float(len(self.perclos_frames))
        s.face_valid = self.face_valid
        s.long_blinks = self._prune(self.long_frames, cfg.long_blink_window_s)
        s.yawn_count = self._prune(self.yawn_frames, cfg.yawn_window_s)
        s.nod_count = self._prune(self.nod_frames, cfg.nod_window_s)
        s.eye_closure_s = self.run / self.fps
        s.longest_closure_s = s.eye_closure_s
        s.validity_score = 1.0           # naive: no notion of validity
        s.calibrating = False
        return s


class EmaPerclosEngine(TemporalEngine):
    """Primary engine, but PERCLOS = EMA of the closed flag over valid time."""

    def __init__(self, cfg: Optional[Config] = None, keep_event_log: bool = False):
        super().__init__(cfg, keep_event_log)
        self.tau_ms = self.cfg.perclos_window_s * 1000.0 / 2.0
        self.ema = 0.0

    def _after_frame(self, v: ValidCue, closed: bool) -> None:
        if v.eye_valid and v.dt_ms > 0:
            a = 1.0 - math.exp(-v.dt_ms / self.tau_ms)
            self.ema += a * ((1.0 if closed else 0.0) - self.ema)

    def _perclos_value(self) -> float:
        return self.ema
