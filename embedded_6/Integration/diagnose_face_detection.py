import cv2
from pathlib import Path

out = Path("embedded_6/evidence/diagnostic_frames")
out.mkdir(parents=True, exist_ok=True)

cap = cv2.VideoCapture(0, cv2.CAP_V4L2)

if not cap.isOpened():
    raise RuntimeError("Camera could not be opened")

cascade_path = (
    "/usr/share/opencv4/haarcascades/"
    "haarcascade_frontalface_default.xml"
)

detector = cv2.CascadeClassifier(cascade_path)

if detector.empty():
    cap.release()
    raise RuntimeError("Haar model failed to load")

print("=== SG6 FACE DETECTION DIAGNOSTIC ===")
print("Keep your face visible, facing the camera.")
print("Testing 90 frames...")

try:
    for i in range(90):
        ok, frame = cap.read()

        if not ok:
            print(f"Capture failed at frame {i}")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = detector.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(40, 40)
        )

        if i % 15 == 0:
            # Save both original and annotated frames.
            cv2.imwrite(str(out / f"raw_{i:03d}.jpg"), frame)

            annotated = frame.copy()

            for x, y, w, h in faces:
                cv2.rectangle(
                    annotated,
                    (x, y),
                    (x + w, y + h),
                    (0, 255, 0),
                    2
                )

            cv2.imwrite(
                str(out / f"detected_{i:03d}.jpg"),
                annotated
            )

            print(f"Frame {i}: {len(faces)} face(s)")

finally:
    cap.release()

print("Diagnostics saved to:", out)
