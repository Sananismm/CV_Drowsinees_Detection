"""Contract and causal-time checks for the SG3-derived mouth adapter."""

from copy import deepcopy
import unittest

from module_5.midterm.sg3_adapter import MOUTH_INDICES, YawnAdapter


def record(t=0.0, frame=0, mar=0.60, width=1000, height=500):
    """Build pixel geometry with a known MAR, then normalize for SG1."""
    points = [[0.5, 0.5] for _ in range(478)]
    points[61], points[291] = [0.4, 0.5], [0.6, 0.5]
    gap = mar * (0.2 * width) / height
    for upper, lower in ((13, 14), (82, 87), (312, 317)):
        points[upper] = [0.5, 0.5 - gap / 2]
        points[lower] = [0.5, 0.5 + gap / 2]
    return {
        "schema_version": "sg1.v1", "frame_id": frame,
        "timestamp_ms": round(t * 1000), "image_width": width,
        "image_height": height, "status": "OK", "landmark_count": 478,
        "landmark_topology": "mediapipe_face_landmarker_478",
        "landmarks_xy_normalized": points,
    }


class YawnAdapterTests(unittest.TestCase):
    def test_pixel_geometry_on_rectangular_frames(self):
        for width, height in ((1000, 500), (500, 1000), (640, 480)):
            with self.subTest(width=width, height=height):
                out = YawnAdapter().step(record(mar=.6, width=width, height=height))
                self.assertTrue(out["valid"])
                self.assertAlmostEqual(out["mar"], .6)
                self.assertTrue(out["yawn_active"])

    def test_raw_opening_is_immediate_but_confirmation_waits(self):
        adapter = YawnAdapter()
        first = adapter.step(record())
        self.assertTrue(first["yawn_active"])
        self.assertFalse(first["yawn_confirmed"])
        self.assertFalse(first["event"])
        for k in range(1, 15):
            out = adapter.step(record(k / 10, k))
            self.assertFalse(out["event"])
        confirmed = adapter.step(record(1.5, 15))
        self.assertTrue(confirmed["yawn_confirmed"])
        self.assertTrue(confirmed["event"])
        self.assertFalse(adapter.step(record(1.6, 16))["event"])

    def test_hysteresis_requires_start_then_allows_lower_hold(self):
        adapter = YawnAdapter()
        self.assertFalse(adapter.step(record(mar=.46))["yawn_active"])
        self.assertTrue(adapter.step(record(.1, 1, .6))["yawn_active"])
        self.assertTrue(adapter.step(record(.2, 2, .46))["yawn_active"])
        self.assertFalse(adapter.step(record(.3, 3, .4))["yawn_active"])
        self.assertFalse(adapter.step(record(.4, 4, .46))["yawn_active"])

    def test_event_fires_once_per_confirmed_opening(self):
        adapter = YawnAdapter(duration_s=.2)
        flags = [adapter.step(record(k / 10, k))["event"] for k in range(6)]
        self.assertEqual(sum(flags), 1)
        adapter.step(record(.6, 6, .1))
        flags = [adapter.step(record(k / 10, k))["event"] for k in range(7, 11)]
        self.assertEqual(sum(flags), 1)

    def test_gap_greater_than_point_two_resets_continuity(self):
        adapter = YawnAdapter(duration_s=.2)
        adapter.step(record())
        adapter.step(record(.1, 1))
        out = adapter.step(record(.4, 2))
        self.assertTrue(out["yawn_active"])
        self.assertFalse(out["yawn_confirmed"])
        self.assertTrue(adapter.step(record(.6, 3))["event"])

    def test_missing_face_clears_opening(self):
        adapter = YawnAdapter(duration_s=.2)
        adapter.step(record())
        missing = record(.1, 1)
        missing.update(status="NO_FACE", landmarks_xy_normalized=[], landmark_count=0)
        out = adapter.step(missing)
        self.assertFalse(out["valid"])
        self.assertIsNone(out["mar"])
        self.assertFalse(out["yawn_active"])
        self.assertFalse(out["yawn_confirmed"])
        self.assertFalse(adapter.step(record(.2, 2))["event"])

    def test_bad_geometry_is_invalid_without_invented_confidence(self):
        invalids = []
        zero = record()
        zero["landmarks_xy_normalized"][291] = zero["landmarks_xy_normalized"][61]
        invalids.append(zero)
        for value in (float("nan"), float("inf"), -.1, 1.1, True, "0.5"):
            bad = record()
            bad["landmarks_xy_normalized"][13][0] = value
            invalids.append(bad)
        bad = record()
        bad["landmarks_xy_normalized"].pop()
        invalids.append(bad)
        bad = record()
        del bad["image_width"]
        invalids.append(bad)
        for bad in invalids:
            with self.subTest(reason=str(bad.get("image_width"))):
                out = YawnAdapter().step(bad)
                self.assertFalse(out["valid"])
                self.assertIsNone(out["mar"])
                self.assertIsNone(out["confidence"])
                self.assertFalse(out["event"])

    def test_shared_identity_time_source_and_no_input_mutation(self):
        source = record(12.345, 42)
        previous = deepcopy(source)
        out = YawnAdapter().step(source)
        self.assertEqual(out["time_s"], 12.345)
        self.assertEqual(out["frame_id"], 42)
        self.assertEqual(out["source"]["branch"], "sg3")
        self.assertEqual(out["source"]["path"], "module_3/Week 8 Progress.py")
        self.assertIsNone(out["confidence"])
        self.assertEqual(source, previous)
        self.assertEqual(MOUTH_INDICES, (61, 291, 13, 14, 82, 87, 312, 317))

    def test_nonmonotonic_identity_raises_and_clears_continuity(self):
        for bad in (record(.1, 2), record(.3, 1)):
            adapter = YawnAdapter(duration_s=.2)
            adapter.step(record(.2, 2))
            with self.assertRaises(ValueError):
                adapter.step(bad)
            self.assertFalse(adapter.step(record(.3, 3))["event"])

    def test_malformed_time_is_not_fabricated(self):
        for field, value in (("timestamp_ms", -1), ("timestamp_ms", float("nan")),
                             ("timestamp_ms", True), ("frame_id", "1")):
            bad = record()
            bad[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                YawnAdapter().step(bad)


if __name__ == "__main__":
    unittest.main()
