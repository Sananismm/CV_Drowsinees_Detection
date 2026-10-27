import sys
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE / "src"))
sys.path.insert(0, str(MODULE / "tools"))

from sg4.config import load_config  # noqa: E402


@pytest.fixture
def cfg():
    return load_config()


def rec(t_ms, closure=0.1, face=True, face_conf=0.95, yawn=0.05, pitch=-3.0, eye=True, frame_id=None):
    """Build one sg4.input.v1 record. closure/yawn/pitch=None -> that block is null."""
    face_ok = face and face_conf is not None
    return {
        "schema": "sg4.input.v1",
        "frame_id": frame_id if frame_id is not None else t_ms // 10,
        "timestamp_ms": t_ms,
        "face": {"present": bool(face), "confidence": face_conf},
        "eye": ({"closure_prob": closure, "state": "closed" if closure >= 0.5 else "open",
                 "ear": 0.3, "confidence": 0.95} if (eye and face_ok and closure is not None) else None),
        "mouth": ({"yawn_prob": yawn, "mar": 0.3, "confidence": 0.95} if (face_ok and yawn is not None) else None),
        "head": ({"pitch_deg": pitch, "yaw_deg": 0.0, "roll_deg": 0.0, "confidence": 0.95}
                 if (face_ok and pitch is not None) else None),
    }


def run_frames(engine, frames):
    """Push records; return the list of emitted vectors."""
    return [o for o in (engine.push(r) for r in frames) if o is not None]


def stream(t0, t1, step=40, **kw):
    """Records every `step` ms in [t0, t1)."""
    return [rec(t, **kw) for t in range(t0, t1, step)]
