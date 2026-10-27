import copy
import json
import math
from pathlib import Path
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
import cv2
import numpy as np
import torch
from module_2.eye_analysis import calculate_ear, classify_eye_state, LEFT_EYE
from module_2.adapters import process_sg1_eye_packet, to_sg4, SG4Bridge
from module_2.crops import extract_eye_crops
from module_2.events import ClosureTracker
from module_2.cnn import EyeCNN, CNNInference, preprocess
from module_2.metrics import binary_metrics
from module_2.demo import load_sg4
from module_2.train import load_manifest
from module_2.prepare_data import annotations, select_samples

FIXTURES=Path(__file__).parent/"fixtures"
(Path(__file__).resolve().parents[1]/"local").mkdir(exist_ok=True)


def fixture(name="sg1_to_sg2_v1_ok.json"):
    return json.loads((FIXTURES/name).read_text())


def frame(t,state="CLOSED",fid=None):
    return dict(timestamp_sec=t, frame_id=round(t*1000) if fid is None else fid,
                eye_state=state, valid=state!="UNKNOWN")


class EARTests(unittest.TestCase):
    def test_known_geometry_and_objects(self):
        # Pixel distances: 2 vertical / 10 horizontal -> EAR .2.
        points=[[0,0],[.025,-.02],[.075,-.02],[.1,0],[.075,.02],[.025,.02]]
        self.assertAlmostEqual(calculate_ear(points,range(6),100,50),0.2)
        objects=[SimpleNamespace(x=x,y=y) for x,y in points]
        self.assertAlmostEqual(calculate_ear(objects,range(6),100,50),0.2)

    def test_threshold_and_nonfinite(self):
        self.assertEqual(classify_eye_state(.15),"OPEN")
        self.assertEqual(classify_eye_state(.149),"CLOSED")
        for value in (None,float("nan"),float("inf"),-1):
            self.assertEqual(classify_eye_state(value),"UNKNOWN")
        with self.assertRaises(ValueError):classify_eye_state(.2,0)

    def test_actual_full_and_selected_packets(self):
        full=process_sg1_eye_packet(fixture("sg1_v1_ok.json"))
        selected=process_sg1_eye_packet(fixture())
        self.assertTrue(full["valid"])
        self.assertAlmostEqual(full["ear"],selected["ear"],places=12)
        self.assertEqual(full["frame_id"],0)
        self.assertEqual(full["timestamp_sec"],0)
        self.assertTrue(math.isfinite(full["left_ear"]))
        self.assertTrue(math.isfinite(full["right_ear"]))

    def test_invalid(self):
        for name in ("sg1_v1_no_face.json","sg1_to_sg2_v1_no_face.json"):
            out=process_sg1_eye_packet(fixture(name))
            self.assertFalse(out["valid"]);self.assertEqual(out["eye_state"],"UNKNOWN");self.assertIsNone(out["ear"])
        packet=fixture()
        for change in ({"image_width":0},{"image_height":None},{"eyes_valid":False},
                       {"left_eye_points_xy_normalized":[[0,0]]*6},
                       {"left_eye_points_xy_normalized":[[0,float("nan")]]*6},
                       {"left_eye_points_xy_normalized":[]},
                       {"left_eye_points_xy_normalized":[["0.2",0.4]]*6},
                       {"left_eye_points_xy_normalized":[[True,0.4]]*6},
                       {"left_eye_landmark_indices":list(reversed(LEFT_EYE))}):
            out=process_sg1_eye_packet(dict(packet,**change))
            self.assertFalse(out["valid"])
        for change in ({"frame_id":None},{"timestamp_sec":float("nan")}):
            with self.assertRaises(ValueError):process_sg1_eye_packet(dict(packet,**change))

    def test_full_invalid_and_legacy_main(self):
        packet=fixture("sg1_v1_ok.json")
        for change in ({"schema_version":"x"},{"landmark_topology":"x"},{"landmark_count":477},
                       {"face_bbox_xyxy":[0,0,99999,99999]}, {"landmarks_xy_normalized":None}):
            self.assertFalse(process_sg1_eye_packet(dict(packet,**change))["valid"])
        packet.pop("schema_version");packet.pop("landmark_topology")
        self.assertTrue(process_sg1_eye_packet(packet)["valid"])


