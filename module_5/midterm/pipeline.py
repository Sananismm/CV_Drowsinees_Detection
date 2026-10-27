"""Actual SG1 -> SG2 + causal SG3 adapter -> real SG4 -> SG5 -> SG6 packets.

Saved video is the reproducible default. Camera use is explicitly requested by
the operator. No accuracy is inferred from unlabelled video; no model trains.
"""

import argparse
from collections import Counter
from contextlib import ExitStack
import csv
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import platform
import statistics
import sys
import time

from .engine import CONFIGURATIONS, DecisionEngine, to_legacy_sg6


ROOT = Path(__file__).resolve().parents[2]


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def dump_line(stream, record):
    stream.write(json.dumps(record, allow_nan=False, separators=(",", ":")) + "\n")


def run_video(args):
    # Optional vision imports stay outside the deployable decision engine.
    import cv2
    import mediapipe
    import numpy
    source_dir = ROOT / "module_1" / "scripts"
    if str(source_dir) not in sys.path:
        sys.path.insert(0, str(source_dir))
    from sg1_detector import DetectorConfig, SG1FaceLandmarkDetector
    from sg1_contract import validate_sg1_record
    from module_2.processor import SG2Processor
    from module_2.adapters import to_sg4
    from .sg3_adapter import YawnAdapter
    from .sg4_bridge import SG4Bridge, synchronized_frame

    model = Path(args.model)
    if not model.is_file():
        raise ValueError("Landmark model missing. Run python module_1/scripts/download_model.py first.")
    expected_model = "64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff"
    if sha256_file(model) != expected_model:
        raise ValueError("Landmark model SHA-256 differs from SG1's pinned model.")
    is_camera = args.camera is not None
    source = args.camera if is_camera else str(Path(args.video).resolve())
    capture = cv2.VideoCapture(source)
    if not capture.isOpened():
        raise ValueError("Cannot open the requested camera/video: %s" % source)
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    if not is_camera and (not math.isfinite(fps) or fps <= 0):
        capture.release()
        raise ValueError("Video FPS is unavailable; do not invent capture timestamps.")
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    config = CONFIGURATIONS[args.config]
    sg5 = DecisionEngine(config, session_id=args.session)
    ear_config = json.loads((ROOT / "module_2/final_method.json").read_text())["selected"]
    if ear_config["method"] != "EAR":
        capture.release()
        raise ValueError("This lightweight integration is validated only with SG2's EAR mode.")
    eyes = SG2Processor(method_config=ear_config)
    mouth = YawnAdapter()
    temporal = SG4Bridge()
    detector = SG1FaceLandmarkDetector(model, DetectorConfig("sg5_midterm", 256, .5, .5, .5))
    if args.show:
        cv2.namedWindow("SG1 to SG6 midterm", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("SG1 to SG6 midterm", 1280, 720)
    started = time.perf_counter()
    capture_origin = time.monotonic()
    counts, statuses = Counter(), Counter()
    timings, sg5_timings, frame_id, sg4_count = [], [], 0, 0
    face_count = eye_count = yawn_events = legacy_count = 0
    writer = None
    last_decision = None
    transitions = []
    sg1_example = sg2_example = sg3_example = sg4_example = sg6_example = None
    sample_images = set()
    try:
        with ExitStack() as stack:
            streams = {name: stack.enter_context((output / (name + ".jsonl")).open("w", encoding="utf-8"))
                       for name in ("sg1_frames", "sg2_frames", "sg3_frames", "sg4_stream", "sg6_stream")}
            table = stack.enter_context((output / "frame_timings.csv").open("w", newline="", encoding="utf-8"))
            table_writer = csv.writer(table)
            table_writer.writerow(["frame_id", "time_s", "sg1_ms", "sg2_ms", "sg3_ms", "sg4_ms", "sg5_ms", "processing_ms"])
            while not args.max_frames or frame_id < args.max_frames:
                ok, frame = capture.read()
                if not ok:
                    break
                begin = time.perf_counter()
                source_t = time.monotonic() - capture_origin if is_camera else frame_id / fps
                sg1 = detector.process(frame, frame_id, round(source_t * 1000))
                validate_sg1_record(sg1)  # Returns the record or raises a contract error.
                t = sg1["timestamp_ms"] / 1000.0
                sg2, _, eye_timing = eyes.process(sg1, frame, frame_id=frame_id, timestamp_sec=t)
                cue = to_sg4(sg2)
                stage = time.perf_counter()
                sg3 = mouth.step(sg1)
                mouth_ms = (time.perf_counter() - stage) * 1000
                stage = time.perf_counter()
                vector = temporal.push(synchronized_frame(sg1, cue, sg3))
                temporal_ms = (time.perf_counter() - stage) * 1000
                decision_ms = 0.0
                if vector is not None:
                    stage = time.perf_counter()
                    decision = sg5.step(vector)
                    decision_ms = (time.perf_counter() - stage) * 1000
                    sg5_timings.append(decision_ms)
                    sg4_count += 1
                    counts[decision["driver_state"]] += 1
                    statuses[decision["status"]] += 1
                    dump_line(streams["sg4_stream"], vector)
                    dump_line(streams["sg6_stream"], decision)
                    if decision["status"] == "OK":
                        to_legacy_sg6(decision)
                        legacy_count += 1
                    if last_decision is None or (last_decision["driver_state"], last_decision["status"]) != (decision["driver_state"], decision["status"]):
                        transitions.append({k: decision[k] for k in ("time_s", "driver_state", "status", "reason")})
                        print("%7.3fs  %-7s  %-21s  %s" % (t, decision["driver_state"], decision["status"], decision["reason"]), flush=True)
                    last_decision = decision
                    if sg6_example is None or decision["driver_state"] == "DROWSY":
                        sg4_example, sg6_example = vector, decision
                processing_ms = (time.perf_counter() - begin) * 1000
                timings.append(processing_ms)
                face_count += sg1["status"] == "OK"
                eye_count += cue["eye_valid"]
                yawn_events += sg3["event"]
                compact_sg1 = {k: v for k, v in sg1.items() if k != "landmarks_xy_normalized"}
                dump_line(streams["sg1_frames"], compact_sg1)
                dump_line(streams["sg2_frames"], cue)
                dump_line(streams["sg3_frames"], sg3)
                table_writer.writerow([frame_id, t, sg1["inference_ms"], eye_timing["processing_ms"], mouth_ms, temporal_ms, decision_ms, processing_ms])
                if sg1_example is None and sg1["status"] == "OK":
                    sg1_example, sg2_example, sg3_example = compact_sg1, cue, sg3
                shown = frame.copy()
                if args.annotated or args.show:
                    box = sg1.get("face_bbox_xyxy")
                    if box:
                        cv2.rectangle(shown, tuple(box[:2]), tuple(box[2:]), (50, 200, 100), 2)
                    panel = numpy.zeros((shown.shape[0], 360, 3), dtype=numpy.uint8)
                    lines = ["SG5 MIDTERM INTEGRATION", "t %.2fs / frame %d" % (t, frame_id), "SG1: " + sg1["status"],
                             "SG2: " + cue["eye_state"], "SG3 MAR: " + ("unavailable" if sg3["mar"] is None else "%.3f" % sg3["mar"]),
                             "Yawn segment: " + str(sg3["yawn_active"])]
                    if last_decision:
                        lines += ["SG5: " + last_decision["driver_state"], "Status: " + last_decision["status"],
                                  "Score: %.3f" % last_decision["smoothed_score"], "No ground-truth accuracy claim"]
                    for i, line in enumerate(lines):
                        cv2.putText(panel, line, (12, 28 + i * 26), cv2.FONT_HERSHEY_SIMPLEX, .48, (230, 230, 230), 1, cv2.LINE_AA)
                    shown = numpy.concatenate([shown, panel], axis=1)
                    if args.annotated:
                        if writer is None:
                            writer = cv2.VideoWriter(str(output / "annotated.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), fps if fps > 0 else 25.0, (shown.shape[1], shown.shape[0]))
                            if not writer.isOpened():
                                raise ValueError("Annotated video writer could not be opened.")
                        writer.write(shown)
                    kind = last_decision["driver_state"] if last_decision else "START"
                    if kind not in sample_images:
                        cv2.imwrite(str(output / ("example_" + kind.lower() + ".jpg")), shown)
                        sample_images.add(kind)
                    if args.show:
                        cv2.imshow("SG1 to SG6 midterm", shown)
                        if cv2.waitKey(1) & 0xff in (ord("q"), 27):
                            frame_id += 1
                            break
                frame_id += 1
                if frame_id % 250 == 0:
                    print("Processed %d frames" % frame_id, flush=True)
        eyes.flush()
    finally:
        capture.release()
        detector.close()
        if writer is not None:
            writer.release()
        if args.show:
            cv2.destroyAllWindows()
    if not frame_id:
        raise ValueError("Source contained no readable frames.")
    elapsed = time.perf_counter() - started
    measured = sorted(timings)
    summary = {
        "evidence_kind": "real_video_integration_without_independent_drowsiness_labels" if not is_camera else "live_camera_integration_without_independent_labels",
        "source": str(Path(source).name) if not is_camera else "camera_%s" % source,
        "source_sha256": sha256_file(source) if not is_camera else None,
        "source_fps": fps, "processed_frames": frame_id, "sg4_vectors": sg4_count,
        "face_present_frames": face_count, "eye_valid_frames": eye_count,
        "sg3_confirmed_yawn_segments": yawn_events, "sg5_states": dict(counts), "sg5_statuses": dict(statuses),
        "legacy_valid_packets": legacy_count, "transitions": transitions,
        "mean_pipeline_processing_ms": statistics.mean(timings),
        "p95_pipeline_processing_ms": measured[min(len(measured)-1, math.ceil(.95*len(measured))-1)],
        "mean_sg5_processing_ms": statistics.mean(sg5_timings) if sg5_timings else None,
        "wall_seconds_including_io": elapsed, "offline_throughput_fps_including_io": frame_id / elapsed,
        "timing_scope": "PC processing excludes video acquisition and annotation/encoding; wall throughput includes IO, not a Jetson or camera FPS claim",
        "platform": platform.platform(), "python": platform.python_version(),
        "versions": {"numpy": numpy.__version__, "opencv": cv2.__version__, "mediapipe": mediapipe.__version__},
        "config": asdict(config), "model_sha256": expected_model,
        "sg2_config": ear_config, "sg3_adapter_owner_acceptance": "PENDING",
        "sg4_availability_adapter_owner_acceptance": "PENDING", "sg6_v2_owner_acceptance": "PENDING",
        "accuracy": None, "accuracy_note": "No independent ground truth; states and counts are predictions, not accuracy.",
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (output / "examples.json").write_text(json.dumps({"sg1": sg1_example, "sg2": sg2_example, "sg3": sg3_example, "sg4": sg4_example, "sg6": sg6_example}, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, allow_nan=False))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--video")
    source.add_argument("--camera", type=int)
    parser.add_argument("--model", default=str(ROOT / "module_1/models/face_landmarker.task"))
    parser.add_argument("--output", default=str(ROOT / "module_5/midterm/results/video_demo"))
    parser.add_argument("--session", default="midterm-video")
    parser.add_argument("--config", choices=tuple(CONFIGURATIONS), default="stable_c")
    parser.add_argument("--max-frames", type=int, default=0, help="0 processes the whole source")
    parser.add_argument("--annotated", action="store_true", help="save annotated video and example images")
    parser.add_argument("--show", action="store_true", help="explicitly open an interactive preview")
    args = parser.parse_args()
    if args.max_frames < 0:
        parser.error("--max-frames must be nonnegative")
    try:
        run_video(args)
    except (ValueError, OSError) as exc:
        parser.exit(1, "ERROR: %s\n" % exc)


if __name__ == "__main__":
    main()
