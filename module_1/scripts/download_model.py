import hashlib
from pathlib import Path
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "models" / "face_landmarker.task"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/1/face_landmarker.task"
)
MODEL_SHA256 = "64184E229B263107BC2B804C6625DB1341FF2BB731874B0BCC2FE6544E0BC9FF"
MODEL_MIN_BYTES = 1_000_000


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def verify_model(path):
    if not path.exists() or path.stat().st_size < MODEL_MIN_BYTES:
        return False
    return sha256_file(path) == MODEL_SHA256


def main():
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    if verify_model(MODEL_PATH):
        print(f"Verified model already present: {MODEL_PATH}")
        return

    if MODEL_PATH.exists():
        print("Existing model failed verification and will be replaced.")

    temporary_path = MODEL_PATH.with_suffix(MODEL_PATH.suffix + ".part")
    temporary_path.unlink(missing_ok=True)
    print(f"Downloading official MediaPipe model to {MODEL_PATH}")
    try:
        with urlopen(MODEL_URL, timeout=60) as response, temporary_path.open(
            "wb"
        ) as out:
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                out.write(block)

        if not verify_model(temporary_path):
            raise RuntimeError("Downloaded model failed size or SHA-256 verification.")
        temporary_path.replace(MODEL_PATH)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    print(f"Downloaded {MODEL_PATH.stat().st_size:,} bytes")
    print(f"Verified SHA-256: {MODEL_SHA256}")


if __name__ == "__main__":
    main()
