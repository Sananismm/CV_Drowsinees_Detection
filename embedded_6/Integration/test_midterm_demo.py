"""Tests use synthetic frames and a mock camera; recorded-frame tests use private evidence."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import cv2
import run_midterm_demo as demo


class Capture:
    def __init__(self, opened=True, reads=()):
        self.opened, self.reads, self.released = opened, iter(reads), False
    def isOpened(self): return self.opened
    def set(self, *args): pass
    def read(self): return next(self.reads)
    def release(self): self.released = True


class DemoTests(unittest.TestCase):
    def test_help_and_invalid_selection(self):
        for args, code in [(['--help'], 0), (['--detector', 'invalid'], 2)]:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as e:
                demo.main(args)
            self.assertEqual(e.exception.code, code)

    def test_real_detectors_on_blank_and_sample(self):
        blank = np.zeros((480, 640, 3), dtype=np.uint8)
        sample = demo.ROOT / 'evidence' / 'benchmark_frames' / 'frame_001.jpg'
        for name in ('haar', 'yunet'):
            detector = demo.create_detector(cv2, name)
            self.assertEqual(len(demo.detect(cv2, detector, name, blank)), 0)
            if sample.exists():
                frame = cv2.imread(str(sample))
                self.assertIsNotNone(frame)
                self.assertGreater(len(demo.detect(cv2, detector, name, frame)), 0)

    def test_missing_model(self):
        with patch.object(demo, 'MODEL', Path('/missing/yunet.onnx')):
            with self.assertRaisesRegex(RuntimeError, 'model missing'):
                demo.create_detector(cv2, 'yunet')

    def test_metrics(self):
        m = demo.summarize([10, 20, 30], 3, 3, 2, 4, 1, 2)
        self.assertEqual(m['median_inference_ms'], 20)
        self.assertEqual(m['mean_inference_ms'], 20)
        self.assertAlmostEqual(m['face_coverage_percent'], 200/3)
        self.assertEqual(m['processing_fps'], 1.5)
        self.assertIsNone(demo.summarize([], 0, 0, 0, 0, 0, 0)['mean_inference_ms'])

    def test_headless_and_cleanup(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        for name in ('haar', 'yunet'):
            cap = Capture(reads=[(True, frame)])
            with tempfile.TemporaryDirectory() as tmp, patch.object(cv2, 'VideoCapture', return_value=cap), contextlib.redirect_stdout(io.StringIO()) as out:
                code = demo.main(['--headless', '--frames', '1', '--detector', name, '--save-metrics', '--output-dir', tmp])
                metrics = json.loads(next(Path(tmp).glob('*.json')).read_text())
            self.assertEqual(code, 0)
            self.assertTrue(cap.released)
            self.assertIn('NO FACE', out.getvalue())
            self.assertEqual(metrics['frames_processed'], 1)
            self.assertEqual(metrics['actual_resolution'], [640, 480])

    def test_open_and_read_failure_cleanup(self):
        for cap in (Capture(opened=False), Capture(reads=[(False, None)])):
            with patch.object(cv2, 'VideoCapture', return_value=cap), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(demo.main(['--headless']), 1)
            self.assertTrue(cap.released)

    def test_interrupt_cleanup(self):
        cap = Capture()
        cap.read = lambda: (_ for _ in ()).throw(KeyboardInterrupt())
        with patch.object(cv2, 'VideoCapture', return_value=cap), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(demo.main(['--headless']), 0)
        self.assertTrue(cap.released)

if __name__ == '__main__':
    unittest.main()
