"""Generate real SG-1 V1 fixtures from tracked, reviewable inputs."""

import json
from pathlib import Path

import cv2
import numpy as np

from sg1_contract import to_sg2_input, validate_sg1_record
from sg1_detector import DetectorConfig, SG1FaceLandmarkDetector


MODULE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = MODULE_ROOT.parent
MODEL_PATH = MODULE_ROOT / "models" / "face_landmarker.task"
SOURCE_IMAGE = (
    MODULE_ROOT
    / "results"
    / "downloaded_samples"
    / "qualitative_review.png"
)
OUTPUT_DIR = REPOSITORY_ROOT / "interfaces" / "examples"


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def main():
    image = cv2.imread(str(SOURCE_IMAGE))
    if image is None:
        raise RuntimeError(f"could not read fixture source: {SOURCE_IMAGE}")

    # The tracked contact sheet contains five 640x360 panels.
    # Crop the primary face from the first panel. Running on the whole panel at
    # 256 px makes the face too small and correctly produces NO_FACE.
    positive_frame = image[30:270, 130:360].copy()
    black_frame = np.zeros((240, 320, 3), dtype=np.uint8)
    config = DetectorConfig("fixture_baseline", 256, 0.5, 0.5, 0.5)
    detector = SG1FaceLandmarkDetector(MODEL_PATH, config)
    try:
        positive = detector.process(positive_frame, frame_id=0, timestamp_ms=0)
        no_face = detector.process(black_frame, frame_id=1, timestamp_ms=40)
    finally:
        detector.close()

    validate_sg1_record(positive)
    validate_sg1_record(no_face)
    if positive["status"] != "OK":
        raise RuntimeError("tracked positive fixture source produced NO_FACE")
    if no_face["status"] != "NO_FACE":
        raise RuntimeError("black fixture source unexpectedly produced a face")

    # Timing varies by machine. Fixtures test structure, not benchmark values.
    positive["inference_ms"] = 0.0
    no_face["inference_ms"] = 0.0

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_json(OUTPUT_DIR / "sg1_v1_ok.json", positive)
    write_json(OUTPUT_DIR / "sg1_v1_no_face.json", no_face)
    write_json(OUTPUT_DIR / "sg1_to_sg2_v1_ok.json", to_sg2_input(positive))
    write_json(OUTPUT_DIR / "sg1_to_sg2_v1_no_face.json", to_sg2_input(no_face))
    print(f"Wrote verified interface fixtures to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
