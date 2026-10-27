"""SG-4 Temporal Behaviour Analysis: per-frame cues -> temporal indicators for SG-5."""
from .config import Config, load_config
from .engine import TemporalEngine
from .sg5_output import to_sg5

__version__ = "1.1.0"
__all__ = ["Config", "load_config", "TemporalEngine", "to_sg5", "__version__"]
