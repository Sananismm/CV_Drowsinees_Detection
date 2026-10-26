import cv2
import json
import time
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRAMES = ROOT / "evidence" / "benchmark_frames"
MODEL = ROOT / "models" / "face_detection_yunet_2023mar.onnx"
OUTPUT = ROOT / "evidence" / "detector_benchmark.json"

images = sorted(FRAMES.glob("frame_*.jpg"))

if len(images) != 150:
    raise SystemExit(f"Expected 150 images, found {len(images)}")

if not MODEL.is_file():
    raise SystemExit("YuNet model missing")

haar_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
haar = cv2.CascadeClassifier(haar_path)

if haar.empty():
    raise SystemExit("Haar classifier could not be loaded")

sample = cv2.imread(str(images[0]))

if sample is None:
    raise SystemExit("Cannot read first benchmark image")

h, w = sample.shape[:2]

yunet = cv2.FaceDetectorYN_create(
    str(MODEL), "", (w, h), 0.6, 0.3, 5000
)

def detect_haar(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = haar.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(40, 40)
    )
    return len(faces)

def detect_yunet(frame):
    yunet.setInputSize((frame.shape[1], frame.shape[0]))
    _, faces = yunet.detect(frame)
    return 0 if faces is None else len(faces)

def benchmark(name, detector, frames):
    timings = []
    detections = []
    frames_with_faces = 0

    # Warm up model / detector without measuring.
    for _ in range(5):
        detector(frames[0])

    for frame in frames:
        start = time.perf_counter()
        count = detector(frame)
        elapsed = time.perf_counter() - start

        timings.append(elapsed)
        detections.append(count)

        if count > 0:
            frames_with_faces += 1

    total_time = sum(timings)

    result = {
        "detector": name,
        "frames_processed": len(frames),
        "frames_with_faces": frames_with_faces,
        "total_face_detections": sum(detections),
        "face_coverage_percent": round(
            100 * frames_with_faces / len(frames), 2
        ),
        "mean_inference_ms": round(
            statistics.mean(timings) * 1000, 2
        ),
        "inference_fps": round(
            len(frames) / total_time, 2
        ),
    }

    print(json.dumps(result, indent=2))
    return result

print("=== SG6 DETECTOR BENCHMARK ===")
print("OpenCV:", cv2.__version__)
print("Frames:", len(images))

# Load identical images for both detectors.
frames = []
for path in images:
    frame = cv2.imread(str(path))
    if frame is None:
        raise SystemExit(f"Cannot read {path}")
    frames.append(frame)

results = {
    "opencv_version": cv2.__version__,
    "dataset_frames": len(frames),
    "haar": benchmark("Haar Cascade", detect_haar, frames),
    "yunet": benchmark("YuNet", detect_yunet, frames),
}

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(results, indent=2))

print("\nResults saved:", OUTPUT)
print("RESULT: BENCHMARK COMPLETED")
