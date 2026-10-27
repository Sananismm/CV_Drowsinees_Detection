"""Hardware evidence tests use mocked devices; no physical camera is opened."""

import contextlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from embedded_6.sg5_handoff import check_platform as tool


class PlatformEvidenceTests(unittest.TestCase):
    def test_arm_linux_alone_does_not_claim_jetson(self):
        with patch.object(tool.platform, "system", return_value="Linux"), \
                patch.object(tool.platform, "machine", return_value="aarch64"), \
                patch.object(tool, "read_linux_text", return_value=None), \
                patch.object(tool, "ram_bytes", return_value=8 * 1024 ** 3):
            report = tool.platform_evidence()
        self.assertFalse(report["jetson_family_detected"])
        self.assertFalse(report["reported_orin_nano_model"])
        self.assertIsNone(report["exact_target_8gb_sku_verified"])

    def test_device_tree_and_tegra_metadata_identify_reported_model(self):
        files = {"/proc/device-tree/model": "NVIDIA Jetson Orin Nano Developer Kit",
                 "/etc/nv_tegra_release": "# R36 (release), REVISION: 4.3",
                 "/proc/meminfo": "MemTotal:        8123456 kB\n"}
        with patch.object(tool.platform, "system", return_value="Linux"), \
                patch.object(tool.platform, "machine", return_value="aarch64"), \
                patch.object(tool, "read_linux_text", side_effect=files.get):
            report = tool.platform_evidence()
        self.assertTrue(report["jetson_family_detected"])
        self.assertEqual(report["device_tree_model"], files["/proc/device-tree/model"])
        self.assertEqual(report["ram_bytes"], 8123456 * 1024)

    def test_default_capture_probe_never_imports_opencv_or_opens_a_camera(self):
        with patch.object(tool.importlib, "import_module") as importer:
            report = tool.capture_evidence()
        importer.assert_not_called()
        self.assertFalse(report["requested"])
        self.assertIsNone(report["success"])

    def test_mock_physical_camera_frames_are_read_and_discarded(self):
        capture = Mock()
        capture.isOpened.return_value = True
        capture.get.return_value = 30.0
        capture.read.return_value = (True, SimpleNamespace(shape=(480, 640, 3)))
        cv2 = SimpleNamespace(VideoCapture=Mock(return_value=capture), CAP_PROP_FPS=5)
        report = tool.capture_evidence(camera=0, frames=30, cv2_module=cv2)
        cv2.VideoCapture.assert_called_once_with(0)
        self.assertEqual(capture.read.call_count, 30)
        capture.release.assert_called_once()
        self.assertTrue(report["physical_camera_evidence"])
        self.assertEqual(report["observed_resolution"], {"width": 640, "height": 480})
        self.assertEqual(report["frames_saved"], 0)

    def test_prerecorded_fallback_is_never_physical_camera_evidence(self):
        capture = Mock()
        capture.isOpened.return_value = True
        capture.get.return_value = 25.0
        capture.read.return_value = (True, SimpleNamespace(shape=(240, 320, 3)))
        cv2 = SimpleNamespace(VideoCapture=Mock(return_value=capture), CAP_PROP_FPS=5)
        report = tool.capture_evidence(video=Path("example.mp4"), frames=2, cv2_module=cv2)
        self.assertTrue(report["success"])
        self.assertFalse(report["physical_camera_evidence"])
        self.assertEqual(report["source_kind"], "prerecorded_video_fallback")

    def test_camera_open_failure_releases_device_and_is_not_success(self):
        capture = Mock()
        capture.isOpened.return_value = False
        cv2 = SimpleNamespace(VideoCapture=Mock(return_value=capture), CAP_PROP_FPS=5)
        report = tool.capture_evidence(camera=0, cv2_module=cv2)
        self.assertFalse(report["success"])
        self.assertEqual(report["frames_read"], 0)
        capture.release.assert_called_once()

    def test_windows_runtime_success_does_not_become_jetson_readiness(self):
        host = {"jetson_family_detected": False, "python_at_least_3_10": True}
        runtime = {"sg5_core": {"smoke_ok": True},
                   "optional_imports": {"cv2": {"import_ok": True}}}
        capture = {"source_kind": "live_camera", "success": True}
        readiness = tool.readiness_evidence(host, runtime, capture)
        self.assertFalse(readiness["jetson_boot"]["verified"])
        self.assertIsNone(readiness["software_stack"]["verified"])
        self.assertIsNone(readiness["physical_camera"]["verified"])
        self.assertFalse(readiness["all_three_verified"])

    def test_cuda_and_torch_are_metadata_only_not_runtime_imports(self):
        def importer(name):
            self.assertNotIn(name, ("torch", "cuda", "mediapipe"))
            return SimpleNamespace(__version__="test")
        with patch.object(tool.importlib, "import_module", side_effect=importer), \
                patch.object(tool, "distribution_metadata", return_value={"metadata_found": False, "version": None}):
            report = tool.runtime_evidence()
        self.assertFalse(report["torch_imported_by_this_tool"])
        self.assertFalse(report["cuda_runtime_checked"])
        self.assertIsNone(report["cuda_available"])
        self.assertTrue(report["sg5_core"]["smoke_ok"])

    def test_strict_cli_reports_non_target_failure_without_opening_a_device(self):
        host = {"jetson_family_detected": False, "python_at_least_3_10": True}
        runtime = {"sg5_core": {"smoke_ok": True}, "optional_imports": {}}
        with patch.object(tool, "platform_evidence", return_value=host), \
                patch.object(tool, "runtime_evidence", return_value=runtime), \
                patch.object(tool, "capture_evidence", return_value={"requested": False}) as capture, \
                contextlib.redirect_stdout(io.StringIO()) as output:
            code = tool.main(["--strict"])
        self.assertEqual(code, 1)
        capture.assert_called_once_with(camera=None, video=None, frames=30)
        self.assertFalse(json.loads(output.getvalue())["readiness"]["all_three_verified"])

    def test_on_target_scoped_stack_and_camera_can_pass_with_mocked_evidence(self):
        host = {"jetson_family_detected": True, "python_at_least_3_10": True}
        runtime = {"sg5_core": {"smoke_ok": True},
                   "optional_imports": {"numpy": {"import_ok": True}, "cv2": {"import_ok": True}}}
        capture = {"source_kind": "live_camera", "success": True}
        self.assertTrue(tool.readiness_evidence(host, runtime, capture)["all_three_verified"])


if __name__ == "__main__":
    unittest.main()
