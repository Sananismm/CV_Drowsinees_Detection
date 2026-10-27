from dataclasses import dataclass
from pathlib import Path
import time

import cv2
import mediapipe as mp
import numpy as np

from sg1_contract import LANDMARK_TOPOLOGY, SCHEMA_VERSION


def clamped_landmark_box(coords, image_width: int, image_height: int):
    """Return an in-frame xyxy box for normalized landmark coordinates."""

    points = np.asarray(coords, dtype=np.float32)
    if points.ndim != 2 or points.shape[1] != 2 or len(points) == 0:
        raise ValueError("coords must contain at least one normalized [x,y] point")
    if not np.isfinite(points).all():
        raise ValueError("coords must contain only finite values")
    if image_width < 1 or image_height < 1:
        raise ValueError("image dimensions must be positive")

    x1 = max(0, min(image_width, int(np.floor(points[:, 0].min() * image_width))))
    y1 = max(0, min(image_height, int(np.floor(points[:, 1].min() * image_height))))
    x2 = max(0, min(image_width, int(np.ceil(points[:, 0].max() * image_width))))
    y2 = max(0, min(image_height, int(np.ceil(points[:, 1].max() * image_height))))
    return [x1, y1, x2, y2]


@dataclass(frozen=True)
class DetectorConfig:
    name: str
    input_long_side: int
    min_face_detection_confidence: float
    min_face_presence_confidence: float
    min_tracking_confidence: float


class SG1FaceLandmarkDetector:
    """Single-driver face/landmark detector with a stable SG-1 output schema."""

    def __init__(self, model_path: Path, config: DetectorConfig):
        self.config = config
        options = mp.tasks.vision.FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(model_path)),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_faces=1,
            min_face_detection_confidence=config.min_face_detection_confidence,
            min_face_presence_confidence=config.min_face_presence_confidence,
            min_tracking_confidence=config.min_tracking_confidence,
            output_face_blendshapes=False,
        )
        self._task = mp.tasks.vision.FaceLandmarker.create_from_options(options)
        self._last_timestamp = -1

    def close(self):
        self._task.close()

    def _resize(self, frame):
        h, w = frame.shape[:2]
        side = max(h, w)
        if side <= self.config.input_long_side:
            return frame
        scale = self.config.input_long_side / side
        return cv2.resize(frame, (max(1, round(w * scale)), max(1, round(h * scale))), interpolation=cv2.INTER_AREA)

    def process(self, frame_bgr, frame_id: int, timestamp_ms: int):
        started = time.perf_counter()
        if (
            not isinstance(frame_bgr, np.ndarray)
            or frame_bgr.ndim != 3
            or frame_bgr.shape[2] != 3
            or frame_bgr.size == 0
        ):
            raise ValueError("frame_bgr must be a non-empty HxWx3 NumPy array")
        if not isinstance(frame_id, int) or isinstance(frame_id, bool) or frame_id < 0:
            raise ValueError("frame_id must be a non-negative integer")
        h, w = frame_bgr.shape[:2]
        frame = self._resize(frame_bgr)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
        timestamp_ms = max(int(timestamp_ms), self._last_timestamp + 1)
        self._last_timestamp = timestamp_ms
        result = self._task.detect_for_video(mp_image, timestamp_ms)
        elapsed_ms = (time.perf_counter() - started) * 1000.0

        base = {
            "schema_version": SCHEMA_VERSION,
            "frame_id": int(frame_id),
            "timestamp_ms": int(timestamp_ms),
            "image_width": int(w),
            "image_height": int(h),
            "landmark_topology": LANDMARK_TOPOLOGY,
            "config_name": self.config.name,
        }
        if not result.face_landmarks:
            return {
                **base,
                "status": "NO_FACE",
                "face_bbox_xyxy": None,
                "landmarks_xy_normalized": [],
                "landmark_count": 0,
                "detection_confidence": None,
                "inference_ms": elapsed_ms,
            }

        landmarks = result.face_landmarks[0]
        coords = np.asarray([[float(p.x), float(p.y)] for p in landmarks], dtype=np.float32)
        # Coordinates are normalized to the resized image; preserve full-frame geometry
        # by mapping the normalized points through the same scale ratio.
        face_box = clamped_landmark_box(coords, w, h)
        return {
            **base,
            "status": "OK",
            "face_bbox_xyxy": face_box,
            "landmarks_xy_normalized": coords.round(6).tolist(),
            "landmark_count": int(len(coords)),
            # The MediaPipe Tasks result exposes landmarks, not the detector's per-face
            # confidence score. Thresholds are not scores, so do not mislabel them.
            "detection_confidence": None,
            "inference_ms": elapsed_ms,
        }


def draw_result(frame, output):
    box = output.get("face_bbox_xyxy")
    if box:
        x1, y1, x2, y2 = box
        cv2.rectangle(frame, (x1, y1), (x2, y2), (40, 145, 255), 2)
        cv2.putText(frame, f"SG1 {output['config_name']}", (x1, max(22, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (40, 145, 255), 2)
        w, h = output["image_width"], output["image_height"]
        for x, y in output["landmarks_xy_normalized"]:
            cv2.circle(frame, (int(x * w), int(y * h)), 1, (60, 230, 120), -1)
    else:
        cv2.putText(frame, "NO FACE", (20, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (30, 30, 230), 2)
    return frame
