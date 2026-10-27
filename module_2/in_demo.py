"""CS-477 instructor demonstration: orchestration, verification and presentation.

Run from the repository root: python -m module_2.in_demo
Detection is delegated to demo.py; this file implements no eye-state algorithm.
Video I/O: https://docs.opencv.org/4.x/d8/dfe/classcv_1_1VideoCapture.html
Plots: https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.savefig.html
"""

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import importlib
from itertools import zip_longest
import json
import math
import os
from pathlib import Path
import sys
import tempfile


MODULE = Path(__file__).resolve().parent
REPOSITORY = MODULE.parent


class DemoError(RuntimeError):
    """An actionable setup or output-verification error."""


def find_video(requested=None, repository=REPOSITORY):
    """Search input folders only, never previous annotated demo outputs."""
    if requested is not None:
        video = Path(requested).expanduser().resolve()
        if not video.is_file():
            raise DemoError(f"Video not found: {video}. Use --video with an original video.")
        return video
    folders = [repository / "Sg 1 data", repository / "datasets",
               repository / "videos", repository / "module_2/local/videos"]
    for folder in folders:
        preferred = folder / "P1042801_720.mp4"
        if preferred.is_file():
            return preferred.resolve()
        if folder.is_dir():
            for video in sorted(folder.iterdir()):
                if (video.is_file() and video.suffix.lower() in {".mp4", ".avi", ".mov", ".mkv"}
                        and not any(word in video.stem.lower() for word in ("overlay", "annotated"))):
                    return video.resolve()
    raise DemoError("No original video found. Put it in 'Sg 1 data', datasets, videos, "
                    "or module_2/local/videos; or provide --video PATH.")


def find_model(requested=None, repository=REPOSITORY):
    candidates = ([Path(requested).expanduser()] if requested is not None else
                  [repository / "module_1/models/face_landmarker.task",
                   repository / "module_2/local/face_landmarker.task"])
    for model in candidates:
        if model.is_file():
            return model.resolve()
    raise DemoError("Face Landmarker model not found. Download the official model to "
                    "module_2/local/face_landmarker.task (README), or use --model PATH. "
                    "Cached landmarks will not be substituted.")


def require_file(path, description):
    if not path.is_file():
        raise DemoError(f"Missing {description}: {path}. Restore the required project file.")
    return path


def dependencies():
    """Delay heavy imports so --help and missing-input errors remain useful."""
    loaded = {}
    for name in ("cv2", "numpy", "torch", "mediapipe", "matplotlib"):
        try:
            loaded[name] = importlib.import_module(name)
        except (ImportError, OSError) as error:
            raise DemoError(f"Cannot load {name}: {error}. In the active environment run: "
                            "python -m pip install -r module_2/requirements-demo.txt") from error
    return loaded


def selected_settings(module=MODULE):
    """Read and guard the approved settings; never alter or retune them."""
    frozen = json.loads((module / "final_method.json").read_text(encoding="utf-8"))
    selected = frozen["selected"]
    expected = dict(method="EAR", ear_threshold=0.15, open_frames=2, max_open_delay_sec=0.08)
    if any(selected.get(key) != value for key, value in expected.items()):
        raise DemoError("Selected configuration differs from approved EAR 0.15 / OPEN2 / "
                        "0.08-second settings. Restore it; the launcher will not retune it.")
    for filename, key in (("selection_protocol.json", "protocol_sha256"),
                          ("models/best.pt", "checkpoint_sha256")):
        path = require_file(module / filename, filename)
        if hashlib.sha256(path.read_bytes()).hexdigest() != frozen[key]:
            raise DemoError(f"Checksum mismatch for {filename}; restore the approved artifact.")
    return selected


def new_run_directory(base):
    """Atomic unique allocation preserves all historical and earlier run outputs."""
    base = Path(base).expanduser().resolve()
    base.mkdir(parents=True, exist_ok=True)
    prefix = datetime.now(timezone.utc).strftime("run_%Y%m%dT%H%M%SZ_")
    return Path(tempfile.mkdtemp(prefix=prefix, dir=base))


def run_pipeline(video, model, output, repository=REPOSITORY):
    """Use the existing CLI implementation with fresh SG-1 input, all frames, EAR only."""
    from module_2 import demo
    arguments = ["module_2.demo", "--video", str(video),
                 "--sg1-source", str(repository / "module_1/scripts/sg1_detector.py"),
                 "--landmarker-model", str(model),
                 "--sg4-notebook", str(repository / "module_4/D2-SG4.ipynb"),
                 "--mode", "EAR", "--threshold", "0.15", "--output", str(output)]
    previous = sys.argv
    try:
        sys.argv = arguments
        demo.main()
    finally:
        sys.argv = previous
    return arguments[1:]


