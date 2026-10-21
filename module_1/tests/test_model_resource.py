from pathlib import Path
import sys
import unittest


MODULE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_ROOT / "scripts"))

from download_model import MODEL_PATH, MODEL_SHA256, sha256_file, verify_model  # noqa: E402


class ModelResourceTests(unittest.TestCase):
    def test_downloaded_model_hash(self):
        if not MODEL_PATH.exists():
            self.skipTest("model is not downloaded")
        self.assertTrue(verify_model(MODEL_PATH))
        self.assertEqual(sha256_file(MODEL_PATH), MODEL_SHA256)


if __name__ == "__main__":
    unittest.main()