class EventTests(unittest.TestCase):
    def test_closure_and_single_blink_candidate(self):
        tracker=ClosureTracker()
        self.assertIsNone(tracker.update(frame(0,"OPEN")))
        self.assertIsNone(tracker.update(frame(.04)))
        tracker.update(frame(.08));tracker.update(frame(.12))
        event=tracker.update(frame(.16,"OPEN"))
        self.assertAlmostEqual(event["duration_sec"],.12)
        self.assertTrue(event["complete"]);self.assertTrue(event["is_blink_candidate"])
        self.assertIsNone(tracker.update(frame(.20,"OPEN")))

    def test_unknown_gap_and_eof(self):
        for ending in ("UNKNOWN","GAP","EOF"):
            tracker=ClosureTracker();tracker.update(frame(0,"OPEN"));tracker.update(frame(.04));tracker.update(frame(.08))
            if ending=="EOF":event=tracker.flush()
            elif ending=="GAP":event=tracker.update(frame(.5))
            else:event=tracker.update(frame(.12,"UNKNOWN"))
            self.assertFalse(event["complete"]);self.assertFalse(event["is_blink_candidate"])
            self.assertAlmostEqual(event["end_sec"],.08)

    def test_left_censor_and_order(self):
        tracker=ClosureTracker();tracker.update(frame(0));tracker.update(frame(.04))
        event=tracker.update(frame(.12,"OPEN"))
        self.assertTrue(event["left_censored"]);self.assertFalse(event["complete"])
        with self.assertRaises(ValueError):tracker.update(frame(.12,"OPEN"))
        tracker=ClosureTracker();tracker.update(frame(0))
        with self.assertRaises(ValueError):tracker.update(frame(.04,fid=0))


class CropCNNTests(unittest.TestCase):
    def test_synchronized_crops(self):
        packet=fixture();image=np.zeros((240,230,3),dtype=np.uint8)
        crops,boxes=extract_eye_crops(image,packet,frame_id=0,timestamp_sec=0)
        self.assertEqual(len(crops),2);self.assertEqual(len(boxes),2)
        with self.assertRaises(ValueError):extract_eye_crops(image,packet,frame_id=1,timestamp_sec=0)
        with self.assertRaises(ValueError):extract_eye_crops(image,packet,frame_id=0,timestamp_sec=1)
        with self.assertRaises(ValueError):extract_eye_crops(image[:100],packet,frame_id=0,timestamp_sec=0)

    def test_model_shape_gradients_preprocessing(self):
        torch.set_num_threads(2)
        model=EyeCNN();x=torch.rand(4,1,32,32)
        logits=model(x);self.assertEqual(tuple(logits.shape),(4,2))
        loss=torch.nn.functional.cross_entropy(logits,torch.tensor([0,1,0,1]));loss.backward()
        self.assertTrue(all(p.grad is not None and torch.isfinite(p.grad).all() for p in model.parameters()))
        self.assertLess(sum(p.numel() for p in model.parameters()),10000)
        self.assertEqual(tuple(preprocess(np.zeros((20,40,3),np.uint8)).shape),(1,32,32))

    def test_reject_untrained_checkpoint(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parents[1]/"local") as d:
            p=Path(d)/"bad.pt";torch.save({"trained":False},p)
            with self.assertRaises(ValueError):CNNInference(p)

    def test_actual_checkpoint_if_available(self):
        p=Path(__file__).parents[1]/"models/best.pt"
        if not p.exists():self.skipTest("trained checkpoint not yet available")
        cnn=CNNInference(p)
        results,ms=cnn.predict([np.zeros((32,32),np.uint8)]*2)
        self.assertEqual(len(results),2);self.assertGreater(ms,0)
        self.assertTrue(all(0<=r["closed_softmax"]<=1 for r in results))


