import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from module_5.midterm.engine import DecisionEngine


ROOT = Path(__file__).resolve().parents[3]


class PublicInterfaceTests(unittest.TestCase):
    def test_machine_schema_accepts_ok_missing_and_stale_packets(self):
        import jsonschema
        schema = json.loads((ROOT / "interfaces/sg5_sg6_v2.schema.json").read_text())
        jsonschema.Draft202012Validator.check_schema(schema)
        engine = DecisionEngine()
        base = dict(time_s=0., face_valid=1, perclos=.1, eye_closure_s=0., long_blinks=0, yawn_count=0)
        outputs = [engine.step(base), engine.step(dict(base, time_s=.1, face_valid=0)), engine.tick(1.)]
        for output in outputs:
            jsonschema.validate(output, schema)
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(dict(outputs[0], unexpected=True), schema)

    def test_pipeline_import_does_not_need_vision_or_plotting_packages(self):
        command = [sys.executable, "-S", "-c", "import module_5.midterm.pipeline,sys; assert not any(x in sys.modules for x in ('numpy','cv2','mediapipe','matplotlib','torch'))"]
        run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)

    def test_replay_and_consumer_cli_execute_real_sg4_end_to_end(self):
        with tempfile.TemporaryDirectory(prefix="sg5-replay-") as output:
            run = subprocess.run([sys.executable, "-m", "module_5.midterm.demo", "--scenario", "drowsy", "--output", output], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            summary = json.loads((Path(output) / "summary.json").read_text())
            self.assertEqual(summary["sg4_vectors"], 900)
            self.assertGreater(summary["states"].get("DROWSY", 0), 0)
            consumer = subprocess.run([sys.executable, "embedded_6/sg5_handoff/consume.py", "--input", str(Path(output) / "sg6_stream.jsonl"), "--events-only"], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(consumer.returncode, 0, consumer.stderr)
            messages = [json.loads(line) for line in consumer.stdout.splitlines()]
            self.assertTrue(any(m["buzzer_requested"] for m in messages))


if __name__ == "__main__":
    unittest.main()
