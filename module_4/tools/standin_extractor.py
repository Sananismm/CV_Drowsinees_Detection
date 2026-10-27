"""STAND-IN CUE EXTRACTOR - TEST HARNESS ONLY (dev PC).

*** This is NOT SG-2's or SG-3's deliverable. ***
It stands in for SG-1/SG-2/SG-3 so SG-4 can be demonstrated live and run on
videos before the real upstream modules exist. It uses MediaPipe Face Mesh:
  EAR (eye aspect ratio)  -> closure_prob (scaled by the session's open-eye EAR)
  MAR (mouth aspect ratio) -> yawn_prob
  solvePnP head pose       -> pitch_deg (negative = head down; check with --pitch-sign)
and writes sg4.input.v1 JSONL and/or feeds the SG-4 engine live with an overlay.

    pip install -r module_4/requirements-dev.txt
    python module_4/tools/standin_extractor.py --camera 0 --live                # webcam + overlay
    python module_4/tools/standin_extractor.py --video clip.mp4 --out clip.jsonl  # offline

The mapping constants below are harness choices, not SG-4 core thresholds.
"""
import argparse
import json
import sys
import time
from collections import deque
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from sg4.engine import TemporalEngine  # noqa: E402

LEFT_EYE = (362, 385, 387, 263, 373, 380)      # p1..p6 in the EAR formula
RIGHT_EYE = (33, 160, 158, 133, 153, 144)
MOUTH = (13, 14, 78, 308)                      # upper lip, lower lip, left corner, right corner
POSE_IDX = (1, 152, 263, 33, 287, 57)          # nose tip, chin, eye corners, mouth corners
POSE_3D = np.array([(0.0, 0.0, 0.0), (0.0, -330.0, -65.0), (-225.0, 170.0, -135.0),
                    (225.0, 170.0, -135.0), (-150.0, -150.0, -125.0), (150.0, -150.0, -125.0)])
CLOSED_EAR_RATIO = 0.45    # EAR at or below 45% of the open-eye EAR -> closure_prob 1
MAR_OPEN, MAR_YAWN = 0.35, 0.60


def ear(pts, idx):
    p = [pts[i] for i in idx]
    return (np.linalg.norm(p[1] - p[5]) + np.linalg.norm(p[2] - p[4])) / (2.0 * np.linalg.norm(p[0] - p[3]) + 1e-6)


def mar(pts):
    up, lo, l, r = (pts[i] for i in MOUTH)
    return np.linalg.norm(up - lo) / (np.linalg.norm(l - r) + 1e-6)


def pitch_deg(pts, w, h, cv2):
    img = np.array([pts[i] for i in POSE_IDX], dtype=float)
    cam = np.array([[w, 0, w / 2.0], [0, w, h / 2.0], [0, 0, 1]], dtype=float)
    ok, rvec, _ = cv2.solvePnP(POSE_3D, img, cam, np.zeros(4), flags=cv2.SOLVEPNP_ITERATIVE)
    if not ok:
        return None
    R, _ = cv2.Rodrigues(rvec)
    angles = cv2.RQDecomp3x3(R)[0]
    p = angles[0]
    return float(p - 180.0 if p > 90 else (p + 180.0 if p < -90 else p))


