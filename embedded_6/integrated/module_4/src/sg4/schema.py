"""Record types for SG-4 input/output and their validation.

`CueRecord` is SG-4's internal, flattened view of one frame. It is produced by
`adapters.py` (the only place upstream field names appear) and consumed by the
core. Output validation uses the JSON Schema in interfaces/ via jsonschema.
"""
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .paths import interfaces_dir

INPUT_SCHEMA_ID = "sg4.input.v1"
OUTPUT_SCHEMA_ID = "sg4.output.v1.1"
INPUT_SCHEMA_FILE = "sg4_input_v1.schema.json"
OUTPUT_SCHEMA_FILE = "sg4_output_v1_1.schema.json"


@dataclass
class CueRecord:
    """One frame of upstream cues. None = unavailable (never 'closed' or 'yawning')."""
    frame_id: int
    t_ms: int                              # SG-1 monotonic capture clock
    face_present: bool = False
    face_conf: Optional[float] = None
    closure_prob: Optional[float] = None   # 0 open .. 1 closed
    eye_state: str = "unknown"             # open | closed | unknown
    eye_conf: Optional[float] = None
    ear: Optional[float] = None
    yawn_prob: Optional[float] = None
    mouth_conf: Optional[float] = None
    pitch_deg: Optional[float] = None      # negative = head down
    head_conf: Optional[float] = None


@dataclass
class ValidCue:
    """CueRecord after sync: per-cue validity decided once, using config thresholds."""
    frame_id: int
    t_ms: int
    dt_ms: int              # observed time credited to this frame (capped at max_frame_dt_ms)
    face_valid: bool
    eye_valid: bool
    closure_prob: float     # only meaningful when eye_valid
    mouth_valid: bool
    yawn_prob: float
    head_valid: bool
    pitch_deg: float
    ear: Optional[float]


def _load(name: str) -> Dict[str, Any]:
    with open(str(interfaces_dir() / name), "r") as f:
        return json.load(f)


def load_input_schema() -> Dict[str, Any]:
    return _load(INPUT_SCHEMA_FILE)


def load_output_schema() -> Dict[str, Any]:
    return _load(OUTPUT_SCHEMA_FILE)


_validators = {}


def _validator(name: str):
    if name not in _validators:
        import jsonschema  # validation-only dependency
        schema = _load(name)
        cls = jsonschema.validators.validator_for(schema)
        _validators[name] = cls(schema)
    return _validators[name]


def validate_input(record: Dict[str, Any]) -> List[str]:
    """Return a list of schema errors for one sg4.input.v1 record (empty = valid)."""
    return [e.message for e in _validator(INPUT_SCHEMA_FILE).iter_errors(record)]


def validate_output(vector: Dict[str, Any]) -> List[str]:
    """Return a list of schema errors for one sg4.output.v1.1 vector (empty = valid)."""
    return [e.message for e in _validator(OUTPUT_SCHEMA_FILE).iter_errors(vector)]
