from pathlib import Path
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "models" / "face_landmarker.task"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/1/face_landmarker.task"
)


def main():
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    if MODEL_PATH.exists() and MODEL_PATH.stat().st_size > 1_000_000:
        print(f"Model already present: {MODEL_PATH}")
        return
    print(f"Downloading official MediaPipe model to {MODEL_PATH}")
    with urlopen(MODEL_URL, timeout=60) as response, MODEL_PATH.open("wb") as out:
        while True:
            block = response.read(1024 * 1024)
            if not block:
                break
            out.write(block)
    if MODEL_PATH.stat().st_size < 1_000_000:
        MODEL_PATH.unlink(missing_ok=True)
        raise RuntimeError("Downloaded model is unexpectedly small; download failed.")
    print(f"Downloaded {MODEL_PATH.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
