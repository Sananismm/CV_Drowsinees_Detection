"""Deterministic full-frame exact/near-copy audit across participant splits.

Perceptual hash is an engineering duplicate screen, not an identity classifier.
Accept no cross-split match under the predeclared hash+pixel rule.
OpenCV DCT API: https://docs.opencv.org/4.x/d2/de8/group__core__array.html
"""
from collections import defaultdict
import argparse
import hashlib
import json
from pathlib import Path
import cv2
import numpy as np


class NearDuplicateGuard:
    def __init__(self):
        self.buckets=defaultdict(set);self.entries=[];self.candidates_checked=0;self.splits=set()

    @staticmethod
    def fingerprint(image):
        if image is None or image.size==0:raise ValueError("empty duplicate-audit image")
        gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY) if image.ndim==3 else image
        thumb=cv2.resize(gray,(32,32),interpolation=cv2.INTER_AREA)
        coefficients=cv2.dct(thumb.astype(np.float32))[:8,:8].flatten()
        bits=coefficients>np.median(coefficients[1:]);bits[0]=False
        code=int.from_bytes(np.packbits(bits).tobytes(),"big")
        return code,thumb.astype(np.int16)

    def add(self,image,split,identity):
        code,thumb=self.fingerprint(image)
        keys=[(i,(code>>(i*12))&((1<<(16 if i==4 else 12))-1)) for i in range(5)]
        other_splits=self.splits
        candidates=set().union(*(self.buckets[(other,k)] for other in other_splits if other!=split for k in keys))
        for idx in candidates:
            old_code,old_thumb,old_split,old_identity=self.entries[idx]
            if old_split==split:continue
            self.candidates_checked+=1
            if (code^old_code).bit_count()<=4 and float(np.mean(np.abs(thumb-old_thumb)))<=2:
                raise ValueError(f"cross-split near duplicate: {identity} vs {old_identity}")
        index=len(self.entries);self.entries.append((code,thumb,split,identity))
        self.splits.add(split)
        for key in keys:self.buckets[(split,key)].add(index)


def main():
    root=Path(__file__).resolve().parent
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset",type=Path,default=root/"local/eyeblink8/eyeblink8")
    args=p.parse_args();config=json.loads((root/"config.json").read_text());guard=NearDuplicateGuard();counts={};tails={}
    subjects={};videos={}
    for vid,assignment in config["split_by_video"].items():
        split=assignment["split"];subject=assignment["subject_id"]
        if subject in subjects and subjects[subject]!=split:raise ValueError("participant leakage")
        subjects[subject]=split;videos[vid]=split
        video=next((args.dataset/vid).glob("*.avi"));cap=cv2.VideoCapture(str(video));fid=0
        try:
            while True:
                ok,image=cap.read()
                if not ok:break
                guard.add(image,split,(vid,fid));fid+=1
            tails[vid]=int(cap.get(cv2.CAP_PROP_FRAME_COUNT))-fid
            if tails[vid]<0:raise ValueError("decoded count exceeds header")
        finally:cap.release()
        counts[vid]=fid;print(vid,fid,"duplicate screen passed",flush=True)
    report=dict(passed=True,scope="all decoded full frames from all eight recordings across train/val/test groups",
        rule="64-bit DCT pHash Hamming<=4 AND 32x32 grayscale pixel MAE<=2 intensity levels",
        counts=counts,undecodable_tail_frames=tails,total_frames=sum(counts.values()),cross_split_candidates_checked=guard.candidates_checked,
        subject_groups=subjects,video_groups=videos,grouping_status=config["grouping_evidence"],
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        limitation="Heuristic copy screen, not proof of participant identity or absence of every possible transformed duplicate; participant grouping is primary separation")
    (root/"results/leakage_audit.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))


if __name__=="__main__":main()
