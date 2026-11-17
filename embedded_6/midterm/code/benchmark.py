#!/usr/bin/env python3
"""Compare YuNet/Haar on identical local images; saves metrics, never imagery."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Integration'))
import run_midterm_demo as demo


def summary(timings_ms, counts):
    if not timings_ms or len(timings_ms) != len(counts):
        raise ValueError('nonempty matching timing and count arrays required')
    ordered = sorted(timings_ms)
    # Nearest-rank 95th percentile.
    import math
    total_ms = sum(timings_ms)
    return {
        'frames_processed': len(counts),
        'frames_with_face': sum(c > 0 for c in counts),
        'total_face_detections': sum(counts),
        'face_coverage_percent': 100 * sum(c > 0 for c in counts) / len(counts),
        'mean_detector_ms': statistics.mean(timings_ms),
        'median_detector_ms': statistics.median(timings_ms),
        'p95_detector_ms': ordered[math.ceil(.95 * len(ordered)) - 1],
        'detector_only_fps': 1000 * len(counts) / total_ms if total_ms else None,
        'detector_ms': timings_ms,
        'face_counts': counts,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--frames-dir', type=Path, required=True)
    p.add_argument('--frames', type=int, default=150)
    p.add_argument('--warmup', type=int, default=5)
    p.add_argument('--repeats', type=int, default=3)
    p.add_argument('--output', type=Path, default=ROOT / 'evidence' / 'post_midterm_benchmark.json')
    args = p.parse_args(argv)
    if args.frames < 1 or args.warmup < 0 or args.repeats < 1:
        p.error('frames/repeats must be positive; warmup must be non-negative')
    try:
        import cv2
        import numpy
        paths = sorted(path for path in args.frames_dir.iterdir()
                       if path.is_file() and path.suffix.lower() in ('.jpg', '.jpeg', '.png'))[:args.frames]
        if len(paths) != args.frames:
            raise ValueError(f'Expected {args.frames} images; found {len(paths)}')
        blobs = [path.read_bytes() for path in paths]
        frames = [cv2.imdecode(numpy.frombuffer(blob, dtype=numpy.uint8), cv2.IMREAD_COLOR) for blob in blobs]
        if any(frame is None for frame in frames):
            raise ValueError('At least one selected image could not be decoded')
        if len({frame.shape for frame in frames}) != 1:
            raise ValueError('Use a single resolution for a comparable benchmark')
        detectors = {name: demo.create_detector(cv2, name) for name in ('haar', 'yunet')}
        results = []
        for repeat in range(args.repeats):
            order = ('haar', 'yunet') if repeat % 2 == 0 else ('yunet', 'haar')
            run = {'repeat': repeat + 1, 'order': list(order), 'detectors': {}}
            for name in order:
                detector = detectors[name]
                for _ in range(args.warmup):
                    demo.detect(cv2, detector, name, frames[0])
                timings, counts = [], []
                for frame in frames:
                    start = time.perf_counter_ns()
                    faces = demo.detect(cv2, detector, name, frame)
                    timings.append((time.perf_counter_ns() - start) / 1e6)
                    counts.append(len(faces))
                run['detectors'][name] = summary(timings, counts)
            results.append(run)
        haar = Path(cv2.data.haarcascades) / 'haarcascade_frontalface_default.xml'
        result = {
            'schema_version': 'sg6.detector-benchmark.v1',
            'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
            'platform': platform.platform(), 'architecture': platform.machine(),
            'python': platform.python_version(), 'opencv': cv2.__version__, 'numpy': numpy.__version__,
            'resolution': [frames[0].shape[1], frames[0].shape[0]],
            'frames_per_repeat': len(frames), 'warmup_calls_per_detector_per_repeat': args.warmup,
            'backend': 'OpenCV default CPU; no CUDA requested',
            'timing_boundary': 'detect() including Haar grayscale / YuNet input-size setup; excludes decode, capture, display and downstream pipeline',
            'parameters': {'haar': {'scale_factor': 1.1, 'min_neighbors': 5, 'min_size': [40, 40]},
                           'yunet': {'score_threshold': .6, 'nms_threshold': .3, 'top_k': 5000}},
            'model_sha256': {name: hashlib.sha256(path.read_bytes()).hexdigest()
                             for name, path in (('yunet', demo.MODEL), ('haar', haar))},
            # Hashes preserve dataset identity without publishing faces or filenames.
            'input_sha256_in_order': [hashlib.sha256(blob).hexdigest() for blob in blobs],
            'accuracy_ground_truth': None,
            'limitations': ['coverage is not accuracy', 'power/temperature are not measured',
                            'repeat order alternates; frequency/thermal state remain uncontrolled'],
            'repeats': results,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        print(f'Metrics saved to {args.output}; images were not copied.')
        return 0
    except (ImportError, OSError, ValueError, RuntimeError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
