"""Create report figures from verified snapshots and actual saved-video cues.

Run in the PC vision environment. No training, camera capture or inference is
performed. Existing practice outputs are read, never overwritten. New native
SG4 demonstration captures go only into ignored tmp/report_capture/.
"""

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[3]
ASSETS = ROOT / "module_5/midterm/report/assets"
SOURCE_REF = "bf15c3b2d97040f9589cf0b9a9b07aad0e331268"
COLORS = ["#C7762C", "#7D72A9", "#3A8979", "#326E9B", "#A26590"]
NAMES = ["A", "B", "C original", "C robust", "C fast"]


def blob(path, ref=SOURCE_REF):
    return subprocess.check_output(["git", "show", ref + ":" + path], cwd=ROOT)


def snapshot(path):
    return json.loads(blob(path))


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def asset_hash(path):
    data = path.read_bytes()
    if path.suffix in {".json", ".jsonl", ".txt", ".svg"}:
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def plot_comparison(evidence):
    rows = evidence["overall"]
    fig, axes = plt.subplots(2, 2, figsize=(11, 6.5), constrained_layout=True)
    panels = [("accuracy", "Correct state predictions (%)", 100),
              ("false_drowsy_duration_s", "Time DROWSY outside a labelled episode (s)", 1),
              ("driver_state_changes", "Driver-state changes (status changes excluded)", 1),
              ("drowsy_recall", "DROWSY samples caught (%)", 100)]
    for axis, (key, title, scale) in zip(axes.flat, panels):
        values = [r[key] * scale for r in rows]
        bars = axis.bar(NAMES, values, color=COLORS, width=.62)
        axis.bar_label(bars, labels=[f"{v:.1f}" if scale == 100 or key.endswith("_s") else f"{v:.3f}" if key == "macro_f1" else str(int(v)) for v in values], padding=4, fontsize=10)
        axis.set_title(title, loc="left", fontsize=10, pad=12)
        axis.set_ylim(0, max(values) * 1.24 if max(values) else 1)
        axis.grid(axis="y", alpha=.18)
        axis.set_axisbelow(True)
        axis.spines[["top", "right"]].set_visible(False)
        axis.tick_params(axis="x", labelsize=9)
    fig.savefig(ASSETS / "results_dashboard.png", dpi=180)
    plt.close(fig)

    row = next(r for r in rows if r["method"] == "stable_c")
    counts = np.array(row["confusion"]["counts"])
    percent = counts / counts.sum(axis=1, keepdims=True) * 100
    fig, axis = plt.subplots(figsize=(6.4, 3.8), constrained_layout=True)
    axis.imshow(percent, vmin=0, vmax=100, cmap="Blues", aspect="auto")
    for i in range(3):
        for j in range(4):
            axis.text(j, i, f"{percent[i,j]:.1f}%\n{counts[i,j]} rows", ha="center", va="center", fontsize=10, color="white" if percent[i,j] > 50 else "#182B45")
    axis.set_xticks(range(4), ["NORMAL", "WARNING", "DROWSY", "UNKNOWN"])
    axis.set_yticks(range(3), ["NORMAL", "WARNING", "DROWSY"])
    axis.set_xlabel("Robust C prediction")
    axis.set_ylabel("Reference label")
    axis.tick_params(labelsize=8)
    fig.savefig(ASSETS / "robust_c_confusion.png", dpi=180)
    plt.close(fig)


