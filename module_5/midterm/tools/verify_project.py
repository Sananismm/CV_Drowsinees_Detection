"""Record reproducible software evidence, without claiming hardware readiness."""

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def run(command):
    begin = time.perf_counter()
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    combined = completed.stdout + completed.stderr
    count = re.search(r"Ran (\d+) tests?", combined) or re.search(r"(\d+) passed", combined)
    return {"command": command, "exit_code": completed.returncode, "passed": completed.returncode == 0,
            "test_count": int(count[1]) if count else None, "elapsed_s": time.perf_counter() - begin,
            "stdout": completed.stdout[-16000:], "stderr": completed.stderr[-16000:]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sg2-python", help="optional separate interpreter with SG2 CNN/test dependencies")
    parser.add_argument("--pr-url")
    parser.add_argument("--output", default=str(ROOT / "module_5/midterm/results/verification.json"))
    args = parser.parse_args()
    checks = [run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "module_5/midterm/tests", "-q"]),
              run([sys.executable, "-m", "pytest", "module_1/tests", "module_4/tests", "-q", "--disable-warnings"]),
              run([sys.executable, "-m", "pip", "check"])]
    if args.sg2_python:
        checks.append(run([args.sg2_python, "-B", "-m", "unittest", "discover", "-s", "module_2/tests", "-q"]))
    from embedded_6.sg5_handoff.consume import validate_decision, hardware_request
    videos = []
    for directory in sorted((ROOT / "module_5/midterm/results").glob("video[0-9][0-9]")):
        summary = json.loads((directory / "summary.json").read_text())
        count = 0
        for line in (directory / "sg6_stream.jsonl").read_text().splitlines():
            validate_decision(json.loads(line))
            hardware_request(json.loads(line))
            count += 1
        if count != summary["sg4_vectors"]:
            raise ValueError("Video output vector counts differ: %s" % directory)
        import cv2
        capture = cv2.VideoCapture(str(directory / "annotated.mp4"))
        encoded_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        first_ok, _ = capture.read()
        capture.set(cv2.CAP_PROP_POS_FRAMES, max(0, encoded_frames - 1))
        last_ok, _ = capture.read()
        capture.release()
        if not first_ok or not last_ok or encoded_frames != summary["processed_frames"]:
            raise ValueError("Annotated video failed playback/frame-count verification: %s" % directory)
        videos.append({"source": summary["source"], "frames": summary["processed_frames"], "vectors": count,
                       "sg6_packets_valid": True, "annotated_video_frames": encoded_frames,
                       "first_and_last_frame_decode": True, "accuracy": None})
    evaluation = json.loads((ROOT / "module_5/midterm/results/evaluation/evaluation.json").read_text())
    evidence = {
        "schema_version": "sg5.verification.v1",
        "assessment_date": "2026-10-28", "recorded_karachi": datetime.now(timezone(timedelta(hours=5))).isoformat(),
        "platform": platform.platform(), "python": platform.python_version(),
        "branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip(),
        "tested_code_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "all_recorded_checks_pass": all(c["passed"] for c in checks),
        "total_passing_tests": sum(c["test_count"] or 0 for c in checks if c["passed"]),
        "checks": checks, "video_runs": videos,
        "total_real_video_frames": sum(v["frames"] for v in videos),
        "total_real_video_vectors": sum(v["vectors"] for v in videos),
        "synthetic_rows": evaluation["dataset"]["total_rows"],
        "evaluation_sha256": hashlib.sha256((ROOT / "module_5/midterm/results/evaluation/evaluation.json").read_bytes()).hexdigest(),
        "pull_request": args.pr_url,
        "hardware_verified": False,
        "limitations": ["No independent real-video drowsiness annotations", "Optional SG2 tests may use a separate existing Torch environment; that is not a single universal environment claim", "SG3/SG4 adapter and SG6 v2 acceptance remains open", "PC tests do not verify Jetson, GPIO or live camera readiness"],
    }
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(evidence, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print("Passing tests: %d; video frames: %d; SG6 packets: %d" % (evidence["total_passing_tests"], evidence["total_real_video_frames"], evidence["total_real_video_vectors"]))
    print(destination)
    if not evidence["all_recorded_checks_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
