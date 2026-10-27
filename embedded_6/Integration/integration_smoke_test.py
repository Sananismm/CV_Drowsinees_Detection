import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
MOCK = BASE / "mock_data"


def load_json(filename):
    path = MOCK / filename

    print(f"Loading: {path}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


sg1 = load_json("sg1_output.json")
sg2 = load_json("sg2_output.json")
sg3 = load_json("sg3_output.json")
sg4 = load_json("sg4_output.json")
sg5 = load_json("sg5_output.json")


print("\n=== SG6 INTEGRATION SMOKE TEST ===")


print("\n[SG1] Face & Landmark Detection")
print("Face Detected:", sg1["face_detected"])
print("Face Confidence:", sg1["face_confidence"])
print("Face Bounding Box:", sg1["face_bbox"])


print("\n[SG2] Eye State & Blink Analysis")
print("Eyes Closed:", sg2["eyes_closed"])
print("Eye Metric:", sg2["eye_metric"])
print("Blink Detected:", sg2["blink_detected"])


print("\n[SG3] Yawn & Facial Cue Analysis")
print("Yawn Detected:", sg3["yawn_detected"])
print("Mouth Metric:", sg3["mouth_metric"])
print("Confidence:", sg3["confidence"])


print("\n[SG4] Temporal Behaviour Analysis")
print("Eye Closure Duration:", sg4["eye_closure_duration"])
print("Blink Frequency:", sg4["blink_frequency"])
print("Eye Warning:", sg4["eye_warning"])
print("Yawn Warning:", sg4["yawn_warning"])


print("\n[SG5] Drowsiness Decision")
print("Driver State:", sg5["driver_state"])
print("Alert:", sg5["alert"])
print("Confidence:", sg5["confidence"])


print("\n================================")
print("SG6 integration smoke test PASSED")
print("SG1 -> SG2/SG3 -> SG4 -> SG5 data interfaces loaded successfully.")
print("================================")
