#!/usr/bin/env python3
"""SG1–SG6 demonstration. Predictions are experimental, not a safety system."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / 'integrated'
MODEL = ROOT / 'models' / 'face_landmarker.task'
MODEL_HASH = '64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff'
sys.path.insert(0, str(SNAPSHOT))
sys.path.insert(0, str(SNAPSHOT / 'module_1' / 'scripts'))


def build_pipeline():
    from module_2.processor import SG2Processor
    from module_5.midterm.sg3_adapter import YawnAdapter
    from module_5.midterm.sg4_bridge import SG4Bridge
    from module_5.midterm.engine import CONFIGURATIONS, DecisionEngine
    config = json.loads((SNAPSHOT / 'module_2' / 'final_method.json').read_text())['selected']
    return SG2Processor(method_config=config), YawnAdapter(), SG4Bridge(), DecisionEngine(CONFIGURATIONS['stable_c'], session_id='sg6-live')


def process_record(record, frame, pipeline):
    from module_2.adapters import to_sg4
    from module_5.midterm.sg4_bridge import synchronized_frame
    eyes, mouth, temporal, decision = pipeline
    t = record['timestamp_ms'] / 1000.0
    eye, _, _ = eyes.process(record, frame, frame_id=record['frame_id'], timestamp_sec=t)
    cue = to_sg4(eye)
    yawn = mouth.step(record)
    vector = temporal.push(synchronized_frame(record, cue, yawn))
    result = decision.step(vector) if vector is not None else None
    return cue, yawn, vector, result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument('--camera', type=int, default=0)
    source.add_argument('--video', help='read a local video instead of a camera')
    parser.add_argument('--headless', action='store_true')
    parser.add_argument('--frames', type=int, default=0, help='stop after N frames; 0 is unlimited')
    parser.add_argument('--model', type=Path, default=MODEL)
    args = parser.parse_args(argv)
    if args.camera < 0 or args.frames < 0:
        parser.error('camera and frames must be non-negative')
    if not args.model.is_file():
        print(f'ERROR: SG1 landmark model missing: {args.model}. See embedded_6/integrated/README.md.', file=sys.stderr)
        return 1
    if hashlib.sha256(args.model.read_bytes()).hexdigest() != MODEL_HASH:
        print('ERROR: SG1 landmark model SHA-256 does not match the pinned model.', file=sys.stderr)
        return 1
    try:
        import cv2
        import mediapipe
        import numpy
        from sg1_detector import DetectorConfig, SG1FaceLandmarkDetector
        from sg1_contract import validate_sg1_record
    except ImportError as exc:
        print(f'ERROR: Missing dependency: {exc}. Use the integrated environment; see embedded_6/integrated/README.md.', file=sys.stderr)
        return 1
    if not args.headless and not (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')):
        print('ERROR: No graphical display; use --headless.', file=sys.stderr)
        return 1
    cap = detector = window = None
    closed = False
    try:
        if not args.headless:
            import tkinter as tk
            window = tk.Tk()
            window.title('SG1–SG6 demo — q or Escape to quit')
            label = tk.Label(window)
            label.pack()
            def close(event=None):
                nonlocal closed
                closed = True
            window.protocol('WM_DELETE_WINDOW', close)
            window.bind('q', close)
            window.bind('<Escape>', close)
        source = args.video if args.video else args.camera
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            print(f'ERROR: Cannot open source {source}.', file=sys.stderr)
            return 1
        if not args.video:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        fps = float(cap.get(cv2.CAP_PROP_FPS)) if args.video else 0
        if args.video and (not numpy.isfinite(fps) or fps <= 0):
            print('ERROR: Video FPS is unavailable; cannot establish timestamps.', file=sys.stderr)
            return 1
        detector = SG1FaceLandmarkDetector(args.model, DetectorConfig('sg6', 256, .5, .5, .5))
        pipeline = build_pipeline()
        start = time.monotonic()
        frame_id = 0
        last_print = 0.0
        last_decision = None
        previous_timestamp = None
        warned_gap = False
        print('SG1 landmarks → SG2 eyes + SG3 yawn → SG4 temporal → SG5 decision → SG6 display; no images saved', flush=True)
        while not args.frames or frame_id < args.frames:
            ok, frame = cap.read()
            if not ok or frame is None:
                if args.video and frame_id:
                    break
                print('ERROR: Frame acquisition failed.', file=sys.stderr)
                return 1
            t = frame_id / fps if args.video else time.monotonic() - start
            record = detector.process(frame, frame_id, round(t * 1000))
            validate_sg1_record(record)
            if previous_timestamp is not None and record['timestamp_ms'] - previous_timestamp > 200 and not warned_gap:
                print('WARNING: Input gaps exceed 200 ms; temporal eye/yawn events may reset.', file=sys.stderr, flush=True)
                warned_gap = True
            previous_timestamp = record['timestamp_ms']
            eye, yawn, vector, decision = process_record(record, frame, pipeline)
            if decision is not None:
                last_decision = decision
            state = 'WAITING' if last_decision is None else (last_decision['driver_state'] if last_decision['status'] == 'OK' else last_decision['status'])
            if record['status'] != 'OK' or not eye['eye_valid']:
                state = 'INSUFFICIENT_EVIDENCE'
            yawn_state = 'UNKNOWN' if not yawn['valid'] else ('YAWN' if yawn['yawn_confirmed'] else ('MOUTH OPEN' if yawn['yawn_active'] else 'NO YAWN'))
            mar = 'n/a' if yawn['mar'] is None else f"{yawn['mar']:.2f}"
            elapsed = time.monotonic() - start
            frame_id += 1
            speed = frame_id / elapsed if elapsed > 0 else 0
            info = f"face={record['status']} eyes={eye['eye_state']} yawn={yawn_state} MAR={mar} decision={state} fps={speed:.1f}"
            if args.headless:
                if elapsed - last_print >= 1 or frame_id == 1 or (args.frames and frame_id == args.frames):
                    print(info, flush=True)
                    last_print = elapsed
            else:
                box = record['face_bbox_xyxy']
                if box:
                    cv2.rectangle(frame, tuple(box[:2]), tuple(box[2:]), (0, 255, 0), 2)
                for i, line in enumerate((f"Face: {record['status']}   Eyes: {eye['eye_state']}", f'Yawn: {yawn_state}  MAR: {mar}', f'Decision: {state}   FPS: {speed:.1f}')):
                    alert = (i == 1 and yawn_state == 'YAWN') or (i == 2 and state in ('WARNING', 'DROWSY', 'INSUFFICIENT_EVIDENCE'))
                    cv2.putText(frame, line, (8, 25 + 25*i), cv2.FONT_HERSHEY_SIMPLEX, .55, (0, 0, 255) if alert else (0, 255, 0), 2)
                ok, encoded = cv2.imencode('.ppm', frame)
                if not ok:
                    raise RuntimeError('Could not prepare display frame')
                photo = tk.PhotoImage(data=encoded.tobytes(), format='PPM')
                label.configure(image=photo)
                label.image = photo
                window.update_idletasks()
                window.update()
                if closed:
                    break
        if not frame_id:
            print('ERROR: No readable frames.', file=sys.stderr)
            return 1
        return 0
    except KeyboardInterrupt:
        print('\nStopped by user.')
        return 0
    except Exception as exc:
        print(f'ERROR: {type(exc).__name__}: {exc}', file=sys.stderr)
        return 1
    finally:
        if cap is not None:
            cap.release()
        if detector is not None:
            detector.close()
        if window is not None:
            window.destroy()


if __name__ == '__main__':
    sys.exit(main())