def validate_outputs(output, cv2, fps, source_frames):
    """Check saved artifacts, including a full MP4 decode, before reporting success."""
    from module_2.adapters import to_sg4, validate_sg4_cue
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    records = []
    with ((output / "sg1.jsonl").open(encoding="utf-8") as sg1,
          (output / "sg2.jsonl").open(encoding="utf-8") as sg2,
          (output / "sg4.jsonl").open(encoding="utf-8") as sg4):
        previous = -1.0
        for index, lines in enumerate(zip_longest(sg1, sg2, sg4)):
            if any(line is None for line in lines):
                raise DemoError("Output record streams have different lengths.")
            upstream, result, cue = [json.loads(line) for line in lines]
            timestamp = upstream["timestamp_ms"] / 1000
            validate_sg4_cue(cue)
            if not (upstream["frame_id"] == result["frame_id"] == cue["frame_id"] == index
                    and result["timestamp_sec"] == cue["timestamp"] == timestamp
                    and timestamp > previous and abs(timestamp - index / fps) <= 0.000501
                    and cue == to_sg4(result) and result["ear_threshold"] == 0.15
                    and not result["cnn"]["called"]):
                raise DemoError(f"Output synchronization/selected-method mismatch at frame {index}.")
            records.append(result)
            previous = timestamp
    count = len(records)
    if (not count or count != summary["frames"] or summary["unprocessed_container_tail"] != 0
            or (source_frames > 0 and count != source_frames)
            or dict(Counter(row["eye_state"] for row in records)) != summary["counts"]["FINAL"]
            or summary["cnn_inference_calls"] != 0):
        raise DemoError("Incomplete video or inconsistent summary counts.")
    events = json.loads((output / "closures.json").read_text(encoding="utf-8"))
    if (len(events) != summary["closure_events"] or
            sum(row["is_blink_candidate"] for row in records) != summary["blink_candidates"]):
        raise DemoError("Closure/blink-candidate summary mismatch.")
    capture = cv2.VideoCapture(str(output / "overlay.mp4"))
    decoded = 0
    try:
        if not capture.isOpened() or not math.isclose(capture.get(cv2.CAP_PROP_FPS), fps):
            raise DemoError("Annotated MP4 cannot be opened or its FPS differs.")
        while capture.read()[0]:
            decoded += 1
    finally:
        capture.release()
    if decoded != count:
        raise DemoError(f"Annotated MP4 decodes to {decoded} frames; expected {count}.")
    verification = dict(status="PASS", records_per_stream=count, decoded_annotated_frames=decoded,
                        frame_ids_timestamps_and_sg4_cues_valid=True, cnn_inference_calls=0)
    (output / "verification.json").write_text(json.dumps(verification, indent=2) + "\n")
    return records, summary


