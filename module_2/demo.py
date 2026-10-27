"""Synchronized video + SG-1 records -> EAR/CNN, events, SG-4 cues and overlay.

Uses SG-1's detector exactly once only when --sg1-jsonl is not supplied.
OpenCV video API: https://docs.opencv.org/4.x/dd/d9e/classcv_1_1VideoWriter.html
"""
import argparse
import ast
from collections import deque
import importlib.util
import json
from pathlib import Path
import sys
import time
import cv2
from .adapters import to_sg4, SG4Bridge


def load_sg1(source, model):
    source=Path(source).resolve()
    sys.path.insert(0,str(source.parent))
    try:
        spec=importlib.util.spec_from_file_location("sg2_external_sg1",source)
        module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    config=module.DetectorConfig("baseline",256,0.5,0.5,0.5)
    return module.SG1FaceLandmarkDetector(Path(model),config)


def load_sg4(path, fps):
    """Load only the actual TemporalAnalyzer class, never notebook shell/demo cells."""
    notebook=json.loads(Path(path).read_text(encoding="utf-8"))
    for cell in notebook["cells"]:
        source="".join(cell.get("source",[]))
        if cell["cell_type"] == "code" and "class TemporalAnalyzer" in source:
            tree=ast.parse(source)
            nodes=[n for n in tree.body if isinstance(n,ast.ClassDef) and n.name == "TemporalAnalyzer"]
            if len(nodes) != 1: continue
            namespace={"deque":deque,"time":time}
            exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),"exec"),namespace)
            return namespace["TemporalAnalyzer"](fps=fps)
    raise ValueError("SG-4 TemporalAnalyzer not found")


def render(frame,record,output,boxes,event_count,blink_count):
    """Annotations are drawn only after all inference on untouched pixels."""
    import numpy as np
    from .adapters import eye_packet
    thumbnails=[frame[y1:y2,x1:x2].copy() for x1,y1,x2,y2 in boxes]
    display=frame.copy();h,w=display.shape[:2]
    for x1,y1,x2,y2 in boxes:cv2.rectangle(display,(x1,y1),(x2,y2),(0,255,0),1)
    packet=eye_packet(record)
    if packet["eyes_valid"]:
        for side in ("left","right"):
            for x,y in packet[side+"_eye_points_xy_normalized"]:
                cv2.circle(display,(round(x*w),round(y*h)),1,(0,255,255),-1)
    panel=np.full((max(h,480),400,3),245,np.uint8)
    fmt=lambda x:"N/A" if x is None else f"{x:.3f}"
    lines=["SG-2: FINAL EYE ANALYSIS",f"Frame {output['frame_id']}  t={output['timestamp_sec']:.3f}s",
        f"L EAR {fmt(output['left_ear'])}   R EAR {fmt(output['right_ear'])}",
        f"EAR: {output['ear_eye_state']}",
        ("CNN: "+output["cnn"]["eye_state"] if output["cnn"].get("called") else "CNN: not called"),
        f"FINAL: {output['eye_state']}  valid={output['valid']}",
        "Method: "+output["method"],f"Closure elapsed: {fmt(output['closure_duration_sec'])} s",
        f"Closure events: {event_count}   Blink candidates: {blink_count}",
        "Status: "+str(output["invalid_reason"] or "observed"),"Scores are uncalibrated"]
    import textwrap
    y=25
    for line in lines:
        for wrapped in textwrap.wrap(line,48):
            cv2.putText(panel,wrapped,(10,y),cv2.FONT_HERSHEY_SIMPLEX,0.45,(25,25,25),1);y+=23
    for i,crop in enumerate(thumbnails):
        thumb=cv2.resize(crop,(160,90));x=10+i*185
        panel[370:460,x:x+160]=thumb
        cv2.putText(panel,"left" if i==0 else "right",(x,365),cv2.FONT_HERSHEY_SIMPLEX,0.45,(30,30,30),1)
    canvas=np.zeros((panel.shape[0],w+400,3),np.uint8);canvas[:h,:w]=display;canvas[:,w:]=panel
    return canvas


