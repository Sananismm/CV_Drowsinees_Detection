import argparse
import csv
import json
from pathlib import Path
import statistics
import time

import cv2
import numpy as np

from sg1_detector import DetectorConfig, SG1FaceLandmarkDetector, draw_result


ROOT = Path(__file__).resolve().parents[1]


def read_configs(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    configs = [DetectorConfig(**item) for item in data["configurations"]]
    model_path = (ROOT / data["model_path"]).resolve()
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}. Run scripts/download_model.py first.")
    return data, configs, model_path


def process_one(video_path, output_dir, config, model_path, frame_stride, max_frames, save_video):
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")
    source_fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
    source_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    source_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    pred_path = output_dir / f"predictions_{config.name}.jsonl"
    fail_path = output_dir / f"failures_{config.name}.csv"
    video_writer = None
    if save_video:
        out_path = output_dir / f"annotated_{config.name}.mp4"
        output_fps = source_fps / max(1, frame_stride) if source_fps > 0 else 20
        video_writer = cv2.VideoWriter(str(out_path), cv2.VideoWriter_fourcc(*"mp4v"), output_fps, (source_w, source_h))
        if not video_writer.isOpened():
            cap.release()
            raise RuntimeError(f"Could not create annotated video: {out_path}")

    detector = SG1FaceLandmarkDetector(model_path, config)
    latencies, centers, landmark_counts = [], [], []
    frame_id = 0
    processed = detected = 0
    wall_start = time.perf_counter()
    with pred_path.open("w", encoding="utf-8") as predictions, fail_path.open("w", newline="", encoding="utf-8") as failures:
        fail_writer = csv.writer(failures)
        fail_writer.writerow(["frame_idx", "timestamp_ms", "reason"])
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            current_id = frame_id
            frame_id += 1
            if current_id % frame_stride:
                continue
            if max_frames and processed >= max_frames:
                break
            timestamp_ms = int(round(current_id * 1000.0 / source_fps)) if source_fps > 0 else current_id * 33
            output = detector.process(frame, current_id, timestamp_ms)
            predictions.write(json.dumps(output, separators=(",", ":")) + "\n")
            processed += 1
            latencies.append(float(output["inference_ms"]))
            if output["status"] == "OK":
                detected += 1
                landmark_counts.append(int(output["landmark_count"]))
                x1, y1, x2, y2 = output["face_bbox_xyxy"]
                centers.append(((x1 + x2) / (2 * source_w), (y1 + y2) / (2 * source_h)))
            else:
                fail_writer.writerow([current_id, timestamp_ms, "NO_FACE"])
            if video_writer is not None:
                video_writer.write(draw_result(frame, output))

    wall_elapsed = time.perf_counter() - wall_start
    detector.close()
    cap.release()
    if video_writer is not None:
        video_writer.release()
    jitter = [float(np.linalg.norm(np.subtract(b, a))) for a, b in zip(centers, centers[1:])]
    sorted_lat = sorted(latencies)
    p95 = float(np.percentile(sorted_lat, 95)) if sorted_lat else 0.0
    return {
        "config_name": config.name,
        "input_long_side": config.input_long_side,
        "min_face_detection_confidence": config.min_face_detection_confidence,
        "min_face_presence_confidence": config.min_face_presence_confidence,
        "min_tracking_confidence": config.min_tracking_confidence,
        "video": str(video_path),
        "source_width": source_w,
        "source_height": source_h,
        "source_fps": round(source_fps, 3),
        "source_frames": total_frames,
        "processed_frames": processed,
        "faces_found": detected,
        "face_coverage": round(detected / processed, 6) if processed else 0.0,
        "frames_with_landmarks": len(landmark_counts),
        "mean_landmarks_per_detected_face": round(statistics.mean(landmark_counts), 2) if landmark_counts else 0.0,
        "no_face_frames": processed - detected,
        "mean_inference_ms": round(statistics.mean(latencies), 3) if latencies else 0.0,
        "p95_inference_ms": round(p95, 3),
        "approx_inference_fps": round(1000 / statistics.mean(latencies), 3) if latencies and statistics.mean(latencies) else 0.0,
        "end_to_end_processed_fps": round(processed / wall_elapsed, 3) if wall_elapsed else 0.0,
        "mean_normalized_center_step": round(statistics.mean(jitter), 6) if jitter else None,
        "wall_seconds": round(wall_elapsed, 3),
        "predictions_file": pred_path.name,
        "failures_file": fail_path.name,
    }


def main():
    parser = argparse.ArgumentParser(description="Compare SG-1 face/landmark configurations on one video.")
    parser.add_argument("--input", required=True, type=Path, help="Driver-facing video file")
    parser.add_argument("--config", type=Path, default=ROOT / "configs" / "experiment.json")
    parser.add_argument("--output-dir", type=Path, help="Defaults to results/<video-stem>")
    parser.add_argument("--frame-stride", type=int, help="Override config frame stride")
    parser.add_argument("--max-frames", type=int, help="0 means process the whole clip")
    parser.add_argument("--save-video", action="store_true", help="Also save annotated MP4 for each setting")
    args = parser.parse_args()
    video_path = args.input.resolve()
    if not video_path.exists():
        parser.error(f"Input video not found: {video_path}")
    config_data, configs, model_path = read_configs(args.config.resolve())
    output_dir = args.output_dir.resolve() if args.output_dir else ROOT / "results" / video_path.stem
    output_dir.mkdir(parents=True, exist_ok=True)
    stride = args.frame_stride if args.frame_stride is not None else int(config_data.get("frame_stride", 1))
    max_frames = args.max_frames if args.max_frames is not None else int(config_data.get("max_frames", 0))
    if stride < 1 or max_frames < 0:
        parser.error("frame stride must be >= 1 and max frames must be >= 0")

    rows = []
    for config in configs:
        print(f"Running {config.name}: input_long_side={config.input_long_side}, thresholds={config.min_face_detection_confidence:.2f}")
        rows.append(process_one(video_path, output_dir, config, model_path, stride, max_frames, args.save_video))
    comparison_path = output_dir / "comparison.csv"
    with comparison_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    metadata = {
        "model_path": str(model_path),
        "mediapipe_version": __import__("mediapipe").__version__,
        "opencv_version": cv2.__version__,
        "input_video": str(video_path),
        "frame_stride": stride,
        "max_frames": max_frames,
        "configurations": [config.__dict__ for config in configs],
        "note": "Coverage and jitter are unlabeled proxies; they are not precision, recall, or landmark accuracy.",
    }
    (output_dir / "run_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"\nComparison written to: {comparison_path}")
    for row in rows:
        print(f"{row['config_name']}: coverage={row['face_coverage']:.1%}, mean={row['mean_inference_ms']:.1f} ms, p95={row['p95_inference_ms']:.1f} ms, end-to-end={row['end_to_end_processed_fps']:.1f} FPS")


if __name__ == "__main__":
    main()