def export_presentation(records, output):
    """Plot saved predictions without smoothing/reclassification; preserve nested CSV data."""
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt
    with (output / "sg2.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        for row in records:
            writer.writerow({key: json.dumps(value, allow_nan=False) if isinstance(value, (dict, list))
                             else value for key, value in row.items()})
    times = [row["timestamp_sec"] for row in records]
    figure, axis = plt.subplots(figsize=(12, 4))
    for field, label in (("left_ear", "Left EAR"), ("right_ear", "Right EAR"), ("ear", "Average EAR")):
        axis.plot(times, [row[field] if row[field] is not None else math.nan for row in records],
                  label=label, linewidth=1)
    axis.axhline(records[0]["ear_threshold"], color="black", linestyle="--", label="Threshold 0.15")
    axis.set(xlabel="Source timestamp (seconds)", ylabel="EAR", title="SG-2 observed EAR (no added filtering)")
    axis.legend(); axis.grid(alpha=0.25)
    figure.savefig(output / "ear_timeline.png", dpi=160, bbox_inches="tight")
    plt.close(figure)
    figure, axis = plt.subplots(figsize=(12, 3))
    states = {"UNKNOWN": -1, "CLOSED": 0, "OPEN": 1}
    axis.scatter(times, [states[row["eye_state"]] for row in records], s=5)
    axis.set(yticks=[-1, 0, 1], yticklabels=["UNKNOWN", "CLOSED", "OPEN"],
             xlabel="Source timestamp (seconds)", title="SG-2 final state at each observed frame")
    axis.grid(alpha=0.25)
    figure.savefig(output / "eye_state_timeline.png", dpi=160, bbox_inches="tight")
    plt.close(figure)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, help="Original video; otherwise search repository input folders")
    parser.add_argument("--model", type=Path, help="Existing official Face Landmarker .task asset")
    parser.add_argument("--output", type=Path, default=MODULE / "results/instructor_demo",
                        help="Output parent; always create a unique run subdirectory")
    args = parser.parse_args(argv)
    output = None
    try:
        # 1. Resolve originals and verify the approved configuration, without altering it.
        video = find_video(args.video)
        source = require_file(REPOSITORY / "module_1/scripts/sg1_detector.py", "actual SG-1 detector")
        require_file(REPOSITORY / "module_4/D2-SG4.ipynb", "SG-4 analyzer notebook")
        model = find_model(args.model)
        selected = selected_settings()
        output = new_run_directory(args.output)
        os.environ.setdefault("MPLCONFIGDIR", str(output / ".mplconfig"))
        loaded = dependencies()
        from module_2.events import ClosureTracker
        tracker = ClosureTracker()  # Read existing event bounds for explanation, not a second tracker pipeline.
        capture = loaded["cv2"].VideoCapture(str(video))
        try:
            if not capture.isOpened():
                raise DemoError(f"Cannot decode original video: {video}.")
            fps = capture.get(loaded["cv2"].CAP_PROP_FPS)
            frames = int(capture.get(loaded["cv2"].CAP_PROP_FRAME_COUNT))
            if not math.isfinite(fps) or fps <= 0:
                raise DemoError("Video must have a known positive FPS.")
        finally:
            capture.release()
        # 2. Explain the method and traceable inputs before starting fresh inference.
        print("\nSG-2 INSTRUCTOR DEMONSTRATION", flush=True)
        print(f"Selected method: EAR-only; EAR threshold: {selected['ear_threshold']}")
        print(f"Temporal filter: immediate CLOSED; OPEN confirmation {selected['open_frames']} frames; "
              f"maximum configured delay {selected['max_open_delay_sec']} s; gap reset {tracker.max_gap} s")
        print(f"Blink criteria: complete uncensored closure, {tracker.blink_min} to {tracker.blink_max} s")
        print("Blink outputs are predicted candidates, NOT human-verified blinks.")
        print(f"SG-1 input: fresh actual detector {source}; no cached landmark input")
        print("SG-4 output: sg2.sg4.v2 hard-state cues via existing SG4Bridge; "
              "native nullable-confidence handling remains a consumer caveat; SG-3 cues disabled")
        print(f"Video: {video.name}; FPS: {fps:g}; container frames: {frames}")
        print(f"Output directory: {output}", flush=True)
        metadata = dict(status="RUNNING", video=str(video), model=str(model), sg1_source=str(source),
                        sg1_source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                        method=selected, fresh_sg1=True, cached_landmarks_used=False)
        (output / "run_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
        # 3. Delegate ALL detection, temporal filtering, event tracking and annotation.
        arguments = run_pipeline(video, model, output)
        # 4. Validate persisted streams/video, then export presentation-only artifacts.
        records, summary = validate_outputs(output, loaded["cv2"], fps, frames)
        export_presentation(records, output)
        metadata.update(status="PASS", pipeline_arguments=arguments)
        (output / "run_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
        # 5. Present the observed predictions and exact artifact locations.
        print("\nVERIFIED DEMONSTRATION COMPLETE")
        print(f"Total frames processed: {summary['frames']}")
        print("Frame states: " + ", ".join(f"{state}={summary['counts']['FINAL'].get(state, 0)}"
                                             for state in ("OPEN", "CLOSED", "UNKNOWN")))
        print(f"Closure events: {summary['closure_events']}; predicted blink candidates: {summary['blink_candidates']}")
        for label, filename in (("Annotated video", "overlay.mp4"), ("EAR graph", "ear_timeline.png"),
                                ("Eye-state timeline", "eye_state_timeline.png"), ("SG-2 JSONL", "sg2.jsonl"),
                                ("SG-2 CSV", "sg2.csv"), ("SG-4 cues", "sg4.jsonl"),
                                ("Fresh SG-1 records", "sg1.jsonl"), ("Closure summary", "closures.json"),
                                ("Results summary", "summary.json"), ("Validation", "verification.json")):
            print(f"{label}: {output / filename}")
        return 0
    except (DemoError, OSError, ValueError, ImportError, RuntimeError) as error:
        print(f"Instructor demo failed: {error}", file=sys.stderr)
        if output is not None:
            print(f"Partial outputs, if any, retained in: {output}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    # Also allow VS Code's Run Python File action; -m remains the documented command.
    if __package__ in (None, ""):
        sys.path.insert(0, str(REPOSITORY))
    raise SystemExit(main())
