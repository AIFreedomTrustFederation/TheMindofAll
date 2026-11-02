"""Regression tests for model/manifest rollback on publication failure."""

import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import import_model  # noqa: E402


class ImportManifestRollbackTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.models = self.root / "models"
        self.models.mkdir()
        self.manifest_path = self.models / "manifest.json"
        for name, value in (("MODELS_DIR", self.models), ("MANIFEST_PATH", self.manifest_path)):
            mock = patch.object(import_model, name, value)
            mock.start()
            self.addCleanup(mock.stop)
        self.source = self.root / "source"
        self.source.mkdir()
        (self.source / "weights.bin").write_bytes(b"new weights")

    def old_model(self):
        destination = self.models / "demo"
        destination.mkdir()
        (destination / "weights.bin").write_bytes(b"valuable weights")
        self.manifest_path.write_text(
            json.dumps({"version": 1, "models": [{"id": "demo", "files": []}]}),
            encoding="utf-8",
        )
        return destination

    def run_import(self, replace=False):
        output = io.StringIO()
        args = [str(self.source), "--id", "demo"] + (["--replace"] if replace else [])
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(output):
            result = import_model.main(args)
        return result, output.getvalue()

    def test_failed_manifest_replace_restores_previous_model_and_manifest(self):
        destination = self.old_model()
        original = self.manifest_path.read_bytes()
        with patch.object(import_model, "write_manifest", side_effect=OSError("disk full")):
            result, error = self.run_import(replace=True)
        self.assertEqual(result, 1)
        self.assertIn("disk full", error)
        self.assertEqual((destination / "weights.bin").read_bytes(), b"valuable weights")
        self.assertEqual(self.manifest_path.read_bytes(), original)
        self.assertEqual(sorted(p.name for p in self.models.iterdir()), ["demo", "manifest.json"])

    def test_failed_manifest_on_first_import_removes_uncommitted_model(self):
        original = b'{"version": 1, "models": []}\n'
        self.manifest_path.write_bytes(original)
        with patch.object(import_model, "write_manifest", side_effect=OSError("disk full")):
            result, error = self.run_import()
        self.assertEqual(result, 1)
        self.assertIn("disk full", error)
        self.assertFalse((self.models / "demo").exists())
        self.assertEqual(self.manifest_path.read_bytes(), original)
        self.assertEqual(sorted(p.name for p in self.models.iterdir()), ["manifest.json"])

    def test_successful_replace_updates_model_and_matching_manifest(self):
        destination = self.old_model()
        result, error = self.run_import(replace=True)
        self.assertEqual(result, 0, error)
        self.assertEqual((destination / "weights.bin").read_bytes(), b"new weights")
        record = json.loads(self.manifest_path.read_text(encoding="utf-8"))["models"][0]
        self.assertEqual(record["id"], "demo")
        self.assertEqual(record["files"][0]["sha256"], hashlib.sha256(b"new weights").hexdigest())
        self.assertEqual(sorted(p.name for p in self.models.iterdir()), ["demo", "manifest.json"])

    def test_failed_restore_preserves_old_model_for_manual_recovery(self):
        destination = self.old_model()
        original_rename = Path.rename

        def fail_restore(path, target):
            if path.name == "previous" and Path(target) == destination:
                raise OSError("simulated restore failure")
            return original_rename(path, target)

        with patch.object(import_model, "write_manifest", side_effect=OSError("disk full")):
            with patch.object(Path, "rename", fail_restore):
                result, error = self.run_import(replace=True)
        self.assertEqual(result, 1)
        self.assertIn("recovery files retained", error)
        stages = list(self.models.glob(".demo-import-*"))
        self.assertEqual(len(stages), 1)
        self.assertEqual((stages[0] / "previous" / "weights.bin").read_bytes(), b"valuable weights")
        self.assertEqual((stages[0] / "uncommitted" / "weights.bin").read_bytes(), b"new weights")
        self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