class Extractor:
    def __init__(self, pitch_sign=1.0):
        import cv2
        import mediapipe as mp
        self.cv2 = cv2
        self.mesh = mp.solutions.face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=True,
                                                    min_detection_confidence=0.5, min_tracking_confidence=0.5)
        self.open_ears = deque(maxlen=300)     # ~10 s of open-eye EAR samples
        self.pitch_sign = pitch_sign
        self.pitch0 = deque(maxlen=150)        # neutral pitch from the first ~5 s

    def record(self, frame_bgr, frame_id, t_ms):
        h, w = frame_bgr.shape[:2]
        res = self.mesh.process(self.cv2.cvtColor(frame_bgr, self.cv2.COLOR_BGR2RGB))
        rec = {"schema": "sg4.input.v1", "frame_id": frame_id, "timestamp_ms": int(t_ms),
               "face": {"present": False, "confidence": 0.0}, "eye": None, "mouth": None, "head": None}
        if not res.multi_face_landmarks:
            return rec
        lm = res.multi_face_landmarks[0].landmark
        pts = np.array([(p.x * w, p.y * h) for p in lm])
        e = (ear(pts, LEFT_EYE) + ear(pts, RIGHT_EYE)) / 2.0
        if not self.open_ears or e > 0.8 * np.median(self.open_ears):
            self.open_ears.append(e)
        e_open = float(np.percentile(self.open_ears, 90))
        closure = float(np.clip((e_open - e) / (e_open * (1 - CLOSED_EAR_RATIO) + 1e-6), 0.0, 1.0))
        m = mar(pts)
        yawn = float(np.clip((m - MAR_OPEN) / (MAR_YAWN - MAR_OPEN), 0.0, 1.0))
        p = pitch_deg(pts, w, h, self.cv2)
        rec["face"] = {"present": True, "confidence": 0.9}
        rec["eye"] = {"closure_prob": round(closure, 3), "state": "closed" if closure >= 0.5 else "open",
                      "ear": round(float(e), 4), "confidence": 0.9}
        rec["mouth"] = {"yawn_prob": round(yawn, 3), "mar": round(float(m), 4), "confidence": 0.9}
        if p is not None:
            if len(self.pitch0) < self.pitch0.maxlen:
                self.pitch0.append(p)
            rel = self.pitch_sign * (p - float(np.median(self.pitch0)))
            rec["head"] = {"pitch_deg": round(rel, 2), "yaw_deg": None, "roll_deg": None, "confidence": 0.9}
        return rec


def overlay(frame, vec, cv2):
    lines = ["SG-4 (stand-in cues: NOT SG-2/SG-3 output)"]
    if vec:
        lines += ["perclos %.3f   face_valid %d" % (vec["perclos"], vec["face_valid"]),
                  "eye_closure_s %.2f   long_blinks(30s) %d" % (vec["eye_closure_s"], vec["long_blinks"]),
                  "yawn_count(60s) %d   nod_count %d" % (vec["yawn_count"], vec["nod_count"]),
                  "blinks/min %.1f   trend %s" % (vec["blink_rate_bpm"], vec["trend"])]
    for i, s in enumerate(lines):
        cv2.putText(frame, s, (10, 25 + 24 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--camera", type=int)
    src.add_argument("--video")
    ap.add_argument("--out", help="write sg4.input.v1 JSONL here")
    ap.add_argument("--sg4-out", help="also write the SG-4 output vectors here")
    ap.add_argument("--live", action="store_true", help="show the overlay window")
    ap.add_argument("--pitch-sign", type=float, default=1.0, help="use -1 if nodding down gives positive pitch")
    a = ap.parse_args(argv)

    import cv2
    cap = cv2.VideoCapture(a.camera if a.video is None else a.video)
    if not cap.isOpened():
        sys.exit("cannot open input")
    ex, engine = Extractor(a.pitch_sign), TemporalEngine()
    fin = open(a.out, "w") if a.out else None
    fout = open(a.sg4_out, "w") if a.sg4_out else None
    t0, i, vec = time.monotonic(), 0, None
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            t_ms = cap.get(cv2.CAP_PROP_POS_MSEC) if a.video else (time.monotonic() - t0) * 1000.0
            rec = ex.record(frame, i, t_ms)
            i += 1
            if fin:
                fin.write(json.dumps(rec) + "\n")
            out = engine.push(rec)
            if out is not None:
                vec = out
                if fout:
                    fout.write(json.dumps(out) + "\n")
            if a.live:
                overlay(frame, vec, cv2)
                cv2.imshow("SG-4 stand-in demo (q to quit)", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
    finally:
        cap.release()
        for f in (fin, fout):
            if f:
                f.close()
        if a.live:
            cv2.destroyAllWindows()
    print("%d frames processed" % i)


if __name__ == "__main__":
    main()
