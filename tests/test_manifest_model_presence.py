"""Ensure the manifest integrity gate cannot certify phantom model entries."""

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import validate_manifest  # noqa: E402


class ManifestModelPresenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "models").mkdir()
        schema = Path(__file__).resolve().parents[1] / "models" / "manifest.schema.json"
        for name, value in (
            ("REPO_ROOT", self.root),
            ("MANIFEST_PATH", self.root / "models" / "manifest.json"),
            ("SCHEMA_PATH", schema),
        ):
            patched = patch.object(validate_manifest, name, value)
            patched.start()
            self.addCleanup(patched.stop)
        tracked = patch.object(validate_manifest, "is_lfs_tracked", return_value=False)
        tracked.start()
        self.addCleanup(tracked.stop)

    def write_manifest(self, files):
        model = {
            "id": "phantom-model", "name": "Phantom Model", "task": "embedding",
            "path": "models/phantom-model", "format": "onnx", "runtime": "onnxruntime",
            "license": "test-only", "source": "test-fixture",
            "createdAt": "2026-10-18T00:00:00Z", "files": files,
        }
        manifest = {"version": 1, "updatedAt": "2026-10-18T00:00:00Z", "models": [model]}
        (self.root / "models" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    def test_missing_model_directory_is_rejected(self):
        self.write_manifest([])
        self.assertTrue(
            any("model directory does not exist" in error for error in validate_manifest.validate())
        )

    def test_empty_model_file_inventory_is_rejected(self):
        (self.root / "models" / "phantom-model").mkdir()
        self.write_manifest([])
        self.assertTrue(
            any("must declare at least one file" in error for error in validate_manifest.validate())
        )

    def test_existing_model_with_matching_artifact_is_valid(self):
        model_dir = self.root / "models" / "phantom-model"
        model_dir.mkdir()
        payload = b"synthetic model fixture\n"
        (model_dir / "weights.bin").write_bytes(payload)
        self.write_manifest([{
            "path": "weights.bin", "sizeBytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(), "lfsTracked": False,
        }])
        self.assertEqual(validate_manifest.validate(), [])


if __name__ == "__main__":
    unittest.main()
