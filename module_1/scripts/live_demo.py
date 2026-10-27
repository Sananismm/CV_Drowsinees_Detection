"""Preview the SG-1 face/landmark detector on a webcam or saved video.

The preview does not record or upload frames. FPS shown on screen is a rough
preview rate, not the controlled benchmark from run_experiment.py.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
import sys
import time

import cv2

from run_experiment import ROOT, read_configs
from sg1_detector import SG1FaceLandmarkDetector, draw_result


WINDOW_NAME = "SG-1 live face and landmark demo"


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--camera", type=int, help="OpenCV webcam index (default: 0)")
    source.add_argument("--video", type=Path, help="Use a saved video instead of a webcam")
    parser.add_argument("--config", type=Path, default=ROOT / "configs" / "experiment.json")
    parser.add_argument("--preset", default="lower_resolution", help="Configuration name (default: lower_resolution)")
    parser.add_argument("--display-width", type=int, default=1280, help="Maximum preview width in pixels")
    parser.add_argument("--max-frames", type=int, default=0, help="Stop after this many frames; 0 means no limit")
    parser.add_argument("--headless", action="store_true", help="Process without opening a preview window")
    return parser


def validate_args(parser, args):
    if args.camera is not None and args.camera < 0:
        parser.error("--camera must be a non-negative index")
    if args.video is not None and not args.video.is_file():
        parser.error(f"Video not found: {args.video}")
    if args.display_width < 1:
        parser.error("--display-width must be positive")
    if args.max_frames < 0:
        parser.error("--max-frames must be non-negative")
    if args.headless and args.video is None and args.max_frames == 0:
        parser.error("headless webcam mode requires --max-frames so it stops automatically")


def _display_frame(frame, output, source_label, preview_fps, max_width):
    """Draw after inference, then shrink only the displayed copy if needed."""
    preview = draw_result(frame.copy(), output)
    lines = (
        f"{source_label} | {output['status']} | {output['landmark_count']} landmarks | preview {preview_fps:.1f} FPS",
        "SG-1: face and landmarks (not a drowsiness decision)",
        "Press Q or Esc to exit",
    )
    for index, line in enumerate(lines):
        y = 28 + index * 26
        cv2.putText(preview, line, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 4)
        cv2.putText(preview, line, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
    height, width = preview.shape[:2]
    if width > max_width:
        scale = max_width / width
        preview = cv2.resize(preview, (max_width, max(1, round(height * scale))), interpolation=cv2.INTER_AREA)
    return preview


def run_preview(args, config, model_path, *, capture_factory=None, detector_factory=None, clock=None):
    """Run the preview and return counts; injectable factories support camera-free tests."""
    capture_factory = capture_factory or cv2.VideoCapture
    detector_factory = detector_factory or SG1FaceLandmarkDetector
    clock = clock or time.monotonic
    is_video = args.video is not None
    source = str(args.video) if is_video else (args.camera if args.camera is not None else 0)
    source_label = f"Video: {args.video.name}" if is_video else f"Camera: {source}"
    capture = detector = None
    window_open = False
    processed = face_count = no_face_count = 0
    last_timestamp = -1
    started = None

    try:
        capture = capture_factory(source)
        if not capture.isOpened():
            raise RuntimeError(f"Could not open {source_label}. Check the camera index or video path.")
        source_fps = float(capture.get(cv2.CAP_PROP_FPS)) if is_video else 0.0
        if is_video and (not math.isfinite(source_fps) or source_fps <= 0):
            source_fps = 25.0
            print("Video FPS unavailable; using 25 FPS for playback and timestamps.", file=sys.stderr)
        detector = detector_factory(model_path, config)
        if not args.headless:
            try:
                cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
            except cv2.error as exc:
                raise RuntimeError("Could not open a preview window. Check the OpenCV GUI installation.") from exc
            window_open = True
        started = clock()
        while not args.max_frames or processed < args.max_frames:
            ok, frame = capture.read()
            if not ok or frame is None:
                if is_video and processed:
                    break
                kind = "video" if is_video else "camera"
                raise RuntimeError(f"Could not read a frame from the {kind} after {processed} frame(s).")

            if is_video:
                timestamp = int(round(processed * 1000.0 / source_fps))
            else:
                timestamp = int(max(0.0, clock() - started) * 1000.0)
            timestamp = max(timestamp, last_timestamp + 1)
            last_timestamp = timestamp
            output = detector.process(frame, processed, timestamp)
            processed += 1
            if output["status"] == "OK":
                face_count += 1
            elif output["status"] == "NO_FACE":
                no_face_count += 1
            else:
                raise RuntimeError(f"Unexpected SG-1 status: {output['status']}")

            if not args.headless:
                elapsed = max(clock() - started, 1e-9)
                preview = _display_frame(frame, output, source_label, processed / elapsed, args.display_width)
                cv2.imshow(WINDOW_NAME, preview)
                # Keep saved-video playback near its source rate; headless runs do not sleep.
                if is_video:
                    delay_ms = max(1, round((started + processed / source_fps - clock()) * 1000))
                else:
                    delay_ms = 1
                key = cv2.waitKey(delay_ms) & 0xFF
                if key in (ord("q"), ord("Q"), 27):
                    break
                try:
                    if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
                        break
                except cv2.error:
                    break  # Some OpenCV backends raise after the user closes the window.

        return {"source": source_label, "processed": processed, "faces": face_count, "no_face": no_face_count}
    finally:
        try:
            if detector is not None:
                detector.close()
        finally:
            try:
                if capture is not None:
                    capture.release()
            finally:
                if window_open:
                    cv2.destroyAllWindows()


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    validate_args(parser, args)
    try:
        _, configs, model_path = read_configs(args.config.resolve())
        config = next((item for item in configs if item.name == args.preset), None)
        if config is None:
            raise ValueError(f"Unknown preset {args.preset!r}; choose from: {', '.join(item.name for item in configs)}")
        print("SG-1 preview: face and landmarks only, not a drowsiness decision.")
        print("No footage is saved. Press Q or Esc to close the preview.")
        result = run_preview(args, config, model_path)
    except (OSError, ValueError, RuntimeError, cv2.error) as exc:
        print(f"SG-1 preview error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("SG-1 preview stopped.")
        return 130
    print(f"{result['source']}: {result['processed']} frames, {result['faces']} OK, {result['no_face']} NO_FACE.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
