"""Select fusion ONLY on validation, then report exploratory test results.

Definitions/protocol: selection_protocol.json; https://www.blinkingmatters.com/research
No probability calibration or safety certification is claimed.
"""
import argparse
from collections import Counter,defaultdict
import csv
import hashlib
import json
from pathlib import Path
import platform
import time
import numpy as np
from .fusion import candidates,decide,OpenHysteresis
from .events import ClosureTracker
from .metrics import binary_metrics,latency_summary

ROOT=Path(__file__).resolve().parent


def load_rows(folder, videos, expected_split):
    rows=[]
    for vid in videos:
        path=Path(folder)/(vid+".jsonl")
        audit=json.loads(path.with_suffix(".audit.json").read_text())
        if audit["split"]!=expected_split or hashlib.sha256(path.read_bytes()).hexdigest()!=audit["features_sha256"]:
            raise ValueError("sequence provenance/split mismatch")
        previous=-1
        for fid,line in enumerate(path.open()):
            r=json.loads(line)
            if r["split"]!=expected_split or r["video_id"]!=vid or r["frame_id"]!=fid or r["timestamp_sec"]<=previous:
                raise ValueError("sequence identity/order mismatch")
            previous=r["timestamp_sec"];rows.append(r)
        if fid+1!=audit["frames"]:raise ValueError("sequence length mismatch")
    return rows


def interval_metrics(truth,predicted,iou_threshold=0.2):
    pairs=[]
    for i,a in enumerate(truth):
        for j,b in enumerate(predicted):
            if a["video_id"]!=b["video_id"]:continue
            intersection=max(0,min(a["end_sec"],b["end_sec"])-max(a["start_sec"],b["start_sec"]))
            union=max(a["end_sec"],b["end_sec"])-min(a["start_sec"],b["start_sec"])
            iou=intersection/union if union>0 else 0
            if iou>=iou_threshold:pairs.append((iou,i,j))
    used_t=set();used_p=set();onsets=[];offsets=[];durations=[]
    for _,i,j in sorted(pairs,reverse=True):
        if i in used_t or j in used_p:continue
        used_t.add(i);used_p.add(j)
        onsets.append(predicted[j]["start_sec"]-truth[i]["start_sec"])
        offsets.append(predicted[j]["end_sec"]-truth[i]["end_sec"])
        durations.append(predicted[j]["duration_sec"]-truth[i]["duration_sec"])
    tp=len(used_t);fp=len(predicted)-tp;fn=len(truth)-tp
    div=lambda a,b:a/b if b else None
    timing=lambda x:dict(mean_signed_sec=float(np.mean(x)),mean_absolute_sec=float(np.mean(np.abs(x))),p95_absolute_sec=float(np.percentile(np.abs(x),95))) if x else None
    prolonged=[i for i,e in enumerate(truth) if e["duration_sec"]>=0.5]
    return dict(ground_truth=len(truth),predicted=len(predicted),matched=tp,false_events=fp,missed_events=fn,
        precision=div(tp,tp+fp),recall=div(tp,tp+fn),f1=div(2*tp,2*tp+fp+fn),iou_threshold=iou_threshold,
        onset_error=timing(onsets),offset_error=timing(offsets),duration_error=timing(durations),
        prolonged_ground_truth=len(prolonged),prolonged_matched=sum(i in used_t for i in prolonged),
        prolonged_recall=div(sum(i in used_t for i in prolonged),len(prolonged)))


