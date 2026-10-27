"""Final deterministic SG-2 processor: synchronized SG-1 + raw frame -> SG-4 cue.

Runtime timings are returned separately, never mixed into canonical frame JSON.
Method selection is frozen in final_method.json; see SG4_HANDOFF.md.
"""
import hashlib
import json
from pathlib import Path
import time
from .adapters import process_sg1_eye_packet,finite,integer
from .crops import extract_eye_crops
from .fusion import decide,OpenHysteresis,should_infer_cnn
from .events import ClosureTracker

ROOT=Path(__file__).resolve().parent


class SG2Processor:
    def __init__(self,checkpoint=None,method_config=None,threshold=None,cnn=None):
        if method_config is None:
            frozen=json.loads((ROOT/"final_method.json").read_text())
            method_config=frozen["selected"]
            checkpoint=Path(checkpoint or ROOT/"models/best.pt")
            if hashlib.sha256(checkpoint.read_bytes()).hexdigest()!=frozen["checkpoint_sha256"]:
                raise ValueError("checkpoint differs from validated final method")
        self.config=dict(method_config)
        selected_threshold=self.config.get("ear_threshold",0.15)
        self.threshold=selected_threshold if threshold is None else threshold
        if not finite(self.threshold) or self.threshold<=0:
            raise ValueError("EAR threshold must be finite and positive")
        if cnn is None and self.config["method"]!="EAR":
            from .cnn import CNNInference
            cnn=CNNInference(checkpoint or ROOT/"models/best.pt")
        self.cnn=cnn
        self.smoother=OpenHysteresis(self.config["open_frames"],self.config["max_open_delay_sec"])
        self.tracker=ClosureTracker();self.last_frame=None;self.last_time=None;self.ended=False

    def process(self,record,frame,*,frame_id,timestamp_sec):
        if self.ended:raise ValueError("stream finished; create a new processor")
        begin=time.perf_counter();ear=process_sg1_eye_packet(record,self.threshold)
        if not integer(frame_id) or not finite(timestamp_sec) or timestamp_sec<0 or frame_id!=ear["frame_id"] or abs(timestamp_sec-ear["timestamp_sec"])>0.002:
            raise ValueError("source frame identity/time mismatch")
        t=ear["timestamp_sec"]
        if self.last_frame is not None and (frame_id<=self.last_frame or t<=self.last_time):
            raise ValueError("frame IDs and timestamps must strictly increase")
        cn=dict(eye_state="UNKNOWN",valid=False,eyes=[],reason="invalid_geometry",called=False)
        boxes=[];inference_ms=0
        if ear["valid"]:
            if should_infer_cnn(ear,self.config):
                crops,boxes=extract_eye_crops(frame,record,frame_id=frame_id,timestamp_sec=timestamp_sec)
                if crops:
                    cn["called"]=True
                    if self.cnn is None:
                        raise RuntimeError("CNN inference requested without an initialized CNN")
                    eyes,inference_ms=self.cnn.predict(crops)
                    states=[r["eye_state"] for r in eyes]
                    agrees=len(states)==2 and states[0]==states[1]
                    cn=dict(eye_state=states[0] if agrees else "UNKNOWN",valid=agrees,eyes=eyes,
                            reason=None if agrees else "eye_disagreement",called=True)
                else:cn["reason"]="invalid_crops"
            else:cn["reason"]="disabled_in_ear_only" if self.config["method"]=="EAR" else "outside_ear_uncertainty_band"
        raw,quality=decide(ear,cn,self.config)
        state=self.smoother.update(raw,t)
        output=dict(ear,schema_version="sg2.v2",image_width=record.get("image_width"),image_height=record.get("image_height"),
            ear_eye_state=ear["eye_state"],eye_state=state,valid=state!="UNKNOWN",cnn=cn,
            method=self.config["name"],raw_eye_state=raw,quality=quality,
            invalid_reason=ear["invalid_reason"] if not ear["valid"] else ("method_abstained" if state=="UNKNOWN" else None))
        output["closure_event"]=self.tracker.update(output)
        output["closure_duration_sec"]=t-self.tracker.active["start_sec"] if self.tracker.active else None
        output["is_blink_candidate"]=bool(output["closure_event"] and output["closure_event"]["is_blink_candidate"])
        self.last_frame,self.last_time=frame_id,t
        timing=dict(processing_ms=(time.perf_counter()-begin)*1000,cnn_ms=inference_ms)
        return output,boxes,timing

    def flush(self):
        self.ended=True
        return self.tracker.flush()
