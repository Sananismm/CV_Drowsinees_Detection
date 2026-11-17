"""Exercise real detector inference on blank fixtures and benchmark error paths."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'code'))
import benchmark


class BenchmarkTests(unittest.TestCase):
    def test_latency_units_and_coverage(self):
        out = benchmark.summary([10, 20, 30], [0, 1, 2])
        self.assertEqual(out['mean_detector_ms'], 20)
        self.assertEqual(out['median_detector_ms'], 20)
        self.assertEqual(out['p95_detector_ms'], 30)
        self.assertEqual(out['detector_only_fps'], 50)
        self.assertAlmostEqual(out['face_coverage_percent'], 200 / 3)
        with self.assertRaises(ValueError):
            benchmark.summary([], [])

    def test_identical_inputs_alternating_order_and_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            cv2.imwrite(str(folder / 'blank.png'), np.zeros((480, 640, 3), np.uint8))
            output = folder / 'metrics.json'
            with contextlib.redirect_stdout(io.StringIO()):
                code = benchmark.main(['--frames-dir', tmp, '--frames', '1', '--repeats', '2',
                                       '--warmup', '0', '--output', str(output)])
            self.assertEqual(code, 0)
            data = json.loads(output.read_text())
            self.assertEqual(data['resolution'], [640, 480])
            self.assertEqual(data['repeats'][0]['order'], ['haar', 'yunet'])
            self.assertEqual(data['repeats'][1]['order'], ['yunet', 'haar'])
            self.assertEqual(len(data['input_sha256_in_order'][0]), 64)
            for repeat in data['repeats']:
                for metrics in repeat['detectors'].values():
                    self.assertEqual(metrics['frames_processed'], 1)
                    self.assertEqual(metrics['frames_with_face'], 0)
                    self.assertGreater(metrics['mean_detector_ms'], 0)
            self.assertIsNone(data['accuracy_ground_truth'])

    def test_missing_or_corrupt_frames_produce_no_result(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stderr(io.StringIO()):
            output = Path(tmp) / 'metrics.json'
            command = ['--frames-dir', tmp, '--frames', '1', '--output', str(output)]
            self.assertEqual(benchmark.main(command), 1)
            (Path(tmp) / 'bad.png').write_bytes(b'invalid image')
            self.assertEqual(benchmark.main(command), 1)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