def sequence_score(rows,config,protocol,save_predictions=False):
    truth=[];pred=[];unknown_closed=unknown_open=0
    actual_events=[];pred_events=[];states=[];times=[];flip_count=0;known_pairs=0;previous=None
    opening_delays=[];pending_open=None
    track=gt_track=smoother=None;last_video=None;incomplete=0
    for r in rows:
        video=r["video_id"];t=r["timestamp_sec"]
        if video!=last_video:
            if track:
                tail=track.flush();incomplete+=int(tail is not None)
            track=ClosureTracker();gt_track=ClosureTracker()
            smoother=OpenHysteresis(config["open_frames"],config["max_open_delay_sec"])
            previous=None;pending_open=None;last_video=video
        start=time.perf_counter();raw,_=decide(r["ear"],r["cnn"],config)
        state=smoother.update(raw,t);times.append((time.perf_counter()-start)*1000)
        states.append(state)
        if raw=="OPEN" and state=="CLOSED":
            if pending_open is None:pending_open=t
        elif raw=="OPEN" and pending_open is not None:
            opening_delays.append(t-pending_open);pending_open=None
        elif raw!="OPEN":pending_open=None
        y=r["label"]["truth"]
        value=1 if state=="CLOSED" else (0 if state=="OPEN" else None)
        if y is not None:
            truth.append(y);pred.append(value)
            unknown_closed+=int(y==1 and value is None);unknown_open+=int(y==0 and value is None)
        if previous and t-previous[0]<=0.2 and state!="UNKNOWN" and previous[1]!="UNKNOWN":
            known_pairs+=1;flip_count+=int(state!=previous[1])
        previous=(t,state)
        visible=r["label"]["visible"]
        gt_state=("CLOSED" if r["label"]["fully_closed"] else "OPEN") if visible else "UNKNOWN"
        sample=dict(frame_id=r["frame_id"],timestamp_sec=t)
        a=gt_track.update(dict(sample,eye_state=gt_state,valid=visible))
        b=track.update(dict(sample,eye_state=state if visible else "UNKNOWN",valid=visible and state!="UNKNOWN"))
        if a and a["complete"]:actual_events.append(dict(a,video_id=video))
        if b:
            if b["complete"]:pred_events.append(dict(b,video_id=video))
            else:incomplete+=1
    if track:incomplete+=int(track.flush() is not None)
    metrics=binary_metrics(truth,pred);n_closed=sum(truth);n_open=len(truth)-n_closed
    metrics.update(stream_frames=len(states),stream_unknown=states.count("UNKNOWN"),stream_coverage=1-states.count("UNKNOWN")/len(states),
        unknown_closed=unknown_closed,unknown_open=unknown_open,unknown_rate=1-metrics["coverage"],
        closed_misses_including_unknown=metrics["false_open"]+unknown_closed,
        closed_miss_rate=(metrics["false_open"]+unknown_closed)/n_closed,
        decision_cost=5*metrics["false_open"]/n_closed+2*unknown_closed/n_closed+metrics["false_closed"]/n_open+0.25*unknown_open/n_open)
    result=dict(config=config,classification=metrics,events=interval_metrics(actual_events,pred_events,protocol["event_iou_threshold"]),
        stability=dict(state_changes=flip_count,known_adjacent_pairs=known_pairs,change_fraction=flip_count/known_pairs if known_pairs else None,
                       incomplete_events=incomplete,opening_confirmation_delay=dict(count=len(opening_delays),mean_sec=float(np.mean(opening_delays)),max_sec=max(opening_delays),p95_sec=float(np.percentile(opening_delays,95))) if opening_delays else None,maximum_configured_open_delay_sec=config["max_open_delay_sec"] if config["open_frames"]>1 else 0),
        decision_latency=latency_summary(times))
    return (result,states) if save_predictions else result


def rank(result):
    m=result["classification"];c=result["config"]
    complexity={"EAR":0,"CNN":1,"agreement":2,"fallback":2,"confidence":3,"ear_first":3,"weighted":4,"reliability":5}
    return (m["decision_cost"],result["events"]["false_events"],-m["coverage"],c["open_frames"],complexity[c["method"]],c["name"])