def main():
    from collections import Counter
    from .processor import SG2Processor
    from .metrics import latency_summary
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--video",type=Path,required=True)
    group=p.add_mutually_exclusive_group(required=True)
    group.add_argument("--sg1-jsonl",type=Path);group.add_argument("--sg1-source",type=Path)
    p.add_argument("--landmarker-model",type=Path)
    p.add_argument("--checkpoint",type=Path,default=Path(__file__).with_name("models")/"best.pt")
    p.add_argument("--timestamps",type=Path)
    p.add_argument("--sg4-notebook",type=Path)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--threshold",type=float,default=None,help="override the selected EAR threshold")
    p.add_argument("--mode",choices=("EAR","EAR_CNN"),default="EAR",help="EAR is the default; EAR_CNN enables the experimental ear_first mode")
    p.add_argument("--max-frames",type=int,default=0)
    args=p.parse_args()
    if args.sg1_source and not args.landmarker_model:p.error("--landmarker-model required")
    if args.max_frames<0:p.error("--max-frames must be nonnegative")
    # Do not truncate the input if a caller accidentally reuses its output directory.
    destinations=[(args.output/name).resolve() for name in ("sg1.jsonl","sg2.jsonl","sg4.jsonl")]
    if args.sg1_jsonl and args.sg1_jsonl.resolve() in destinations:raise ValueError("input/output paths overlap")
    args.output.mkdir(parents=True,exist_ok=True)
    cap=cv2.VideoCapture(str(args.video))
    if not cap.isOpened():raise ValueError("cannot open video")
    fps=cap.get(cv2.CAP_PROP_FPS);header_frames=int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if not fps>0:raise ValueError("known positive video FPS required")
    import torch
    torch.set_num_threads(2)
    from .processor import ROOT as PROCESSOR_ROOT
    frozen=json.loads((PROCESSOR_ROOT/"final_method.json").read_text(encoding="utf-8"))
    selected=dict(frozen["selected"])
    if args.mode=="EAR_CNN":
        selected.update(frozen.get("previous_selected",{}))
        selected.setdefault("method","ear_first")
        selected.setdefault("ear_uncertainty_band",.8)
        selected.setdefault("cnn_min_margin",0.)
        selected.setdefault("name","ear_first_experimental")
    processor=SG2Processor(args.checkpoint,method_config=selected,threshold=args.threshold)
    detector=load_sg1(args.sg1_source,args.landmarker_model) if args.sg1_source else None
    analyzer=load_sg4(args.sg4_notebook,fps) if args.sg4_notebook else None
    bridge=SG4Bridge(analyzer) if analyzer else None
    records=args.sg1_jsonl.open(encoding="utf-8") if args.sg1_jsonl else None
    timestamps={int(a):float(b) for a,b in (line.split() for line in args.timestamps.read_text().splitlines() if line.strip())} if args.timestamps else None
    handles=[path.open("w",encoding="utf-8") for path in destinations]
    writer=None;fid=0;events=[];counts={name:Counter() for name in ("EAR","CNN","FINAL")};timings=[];blink_count=0;cnn_calls=0;cnn_not_called=Counter()
    try:
        while not args.max_frames or fid<args.max_frames:
            ok,frame=cap.read()
            if not ok:break
            timestamp=timestamps[fid] if timestamps is not None else fid/fps
            if records:
                line=records.readline()
                if not line:raise ValueError("SG-1 stream ended before decoded video")
                record=json.loads(line)
            else:record=detector.process(frame,fid,round(timestamp*1000))
            output,boxes,timing=processor.process(record,frame,frame_id=fid,timestamp_sec=timestamp)
            event=output["closure_event"]
            if event:events.append(event)
            if output["cnn"].get("called",False):cnn_calls+=1
            else:cnn_not_called[output["cnn"].get("reason","unspecified")]+=1
            blink_count+=int(output["is_blink_candidate"])
            counts["EAR"][output["ear_eye_state"]]+=1;counts["CNN"][output["cnn"]["eye_state"]]+=1;counts["FINAL"][output["eye_state"]]+=1
            cue=to_sg4(output)
            if bridge:bridge.process_frame(cue,yawn_prob=0.,head_nod_event=False)
            for handle,obj in zip(handles,(record,output,cue)):handle.write(json.dumps(obj,allow_nan=False,sort_keys=True,separators=(",",":"))+"\n")
            visual=render(frame,record,output,boxes,len(events),blink_count)
            if writer is None:
                writer=cv2.VideoWriter(str(args.output/"overlay.mp4"),cv2.VideoWriter_fourcc(*"mp4v"),fps,(visual.shape[1],visual.shape[0]))
                if not writer.isOpened():raise RuntimeError("could not create overlay")
            writer.write(visual);timings.append(timing["processing_ms"]);fid+=1
            if fid%2000==0:print(fid,"demo frames",flush=True)
        if records and not args.max_frames and records.readline():raise ValueError("SG-1 stream longer than decoded video")
        tail=processor.flush()
        if tail:events.append(tail)
        if fid==0:raise ValueError("no decoded frames")
        summary=dict(frames=fid,container_frames=header_frames,unprocessed_container_tail=header_frames-fid,
            max_frames_limit=args.max_frames,clock="acquisition_timestamps" if timestamps is not None else "video_fps",fps=fps,
            cnn_inference_calls=cnn_calls,cnn_not_called_reasons=dict(cnn_not_called),
            cnn_skipped_confident_ear=cnn_not_called.get("outside_ear_uncertainty_band",0),
            method=processor.config,counts={k:dict(v) for k,v in counts.items()},closure_events=len(events),
            complete_closures=sum(e["complete"] for e in events),incomplete_closures=sum(not e["complete"] for e in events),blink_candidates=blink_count,
            sg4_vector=analyzer.get_temporal_vector() if analyzer else None,
            sg4_note="Eye-only demo; SG-3 cues explicitly disabled. Selected-state closure fraction is not validated P80.",
            overlay_clock="nominal video FPS; JSONL preserves actual acquisition timestamps")
        (args.output/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
        (args.output/"closures.json").write_text(json.dumps(events,indent=2)+"\n")
        (args.output/"timing.json").write_text(json.dumps(latency_summary(timings),indent=2)+"\n")
        print(json.dumps(summary,indent=2))
    finally:
        cap.release()
        if writer:writer.release()
        if detector:detector.close()
        if records:records.close()
        for handle in handles:handle.close()


if __name__=="__main__":main()
