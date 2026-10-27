"""Build independent labelled paired crops from EyeBlink8 using SG-1 once.

Annotation semantics: https://www.blinkingmatters.com/research
Only paths, identities, labels, EAR and provenance belong in committed evidence.
Raw videos, crops and 478-point records stay in ignored module_2/local.
"""
import argparse
from collections import defaultdict, Counter
import csv
import hashlib
import json
from pathlib import Path
import random
import cv2
from .demo import load_sg1
from .adapters import process_sg1_eye_packet
from .crops import extract_eye_crops


def annotations(path):
    rows=[]
    for line in Path(path).read_text().splitlines():
        parts=line.strip().split(":")
        if len(parts)!=19 or not parts[0].isdigit():continue
        fid,blink=int(parts[0]),int(parts[1])
        nf,lfc,lnv,rfc,rnv=parts[2:7]
        if nf!="X" or lnv!="X" or rnv!="X":continue
        label="CLOSED" if lfc==rfc=="C" else ("OPEN" if blink==-1 and lfc==rfc=="X" else None)
        if label:rows.append((fid,blink,label))
    return rows


def select_samples(rows, seed, maximum):
    rng=random.Random(seed)
    events=defaultdict(list)
    for fid,blink,label in rows:
        if label=="CLOSED":events[blink].append(fid)
    closed=[sorted(fids)[len(fids)//2] for _,fids in sorted(events.items())]
    closed=sorted(rng.sample(closed,min(maximum,len(closed))))
    opens=[fid for fid,_,label in rows if label=="OPEN"]
    selected=[(fid,"CLOSED") for fid in closed]+[(fid,"OPEN") for fid in rng.sample(opens,min(len(closed),len(opens)))]
    return sorted(selected)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset",type=Path,required=True)
    p.add_argument("--sg1-source",type=Path,required=True)
    p.add_argument("--landmarker-model",type=Path,required=True)
    p.add_argument("--output",type=Path,default=Path("module_2/local/prepared"))
    p.add_argument("--config",type=Path,default=Path(__file__).with_name("config.json"))
    args=p.parse_args();config=json.loads(args.config.read_text())
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/"crops").mkdir(exist_ok=True);(args.output/"records").mkdir(exist_ok=True)
    manifest=[];audit=[]
    for video_id,assignment in config["split_by_video"].items():
        videos=list((args.dataset/video_id).glob("*.avi"))
        if len(videos)!=1:raise ValueError("one video expected per directory: "+video_id)
        video=videos[0];rows=annotations(video.with_suffix(".tag"))
        selected=select_samples(rows,config["seed"]+int(video_id),config["max_closed_events_per_video"])
        timestamps={int(a):float(b) for a,b in (line.split() for line in video.with_suffix(".txt").read_text().splitlines() if line.strip())}
        cap=cv2.VideoCapture(str(video));detector=load_sg1(args.sg1_source,args.landmarker_model)
        rejected=Counter();retained=Counter();decoded_id=-1
        try:
            for fid,label in selected:
                # Decode sequentially: seeking H.264 can reconstruct early frames differently.
                ok=False;image=None
                while decoded_id < fid:
                    ok,image=cap.read();decoded_id+=1
                    if not ok:break
                if not ok:rejected["decode_failed"]+=1;continue
                timestamp=timestamps[fid]
                record=detector.process(image,fid,round(timestamp*1000))
                out=process_sg1_eye_packet(record)
                crops,_=extract_eye_crops(image,record,frame_id=fid,timestamp_sec=timestamp)
                if not crops:rejected[out["invalid_reason"] or "unusable_crop"]+=1;continue
                stem=f"{video_id}_{fid}"
                crop_paths=[]
                for side,crop in zip(("left","right"),crops):
                    file=Path("crops")/(stem+"_"+side+".png")
                    if not cv2.imwrite(str(args.output/file),crop):raise RuntimeError("crop write failed")
                    crop_paths.append(file.as_posix())
                record_path=Path("records")/(stem+".json")
                (args.output/record_path).write_text(json.dumps(record,allow_nan=False)+"\n")
                manifest.append(dict(video_id=video_id,subject_id=assignment["subject_id"],split=assignment["split"],frame_id=fid,
                    timestamp_sec=record["timestamp_ms"]/1000,label=label,label_source="dataset_annotation",left_crop=crop_paths[0],right_crop=crop_paths[1],
                    sg1_record=record_path.as_posix(),ear=out["ear"] if out["valid"] else "",annotation_sha256=hashlib.sha256(video.with_suffix(".tag").read_bytes()).hexdigest()))
                retained[label]+=1
        finally:cap.release();detector.close()
        entry=dict(video_id=video_id,**assignment,selected=len(selected),retained=dict(retained),rejected=dict(rejected))
        audit.append(entry);print(json.dumps(entry),flush=True)
    if not manifest:raise ValueError("no usable crops")
    with (args.output/"manifest.csv").open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(manifest[0]));writer.writeheader();writer.writerows(manifest)
    provenance=dict(videos=audit,label_policy=config["label_rule"],grouping_evidence=config["grouping_evidence"],
        sg1_source_sha256=hashlib.sha256(args.sg1_source.read_bytes()).hexdigest(),
        landmarker_sha256=hashlib.sha256(args.landmarker_model.read_bytes()).hexdigest(),
        config_sha256=hashlib.sha256(args.config.read_bytes()).hexdigest())
    (args.output/"data_audit.json").write_text(json.dumps(provenance,indent=2)+"\n")


if __name__=="__main__":main()
