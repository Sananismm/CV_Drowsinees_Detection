"""Collect real platform evidence without installing software or operating GPIO.

Default operation does not open a camera. Use --camera explicitly for physical
capture, or --video for a separately labelled prerecorded decode fallback.
Windows/PC success is not evidence of Jetson boot, camera or target stack.
Torch/CUDA are never imported or initialized; distribution metadata is reported
without claiming that a GPU or its runtime works.
"""

import argparse
from datetime import datetime, timezone
import importlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[2]


def read_linux_text(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace").strip("\x00\r\n ")
    except (OSError, ValueError):
        return None


def distribution_metadata(name):
    """Metadata only: a version string does not demonstrate a working import."""
    try:
        return {"metadata_found": True, "version": importlib.metadata.version(name)}
    except importlib.metadata.PackageNotFoundError:
        return {"metadata_found": False, "version": None}


def ram_bytes(system):
    if system == "Linux":
        content = read_linux_text("/proc/meminfo") or ""
        for line in content.splitlines():
            if line.startswith("MemTotal:"):
                try:
                    return int(line.split()[1]) * 1024
                except (ValueError, IndexError):
                    return None
    elif system == "Windows":
        try:
            import ctypes

            class MemoryStatus(ctypes.Structure):
                _fields_ = [("length", ctypes.c_ulong), ("memory_load", ctypes.c_ulong),
                            ("total_phys", ctypes.c_ulonglong), ("avail_phys", ctypes.c_ulonglong),
                            ("total_page", ctypes.c_ulonglong), ("avail_page", ctypes.c_ulonglong),
                            ("total_virtual", ctypes.c_ulonglong), ("avail_virtual", ctypes.c_ulonglong),
                            ("avail_extended", ctypes.c_ulonglong)]

            status = MemoryStatus()
            status.length = ctypes.sizeof(status)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return int(status.total_phys)
        except (AttributeError, OSError):
            pass
    try:
        return int(os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE"))
    except (AttributeError, OSError, ValueError):
        return None


def platform_evidence():
    system, machine = platform.system(), platform.machine()
    model = read_linux_text("/proc/device-tree/model") if system == "Linux" else None
    tegra = read_linux_text("/etc/nv_tegra_release") if system == "Linux" else None
    arm = machine.lower().startswith(("arm", "aarch64"))
    jetson = system == "Linux" and arm and bool(tegra or (model and "jetson" in model.lower()))
    try:
        git = subprocess.run(["git", "--version"], text=True, capture_output=True,
                             timeout=5, check=False)
        git_version = git.stdout.strip() if git.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        git_version = None
    memory = ram_bytes(system)
    return {
        "system": system, "machine": machine, "platform": platform.platform(),
        "python": platform.python_version(), "python_executable": sys.executable,
        "python_at_least_3_10": tuple(sys.version_info[:2]) >= (3, 10),
        "git_version": git_version,
        "ram_bytes": memory, "ram_gib": round(memory / (1024 ** 3), 3) if memory else None,
        "device_tree_model": model, "nv_tegra_release": tegra,
        "jetson_family_detected": jetson,
        "reported_orin_nano_model": bool(jetson and model and "orin nano" in model.lower()),
        "exact_target_8gb_sku_verified": None,
        "target_note": "ARM alone does not identify a Jetson. Reported model and available RAM are separate observations; an 8 GB Orin Nano is not assumed.",
    }


def runtime_evidence():
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    imports = {}
    for name in ("numpy", "yaml", "jsonschema", "cv2"):
        try:
            module = importlib.import_module(name)
            version = vars(module).get("__version__")
            if version is None:
                version = distribution_metadata({"yaml": "PyYAML"}.get(name, name))["version"]
            imports[name] = {"import_ok": True, "version": version}
        except Exception as exc:
            imports[name] = {"import_ok": False, "error": type(exc).__name__ + ": " + str(exc)}
    try:
        from module_5.midterm.engine import DecisionEngine
        result = DecisionEngine().step({"time_s": 0.0, "face_valid": 1, "eye_valid": True,
                                        "validity_score": 1.0, "perclos": 0.05,
                                        "long_blinks": 0, "yawn_count": 0, "eye_closure_s": 1.6})
        core = {"import_ok": True, "smoke_ok": result["status"] == "OK" and result["driver_state"] == "DROWSY",
                "observed_state": result["driver_state"], "hardware_operations": False}
    except Exception as exc:
        core = {"import_ok": False, "smoke_ok": False,
                "error": type(exc).__name__ + ": " + str(exc), "hardware_operations": False}
    distributions = {name: distribution_metadata(name) for name in (
        "numpy", "PyYAML", "jsonschema", "opencv-python", "opencv-contrib-python",
        "mediapipe", "torch", "nvidia-cuda-runtime-cu12",
    )}
    return {
        "sg5_core": core, "optional_imports": imports, "distribution_metadata": distributions,
        "torch_imported_by_this_tool": False,
        "cuda_runtime_checked": False, "cuda_available": None,
        "full_vision_gpu_stack_verified": None,
        "cuda_note": "Torch/CUDA metadata is not GPU, CUDA execution or full-pipeline dependency proof. No Torch import or CUDA initialization is performed.",
        "scope": "SG5 core smoke plus lightweight SG4/OpenCV imports; not a full MediaPipe camera pipeline or a Torch model test",
    }


def capture_evidence(*, camera=None, video=None, frames=30, cv2_module=None):
    """Read and discard frames only when a source was explicitly requested."""
    if camera is None and video is None:
        return {"requested": False, "source_kind": None, "success": None,
                "reason": "No source selected; no camera was opened."}
    if camera is not None and video is not None:
        raise ValueError("camera and prerecorded video are mutually exclusive")
    if type(frames) is not int or not 1 <= frames <= 10000:
        raise ValueError("frames must be between 1 and 10000")
    kind = "live_camera" if camera is not None else "prerecorded_video_fallback"
    report = {"requested": True, "source_kind": kind, "frames_requested": frames,
              "source": camera if camera is not None else Path(video).name,
              "physical_camera_evidence": False, "frames_saved": 0}
    try:
        cv2 = cv2_module or importlib.import_module("cv2")
    except Exception as exc:
        return dict(report, success=False, reason="OpenCV import failed: " + str(exc))
    capture = None
    count, shape, duration = 0, None, 0.0
    try:
        capture = cv2.VideoCapture(camera if camera is not None else str(video))
        if not capture.isOpened():
            return dict(report, success=False, frames_read=0, reason="Requested source could not be opened.")
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        start = time.perf_counter()
        for _ in range(frames):
            ok, frame = capture.read()
            if not ok or frame is None:
                break
            count += 1
            shape = getattr(frame, "shape", None)
        duration = time.perf_counter() - start
        success = count == frames
        return dict(
            report, success=success, frames_read=count,
            physical_camera_evidence=kind == "live_camera" and success,
            observed_resolution={"width": int(shape[1]), "height": int(shape[0])} if shape and len(shape) >= 2 else None,
            source_reported_fps=fps if math.isfinite(fps) and fps > 0 else None,
            capture_decode_seconds=duration,
            observed_capture_decode_fps=count / duration if duration > 0 else None,
            timing_scope="Frame acquisition/decode only, without SG1-SG5 processing or display; not detector or end-to-end FPS",
            reason="Requested frames read and discarded; no image saved." if success else "Source ended or read failed before requested frame count.",
        )
    except Exception as exc:
        return dict(report, success=False, frames_read=count, reason=type(exc).__name__ + ": " + str(exc))
    finally:
        if capture is not None:
            capture.release()


def criterion(verified, reason):
    return {"verified": verified,
            "status": "PASS" if verified is True else "FAIL" if verified is False else "UNVERIFIED",
            "reason": reason}


def readiness_evidence(host, runtime, capture):
    target = host["jetson_family_detected"]
    boot = criterion(target, "Live Linux ARM plus NVIDIA Tegra/Jetson device metadata observed." if target
                     else "This runtime is not identified as a Jetson; PC/Linux ARM alone is not boot evidence for the target.")
    stack_ok = (host["python_at_least_3_10"] and runtime["sg5_core"]["smoke_ok"]
                and all(value["import_ok"] for value in runtime["optional_imports"].values()))
    stack = criterion(stack_ok if target else None,
                      "SG5 core smoke and declared lightweight imports executed on the detected Jetson; full vision/GPU stack remains outside this check."
                      if target and stack_ok else "Required runtime checks failed on target; inspect runtime details."
                      if target else "Runtime observations were collected off-target and do not prove the Jetson software stack.")
    if capture.get("source_kind") == "live_camera" and target:
        camera = criterion(capture["success"], "Explicit physical camera capture was attempted on detected Jetson; inspect source result.")
    else:
        camera = criterion(None, "Prerecorded fallback proves decoding only, not a physical camera."
                           if capture.get("source_kind") == "prerecorded_video_fallback"
                           else "No physical camera evidence was collected on the Jetson target.")
    return {"jetson_boot": boot, "software_stack": stack, "physical_camera": camera,
            "all_three_verified": all(item["verified"] is True for item in (boot, stack, camera))}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="save diagnostic JSON; stdout is always available")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--camera", type=int, help="explicitly open this physical camera index")
    source.add_argument("--video", type=Path, help="prerecorded fallback, not physical-camera evidence")
    parser.add_argument("--frames", type=int, default=30)
    parser.add_argument("--strict", action="store_true", help="exit 1 unless target boot, scoped stack and camera all verify")
    args = parser.parse_args(argv)
    if not 1 <= args.frames <= 10000 or (args.camera is not None and args.camera < 0):
        parser.error("frames must be 1..10000 and camera index must be nonnegative")
    host, runtime = platform_evidence(), runtime_evidence()
    capture = capture_evidence(camera=args.camera, video=args.video, frames=args.frames)
    report = {"schema_version": "sg5.platform_evidence.v1",
              "created_utc": datetime.now(timezone.utc).isoformat(),
              "host": host, "runtime": runtime, "capture": capture,
              "readiness": readiness_evidence(host, runtime, capture),
              "limitations": ["No GPIO, buzzer, package installation or training was performed.",
                              "PC execution is not Jetson evidence.",
                              "No camera is opened unless --camera is explicitly supplied.",
                              "A video fallback cannot verify a physical camera.",
                              "CUDA execution and the full SG1-SG6 hardware pipeline are not tested."]}
    serialized = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 1 if args.strict and not report["readiness"]["all_three_verified"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
