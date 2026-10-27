import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "reference_modules"))

from sg2_eye_analysis import create_output_packet

NOTEBOOK = Path(__file__).resolve().parent.parent / "reference_modules" / "sg4_temporal.ipynb"


def load_temporal_analyzer():
    with NOTEBOOK.open(encoding="utf-8") as f:
        notebook = json.load(f)

    for cell in notebook["cells"]:
        source = "".join(cell.get("source", []))

        if "class TemporalAnalyzer:" in source:
            namespace = {"__name__": "sg4_integration_test"}
            exec(compile(source, str(NOTEBOOK), "exec"), namespace)
            return namespace["TemporalAnalyzer"]

    raise RuntimeError("TemporalAnalyzer not found in SG4 notebook")


def adapt_sg2_to_sg4(packet, face_confidence=0.96):
    if packet["eye_state"] == "UNKNOWN" or not packet["valid"]:
        face_confidence = 0.0

    return {
        "timestamp": packet["timestamp_sec"],
        "face_confidence": face_confidence,
        "eye_closure_prob": (
            1.0 if packet["eye_state"] == "CLOSED" else 0.0
        ),
        "is_blink": False,
        "yawn_prob": 0.0,
        "head_nod_event": False,
    }


def main():
    TemporalAnalyzer = load_temporal_analyzer()

    fps = 30
    analyzer = TemporalAnalyzer(window_duration_sec=10, fps=fps)

    # 300 frames = 10 seconds.
    # 60 consecutive frames represent 2 seconds of eye closure.
    for frame_id in range(300):
        closed = 90 <= frame_id < 150

        packet = create_output_packet(
            frame_id=frame_id,
            timestamp_sec=frame_id / fps,
            average_ear=0.10 if closed else 0.30,
            valid=True,
        )

        cue = adapt_sg2_to_sg4(packet)
        analyzer.process_frame(cue)

    result = analyzer.get_temporal_vector()

    print("=== SG6 REAL SG2 -> SG4 TEST ===")
    print(json.dumps(result, indent=2))

    # 60 closed frames / 300 valid frames = 20%.
    assert abs(result["perclos"] - 20.0) < 0.01

    # A continuous 2-second closure exceeds SG4's 0.5-second rule.
    assert result["microsleep_count"] == 1

    assert result["validity_score"] == 1.0

    print("\n[PASS] SG2 classification executed")
    print("[PASS] SG2 output adapted to SG4 input")
    print("[PASS] SG4 temporal analyzer executed")
    print("[PASS] PERCLOS = 20%")
    print("[PASS] Microsleep count = 1")
    print("\nRESULT: PASS - REAL SG2 AND SG4 LOGIC EXECUTED")


if __name__ == "__main__":
    main()
