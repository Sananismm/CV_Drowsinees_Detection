"""Train on independent manual/dataset labels; select checkpoint by validation loss.

See README sources for split, loss and checkpoint documentation.
Run: python -m module_2.train --manifest ... --output module_2/models/best.pt
"""
import argparse
import csv
import hashlib
import json
import random
from pathlib import Path
import cv2
import torch
from torch import nn
from .cnn import EyeCNN, preprocess, SIZE


def load_manifest(path):
    path = Path(path)
    with path.open(newline="", encoding="utf-8") as f: rows = list(csv.DictReader(f))
    groups, videos, hashes, identities = {}, {}, {}, set()
    for row in rows:
        split,subject,video = row["split"],row["subject_id"],row["video_id"]
        if split not in ("train","val","test") or not subject or not video or row["label"] not in ("OPEN","CLOSED"):
            raise ValueError("invalid split, identity or independent label")
        if row["label_source"] not in ("manual", "dataset_annotation"):
            raise ValueError("labels must be independent of EAR/CNN")
        for mapping,key in ((groups,subject),(videos,video)):
            if key in mapping and mapping[key] != split: raise ValueError("subject/video leakage")
            mapping[key] = split
        key = (video,row["frame_id"])
        if key in identities: raise ValueError("duplicate sample identity")
        identities.add(key)
        for field in ("left_crop","right_crop"):
            file = (path.parent/row[field]).resolve()
            image = cv2.imread(str(file),cv2.IMREAD_GRAYSCALE)
            if image is None: raise ValueError("unreadable crop: "+str(file))
            digest = hashlib.sha256(image.tobytes()+str(image.shape).encode()).hexdigest()
            if digest in hashes and hashes[digest] != split: raise ValueError("duplicate image leakage")
            hashes[digest] = split
            row[field] = str(file)
    for split in ("train","val","test"):
        if {r["label"] for r in rows if r["split"] == split} != {"OPEN","CLOSED"}:
            raise ValueError("each split requires both classes")
    return rows


def tensors(rows, split):
    x,y = [],[]
    for r in rows:
        if r["split"] != split: continue
        for side in ("left_crop","right_crop"):
            x.append(preprocess(cv2.imread(r[side],cv2.IMREAD_GRAYSCALE)))
            y.append(int(r["label"] == "CLOSED"))
    return torch.stack(x),torch.tensor(y,dtype=torch.long)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--epochs",type=int,default=30)
    p.add_argument("--batch-size",type=int,default=64)
    p.add_argument("--seed",type=int,default=477)
    p.add_argument("--threads",type=int,default=2)
    args=p.parse_args()
    if args.epochs < 1 or args.batch_size < 1: p.error("positive epochs/batch size required")
    torch.set_num_threads(args.threads)
    random.seed(args.seed); torch.manual_seed(args.seed)
    torch.use_deterministic_algorithms(True)
    rows=load_manifest(args.manifest)
    # Test images validated for split hygiene but never used for optimization/selection.
    x,y=tensors(rows,"train"); vx,vy=tensors(rows,"val")
    model=EyeCNN()
    optimizer=torch.optim.Adam(model.parameters(),lr=0.001)
    counts=torch.bincount(y,minlength=2)
    criterion=nn.CrossEntropyLoss(weight=len(y)/(2*counts.float()))
    best=float("inf"); history=[]
    args.output.parent.mkdir(parents=True,exist_ok=True)
    for epoch in range(args.epochs):
        model.train(); losses=[]
        for idx in torch.randperm(len(y)).split(args.batch_size):
            optimizer.zero_grad(); loss=criterion(model(x[idx]),y[idx]);loss.backward();optimizer.step()
            losses.append(float(loss.detach()))
        model.eval()
        with torch.inference_mode():
            logits=model(vx); val=float(nn.functional.cross_entropy(logits,vy));accuracy=float((logits.argmax(1)==vy).float().mean())
        history.append(dict(epoch=epoch+1,train_loss=sum(losses)/len(losses),val_loss=val,val_eye_accuracy=accuracy))
        if val < best:
            best=val
            torch.save(dict(architecture="sg2.eye_cnn.v1",state_dict=model.state_dict(),classes=["OPEN","CLOSED"],
                input_size=list(SIZE),trained=True,seed=args.seed,best_epoch=epoch+1,validation_loss=val,
                manifest_sha256=hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
                parameters=sum(v.numel() for v in model.parameters()),
                hyperparameters=dict(epochs=args.epochs,batch_size=args.batch_size,lr=0.001,optimizer="Adam",class_weighting="inverse_frequency")),args.output)
        print(json.dumps(history[-1]),flush=True)
    args.output.with_suffix(".history.json").write_text(json.dumps(history,indent=2)+"\n")


if __name__ == "__main__": main()
