"""Final-method tests; synthetic scores are used ONLY as unit-test inputs."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np
from module_2.adapters import process_sg1_eye_packet,to_sg4,validate_sg4_cue
from module_2.fusion import decide,OpenHysteresis,candidates,should_infer_cnn
from module_2.processor import SG2Processor
from module_2.leakage import NearDuplicateGuard
from module_2.evaluate import select,interval_metrics

ROOT=Path(__file__).resolve().parents[1]


def ear(value=.2):
    return dict(ear=value,left_ear=value,right_ear=value,ear_threshold=.15,valid=True,eye_state="CLOSED" if value<.15 else "OPEN")


def cnn(a,b=None):
    return dict(eyes=[dict(closed_softmax=p,eye_state="CLOSED" if p>=.5 else "OPEN",calibrated=False) for p in (a,a if b is None else b)])


def config(method="EAR",**kwargs):
    return dict(method=method,open_frames=1,max_open_delay_sec=.08,name="test_"+method,**kwargs)


class FusionTests(unittest.TestCase):
    def test_baselines_and_agreement(self):
        state,quality=decide(ear(),cnn(.9),config())
        self.assertEqual(state,"OPEN")
        self.assertFalse(quality["cnn_used"])
        self.assertEqual(decide(ear(),cnn(.9),config("CNN"))[0],"CLOSED")
        self.assertEqual(decide(ear(),cnn(.9),config("agreement"))[0],"UNKNOWN")
        self.assertEqual(decide(ear(.1),cnn(.9),config("agreement"))[0],"CLOSED")

    def test_fallback_confidence_and_reliability(self):
        self.assertEqual(decide(ear(),cnn(.9,.1),config("fallback"))[0],"OPEN")
        self.assertEqual(decide(ear(),cnn(.9),config("fallback"))[0],"CLOSED")
        self.assertEqual(decide(ear(),cnn(.6),config("confidence",margin=.5))[0],"OPEN")
        self.assertEqual(decide(ear(),cnn(.9),config("confidence",margin=.5))[0],"CLOSED")
        asymmetric=dict(ear(),left_ear=.05,right_ear=.35)
        self.assertEqual(decide(asymmetric,cnn(.6),config("reliability",margin=.5,max_imbalance=.3))[0],"UNKNOWN")
        self.assertEqual(decide(asymmetric,cnn(.9),config("reliability",margin=.5,max_imbalance=.3))[0],"CLOSED")

    def test_weighted_score_is_explicit_not_probability(self):
        state,d=decide(ear(.1),cnn(.9),config("weighted",ear_weight=.5,threshold=0))
        self.assertEqual(state,"CLOSED");self.assertAlmostEqual(d["fusion_signed_score"],(.05/.15+.8)/2)
        self.assertNotIn("probability",d)
        self.assertEqual(decide(ear(.1),{},config("weighted",ear_weight=.5,threshold=0))[0],"CLOSED")

    def test_ear_first_uses_cnn_only_inside_band_when_bilateral_margin_passes(self):
        cfg=config("ear_first",ear_uncertainty_band=.5,cnn_min_margin=.2)
        state,d=decide(ear(.149),cnn(.9),cfg)
        self.assertEqual(state,"CLOSED");self.assertTrue(d["ear_first_uncertain"]);self.assertTrue(d["cnn_used"])
        state,d=decide(ear(.3),cnn(.9),cfg)
        self.assertEqual(state,"OPEN");self.assertFalse(d["ear_first_uncertain"]);self.assertFalse(d["cnn_used"])
        state,d=decide(ear(.149),cnn(.9,.1),cfg)
        self.assertEqual(state,"CLOSED");self.assertFalse(d["cnn_used"])
        state,d=decide(ear(.149),cnn(.55),cfg)
        self.assertEqual(state,"CLOSED");self.assertFalse(d["cnn_used"])

    def test_no_method_converts_invalid_geometry_to_closed(self):
        protocol=json.loads((ROOT/"selection_protocol.json").read_text())
        for c in candidates(protocol):
            self.assertEqual(decide(dict(ear(),valid=False),cnn(.99),c)[0],"UNKNOWN")

    def test_ear_first_candidates_are_in_validation_grid(self):
        protocol=json.loads((ROOT/"selection_protocol.json").read_text())
        rows=[c for c in candidates(protocol) if c["method"]=="ear_first"]
        self.assertEqual(len(rows),8*4*3)
        self.assertEqual(len({c["name"] for c in rows}),len(rows))

    def test_ear_first_cnn_execution_gate(self):
        cfg=config("ear_first",ear_uncertainty_band=.8,cnn_min_margin=0.)
        self.assertFalse(should_infer_cnn(ear(.01),cfg))
        self.assertTrue(should_infer_cnn(ear(.15),cfg))
        self.assertTrue(should_infer_cnn(ear(.269),cfg))
        self.assertFalse(should_infer_cnn(dict(ear(),valid=False),cfg))

    def test_bad_scores_are_unavailable(self):
        for a in (float("nan"),float("inf"),-.1,1.1,True):
            state,d=decide(ear(),cnn(a),config("CNN"))
            self.assertEqual(state,"UNKNOWN");self.assertFalse(d["cnn_available"])

    def test_smoothing_never_delays_closed_and_resets_unknown(self):
        h=OpenHysteresis(3)
        self.assertEqual(h.update("OPEN",0),"OPEN")
        self.assertEqual(h.update("CLOSED",.03),"CLOSED")
        self.assertEqual(h.update("OPEN",.06),"CLOSED")
        self.assertEqual(h.update("OPEN",.09),"CLOSED")
        self.assertEqual(h.update("OPEN",.12),"OPEN")
        self.assertEqual(h.update("CLOSED",.15),"CLOSED")
        self.assertEqual(h.update("UNKNOWN",.18),"UNKNOWN")
        self.assertEqual(h.update("OPEN",.21),"OPEN")
        self.assertEqual(h.update("CLOSED",.24),"CLOSED")
        self.assertEqual(h.update("OPEN",1),"OPEN")
        with self.assertRaises(ValueError):h.update("OPEN",1)

    def test_selection_rejects_test_rows(self):
        protocol=json.loads((ROOT/"selection_protocol.json").read_text())
        with self.assertRaisesRegex(ValueError,"validation only"):select([dict(split="test")],protocol)

    def test_one_to_one_event_matching(self):
        event=dict(video_id="8",start_sec=1.,end_sec=2.,duration_sec=1.)
        result=interval_metrics([event],[event,event])
        self.assertEqual(result["matched"],1);self.assertEqual(result["false_events"],1)
        self.assertEqual(result["prolonged_recall"],1.)
        self.assertEqual(result["onset_error"]["mean_absolute_sec"],0.)
        result=interval_metrics([event],[dict(event,video_id="9")])
        self.assertEqual(result["matched"],0)


class StaticCNN:
    def __init__(self,score=.9):self.score=score;self.calls=0
    def predict(self,crops):self.calls+=1;return cnn(self.score)["eyes"],.01


class ProcessorTests(unittest.TestCase):
    def setUp(self):
        self.packet=json.loads((ROOT/"tests/fixtures/sg1_to_sg2_v1_ok.json").read_text())
        self.image=np.zeros((240,230,3),np.uint8)

    def test_full_selected_legacy_equivalence_and_determinism(self):
        full=json.loads((ROOT/"tests/fixtures/sg1_v1_ok.json").read_text())
        legacy=copy.deepcopy(full);legacy.pop("schema_version");legacy.pop("landmark_topology")
        outputs=[]
        for packet in (self.packet,full,legacy,self.packet):
            p=SG2Processor(method_config=config(),cnn=StaticCNN())
            output,_,_=p.process(packet,self.image,frame_id=0,timestamp_sec=0)
            outputs.append(json.dumps(output,sort_keys=True,allow_nan=False))
            self.assertEqual(output["eye_state"],"OPEN")
            self.assertEqual(output["cnn"]["eye_state"],"UNKNOWN")
            self.assertFalse(output["cnn"]["called"])
        self.assertTrue(all(o==outputs[0] for o in outputs))

    def test_events_handoff_and_eof(self):
        mock=StaticCNN(.1);p=SG2Processor(method_config=config("CNN"),cnn=mock)
        for fid,t,score in ((0,0,.1),(1,.04,.9),(2,.08,.9),(3,.12,.9),(4,.16,.1)):
            mock.score=score;packet=dict(self.packet,frame_id=fid,timestamp_sec=t)
            output,_,_=p.process(packet,self.image,frame_id=fid,timestamp_sec=t)
        self.assertTrue(output["closure_event"]["complete"])
        self.assertTrue(output["is_blink_candidate"])
        cue=to_sg4(output);self.assertEqual(cue["schema_version"],"sg2.sg4.v2")
        self.assertEqual(cue["eye_state"],"OPEN");self.assertTrue(cue["is_blink"])
        self.assertIsNone(cue["eye_closure_prob"]);self.assertIsNone(cue["face_confidence"])
        self.assertIsNone(p.flush())
        with self.assertRaises(ValueError):p.process(packet,self.image,frame_id=4,timestamp_sec=.16)

    def test_invalid_and_gap_do_not_bridge_events(self):
        p=SG2Processor(method_config=config("CNN"),cnn=StaticCNN())
        for fid,t in ((0,0),(1,.04)):
            p.process(dict(self.packet,frame_id=fid,timestamp_sec=t),self.image,frame_id=fid,timestamp_sec=t)
        output,_,_=p.process(dict(self.packet,frame_id=2,timestamp_sec=.08,eyes_valid=False),self.image,frame_id=2,timestamp_sec=.08)
        self.assertEqual(output["eye_state"],"UNKNOWN");self.assertFalse(output["valid"])
        self.assertFalse(output["closure_event"]["complete"])
        self.assertIsNone(output["closure_duration_sec"])
        output,_,_=p.process(dict(self.packet,frame_id=3,timestamp_sec=1),self.image,frame_id=3,timestamp_sec=1)
        self.assertEqual(output["closure_duration_sec"],0)
        self.assertFalse(p.flush()["complete"])

    def test_identity_mismatch_rejected(self):
        p=SG2Processor(method_config=config(),cnn=StaticCNN())
        with self.assertRaises(ValueError):p.process(self.packet,self.image,frame_id=1,timestamp_sec=0)
        with self.assertRaises(ValueError):p.process(self.packet,self.image,frame_id=0,timestamp_sec=.1)

    def test_processor_calls_cnn_only_inside_ear_first_band(self):
        mock=StaticCNN(.9);cfg=config("ear_first",ear_uncertainty_band=.8,cnn_min_margin=0.)
        p=SG2Processor(method_config=cfg,cnn=mock)
        packet=copy.deepcopy(self.packet)
        # Move the six points' horizontal endpoints apart to create clear OPEN EAR.
        packet["left_eye_points_xy_normalized"]=[[.1,.4],[.12,.35],[.14,.35],[.3,.4],[.14,.45],[.12,.45]]
        packet["right_eye_points_xy_normalized"]=[[.5,.4],[.52,.35],[.54,.35],[.7,.4],[.54,.45],[.52,.45]]
        output,boxes,_=p.process(packet,self.image,frame_id=0,timestamp_sec=0)
        self.assertEqual(mock.calls,0);self.assertFalse(output["cnn"]["called"]);self.assertEqual(boxes,[])
        self.assertFalse(output["quality"]["cnn_used"])
        uncertain=copy.deepcopy(self.packet)
        uncertain["left_eye_points_xy_normalized"]=[[.1,.4],[.12,.385],[.14,.39],[.3,.4],[.14,.41],[.12,.415]]
        uncertain["right_eye_points_xy_normalized"]=[[.5,.4],[.52,.385],[.54,.39],[.7,.4],[.54,.41],[.52,.415]]
        mock2=StaticCNN(.9);p2=SG2Processor(method_config=cfg,cnn=mock2)
        out,_,_=p2.process(uncertain,self.image,frame_id=0,timestamp_sec=0)
        self.assertEqual(mock2.calls,1);self.assertTrue(out["cnn"]["called"]);self.assertTrue(out["quality"]["cnn_used"])

    def test_selected_ear_method_does_not_initialize_or_infer_cnn(self):
        full=json.loads((ROOT/"tests/fixtures/sg1_v1_ok.json").read_text())
        # Valid geometry with EAR clearly OPEN, paired with a mock CNN that says CLOSED.
        points=full["landmarks_xy_normalized"]
        for indices,coords in (([33,160,158,133,153,144],[(.10,.40),(.12,.35),(.14,.35),(.30,.40),(.14,.45),(.12,.45)]),
                               ([362,385,387,263,373,380],[(.50,.40),(.52,.35),(.54,.35),(.70,.40),(.54,.45),(.52,.45)])):
            for idx,xy in zip(indices,coords):points[idx]=list(xy)
        cfg=dict(method="EAR",ear_threshold=.15,open_frames=1,
            max_open_delay_sec=.08,name="EAR_0.15_open2")
        with patch("module_2.cnn.CNNInference", side_effect=AssertionError("EAR-only must not initialize CNN")):
            p=SG2Processor(method_config=cfg)
            output,boxes,_=p.process(full,self.image,frame_id=0,timestamp_sec=0)
        self.assertEqual(boxes,[])
        self.assertEqual(output["ear_eye_state"],"OPEN")
        self.assertEqual(output["cnn"]["eye_state"],"UNKNOWN")
        self.assertEqual(output["cnn"]["reason"],"disabled_in_ear_only")
        self.assertFalse(output["cnn"]["called"])
        self.assertEqual(output["eye_state"],"OPEN")
        self.assertFalse(output["quality"]["cnn_used"])
        mock=StaticCNN(.99)
        p=SG2Processor(method_config=cfg,cnn=mock)
        output,boxes,_=p.process(full,self.image,frame_id=0,timestamp_sec=0)
        self.assertEqual(mock.calls,0)
        self.assertEqual(boxes,[])
        self.assertFalse(output["cnn"]["called"])

    def test_selected_threshold_is_configurable_and_explicit_override_wins(self):
        mock=StaticCNN()
        cfg=dict(method="EAR",ear_threshold=.19,open_frames=1,max_open_delay_sec=.08,name="x")
        p=SG2Processor(method_config=cfg,cnn=mock)
        self.assertEqual(p.threshold,.19)
        p=SG2Processor(method_config=cfg,threshold=.21,cnn=mock)
        self.assertEqual(p.threshold,.21)

    def test_handoff_rejects_fabricated_or_inconsistent_values(self):
        p=SG2Processor(method_config=config(),cnn=StaticCNN())
        out,_,_=p.process(self.packet,self.image,frame_id=0,timestamp_sec=0)
        cue=to_sg4(out)
        for changes in ({"eye_closure_prob":.9},{"eye_state":"UNKNOWN"},{"is_blink":True},{"face_confidence":float("nan")}):
            with self.assertRaises(ValueError):validate_sg4_cue(dict(cue,**changes))

    def test_near_duplicate_guard(self):
        rng=np.random.default_rng(477);image=rng.integers(20,220,(64,64,3),dtype=np.uint8)
        guard=NearDuplicateGuard();guard.add(image,"train","a")
        guard.add(image,"train","same split allowed")
        with self.assertRaisesRegex(ValueError,"near duplicate"):guard.add(image+1,"test","copy with brightness change")


if __name__=="__main__":unittest.main()