def plot_timelines():
    rows = list(csv.DictReader(io.StringIO(blob("module_5/midterm/results/evaluation/drive1_synthetic_predictions.csv").decode("utf-8"))))
    t = np.array([float(r["time_s"]) for r in rows])
    levels = {"NORMAL": 0, "WARNING": 1, "DROWSY": 2, "UNKNOWN": np.nan}
    gt = np.array([levels[r["ground_truth"]] for r in rows])
    fig, axes = plt.subplots(4, 1, figsize=(11, 6.4), sharex=True, constrained_layout=True)
    for axis, key, title, color in zip(axes, ["ground_truth", "week5_A", "week5_B", "stable_c"], ["Reference", "A threshold", "B weighted", "C robust"], ["#182B45", COLORS[0], COLORS[1], COLORS[3]]):
        pred = np.array([levels[r[key]] for r in rows])
        axis.step(t, pred, where="post", color=color, linewidth=1.7)
        if key != "ground_truth":
            axis.step(t, gt, where="post", color="#182B45", alpha=.45, linestyle="--", linewidth=.8)
            axis.fill_between(t, -.25, 2.3, where=np.isnan(pred), step="post", color="#CCD2DA", alpha=.6)
        axis.fill_between(t, -.25, 2.3, where=gt == 2, step="post", color="#F3DAD5", alpha=.45)
        axis.set_yticks([0, 1, 2], ["N", "W", "D"])
        axis.set_ylabel(title, fontsize=9)
        axis.set_ylim(-.25, 2.3)
        axis.grid(alpha=.17)
        axis.spines[["top", "right"]].set_visible(False)
    axes[-1].set_xlabel("Source time (seconds)")
    fig.savefig(ASSETS / "decision_timeline.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(11, 2.5), constrained_layout=True)
    for axis, bounds, title in zip(axes, [(72, 84), (135, 170)], ["Short episode: B misses the closure", "Gradual episode: C responds later"]):
        for track, key, name, color in zip([3, 2, 1, 0], ["ground_truth", "week5_A", "week5_B", "stable_c"], ["Reference", "A", "B", "C robust"], ["#182B45", COLORS[0], COLORS[1], COLORS[3]]):
            on = np.array([r[key] == "DROWSY" for r in rows])
            axis.fill_between(t, track, track + .62, where=on, step="post", color=color)
            axis.axhline(track, color="#D9DEE5", linewidth=.7)
        axis.set_xlim(*bounds)
        axis.set_ylim(-.12, 3.85)
        axis.set_yticks([.31, 1.31, 2.31, 3.31], ["C robust", "B", "A", "Reference"])
        axis.set_title(title, fontsize=10, loc="left")
        axis.set_xlabel("Source time (s)", fontsize=9)
        axis.spines[["top", "right", "left"]].set_visible(False)
        axis.grid(axis="x", alpha=.2)
    fig.savefig(ASSETS / "episode_zoom.png", dpi=180)
    plt.close(fig)


def jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def make_signal_photos():
    directory = ROOT / "module_5/midterm/results/video02"
    eye = jsonl(directory / "sg2_frames.jsonl")
    mouth = jsonl(directory / "sg3_frames.jsonl")
    face = {r["frame_id"]: r for r in jsonl(directory / "sg1_frames.jsonl")}
    mouth_by_id = {r["frame_id"]: r for r in mouth}
    eye_by_id = {r["frame_id"]: r for r in eye}
    chosen = [("signal_open", min((r for r in eye if r["eye_state"] == "OPEN"), key=lambda r: abs(r["ear"] - .30))),
              ("signal_closed", min((r for r in eye if r["eye_state"] == "CLOSED"), key=lambda r: r["ear"])),
              ("signal_mouth_low", min((r for r in mouth if r["valid"]), key=lambda r: r["mar"])),
              ("signal_mouth_high", max((r for r in mouth if r["valid"] and r["yawn_active"]), key=lambda r: r["mar"]))]
    video = ROOT / "module_1/data/videos/driver_sample_02.mp4"
    capture = cv2.VideoCapture(str(video))
    panels = []
    try:
        for name, record in chosen:
            fid = record["frame_id"]
            capture.set(cv2.CAP_PROP_POS_FRAMES, fid)
            ok, image = capture.read()
            if not ok:
                raise ValueError("Cannot extract source frame %d" % fid)
            x1, y1, x2, y2 = face[fid]["face_bbox_xyxy"]
            w, h = x2-x1, y2-y1
            crop = image[max(0,int(y1-.22*h)):min(image.shape[0],int(y2+.22*h)), max(0,int(x1-.32*w)):min(image.shape[1],int(x2+.32*w))]
            if not crop.size:
                raise ValueError("Empty source-frame crop")
            cv2.imwrite(str(ASSETS / (name + ".jpg")), crop, [cv2.IMWRITE_JPEG_QUALITY, 94])
            panels.append({"asset": name + ".jpg", "video": video.name, "frame_id": fid,
                           "time_s": face[fid]["timestamp_ms"]/1000,
                           "eye_state": eye_by_id[fid]["eye_state"], "ear": eye_by_id[fid]["ear"],
                           "mar": mouth_by_id[fid]["mar"], "yawn_active": mouth_by_id[fid]["yawn_active"],
                           "note": "Actual source frame and recorded algorithm prediction; not a ground-truth label"})
    finally:
        capture.release()

    fig, axes = plt.subplots(2, 1, figsize=(11, 2.8), sharex=True, constrained_layout=True)
    axes[0].plot([r["timestamp"] for r in eye], [r["ear"] for r in eye], color=COLORS[3], linewidth=1.1)
    axes[0].axhline(.15, color="#A6584A", linestyle="--", linewidth=.9)
    axes[0].set_ylabel("EAR")
    axes[1].plot([r["time_s"] for r in mouth], [r["mar"] for r in mouth], color=COLORS[2], linewidth=1.1)
    axes[1].axhline(.50, color="#A6584A", linestyle="--", linewidth=.9)
    axes[1].axhline(.45, color="#A6584A", linestyle=":", linewidth=.8)
    axes[1].set_ylabel("MAR")
    axes[1].set_xlabel("Clip 02 source time (s)")
    for axis in axes:
        axis.grid(alpha=.18)
        axis.spines[["top", "right"]].set_visible(False)
        axis.tick_params(labelsize=8)
    fig.savefig(ASSETS / "recorded_eye_mouth_signals.png", dpi=180)
    plt.close(fig)
    return panels


def console_image(name, title, lines):
    # This renders genuine captured text, not an invented application screenshot.
    font_path = Path("C:/Windows/Fonts/consola.ttf")
    font = ImageFont.truetype(str(font_path), 25) if font_path.exists() else ImageFont.load_default(size=25)
    wrapped=[]
    measure=ImageDraw.Draw(Image.new("RGB",(1,1)))
    for line in lines:
        current=""
        for word in line.split():
            candidate=(current+" "+word).strip()
            if current and measure.textlength(candidate,font=font)>1538:
                wrapped.append(current)
                current="    "+word
            else:
                current=candidate
        wrapped.append(current)
    image = Image.new("RGB", (1600, 80 + 38*len(wrapped)), "#142339")
    draw = ImageDraw.Draw(image)
    draw.text((28, 20), title, fill="#B8D5EB", font=font)
    for i, line in enumerate(wrapped):
        color = "#F5C577" if "WARNING" in line else "#F0B1A9" if "DROWSY" in line or "INSUFFICIENT" in line else "#E6EEF5"
        draw.text((28, 70 + 38*i), line, fill=color, font=font)
    image.save(ASSETS / name)


def capture_demos():
    captures = {}
    for scenario in ("drowsy", "face_lost"):
        output = ROOT / "tmp/report_capture" / scenario
        command = [sys.executable, "-m", "module_5.midterm.demo", "--scenario", scenario, "--output", str(output)]
        run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True)
        consumer = subprocess.run([sys.executable, "embedded_6/sg5_handoff/consume.py", "--input", str(output / "sg6_stream.jsonl"), "--events-only"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True)
        (ASSETS / ("demo_" + scenario + "_stdout.txt")).write_text(run.stdout, encoding="utf-8")
        (ASSETS / ("consumer_" + scenario + "_stdout.jsonl")).write_text(consumer.stdout, encoding="utf-8")
        lines = [line for line in run.stdout.splitlines() if re.match(r"^\s*\d+\.\d+s", line)]
        if scenario == "face_lost":
            lines = lines[:3]
        console_image("demo_" + scenario + ".png", "Recorded SG5 console output  |  " + scenario, lines)
        decisions = jsonl(output / "sg6_stream.jsonl")
        selected = {}
        for decision in decisions:
            selected.setdefault(decision["driver_state"] + ":" + decision["status"], decision)
        captures[scenario] = {"summary": json.loads((output / "summary.json").read_text()),
                              "requests": [json.loads(line) for line in consumer.stdout.splitlines() if line.strip()],
                              "example_decisions": list(selected.values()),
                              "command": command[1:-1] + ["<temporary output directory>"],
                              "capture_kind": "actual CLI execution, text rendered for legibility"}
    return captures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-ref", default=SOURCE_REF)
    args = parser.parse_args()
    if args.source_ref != SOURCE_REF:
        raise ValueError("Change the pinned snapshot in source and reverify before changing report evidence.")
    ASSETS.mkdir(parents=True, exist_ok=True)
    evaluation = snapshot("module_5/midterm/results/evaluation/evaluation.json")
    videos = [snapshot(f"module_5/midterm/results/video{i:02d}/summary.json") for i in range(1,6)]
    video02 = ROOT / "module_1/data/videos/driver_sample_02.mp4"
    if hashlib.sha256(video02.read_bytes()).hexdigest() != videos[1]["source_sha256"]:
        raise ValueError("Clip 02 bytes differ from the verified source snapshot.")
    if len(jsonl(ROOT / "module_5/midterm/results/video02/sg2_frames.jsonl")) != videos[1]["processed_frames"]:
        raise ValueError("Clip 02 cue stream is partial; regenerate its full pipeline run first.")
    verification = snapshot("module_5/midterm/results/verification.json")
    sources = snapshot("integration/sg5_midterm_sources.json")
    for i in range(1,6):
        data = blob(f"module_5/midterm/results/video{i:02d}/example_warning.jpg")
        (ASSETS / f"video{i:02d}_output.jpg").write_bytes(data)
    plot_comparison(evaluation)
    plot_timelines()
    signals = make_signal_photos()
    demos = capture_demos()
    bundle = {"schema_version": "sg5.report_evidence.v2", "source_commit": SOURCE_REF,
              "source_note": "Verified full-run snapshots, not later partial interactive reruns",
              "evaluation": evaluation, "videos": videos, "verification": verification,
              "sources": sources, "signal_photos": signals, "demos": demos,
              "photo_provenance": "Actual SG1 shared videos and recorded SG1/SG2/SG3 measurements; ROI crops for legibility; no generated faces or ground-truth claim"}
    save_json(ASSETS / "evidence_bundle.json", bundle)
    manifest = {"source_commit": SOURCE_REF, "text_hash_policy": "Normalize CRLF to LF for .json, .jsonl, .txt and .svg; binary files use exact bytes", "files": {p.name: asset_hash(p) for p in sorted(ASSETS.iterdir()) if p.is_file() and p.name not in {"evidence_manifest.json"}}}
    save_json(ASSETS / "evidence_manifest.json", manifest)
    print("Prepared charts, actual-frame photos and captured demo output at", ASSETS)


if __name__ == "__main__":
    main()
