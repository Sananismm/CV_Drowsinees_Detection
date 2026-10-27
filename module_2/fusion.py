"""Small explicitly defined decision rules, not calibrated probabilities.

Validation protocol: selection_protocol.json. Score calibration background:
https://arxiv.org/abs/1706.04599
All thresholds/weights below are engineering candidates tested on validation.
"""
import math
from .adapters import finite

STATES=("OPEN","CLOSED","UNKNOWN")


def should_infer_cnn(ear, config):
    """Return whether the selected method needs CNN inference for this frame."""
    # EAR is the operational state method and must not initialize or invoke CNN.
    if config["method"]=="EAR":return False
    if config["method"]!="ear_first":return bool(ear.get("valid"))
    if ear.get("valid") is not True or ear.get("eye_state") not in STATES[:2]:return False
    value,threshold=ear.get("ear"),ear.get("ear_threshold")
    if not finite(value) or not finite(threshold) or threshold<=0:return False
    signed=max(-1.,min(1.,(threshold-value)/threshold))
    return abs(signed)<=config["ear_uncertainty_band"]


def diagnostics(ear, cnn):
    valid=ear.get("valid") is True and ear.get("eye_state") in STATES[:2]
    value=ear.get("ear")
    valid=valid and finite(value) and value >= 0
    eyes=cnn.get("eyes",[])
    scores=[e.get("closed_softmax") for e in eyes]
    available=len(scores)==2 and all(finite(p) and 0<=p<=1 for p in scores)
    agrees=available and ((scores[0]>=0.5)==(scores[1]>=0.5))
    cnn_state=("CLOSED" if scores[0]>=0.5 else "OPEN") if agrees else "UNKNOWN"
    imbalance=None
    if valid and finite(ear.get("left_ear")) and finite(ear.get("right_ear")):
        imbalance=abs(ear["left_ear"]-ear["right_ear"])/max(value,1e-8)
    return dict(geometry_valid=valid,cnn_available=available,cnn_agreement=bool(agrees),cnn_used=False,
        cnn_called=bool(cnn.get("called",available)),
        cnn_state=cnn_state,cnn_margin=min(abs(2*p-1) for p in scores) if available else None,
        cnn_signed_score=sum(2*p-1 for p in scores)/2 if available else None,
        ear_signed_score=max(-1.,min(1.,(ear["ear_threshold"]-value)/ear["ear_threshold"])) if valid else None,
        ear_imbalance=imbalance)


def decide(ear, cnn, config):
    d=diagnostics(ear,cnn);method=config["method"]
    if not d["geometry_valid"]:return "UNKNOWN",d
    e,c=ear["eye_state"],d["cnn_state"]
    if method=="EAR":
        state=e
        d["cnn_used"]=False
    elif method=="CNN":state=c
    elif method=="agreement":state=e if e==c else "UNKNOWN"
    elif method=="fallback":state=c if c!="UNKNOWN" else e
    elif method in ("confidence","reliability"):
        reliable=d["cnn_agreement"] and d["cnn_margin"]>=config["margin"]
        state=c if reliable else e
        if method=="reliability" and (d["ear_imbalance"] is None or d["ear_imbalance"]>config["max_imbalance"]):
            state=c if reliable else "UNKNOWN"
    elif method=="weighted":
        if not d["cnn_available"]:state=e
        else:
            weight=config["ear_weight"]
            score=weight*d["ear_signed_score"]+(1-weight)*d["cnn_signed_score"]
            d["fusion_signed_score"]=score
            state="CLOSED" if score>config["threshold"] else "OPEN"
    elif method=="ear_first":
        # EAR remains authoritative outside its validation-selected gray band.
        # Inside the band, use CNN only when both eye crops agree and their
        # explicitly defined softmax margins pass the selected minimum.
        # Otherwise retain the valid EAR decision; no confidence is fabricated.
        band=config["ear_uncertainty_band"]
        d["ear_first_uncertain"]=abs(d["ear_signed_score"])<=band
        d["cnn_used"]=False
        if d["ear_first_uncertain"]:
            reliable=d["cnn_agreement"] and d["cnn_margin"]>=config["cnn_min_margin"]
            if reliable:
                state=c
                d["cnn_used"]=True
            else:
                state=e
        else:
            state=e
    else:raise ValueError("unknown fusion method: "+method)
    return state,d


class OpenHysteresis:
    """Immediate CLOSED; confirm OPEN with bounded delay. UNKNOWN/gaps reset.

    The confirmation limit is checked at observed frames; no state is
    extrapolated between timestamps. CLOSED is never delayed.
    This is an engineering candidate, validated against observed sequences.
    """
    def __init__(self, frames=1, max_delay_sec=0.08, max_gap_sec=0.2):
        if not isinstance(frames,int) or isinstance(frames,bool) or frames<1 or not finite(max_delay_sec) or max_delay_sec<0 or not finite(max_gap_sec) or max_gap_sec<=0:
            raise ValueError("invalid hysteresis configuration")
        self.frames,self.max_delay,self.max_gap=frames,max_delay_sec,max_gap_sec
        self.previous=None;self.state="UNKNOWN";self.open_count=0;self.open_start=None

    def update(self,state,timestamp):
        if state not in STATES or not finite(timestamp) or timestamp<0:raise ValueError("bad state/time")
        if self.previous is not None and timestamp<=self.previous:raise ValueError("timestamps must increase")
        if self.previous is not None and timestamp-self.previous>self.max_gap:
            self.state="UNKNOWN";self.open_count=0;self.open_start=None
        self.previous=timestamp
        if state in ("UNKNOWN","CLOSED"):
            self.state=state;self.open_count=0;self.open_start=None
        elif self.state!="CLOSED" or self.frames==1:
            self.state="OPEN";self.open_count=0;self.open_start=None
        else:
            self.open_count+=1
            if self.open_start is None:self.open_start=timestamp
            if self.open_count>=self.frames or timestamp-self.open_start>=self.max_delay:
                self.state="OPEN";self.open_count=0;self.open_start=None
        return self.state


def candidates(protocol):
    grid=protocol["fusion_grids"]
    base=[dict(method=m) for m in ("EAR","CNN","agreement","fallback")]
    base += [dict(method="confidence",margin=m) for m in grid["confidence_margin"]]
    base += [dict(method="weighted",ear_weight=w,threshold=t) for w in grid["EAR_weight"] for t in grid["decision_threshold"]]
    base += [dict(method="reliability",margin=m,max_imbalance=i) for m in grid["confidence_margin"] for i in grid["maximum_EAR_imbalance"]]
    base += [dict(method="ear_first",ear_uncertainty_band=b,cnn_min_margin=m)
             for b in grid["EAR_first_uncertainty_band"] for m in grid["EAR_first_CNN_minimum_margin"]]
    result=[]
    for config in base:
        for frames in grid["open_confirmation_frames"]:
            c=dict(config,open_frames=frames,max_open_delay_sec=grid["maximum_open_delay_sec"])
            c["name"]="_".join(str(c[k]) for k in sorted(c))
            result.append(c)
    return result
