#!/usr/bin/env python3
"""Run camera-free SG6 checks and preserve their commands, environment and output."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys

REPO = Path(__file__).resolve().parents[3]
SUITES = [
    ('detector_demo', ['-m', 'unittest', 'discover', '-s', 'embedded_6/Integration', '-p', 'test_midterm_demo.py', '-v']),
    ('synthetic_integration', ['-m', 'unittest', 'discover', '-s', 'embedded_6/integrated/tests', '-p', 'test_pipeline.py', '-v']),
    ('sg5_sg6_handoff', ['-m', 'unittest', 'module_5.midterm.tests.test_sg6_contract', '-v']),
    ('submission_utilities', ['-m', 'unittest', 'discover', '-s', 'embedded_6/midterm/tests', '-p', 'test_*.py', '-v']),
]


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output-dir', type=Path, default=REPO / 'embedded_6' / 'evidence' / 'verification')
    args = p.parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for name, command in SUITES:
        try:
            run = subprocess.run([sys.executable, *command], cwd=REPO, capture_output=True,
                                 encoding='utf-8', errors='replace', timeout=180,
                                 env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
            content = run.stdout + run.stderr
            code = run.returncode
        except subprocess.TimeoutExpired:
            content, code = 'Verification suite timed out after 180 seconds.\n', 124
        content = content.replace(str(REPO), '<REPOSITORY>').replace(str(Path.home()), '<HOME>')
        (args.output_dir / f'{name}.txt').write_text(content, encoding='utf-8', newline='\n')
        count = re.search(r'Ran (\d+) tests?', content)
        records.append({'name': name, 'command': ['python', *command], 'exit_code': code,
                        'tests_run': int(count.group(1)) if count else None,
                        'log': f'{name}.txt', 'log_sha256': hashlib.sha256(content.encode()).hexdigest()})
        print(f'{name}: {"PASS" if code == 0 else "FAIL"} ({records[-1]["tests_run"]} tests)', flush=True)
    versions = {}
    for package in ('numpy', 'opencv-python', 'opencv-contrib-python', 'PyYAML', 'jsonschema'):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            pass
    result = {'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
              'platform': platform.platform(), 'architecture': platform.machine(),
              'python': platform.python_version(), 'packages': versions,
              'scope': 'camera-free PC tests; blank-frame detector inference and synthetic integration; no private recorded frame is present',
              'excluded': ['live camera', 'GUI', 'Jetson runtime', 'physical GPIO/buzzer', 'labelled accuracy'],
              'all_passed': all(record['exit_code'] == 0 for record in records), 'suites': records}
    (args.output_dir / 'verification.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return 0 if result['all_passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
