"""Verify the SG-1 environment, model, configuration and optional inference path."""

import argparse
import json
from pathlib import Path
import sys

import cv2
import mediapipe
import numpy as np

from download_model import MODEL_PATH, MODEL_SHA256, sha256_file, verify_model
from sg1_contract import validate_sg1_record
from sg1_detector import DetectorConfig, SG1FaceLandmarkDetector


ROOT = Path(__file__).resolve().parents[1]


def check_configuration():
    config_path = ROOT / "configs" / "experiment.json"
    data = json.loads(config_path.read_text(encoding="utf-8"))
    configurations = data.get("configurations")
    if not isinstance(configurations, list) or not configurations:
        raise RuntimeError("experiment.json has no configurations")
    for item in configurations:
        DetectorConfig(**item)
    return len(configurations)


def smoke_model():
    config = DetectorConfig("setup_smoke", 192, 0.5, 0.5, 0.5)
    detector = SG1FaceLandmarkDetector(MODEL_PATH, config)
    try:
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        output = detector.process(frame, frame_id=0, timestamp_ms=0)
    finally:
        detector.close()
    validate_sg1_record(output)
    if output["status"] != "NO_FACE":
        raise RuntimeError("black-frame smoke test should return NO_FACE")
    return output["inference_ms"]


def main():
    parser = argparse.ArgumentParser(description="Verify the SG-1 local setup.")
    parser.add_argument(
        "--smoke-model",
        action="store_true",
        help="Load the model and run one black-frame inference",
    )
    args = parser.parse_args()

    print(f"Python: {sys.version.split()[0]}")
    print(f"OpenCV: {cv2.__version__}")
    print(f"MediaPipe: {mediapipe.__version__}")
    print(f"NumPy: {np.__version__}")
    print(f"Configurations: {check_configuration()}")

    if not verify_model(MODEL_PATH):
        actual = sha256_file(MODEL_PATH) if MODEL_PATH.exists() else "MISSING"
        raise RuntimeError(
            f"model verification failed: expected {MODEL_SHA256}, found {actual}"
        )
    print(f"Model SHA-256: {MODEL_SHA256}")

    if args.smoke_model:
        elapsed = smoke_model()
        print(f"Black-frame NO_FACE smoke: PASS ({elapsed:.3f} ms)")

    print("SG-1 setup verification: PASS")


if __name__ == "__main__":
    main()
