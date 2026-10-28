#!/usr/bin/env python3
"""Live face detection on a Jetson camera; never records images or video."""
import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / 'models' / 'face_detection_yunet_2023mar.onnx'


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--camera', type=int, default=0, help='V4L2 camera index (default: 0)')
    p.add_argument('--detector', choices=('yunet', 'haar'), default='yunet', help='Face detector (default: yunet)')
    p.add_argument('--headless', action='store_true', help='Print status without opening a window')
    p.add_argument('--duration', type=float, default=0, help='Maximum seconds after camera opens; 0 means unlimited')
    p.add_argument('--frames', type=int, default=0, help='Maximum processed frames; 0 means unlimited')
    p.add_argument('--output-dir', type=Path, default=ROOT / 'evidence', help='Directory for metrics (default: embedded_6/evidence)')
    p.add_argument('--save-metrics', action='store_true', help='Save a JSON measurement summary; no images are saved')
    return p


def create_detector(cv2, name):
    if name == 'yunet':
        if not MODEL.is_file():
            raise RuntimeError(f'YuNet model missing: {MODEL}')
        if not hasattr(cv2, 'FaceDetectorYN_create'):
            raise RuntimeError('OpenCV lacks FaceDetectorYN; use ~/sg6-yunet-env/bin/python')
        return cv2.FaceDetectorYN_create(str(MODEL), '', (640, 480), 0.6, 0.3, 5000)
    path = str(Path(cv2.data.haarcascades) / 'haarcascade_frontalface_default.xml')
    detector = cv2.CascadeClassifier(path)
    if detector.empty():
        raise RuntimeError(f'Haar cascade could not be loaded: {path}')
    return detector


def detect(cv2, detector, name, frame):
    if name == 'yunet':
        detector.setInputSize((frame.shape[1], frame.shape[0]))
        _, faces = detector.detect(frame)
        return [] if faces is None else list(faces)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return list(detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40)))


def summarize(latencies, captured, processed, coverage, faces, failed, elapsed):
    return {'frames_captured': captured, 'frames_processed': processed,
            'frames_with_face': coverage, 'total_face_detections': faces,
            'face_coverage_percent': 100 * coverage / processed if processed else 0.0,
            'mean_inference_ms': statistics.mean(latencies) if latencies else None,
            'median_inference_ms': statistics.median(latencies) if latencies else None,
            'processing_fps': processed / elapsed if elapsed > 0 else 0.0,
            'elapsed_seconds': elapsed, 'failed_frame_reads': failed,
            'dropped_frames': None}


