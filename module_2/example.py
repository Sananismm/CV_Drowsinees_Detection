"""Reproduce the complete decodable-video real-video SG-2 demonstration after bootstrap.

Input source and SG-1/SG-4 revisions: see bootstrap.py and README.md.
"""
from pathlib import Path
import subprocess
import sys


def main():
    root=Path(__file__).resolve().parent
    local=root/"local"
    video=local/"eyeblink8/eyeblink8/10/27122013_153916_cam.avi"
    required=[video,local/"sg1/sg1_detector.py",local/"sg4.ipynb",local/"face_landmarker.task",root/"models/best.pt"]
    if not all(p.exists() for p in required):
        raise SystemExit("Run python -m module_2.bootstrap first; retain the trained models/best.pt checkpoint.")
    input_args=["--sg1-jsonl",str(local/"sequences/10.sg1.jsonl")] if (local/"sequences/10.audit.json").exists() else ["--sg1-source",str(local/"sg1/sg1_detector.py"),"--landmarker-model",str(local/"face_landmarker.task")]
    subprocess.run([sys.executable,"-m","module_2.demo","--video",str(video),
        "--timestamps",str(video.with_suffix(".txt")),*input_args,"--checkpoint",str(root/"models/best.pt"),
        "--sg4-notebook",str(local/"sg4.ipynb"),"--output",str(local/"final_demo_ear_first")],
        cwd=root.parent,check=True)


if __name__=="__main__":main()