def select(rows,protocol):
    if any(r["split"]!="val" for r in rows):raise ValueError("selection accepts validation only")
    results=[sequence_score(rows,c,protocol) for c in candidates(protocol)]
    baseline=next(r for r in results if r["config"]["method"]=="EAR" and r["config"]["open_frames"]==1)
    rule=protocol["rule"];eligible=[]
    for result in results:
        m=result["classification"]
        recall=result["events"]["recall"];base_recall=baseline["events"]["recall"]
        result["eligible"]=bool(m["coverage"]>=rule["minimum_coverage"] and
            m["closed_miss_rate"]<=baseline["classification"]["closed_miss_rate"]+rule["closed_miss_rate_tolerance_over_EAR"] and
            (base_recall is None or (recall is not None and recall>=base_recall-rule["event_recall_tolerance_over_EAR"])))
        if result["eligible"]:eligible.append(result)
    best=min(eligible,key=rank) if eligible else baseline
    return best,results


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--features",type=Path,default=ROOT/"local/sequences")
    p.add_argument("--select-only",action="store_true")
    args=p.parse_args();protocol=json.loads((ROOT/"selection_protocol.json").read_text())
    val=load_rows(args.features,protocol["selection_videos"],"val")
    best,grid=select(val,protocol)
    operational_spec=protocol["fusion_grids"].get("operational_method")
    operational_config=next((c for c in candidates(protocol)
        if operational_spec and all(operational_spec.get(k)==v for k,v in c.items())),None)
    operational=next((r for r in grid if r["config"]==operational_config),None)
    if operational is None:raise ValueError("operational method must exactly match a validation-scored candidate")
    frozen=dict(schema_version="sg2.method.v1",selected=operational["config"],selection_rule=protocol["rule"],
        original_validation_protocol_winner=best["config"],
        operational_selection_status=operational_spec["decision_status"],
        operational_validation_metrics=operational,
        selection_videos=protocol["selection_videos"],evaluation_status=protocol["evaluation_status"],
        protocol_sha256=hashlib.sha256((ROOT/"selection_protocol.json").read_bytes()).hexdigest(),
        checkpoint_sha256=hashlib.sha256((ROOT/"models/best.pt").read_bytes()).hexdigest())
    (ROOT/"final_method.json").write_text(json.dumps(frozen,indent=2)+"\n")
    (ROOT/"results/validation_selection.json").write_text(json.dumps(dict(selected=best,operational=operational,grid=grid),indent=2)+"\n")
    print("ORIGINAL VALIDATION PROTOCOL WINNER",json.dumps(best),flush=True)
    print("USER-DIRECTED OPERATIONAL METHOD",json.dumps(operational),flush=True)
    if args.select_only:return
    # Test features are first opened only after config has been selected and written.
    test=load_rows(args.features,protocol["evaluation_videos"],"test")
    representatives=[]
    for method in ("EAR","CNN","agreement","fallback","confidence","weighted","reliability","ear_first"):
        pool=[r for r in grid if r["config"]["method"]==method and r["config"]["open_frames"]==1]
        representatives.append(min(pool,key=rank)["config"])
    smoothed=min((r for r in grid if r["config"]["open_frames"]>1),key=rank)["config"]
    representatives.append(smoothed)
    configs={c["name"]:c for c in representatives+[operational["config"],best["config"]]}
    scored={};states_by_name={}
    for name,c in configs.items():
        scored[name],states_by_name[name]=sequence_score(test,c,protocol,True)
    selected_name=operational["config"]["name"]
    report=dict(status=protocol["evaluation_status"],selected_name=selected_name,selected=scored[selected_name],
        methods=scored,validation_selected=best,operational_validation=operational,
        original_validation_protocol_winner=best["config"],
        operational_selection_status=operational_spec["decision_status"],
        classification_label_policy="visible non-blink OPEN or both eyes fully CLOSED; transitions excluded",
        event_policy="complete bilateral fully-CLOSED intervals on annotated visible spans; one-to-one greedy IoU>=0.2; candidate blink duration is not independent ground truth",
        validation_frames=len(val),test_frames=len(test),test_videos=protocol["evaluation_videos"],
        cpu=dict(platform=platform.platform(),processor=platform.processor()),
        observed_full_sg2_latency=latency_summary([r["sg2_ms"] for r in test]),
        observed_sg1_latency=latency_summary([r["sg1_ms"] for r in test]),
        checkpoint_sha256=frozen["checkpoint_sha256"],protocol_sha256=frozen["protocol_sha256"],
        sequence_audits=[json.loads((args.features/(vid+".audit.json")).read_text()) for vid in protocol["selection_videos"]+protocol["evaluation_videos"]])
    (ROOT/"results/final_comparison.json").write_text(json.dumps(report,indent=2)+"\n")
    with (ROOT/"results/final_predictions.csv").open("w",newline="") as f:
        fields=["video_id","frame_id","timestamp_sec","truth"]+list(configs)
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for i,r in enumerate(test):writer.writerow(dict(video_id=r["video_id"],frame_id=r["frame_id"],timestamp_sec=r["timestamp_sec"],
            truth="UNKNOWN" if r["label"]["truth"] is None else ("CLOSED" if r["label"]["truth"] else "OPEN"),
            **{name:states[i] for name,states in states_by_name.items()}))
    for result in scored.values():print(json.dumps(result),flush=True)


if __name__=="__main__":main()