def main(argv=None):
    p = parser()
    args = p.parse_args(argv)
    if args.camera < 0 or args.frames < 0 or not 0 <= args.duration < float('inf'):
        p.error('camera, frames and duration must be non-negative and finite')
    try:
        import cv2
    except ImportError:
        print('ERROR: OpenCV unavailable; use ~/sg6-yunet-env/bin/python.', file=sys.stderr)
        return 1
    cap = window = None
    latencies = []
    captured = processed = coverage = total_faces = failed = 0
    start = None
    resolution = None
    result = 0
    closed = False
    try:
        detector = create_detector(cv2, args.detector)
        if not args.headless:
            if not (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')):
                raise RuntimeError('No graphical display; use --headless')
            import tkinter as tk
            try:
                window = tk.Tk()
            except tk.TclError as exc:
                raise RuntimeError(f'Cannot initialize display: {exc}; use --headless') from exc
            window.title('SG6 face detection — q or Escape to quit')
            label = tk.Label(window)
            label.pack()
            def close_window(event=None):
                nonlocal closed
                closed = True
            window.protocol('WM_DELETE_WINDOW', close_window)
            window.bind('q', close_window)
            window.bind('<Escape>', close_window)
        cap = cv2.VideoCapture(args.camera, cv2.CAP_V4L2)
        if not cap.isOpened():
            raise RuntimeError(f'Cannot open camera /dev/video{args.camera}; check connection and permissions')
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        print(f'SG6: /dev/video{args.camera}, {args.detector}, OpenCV {cv2.__version__}; no recording', flush=True)
        start = time.perf_counter()
        last_print = -1.0
        while not closed and (not args.frames or processed < args.frames):
            if args.duration and time.perf_counter() - start >= args.duration:
                break
            ok, frame = cap.read()
            if not ok or frame is None or not getattr(frame, 'size', 0):
                failed += 1
                raise RuntimeError('Camera frame acquisition failed; camera may be disconnected')
            captured += 1
            height, width = frame.shape[:2]
            resolution = [width, height]
            before = time.perf_counter()
            faces = detect(cv2, detector, args.detector, frame)
            latency = (time.perf_counter() - before) * 1000
            latencies.append(latency)
            processed += 1
            count = len(faces)
            coverage += count > 0
            total_faces += count
            elapsed = time.perf_counter() - start
            fps = processed / elapsed if elapsed else 0
            state = 'FACE DETECTED' if count else 'NO FACE'
            confidence = ','.join(f'{float(face[14]):.2f}' for face in faces) if args.detector == 'yunet' and count else 'n/a'
            status = f'{args.detector.upper()} {width}x{height} frame={processed} faces={count} {state} confidence={confidence} inference={latency:.2f}ms processing={fps:.2f} FPS'
            if args.headless:
                if elapsed - last_print >= 1 or processed == 1 or (args.frames and processed == args.frames):
                    print(status, flush=True)
                    last_print = elapsed
            else:
                for face in faces:
                    x, y, w, h = (int(v) for v in face[:4])
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    if args.detector == 'yunet':
                        for i in range(4, 14, 2):
                            cv2.circle(frame, (int(face[i]), int(face[i+1])), 2, (0, 255, 255), -1)
                        cv2.putText(frame, f'{face[14]:.2f}', (x, max(12, y-5)), cv2.FONT_HERSHEY_SIMPLEX, .45, (0, 255, 0), 1)
                for i, line in enumerate((f'{args.detector.upper()} {width}x{height} frame={processed}', f'{state} faces={count}', f'processing={fps:.1f} FPS inference={latency:.1f} ms')):
                    cv2.putText(frame, line, (8, 20 + 20*i), cv2.FONT_HERSHEY_SIMPLEX, .5, (0, 255, 0), 1)
                ok, encoded = cv2.imencode('.ppm', frame)
                if not ok:
                    raise RuntimeError('Could not prepare display frame')
                photo = tk.PhotoImage(data=encoded.tobytes(), format='PPM')
                label.configure(image=photo)
                label.image = photo
                try:
                    window.update_idletasks()
                    window.update()
                except tk.TclError as exc:
                    raise RuntimeError(f'Display failed: {exc}; use --headless') from exc
    except KeyboardInterrupt:
        print('\nStopped by user.')
    except (RuntimeError, ImportError, cv2.error) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        result = 1
    finally:
        elapsed = time.perf_counter() - start if start is not None else 0.0
        if cap is not None:
            cap.release()
        if window is not None:
            try:
                window.destroy()
            except tk.TclError:
                pass
        if args.save_metrics:
            metrics = summarize(latencies, captured, processed, coverage, total_faces, failed, elapsed)
            metrics.update({'detector': args.detector, 'model': MODEL.name if args.detector == 'yunet' else 'haarcascade_frontalface_default.xml',
                            'opencv_version': cv2.__version__, 'camera': f'/dev/video{args.camera}',
                            'requested_resolution': [640, 480], 'actual_resolution': resolution,
                            'duration_limit_seconds': args.duration, 'frame_limit': args.frames,
                            'headless': args.headless, 'backend': 'OpenCV CPU default', 'exit_status': result,
                            'detector_parameters': {'score_threshold': 0.6, 'nms_threshold': 0.3, 'top_k': 5000} if args.detector == 'yunet' else {'scale_factor': 1.1, 'min_neighbors': 5, 'min_size': [40, 40]}})
            try:
                args.output_dir.mkdir(parents=True, exist_ok=True)
                path = args.output_dir / f'midterm_{args.detector}_{time.time_ns()}.json'
                path.write_text(json.dumps(metrics, indent=2) + '\n', encoding='utf-8')
                print(f'Metrics saved: {path}')
            except OSError as exc:
                print(f'ERROR: Unable to save metrics: {exc}', file=sys.stderr)
                result = 1
    return result


if __name__ == '__main__':
    sys.exit(main())
