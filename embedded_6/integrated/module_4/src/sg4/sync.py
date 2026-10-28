"""Sync & validate: ordering, duplicates, gaps, and per-cue validity.

Rules (CLAUDE.md section 5):
  * timestamps are SG-1's monotonic capture clock; out-of-order and duplicate
    timestamps are dropped and counted;
  * gaps > gap_ms are logged; the time credited to one frame is capped at
    max_frame_dt_ms so unobserved time never counts as "closed" or "valid";
  * no face / low confidence / null cue -> that cue is INVALID, never "closed".
"""
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .config import Config
from .schema import CueRecord, ValidCue


def _ok(value, conf, conf_min) -> bool:
    return value is not None and conf is not None and conf >= conf_min


@dataclass
class SyncStats:
    accepted: int = 0
    dropped_out_of_order: int = 0
    dropped_duplicate: int = 0
    gaps: int = 0
    gap_log: List[Tuple[int, int]] = field(default_factory=list)  # (t_ms, gap_ms), last 100


class Synchronizer:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.last_t: Optional[int] = None
        self.stats = SyncStats()

    def process(self, cue: CueRecord) -> Optional[ValidCue]:
        """Return a validated cue, or None if the record is dropped."""
        cfg = self.cfg
        t = cue.t_ms
        if self.last_t is not None:
            if t == self.last_t:
                self.stats.dropped_duplicate += 1
                return None
            if t < self.last_t:
                self.stats.dropped_out_of_order += 1
                return None
            gap = t - self.last_t
            if gap > cfg.gap_ms:
                self.stats.gaps += 1
                self.stats.gap_log.append((t, gap))
                del self.stats.gap_log[:-100]
            dt = min(gap, cfg.max_frame_dt_ms)
        else:
            dt = 0
        self.last_t = t
        self.stats.accepted += 1

        face_valid = bool(cue.face_present) and _ok(True, cue.face_conf, cfg.face_conf_min)
        eye_valid = face_valid and _ok(cue.closure_prob, cue.eye_conf, cfg.eye_conf_min)
        mouth_valid = face_valid and _ok(cue.yawn_prob, cue.mouth_conf, cfg.mouth_conf_min)
        head_valid = face_valid and _ok(cue.pitch_deg, cue.head_conf, cfg.head_conf_min)
        return ValidCue(
            frame_id=cue.frame_id, t_ms=t, dt_ms=dt,
            face_valid=face_valid,
            eye_valid=eye_valid,
            closure_prob=float(cue.closure_prob) if eye_valid else 0.0,
            mouth_valid=mouth_valid,
            yawn_prob=float(cue.yawn_prob) if mouth_valid else 0.0,
            head_valid=head_valid,
            pitch_deg=float(cue.pitch_deg) if head_valid else 0.0,
            ear=cue.ear if eye_valid else None,
        )