class IntegrationTests(unittest.TestCase):
    def test_actual_sg4_class(self):
        # Snapshot contains only the exact pinned SG-4 class; no notebook cells execute.
        path=FIXTURES/"sg4_temporal_analyzer_snapshot.ipynb"
        analyzer=load_sg4(path,25);bridge=SG4Bridge(analyzer)
        valid=process_sg1_eye_packet(fixture())
        cue=to_sg4(valid)
        self.assertIsNone(cue["face_confidence"]);self.assertIsNone(cue["eye_closure_prob"])
        # Demonstrate why the original public method cannot consume null confidence.
        with self.assertRaises(TypeError):analyzer.process_frame(cue)
        bridge.process_frame(cue,yawn_prob=0,head_nod_event=False)
        self.assertTrue(analyzer.buffer[-1]["is_valid"])
        self.assertEqual(analyzer.get_temporal_vector()["validity_score"],1)
        invalid=to_sg4(process_sg1_eye_packet(fixture("sg1_v1_no_face.json")))
        bridge.process_frame(invalid,yawn_prob=0,head_nod_event=False)
        self.assertFalse(analyzer.buffer[-1]["closed"])
        self.assertEqual(analyzer.get_temporal_vector()["validity_score"],.5)
        low=to_sg4(dict(valid,face_confidence=.1))
        bridge.process_frame(low,yawn_prob=0,head_nod_event=False)
        self.assertFalse(analyzer.buffer[-1]["is_valid"])

    def test_metrics(self):
        result=binary_metrics([0,0,1,1],[0,1,0,1])
        self.assertEqual(result["confusion_matrix"],[[1,1],[1,1]])
        self.assertEqual(result["f1"],.5)
        self.assertEqual(result["false_open"],1);self.assertEqual(result["false_closed"],1)
        result=binary_metrics([0,1],[None,1]);self.assertEqual(result["coverage"],.5)
        self.assertEqual(result["accuracy_with_abstentions_as_errors"],.5)


class DataTests(unittest.TestCase):
    def test_annotation_policy(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parents[1]/"local") as d:
            p=Path(d)/"samples.tag"
            base=":0:0:10:10:1:1:2:2:3:3:4:4"
            p.write_text("0:-1:X:X:X:X:X"+base+"\n1:1:X:C:X:C:X"+base+"\n2:1:X:X:X:X:X"+base+"\n3:2:X:C:N:C:X"+base)
            rows=annotations(p)
            self.assertEqual(rows,[(0,-1,"OPEN"),(1,1,"CLOSED")])
            self.assertEqual(select_samples(rows,477,80),[(0,"OPEN"),(1,"CLOSED")])

    def test_subject_and_duplicate_leakage(self):
        import csv
        with tempfile.TemporaryDirectory(dir=Path(__file__).parents[1]/"local") as d:
            root=Path(d);rows=[]
            for i,split in enumerate(("train","val","test")):
                for label in ("OPEN","CLOSED"):
                    value=i*50+(20 if label=="CLOSED" else 0)
                    file=root/f"{split}_{label}.png"
                    cv2.imwrite(str(file),np.full((8,8),value,np.uint8))
                    rows.append(dict(split=split,subject_id=split,video_id=split,frame_id=label,
                        label=label,label_source="dataset_annotation",left_crop=file.name,right_crop=file.name))
            path=root/"manifest.csv"
            def save():
                with path.open("w",newline="") as f:
                    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
            save();self.assertEqual(len(load_manifest(path)),6)
            rows[2]["subject_id"]="train";save()
            with self.assertRaisesRegex(ValueError,"subject/video leakage"):load_manifest(path)
            rows[2]["subject_id"]="val";rows[2]["left_crop"]=rows[0]["left_crop"];save()
            with self.assertRaisesRegex(ValueError,"duplicate image leakage"):load_manifest(path)
            rows[2]["left_crop"]=rows[2]["right_crop"];rows[0]["label_source"]="EAR";save()
            with self.assertRaisesRegex(ValueError,"independent"):load_manifest(path)


if __name__=="__main__":unittest.main()
