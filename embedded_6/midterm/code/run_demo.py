#!/usr/bin/env python3
"""Entry point for the SG6 camera demo, without copying its implementation."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'Integration'))
from run_midterm_demo import main

if __name__ == '__main__':
    sys.exit(main())
