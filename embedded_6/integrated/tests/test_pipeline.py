"""Synthetic contract tests. They do not establish live detection accuracy."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('run_integrated', ROOT / 'Integration' / 'run_integrated.py')
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class IntegratedTest(unittest.TestCase):
    def setUp(self):
        self.record = json.loads((Path(__file__).parent / 'sg1_v1_ok.json').read_text())
        self.frame = np.zeros((240, 230, 3), dtype=np.uint8)
        self.pipeline = app.build_pipeline()

    def record_at(self, frame_id, mouth_open=False):
        record = copy.deepcopy(self.record)
        record['frame_id'], record['timestamp_ms'] = frame_id, frame_id * 100
        if mouth_open:
            for upper, lower in ((13, 14), (82, 87), (312, 317)):
                record['landmarks_xy_normalized'][lower][1] = record['landmarks_xy_normalized'][upper][1] + 0.08
        return record

    def test_identity_and_invalid_inputs(self):
        from sg1_contract import validate_sg1_record, ContractValidationError
        from module_2.adapters import eye_packet
        record = self.record_at(12)
        validate_sg1_record(record)
        cue, _, _, _ = app.process_record(record, self.frame, self.pipeline)
        self.assertEqual(cue['frame_id'], 12)
        self.assertAlmostEqual(cue['timestamp'], 1.2)
        self.assertTrue(cue['eye_valid'])
        self.assertIsNotNone(cue['ear'])
        for field, value in (('frame_id', -1), ('timestamp_ms', -1)):
            bad = copy.deepcopy(record)
            bad[field] = value
            with self.assertRaises(ContractValidationError):
                validate_sg1_record(bad)
            with self.assertRaises(ValueError):
                eye_packet(bad)
        bad = copy.deepcopy(record)
        bad['landmarks_xy_normalized'][0][0] = float('nan')
        with self.assertRaises(ContractValidationError):
            validate_sg1_record(bad)
        self.assertFalse(eye_packet(bad)['eyes_valid'])

    def test_yawn_reaches_temporal_and_decision(self):
        confirmed = False
        vectors = []
        for n in range(35):
            eye, yawn, vector, decision = app.process_record(self.record_at(n, n < 22), self.frame, self.pipeline)
            confirmed |= yawn['event']
            if vector is not None:
                vectors.append((vector, decision))
        self.assertTrue(confirmed, 'SG3 should confirm a sustained mouth opening')
        self.assertTrue(any(v['yawn_count'] >= 1 for v, _ in vectors), 'SG4 should count the yawn')
        self.assertTrue(any(d and d['status'] == 'OK' for _, d in vectors), 'SG5 should consume temporal output')

    def test_sustained_eye_closure_reaches_sg5(self):
        states = []
        for n in range(25):
            record = self.record_at(n)
            points = record['landmarks_xy_normalized']
            for a, b in ((160, 144), (158, 153), (385, 380), (387, 373)):
                points[b] = points[a][:]
            _, _, _, decision = app.process_record(record, self.frame, self.pipeline)
            if decision:
                states.append((decision['driver_state'], decision['status']))
        self.assertIn(('DROWSY', 'OK'), states)

    def test_missing_face_is_not_normal_evidence(self):
        record = self.record_at(0)
        record.update(status='NO_FACE', face_bbox_xyxy=None, landmarks_xy_normalized=[], landmark_count=0)
        eye, yawn, vector, decision = app.process_record(record, self.frame, self.pipeline)
        self.assertEqual(eye['eye_state'], 'UNKNOWN')
        self.assertFalse(yawn['valid'])
        self.assertEqual(decision['status'], 'INSUFFICIENT_EVIDENCE')

if __name__ == '__main__':
    unittest.main()
