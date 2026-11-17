"""SG5 midterm deployment proposal; importing this package has no hardware effects."""

from .engine import CONFIGURATIONS, Config, DecisionEngine, drowsiness_score, to_legacy_sg6

__all__ = ["CONFIGURATIONS", "Config", "DecisionEngine", "drowsiness_score", "to_legacy_sg6"]
