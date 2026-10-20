import argparse
from pathlib import Path
import time

import cv2


def main():
    parser = argparse.ArgumentParser(description="Record a short driver-facing clip for the SG-1 experiment.")
    parser.add_argument("--camera", type=int, default=0, help="OpenCV camera index (default 0)")
    parser.add_argument("--duration", type=float, default=30, help="Recording length in seconds")
    parser.add_argument("--output", type=Path, default=Path("data/videos/driver_sample.mp4"))
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(args.camera)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open camera index {args.camera}")
    ok, frame = cap.read()
    if not ok:
        cap.release()
        raise RuntimeError("Camera opened but returned no frame")
    h, w = frame.shape[:2]
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps < 1 or fps > 120:
        fps = 20.0
    writer = cv2.VideoWriter(str(args.output), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    if not writer.isOpened():
        cap.release()
        raise RuntimeError(f"Could not write MP4 at {args.output}; check the output path and OpenCV codecs")
    print(f"Recording {args.duration:g} seconds to {args.output}. Press q to stop early.")
    start = time.monotonic()
    frames = 0
    while time.monotonic() - start < args.duration:
        if not ok:
            break
        writer.write(frame)
        frames += 1
        preview = frame.copy()
        cv2.putText(preview, f"Recording {time.monotonic() - start:0.1f}s - press q to stop", (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 220, 255), 2)
        cv2.imshow("SG-1 dataset capture", preview)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
        ok, frame = cap.read()
    writer.release()
    cap.release()
    cv2.destroyAllWindows()
    print(f"Saved {frames} frames ({frames / fps:.1f} encoded seconds) to {args.output}")
    print("Use only footage collected with consent and permitted by your course/team.")


if __name__ == "__main__":
    main()
