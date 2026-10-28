
import cv2
import mediapipe as mp
import numpy as np
import math
import time
import urllib.request
import os

# SETTINGS
START_THRESHOLD = 0.50
HOLD_THRESHOLD = 0.45
YAWN_DURATION = 1.5

MODEL_PATH = "face_landmarker.task"

# Download the face landmark model once
if not os.path.exists(MODEL_PATH):
    print("Downloading MediaPipe face model...")
    urllib.request.urlretrieve(
        "https://storage.googleapis.com/mediapipe-models/"
        "face_landmarker/face_landmarker/float16/1/"
        "face_landmarker.task",
        MODEL_PATH
    )

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

options = vision.FaceLandmarkerOptions(
    base_options=python.BaseOptions(
        model_asset_path=MODEL_PATH
    ),
    running_mode=vision.RunningMode.VIDEO,
    num_faces=1
)

detector = vision.FaceLandmarker.create_from_options(options)

def distance(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)

def calculate_mar(lm):
    width = distance(lm[61], lm[291])

    if width < 1e-6:
        return np.nan

    gaps = [
        distance(lm[13], lm[14]),
        distance(lm[82], lm[87]),
        distance(lm[312], lm[317])
    ]

    return sum(gaps) / (3 * width)

# Open laptop webcam
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

if not cap.isOpened():
    detector.close()
    raise RuntimeError("Cannot open webcam.")

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

yawn_count = 0
open_start = None
counted = False
last_seen = None
session_start = time.monotonic()

# Allow small fluctuations without immediately resetting
MAX_GAP = 0.20

print("Webcam started. Press Q to quit.")

try:
    while True:
        ret, frame = cap.read()

        if not ret:
            print("Failed to read webcam frame.")
            break

        frame = cv2.flip(frame, 1)
        now = time.monotonic()

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb
        )

        timestamp_ms = int((now - session_start) * 1000)

        result = detector.detect_for_video(
            image, timestamp_ms
        )

        mar = np.nan
        status = "FACE NOT DETECTED"
        color = (0, 165, 255)

        if result.face_landmarks:
            lm = result.face_landmarks[0]
            mar = calculate_mar(lm)

            h, w = frame.shape[:2]

            # Draw mouth landmarks
            for idx in [61, 291, 13, 14, 82, 87, 312, 317]:
                x = int(lm[idx].x * w)
                y = int(lm[idx].y * h)

                cv2.circle(
                    frame, (x, y), 3,
                    (0, 255, 255), -1
                )

            if np.isfinite(mar):
                if open_start is None:
                    if mar >= START_THRESHOLD:
                        open_start = now
                        last_seen = now
                        counted = False

                elif mar >= HOLD_THRESHOLD:
                    last_seen = now

                elif now - last_seen > MAX_GAP:
                    open_start = None
                    last_seen = None
                    counted = False

                if open_start is not None:
                    elapsed = now - open_start

                    if elapsed >= YAWN_DURATION:
                        if not counted:
                            yawn_count += 1
                            counted = True

                        status = "YAWN DETECTED"
                        color = (0, 0, 255)
                    else:
                        status = "Checking mouth opening"
                        color = (0, 255, 255)
                else:
                    status = "No yawn"
                    color = (0, 255, 0)
            else:
                open_start = None
                last_seen = None
                counted = False

        else:
            open_start = None
            last_seen = None
            counted = False

        mar_text = (
            f"MAR: {mar:.3f}"
            if np.isfinite(mar)
            else "MAR: N/A"
        )

        cv2.putText(
            frame, mar_text, (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8, (255, 255, 0), 2
        )

        cv2.putText(
            frame, status, (20, 75),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7, color, 2
        )

        cv2.putText(
            frame, f"Yawn Count: {yawn_count}",
            (20, 115),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7, (255, 255, 255), 2
        )

        cv2.imshow("Live Yawn Detection", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

finally:
    cap.release()
    detector.close()
    cv2.destroyAllWindows()

print("Total yawns detected:", yawn_count)
