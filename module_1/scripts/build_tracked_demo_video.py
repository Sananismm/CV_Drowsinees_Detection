"""Build a local SG-1 demo video from the tracked qualitative contact sheet.

This is a reproducible setup/demo input. It is not accuracy-test data.
"""

import argparse
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = (
    ROOT / "results" / "downloaded_samples" / "qualitative_review.png"
)
DEFAULT_OUTPUT = ROOT / "data" / "videos" / "sg1_tracked_demo.mp4"


def find_face_crop(panel):
    green = (
        (panel[:, :, 1] > 180)
        & (panel[:, :, 0] < 120)
        & (panel[:, :, 2] < 120)
    )
    green[:40] = False
    ys, xs = np.where(green)
    if len(xs) == 0:
        raise RuntimeError("could not find the tracked green face box")

    x1, x2 = int(xs.min()), int(xs.max())
    y1, y2 = int(ys.min()), int(ys.max())
    box_w = max(1, x2 - x1)
    box_h = max(1, y2 - y1)
    margin_x = int(box_w * 0.65)
    margin_y = int(box_h * 0.45)
    return panel[
        max(0, y1 - margin_y) : min(panel.shape[0], y2 + margin_y),
        max(0, x1 - margin_x) : min(panel.shape[1], x2 + margin_x),
    ].copy()


def letterbox(image, width=640, height=360):
    scale = min(width / image.shape[1], height / image.shape[0])
    resized = cv2.resize(
        image,
        (max(1, round(image.shape[1] * scale)), max(1, round(image.shape[0] * scale))),
        interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR,
    )
    canvas = np.zeros((height, width, 3), dtype=np.uint8)
    x = (width - resized.shape[1]) // 2
    y = (height - resized.shape[0]) // 2
    canvas[y : y + resized.shape[0], x : x + resized.shape[1]] = resized
    return canvas


def main():
    parser = argparse.ArgumentParser(
        description="Build a reproducible local demo video from tracked SG-1 evidence."
    )
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--fps", type=float, default=10.0)
    parser.add_argument("--frames-per-person", type=int, default=20)
    parser.add_argument("--black-frames", type=int, default=10)
    args = parser.parse_args()

    sheet = cv2.imread(str(args.source))
    if sheet is None:
        raise RuntimeError(f"could not read source image: {args.source}")
    if sheet.shape[0] % 5:
        raise RuntimeError("expected the tracked five-panel qualitative contact sheet")

    panel_height = sheet.shape[0] // 5
    frames = []
    for index in range(5):
        panel = sheet[index * panel_height : (index + 1) * panel_height]
        crop = find_face_crop(panel)
        frame = letterbox(crop)
        cv2.putText(
            frame,
            f"Tracked demo subject {index + 1}/5",
            (12, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2,
        )
        frames.extend(frame.copy() for _ in range(args.frames_per_person))

    black = np.zeros((360, 640, 3), dtype=np.uint8)
    cv2.putText(
        black,
        "Intentional NO_FACE segment",
        (140, 185),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
    )
    frames.extend(black.copy() for _ in range(args.black_frames))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        str(args.output),
        cv2.VideoWriter_fourcc(*"mp4v"),
        args.fps,
        (640, 360),
    )
    if not writer.isOpened():
        raise RuntimeError(f"could not create demo video: {args.output}")
    try:
        for frame in frames:
            writer.write(frame)
    finally:
        writer.release()

    print(f"Wrote {len(frames)} frames to {args.output}")
    print("Purpose: setup and interface demonstration only")
    print("Do not use this generated video for an accuracy claim")


if __name__ == "__main__":
    main()
