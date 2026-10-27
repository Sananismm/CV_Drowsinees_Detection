"""Locations of SG-4 files inside the team repo.

`interfaces/`, `evaluation/`, `documentation/` and `datasets/` sit next to `module_4/`.
"""
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parents[2]


def repo_path(name: str) -> Path:
    """Path of a team-level folder such as 'interfaces'."""
    return MODULE_DIR.parent / name


def interfaces_dir() -> Path:
    return repo_path("interfaces")
