import cv2
import time
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
EVIDENCE = BASE / "evidence"
EVIDENCE.mkdir(exist_ok=True)

MODEL = "/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml"

detector = cv2.CascadeClassifier(MODEL)

if detector.empty():
    sys.exit("ERROR: Face detection model could not be loaded")

cap = cv2.VideoCapture(0, cv2.CAP_V4L2)

if not cap.isOpened():
    sys.exit("ERROR: Camera /dev/video0 could not be opened")

print("=== SG6 LIVE FACE DETECTION TEST ===")

total_frames = 0
frames_with_faces = 0
total_faces = 0
inference_times = []
first_face_saved = False

start = time.perf_counter()

try:
    for frame_id in range(150):
        ok, frame = cap.read()

        if not ok:
            print("WARNING: Frame capture failed")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        t0 = time.perf_counter()

        faces = detector.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(40, 40),
        )

        inference_ms = (time.perf_counter() - t0) * 1000
        inference_times.append(inference_ms)

        total_frames += 1
        total_faces += len(faces)

        if len(faces) > 0:
            frames_with_faces += 1

        for x, y, w, h in faces:
            cv2.rectangle(
                frame,
                (x, y),
                (x + w, y + h),
                (0, 255, 0),
                2,
            )

        if len(faces) > 0 and not first_face_saved:
            cv2.imwrite(
                str(EVIDENCE / "face_detection_sample.jpg"),
                frame
            )
            first_face_saved = True

        if frame_id % 30 == 0:
            print(
                f"Frame {frame_id}: "
                f"{len(faces)} face(s), "
                f"inference {inference_ms:.2f} ms"
            )

finally:
    cap.release()

elapsed = time.perf_counter() - start

if total_frames == 0:
    sys.exit("ERROR: No frames captured")

results = {
    "detector": "OpenCV Haar Cascade",
    "device": "/dev/video0",
    "frames_processed": total_frames,
    "frames_with_faces": frames_with_faces,
    "total_face_detections": total_faces,
    "face_coverage": frames_with_faces / total_frames,
    "mean_detection_ms": sum(inference_times) / len(inference_times),
    "end_to_end_fps": total_frames / elapsed,
}

with open(EVIDENCE / "face_detection_results.json", "w") as f:
    json.dump(results, f, indent=2)

print("\n=== RESULTS ===")
print(json.dumps(results, indent=2))
print("\nEvidence saved to:", EVIDENCE)
print("RESULT: TEST COMPLETED")
